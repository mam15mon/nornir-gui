from typing import List
import os
import logging
import pandas as pd
from datetime import datetime
from nornir.core.task import Task, Result
from nornir_netmiko.tasks import netmiko_send_command
from core.db.database import Database
from core.db.models import Settings
from core.utils.logger import log_operation, handle_error
from .base import BaseOperation

logger = logging.getLogger(__name__)

class DnatQuery(BaseOperation):
    """DNAT查询操作类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        
        # 获取基础路径
        with Database().get_session() as session:
            settings = session.query(Settings).first()
            self.base_path = settings.config_base_path if settings and settings.config_base_path else os.path.join(os.getcwd(), "配置文件")
            
        # 创建查询结果目录
        self.query_path = os.path.normpath(os.path.join(self.base_path, "DNAT查询"))
        os.makedirs(self.query_path, exist_ok=True)
    
    def query_dnat(self, task: Task) -> Result:
        """查询单个设备的DNAT配置"""
        if not self.is_running:
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )
            
        device = task.host
        device_name = device.name
        site = device.data.get('site', "未分类")
        
        try:
            # 更新状态为正在查询
            self.status_changed.emit(device_name, "正在查询...")
            logger.info(f"{device_name} - 开始DNAT查询，站点: {site}")
            
            # 根据设备类型选择模板
            template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
            if device.platform == "hp_comware":
                template_name = "h3c_display_nat_server.textfsm"
            else:
                template_name = "huawei_display_nat_server.textfsm"
                
            template_path = os.path.join(template_dir, template_name)
            
            # 检查模板是否存在
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"TextFSM 模板文件不存在: {template_path}")
                
            logger.debug(f"{device_name} - 使用TextFSM模板: {template_path}")
            
            # 执行 display nat server 命令
            logger.debug(f"{device_name} - 执行DNAT查询命令")
            result = task.run(
                task=netmiko_send_command,
                command_string="display nat server",
                use_textfsm=True,
                textfsm_template=template_path
            )
            
            logger.debug(f"{device_name} - 命令执行结果: {result}")
            
            # 检查命令输出
            if not result.result:
                logger.warning(f"{device_name} - 未查询到 NAT 配置")
                status = "无 NAT 配置"
                self.status_changed.emit(device_name, status)
                self.results[device_name] = {
                    'status': status,
                    'result': "未查询到 NAT 配置",
                    'output_file': None
                }
                return Result(
                    host=device,
                    result="未查询到 NAT 配置"
                )
                
            try:
                # 将解析结果转换为 DataFrame
                if isinstance(result.result, list):
                    logger.debug(f"{device_name} - 开始解析结果")
                    # 检查列表内容是否为字典
                    if len(result.result) > 0 and isinstance(result.result[0], dict):
                        df = pd.DataFrame(result.result)
                    else:
                        logger.warning("解析结果列表为空或元素不是字典")
                        status = "无有效数据"
                        self._handle_empty_result(device_name, status)
                        return
                else:
                    logger.warning(f"解析结果类型异常: {type(result.result)}")
                    status = "数据格式错误"
                    self._handle_empty_result(device_name, status)
                    return
                
                logger.debug(f"DataFrame 完整内容:\n{df}")
                
                # 重命名列以更好地显示在 Excel 中
                column_mapping = {
                    # H3C设备
                    'NAME': '规则名称',
                    'GLOBAL_IP': '外部IP',
                    'GLOBAL_START_PORT': '外部起始端口',
                    'GLOBAL_END_PORT': '外部结束端口',
                    'INSIDE_IP': '内部IP',
                    'INSIDE_START_PORT': '内部起始端口',
                    'INSIDE_END_PORT': '内部结束端口',
                    'PROTOCOL': '协议',
                    'INTERFACE': '接口',
                    # 华为设备
                    'name': '规则名称',
                    'id': '规则ID',
                    'global_ip': '外部IP',
                    'global_start_port': '外部起始端口',
                    'global_end_port': '外部结束端口',
                    'inside_ip': '内部IP',
                    'inside_start_port': '内部起始端口',
                    'inside_end_port': '内部结束端口',
                    'protocol': '协议'
                }
                
                # 记录重命名前的列名
                logger.debug(f"重命名前的列名: {df.columns.tolist()}")
                
                # 只重命名存在的列
                existing_columns = {}
                for old_col, new_col in column_mapping.items():
                    if old_col in df.columns:
                        existing_columns[old_col] = new_col
                    else:
                        logger.debug(f"列 {old_col} 不存在于结果中，跳过映射")
                
                df.rename(columns=existing_columns, inplace=True)
                logger.debug(f"重命名后的列名: {df.columns.tolist()}")
                
                # 替换 '---' 为更友好的显示
                df = df.replace(['---', ''], '任意')
                
                # 在协议处理前添加检查
                if '协议' not in df.columns and 'protocol' not in df.columns:
                    logger.warning("未找到协议字段，使用默认值")
                    df['协议'] = '任意'
                else:
                    # 统一协议字段名称
                    df['协议'] = df.get('protocol', df.get('协议', '任意'))
                
                # 在处理协议前添加：
                if device.platform not in ["hp_comware", "huawei"]:
                    logger.warning(f"未知设备平台: {device.platform}")
                    df['协议'] = df.get('协议', '未知协议')
                    return
                
                # 处理端口显示
                def process_ports(row):
                    try:
                        # 添加默认值处理
                        port_fields = [
                            '外部起始端口', '外部结束端口', 
                            '内部起始端口', '内部结束端口'
                        ]
                        
                        for field in port_fields:
                            if field not in row:
                                row[field] = '0'  # 设置默认值
                        
                        # 外部端口处理
                        start_port = str(row['外部起始端口']).split('(')[0]  # 提取括号前的数字
                        end_port = str(row['外部结束端口']).split('(')[0]   # 提取括号前的数字
                        
                        # H3C 设备的特殊处理
                        if device.platform == "hp_comware":
                            if start_port == '0':
                                row['外部端口'] = '任意'
                            elif not end_port or end_port == '任意':
                                row['外部端口'] = start_port
                            else:
                                row['外部端口'] = f"{start_port}-{end_port}"
                        else:
                            if start_port == end_port:
                                row['外部端口'] = start_port
                            else:
                                row['外部端口'] = f"{start_port}-{end_port}"
                        
                        # 内部端口处理
                        start_port = str(row['内部起始端口']).split('(')[0]  # 提取括号前的数字
                        end_port = str(row['内部结束端口']).split('(')[0]   # 提取括号前的数字
                        
                        # H3C 设备的特殊处理
                        if device.platform == "hp_comware":
                            if start_port == '0':
                                row['内部端口'] = '任意'
                            elif not end_port or end_port == '任意':
                                row['内部端口'] = start_port
                            else:
                                row['内部端口'] = f"{start_port}-{end_port}"
                        else:
                            if start_port == end_port:
                                row['内部端口'] = start_port
                            else:
                                row['内部端口'] = f"{start_port}-{end_port}"
                    except Exception as e:
                        logger.error(f"处理端口时出错: {str(e)}")
                        # 设置安全默认值
                        row['外部端口'] = 'N/A'
                        row['内部端口'] = 'N/A'
                    return row
                
                # 处理端口并创建新的端口列
                df = df.apply(process_ports, axis=1)
                
                # 调整列顺序，使用新的端口列
                if device.platform == "hp_comware":
                    # 删除旧的端口列
                    columns_to_drop = ['外部起始端口', '外部结束端口', '内部起始端口', '内部结束端口']
                    df = df.drop([col for col in columns_to_drop if col in df.columns], axis=1)
                    
                    # 设置最终的列顺序
                    column_order = ['接口', '规则名称', '协议', 
                                  '内部IP', '内部端口',
                                  '外部IP', '外部端口']
                else:
                    # 删除旧的端口列
                    columns_to_drop = ['外部起始端口', '外部结束端口', '内部起始端口', '内部结束端口']
                    df = df.drop([col for col in columns_to_drop if col in df.columns], axis=1)
                    
                    # 设置最终的列顺序
                    column_order = ['规则ID', '规则名称', '协议', 
                                  '内部IP', '内部端口',
                                  '外部IP', '外部端口']
                
                # 只选择存在的列
                existing_columns = [col for col in column_order if col in df.columns]
                df = df[existing_columns]
                
                # 创建站点目录
                site_path = os.path.normpath(os.path.join(self.query_path, site))
                os.makedirs(site_path, exist_ok=True)
                
                # 准备 Excel 文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"{device_name}_{timestamp}_dnat.xlsx"
                excel_file = os.path.normpath(os.path.join(site_path, file_name))
                
                # 写入 Excel 文件
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='DNAT配置', index=False)
                    
                    # 获取工作表对象
                    worksheet = writer.sheets['DNAT配置']
                    
                    # 调整列宽
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
                
                status = "成功: DNAT查询完成"
                logger.info(f"{device_name} - DNAT配置已保存到: {excel_file}")
                self.status_changed.emit(device_name, status)
                self.results[device_name] = {
                    'status': status,
                    'result': f"DNAT配置已保存到: {excel_file}",
                    'output_file': excel_file
                }
                
                return Result(
                    host=device,
                    result=f"设备 {device_name} DNAT查询成功"
                )
                
            except Exception as e:
                return Result(
                    host=device,
                    result=handle_error(logger, device_name, e, "DNAT数据处理")
                )
            
        except Exception as e:
            return Result(
                host=device,
                result=handle_error(logger, device_name, e, "DNAT查询")
            )
    
    @log_operation("DNAT查询")
    def start(self, devices: List[str]) -> None:
        """开始查询DNAT"""
        self.is_running = True
        self.results.clear()
        
        try:
            # 过滤无效设备
            valid_devices = [device for device in devices if self._validate_device(device)]
            if not valid_devices:
                logger.warning("没有有效的设备可以查询")
                return
            
            # 初始化nornir
            logger.info("初始化 nornir...")
            nr = self.nornir_mgr.init_nornir(valid_devices)
            if not nr:
                logger.error("nornir 初始化失败")
                return
            
            try:
                # 执行查询
                logger.info("开始执行查询任务...")
                nr.run(
                    name="DNAT查询",
                    task=self.query_dnat
                )
            except Exception as e:
                self.results = handle_error(logger, "全局", e, "DNAT查询")
        finally:
            self.is_running = False
            self.nornir_mgr.close()
            logger.info("查询操作完成")
            
    def _handle_empty_result(self, device_name: str, status: str):
        """处理空结果"""
        self.status_changed.emit(device_name, status)
        self.results[device_name] = {
            'status': status,
            'result': "未查询到有效DNAT配置",
            'output_file': None
        }
