from typing import List
import os
import logging
from datetime import datetime
import difflib
from nornir.core.task import Task, Result
from nornir_netmiko.tasks import netmiko_send_command
from core.db.database import Database
from core.db.models import Settings
from core.utils.logger import log_operation, handle_error
from .base import BaseOperation

logger = logging.getLogger(__name__)

class ConfigDiff(BaseOperation):
    """配置对比操作类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        
        # 获取基础路径
        with Database().get_session() as session:
            settings = session.query(Settings).first()
            self.base_path = settings.config_base_path if settings and settings.config_base_path else os.path.join(os.getcwd(), "配置文件")
            
        # 创建对比目录
        self.diff_path = os.path.normpath(os.path.join(self.base_path, "对比"))
        os.makedirs(self.diff_path, exist_ok=True)
    
    def diff_config(self, task: Task) -> Result:
        """单个设备的配置对比任务"""
        if not self.is_running:
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )

        device = task.host
        device_name = device.name
        site = device.data.get('site', "未分类")
        platform = device.platform
        
        try:
            # 更新状态为正在对比
            self.status_changed.emit(device_name, "正在对比...")
            logger.info(f"{device_name} - 开始配置对比，站点: {site}")
            
            # 根据平台类型选择命令
            if platform == 'hp_comware':
                saved_cmd = 'display saved-configuration'
                current_cmd = 'display current-configuration'
            elif platform in ['huawei', 'huawei_vrp', 'huawei_vrpv8']:
                saved_cmd = 'display saved-configuration'
                current_cmd = 'display current-configuration'
            else:
                raise ValueError(f"不支持的平台类型: {platform}")
            
            logger.debug(f"{device_name} - 获取保存的配置")
            saved_conf = task.run(
                task=netmiko_send_command,
                command_string=saved_cmd
            )
            
            logger.debug(f"{device_name} - 获取当前配置")
            curr_conf = task.run(
                task=netmiko_send_command,
                command_string=current_cmd
            )
            
            # 对比配置
            saved_list = saved_conf.result.splitlines(True)
            curr_list = curr_conf.result.splitlines(True)
            
            differ = difflib.Differ()
            diff = list(differ.compare(saved_list, curr_list))
            
            # 检查是否有差异
            has_diff = not all(line.startswith(' ') for line in diff)
            
            if has_diff:
                # 创建站点目录
                site_path = os.path.normpath(os.path.join(self.diff_path, site))
                os.makedirs(site_path, exist_ok=True)
                
                # 创建日期目录
                date_str = datetime.now().strftime("%Y%m%d")
                date_path = os.path.normpath(os.path.join(site_path, date_str))
                os.makedirs(date_path, exist_ok=True)
                
                # 生成文本格式的差异输出
                diff_content = []
                diff_content.append('设备配置差异报告')
                diff_content.append('=' * 50)
                diff_content.append(f'设备名称: {device_name}')
                diff_content.append(f'IP地址: {device.hostname}')
                diff_content.append(f'站点: {site}')
                diff_content.append(f'对比时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
                diff_content.append('=' * 50)
                diff_content.append('')
                
                for line in diff:
                    if line.startswith('-'):
                        diff_content.append(f'【删除-】{line[2:]}')
                    elif line.startswith('+'):
                        diff_content.append(f'【新增+】{line[2:]}')
                    elif not line.startswith('?'):  # 忽略 difflib 的提示行
                        diff_content.append(f'  {line[2:]}')
                
                # 保存差异文件
                time_str = datetime.now().strftime("%H%M%S")
                file_name = f"{device_name}_{device.hostname}_{time_str}.txt"
                diff_file = os.path.normpath(os.path.join(date_path, file_name))
                
                with open(diff_file, 'w', encoding='utf-8') as f:
                    f.write(''.join(diff_content))
                
                # 生成相对路径用于显示
                rel_path = os.path.relpath(diff_file, self.base_path)
                status = "成功: 发现配置差异"
                logger.info(f"{device_name} - 配置差异已保存到: {rel_path}")
                self.status_changed.emit(device_name, status)
                self.results[device_name] = {
                    'status': status,
                    'result': f"配置存在差异，已生成对比报告: {rel_path}",
                    'output_file': diff_file
                }
            else:
                status = "成功: 配置一致"
                logger.info(f"{device_name} - 配置一致，无需生成报告")
                self.status_changed.emit(device_name, status)
                self.results[device_name] = {
                    'status': status,
                    'result': "配置一致，无需生成报告",
                    'output_file': None
                }
            
            return Result(
                host=device,
                result=f"设备 {device_name} 配置对比完成",
                changed=has_diff
            )
            
        except Exception as e:
            return Result(
                host=device,
                result=handle_error(logger, device_name, e, "配置对比")
            )
    
    @log_operation("配置对比")
    def start(self, devices: List[str]) -> None:
        """开始对比配置"""
        self.is_running = True
        self.results.clear()
        
        try:
            # 过滤无效设备
            valid_devices = [device for device in devices if self._validate_device(device)]
            if not valid_devices:
                logger.warning("没有有效的设备可以对比")
                return
            
            # 初始化nornir
            logger.info("初始化 nornir...")
            nr = self.nornir_mgr.init_nornir(valid_devices)
            if not nr:
                logger.error("nornir 初始化失败")
                return
            
            try:
                # 执行对比
                logger.info("开始执行对比任务...")
                nr.run(
                    name="配置对比",
                    task=self.diff_config
                )
            except Exception as e:
                self.results = handle_error(logger, "全局", e, "配置对比")
        finally:
            self.is_running = False
            self.nornir_mgr.close()
            logger.info("对比操作完成") 