import os
import logging
import pandas as pd
from natsort import natsorted, ns
from typing import List, Any, Dict, Tuple
from datetime import datetime
from nornir_netmiko.tasks import netmiko_send_command
from nornir.core.task import Task, Result
from core.db.database import Database
from core.utils.logger import log_operation, handle_error
from .base import BaseOperation

logger = logging.getLogger(__name__)

# 常量定义
INTERFACE_SPEED_MAPPING = {
    'XGigabitEthernet': '10G',
    'Ten-GigabitEthernet': '10G',
    'XGE': '10G',
    '10GE': '10G',
    'Twenty-FiveGigE': '25G',
    '25GE': '25G',
    'FortyGigE': '40G',
    '40GE': '40G',
    'FGE': '40G',
    'HGE': '100G',
    'HundredGigE': '100G',
    '100GE': '100G',
    'TwoHundredGigE': '200G',
    '200GE': '200G',
    'FourHundredGigE': '400G',
    '400GE': '400G',
    'GigabitEthernet': '1G',
    'GE': '1G'
}

SPEED_ORDER = ['1G', '10G', '25G', '40G', '100G', '200G', '400G']

# 辅助函数
def get_interface_speed(interface_name: str) -> str:
    """获取接口速率"""
    if not isinstance(interface_name, str):
        return 'unknown'
    interface_name_upper = interface_name.upper()
    for pattern, speed in INTERFACE_SPEED_MAPPING.items():
        if pattern.upper() in interface_name_upper:
            return speed
    return 'unknown'

def get_column_mapping(platform: str) -> Dict[str, str]:
    """根据平台返回列映射"""
    if platform == "hp_comware":
        return {
            'INTERFACE': '接口',
            'LINK': '链路状态',  # H3C设备直接使用LINK字段作为链路状态
            'SPEED': '速率',
            'DUPLEX': '双工模式',
            'TYPE': '类型',
            'PVID': 'PVID',
            'DESCRIPTION': '描述'
        }
    return {
        'INTERFACE': '接口',
        'PHY_STATUS': '物理状态',
        'PROTOCOL_STATUS': '协议状态',
        'INBOUND_RATE': '入带宽利用率',
        'OUTBOUND_RATE': '出带宽利用率',
        'IN_ERRORS': '入错误包',
        'OUT_ERRORS': '出错误包'
    }

def adjust_column_width(worksheet) -> None:
    """调整工作表列宽"""
    for column in worksheet.columns:
        max_length = 0
        column = [cell for cell in column]
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

def write_excel_report(file_path: str, summary_df: pd.DataFrame, device_results: Dict) -> None:
    """写入Excel报告"""
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        # 按设备名称排序
        summary_df = summary_df.sort_values('设备名称', ignore_index=True)
        if '合计' in summary_df['设备名称'].values:
            # 提取合计行
            total_row = summary_df[summary_df['设备名称'] == '合计']
            # 删除原合计行
            summary_df = summary_df[summary_df['设备名称'] != '合计']
            # 重新添加到末尾
            summary_df = pd.concat([summary_df, total_row], ignore_index=True)
        
        # 写入汇总表
        summary_df.to_excel(writer, sheet_name='汇总', index=False)
        
        # 写入设备详细信息（按设备名称排序）
        sorted_devices = sorted(device_results.keys())
        for device_name in sorted_devices:
            result = device_results[device_name]
            if 'df' in result and isinstance(result['df'], pd.DataFrame):
                result['df'].to_excel(writer, sheet_name=device_name, index=False)
        
        # 调整列宽
        for sheet_name in writer.sheets:
            adjust_column_width(writer.sheets[sheet_name])
            
        # 冻结首行
        for sheet_name in writer.sheets:
            writer.sheets[sheet_name].freeze_panes = 'A2'

def interface_sort_key(interface_name: str) -> Tuple[int, int, int]:
    """接口排序键函数"""
    try:
        # 提取数字部分
        parts = interface_name.split('/')
        if len(parts) != 3:
            return (999, 999, 999)
            
        # 提取槽位和端口号
        slot = int(parts[1])
        port = int(parts[2])
        
        # 提取槽位前的数字（例如从"10GE1"中提取1）
        type_num = int(''.join(filter(str.isdigit, parts[0].split('GE')[1]))) if 'GE' in parts[0] else 999
        
        return (type_num, slot, port)
    except:
        return (999, 999, 999)

class InterfaceQuery(BaseOperation):
    """接口查询操作类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()

        # 使用统一的路径获取方法
        from core.config.path_utils import get_archive_subdir_path
        self.output_path = get_archive_subdir_path("接口查询", self.db)

    def _process_device_data(self, device_name: str, device, result: Result) -> pd.DataFrame:
        """处理设备数据并返回DataFrame"""
        try:
            # 将解析结果转换为DataFrame
            if isinstance(result.result, list):
                df = pd.DataFrame(result.result)
            else:
                df = pd.DataFrame([result.result])
                
            df.columns = df.columns.str.upper()
            # 去重：优先保留桥接模式中的同名接口记录
            if 'INTERFACE' in df.columns:
                df = df.drop_duplicates(subset=['INTERFACE'], keep='last')
            # 对DataFrame按接口名称自然排序
            df['INTERFACE'] = pd.Categorical(
                df['INTERFACE'],
                categories=natsorted(df['INTERFACE'].unique(), alg=ns.IGNORECASE),
                ordered=True
            )
            df = df.sort_values('INTERFACE')
            
            # 获取列映射并重命名列
            column_mapping = get_column_mapping(device.platform)
            existing_columns = {old: new for old, new in column_mapping.items() if old in df.columns}
            df.rename(columns=existing_columns, inplace=True)
            df = df.replace(['---', ''], '无')
            
            return df
            
        except Exception as e:
            self.results[device_name] = handle_error(device_name, e, "转换为 DataFrame 失败")
            raise

    def _generate_speed_summary(self, device_results: Dict) -> pd.DataFrame:
        """生成速率汇总表"""
        summary_data = []
        total_up = {speed: 0 for speed in SPEED_ORDER}
        total_count = {speed: 0 for speed in SPEED_ORDER}
        
        for device_name, result in device_results.items():
            if 'df' not in result or not isinstance(result['df'], pd.DataFrame):
                continue
                
            df = result['df']
            device = next((d for d in self.nornir_mgr.nr.inventory.hosts.values() if d.name == device_name), None)
            if not device:
                continue

            # 计算每种速率的接口总数和UP数量
            row_data = {'设备名称': device_name}
            for speed in SPEED_ORDER:
                # 从接口名称中提取速率信息
                speed_df = df[df['接口'].apply(lambda x: get_interface_speed(x) == speed)]
                total = len(speed_df)
                
                # 根据设备类型判断接口状态
                if device.platform == "hp_comware":
                    up_count = len(speed_df[speed_df['链路状态'].str.lower() == 'up'])
                else:
                    up_count = len(speed_df[speed_df['物理状态'].str.lower() == 'up'])
                
                row_data[speed] = f"{up_count}/{total}" if total > 0 else "0/0"
                
                # 累加总计
                total_up[speed] += up_count
                total_count[speed] += total
            
            summary_data.append(row_data)
        
        # 创建汇总DataFrame
        if not summary_data:
            return pd.DataFrame(columns=['设备名称'] + SPEED_ORDER)
            
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.reindex(columns=['设备名称'] + SPEED_ORDER)
        
        # 添加合计行
        summary_df.loc['合计'] = ['合计'] + [f"{total_up[speed]}/{total_count[speed]}" for speed in SPEED_ORDER]
        
        return summary_df

    def query_interface(self, task: Task) -> Result:
        """查询单个设备的接口信息"""
        if not self.is_running:
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )

        device = task.host
        device_name = device.name
        
        try:
            # 更新状态为正在查询
            self.status_changed.emit(device_name, "正在查询...")
            logger.info(f"{device_name} - 开始接口查询")
            
            # 根据设备类型选择模板
            template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
            if device.platform == "hp_comware":
                template_name = os.path.join("hp_comware", "h3c_display_interface_brief.textfsm")
            else:
                # 默认使用huawei_vrp的模板
                template_name = os.path.join("huawei_vrp", "huawei_display_interface_brief.textfsm")
                
            template_path = os.path.join(template_dir, template_name)
            logger.debug(f"{device_name} - 使用模板: {template_path}")
            
            # 检查模板是否存在
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"TextFSM 模板文件不存在: {template_path}")
            
            # 执行命令获取原始输出
            logger.debug(f"{device_name} - 执行接口查询命令")
            command_result = task.run(
                task=netmiko_send_command,
                command_string="display interface brief",
                use_textfsm=False
            )
            
            # 记录原始输出
            raw_output = command_result.result
            logger.debug(f"{device_name} - 原始输出:\n{raw_output}")
            
            # 尝试解析
            try:
                from textfsm import TextFSM
                from io import StringIO
                
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                logger.debug(f"{device_name} - 使用的模板内容:\n{template_content}")
                
                template = TextFSM(StringIO(template_content))
                parsed_result = template.ParseText(raw_output)
                
                if not parsed_result:
                    logger.warning(f"{device_name} - 解析结果为空")
                    raise Exception("解析结果为空")
                    
                result = [dict(zip(template.header, row)) for row in parsed_result]
                logger.debug(f"{device_name} - 解析结果:\n{result}")
                
            except Exception as parse_error:
                logger.error(f"{device_name} - TextFSM解析失败: {str(parse_error)}")
                raise Exception(f"TextFSM解析失败: {str(parse_error)}")
            
            # 检查命令输出
            if not result:
                logger.warning(f"{device_name} - 未查询到接口信息")
                status = "失败: 无接口信息"
                self.status_changed.emit(device_name, status)
                self.results[device_name] = {
                    'status': status,
                    'result': "未查询到接口信息",
                    'output_file': None
                }
                return Result(
                    host=device,
                    result="未查询到接口信息"
                )
            
            # 处理结果
            df = self._process_device_data(device_name, device, Result(host=device, result=result))
            
            status = "成功: 接口查询完成"
            logger.info(f"{device_name} - 接口查询完成")
            self.status_changed.emit(device_name, status)
            
            self.results[device_name] = {
                'status': status,
                'result': result,
                'df': df,
                'output_file': None
            }
            
            return Result(
                host=device,
                result=f"设备 {device_name} 接口查询成功"
            )
            
        except Exception as e:
            return Result(
                host=device,
                result=handle_error(logger, device_name, e, "接口查询")
            )

    @log_operation("接口查询")
    def start(self, devices: List[Any]) -> None:
        """开始查询所有设备接口信息"""
        self.is_running = True
        self.results.clear()
        
        try:
            # 初始化 nornir
            logger.info("初始化 nornir...")
            nr = self.nornir_mgr.init_nornir(devices)
            if not nr:
                logger.error("nornir 初始化失败")
                self.operation_finished.emit(False)
                return
                
            # 执行查询
            logger.info("开始执行接口查询任务...")
            result = nr.run(
                task=self.query_interface,
                name="查询接口信息"
            )
            
            # 获取基础路径并生成报告
            logger.info("生成接口状态报告...")
            # 使用配置管理器获取存档基础路径
            from core.config.path_utils import get_archive_base_path
            base_path = get_archive_base_path(self.db)
            output_dir = os.path.normpath(os.path.join(base_path, "接口查询"))
            
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"接口状态查询_{timestamp}.xlsx"
            excel_file = os.path.normpath(os.path.join(output_dir, file_name))
            
            # 生成汇总表并写入Excel
            summary_df = self._generate_speed_summary(self.results)
            write_excel_report(excel_file, summary_df, self.results)
            
            # 更新结果文件路径
            for device_name in self.results:
                if 'df' in self.results[device_name]:
                    self.results[device_name]['output_file'] = excel_file
                    self.results[device_name]['result'] = f"接口状态已保存到: {excel_file}"
            
            logger.info(f"接口状态报告已保存到: {excel_file}")
            self.operation_finished.emit(True)
            
        except Exception as e:
            self.results = handle_error(logger, "全局", e, "接口查询")
            self.operation_finished.emit(False)
        finally:
            self.is_running = False
            self.nornir_mgr.close()
            logger.info("接口查询操作完成")
            
