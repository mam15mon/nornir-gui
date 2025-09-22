from typing import List
import os
import logging
from datetime import datetime
from nornir.core.task import Task, Result
from nornir_netmiko.tasks import netmiko_send_command
from core.db.database import Database

from core.utils.logger import log_operation, handle_error
from .base import BaseOperation

logger = logging.getLogger(__name__)

class ConfigBackup(BaseOperation):
    """配置备份操作类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()

        # 使用统一的路径获取方法
        from core.config.path_utils import get_archive_base_path, get_archive_subdir_path
        self.base_path = get_archive_base_path(self.db)
        self.backup_path = get_archive_subdir_path("备份", self.db)
    
    def backup_config(self, task: Task) -> Result:
        """备份单个设备的配置"""
        if not self.is_running:
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )
            
        device = task.host
        device_name = device.name
        site = device.data.get('site', "未分类")
        
        logger.info(f"{device_name} - 开始备份配置，站点: {site}")
        
        try:
            # 更新状态为正在备份
            self.status_changed.emit(device_name, "正在备份...")
            
            # 执行备份命令
            logger.debug(f"{device_name} - 执行配置备份命令")
            result = task.run(
                task=netmiko_send_command,
                command_string="display current-configuration"
            )
            
            # 检查任务结果
            if result.failed:
                # 从结果中提取原始异常
                error = result[0].exception
                error_msg = str(error)
                
                if isinstance(error, Exception):
                    if "NetmikoTimeoutException" in str(type(error)):
                        error_msg = "设备不可达，请检查: 1.IP地址是否正确 2.端口是否正确 3.是否有防火墙限制"
                    elif "AuthenticationException" in str(type(error)):
                        error_msg = "认证失败，请检查用户名和密码"
                    elif "socket.error" in str(type(error)) or "Connection closed" in str(error):
                        error_msg = "连接异常断开，请检查网络连接"
                
                status = f"失败: {error_msg}"
                self.status_changed.emit(device_name, status)
                self.results[device_name] = {
                    'status': status,
                    'result': error_msg,
                    'output_file': None
                }
                return Result(
                    host=device,
                    result=error_msg,
                    failed=True
                )
            
            # 创建备份目录
            timestamp = datetime.now().strftime("%Y%m%d")
            backup_dir = os.path.normpath(os.path.join(self.base_path, "备份", site, timestamp))
            os.makedirs(backup_dir, exist_ok=True)
            
            # 保存配置文件
            timestamp = datetime.now().strftime("%H%M%S")
            file_name = f"{device_name}_{device.hostname}_{timestamp}.txt"
            backup_file = os.path.normpath(os.path.join(backup_dir, file_name))
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(result[0].result)
            
            status = "成功: 配置已备份"
            logger.info(f"{device_name} - 配置已备份到: {backup_file}")
            self.status_changed.emit(device_name, status)
            self.results[device_name] = {
                'status': status,
                'result': f"配置已备份到: {backup_file}",
                'output_file': backup_file
            }
            
            return Result(
                host=device,
                result=f"设备 {device_name} 配置备份成功"
            )
            
        except Exception as e:
            error_msg = str(e)
            if "NetmikoTimeoutException" in str(type(e)):
                error_msg = "设备不可达，请检查: 1.IP地址是否正确 2.端口是否正确 3.是否有防火墙限制"
            elif "AuthenticationException" in str(type(e)):
                error_msg = "认证失败，请检查用户名和密码"
            elif "socket.error" in str(type(e)) or "Connection closed" in str(e):
                error_msg = "连接异常断开，请检查网络连接"
            
            status = f"失败: {error_msg}"
            self.status_changed.emit(device_name, status)
            self.results[device_name] = {
                'status': status,
                'result': error_msg,
                'output_file': None
            }
            
            return Result(
                host=device,
                result=error_msg,
                failed=True
            )
    
    @log_operation("配置备份")
    def start(self, devices: List[str]) -> None:
        """开始备份配置"""
        self.is_running = True
        self.results.clear()
        
        try:
            # 过滤无效设备
            valid_devices = [device for device in devices if self._validate_device(device)]
            if not valid_devices:
                logger.warning("没有有效的设备可以备份")
                return
            
            # 初始化nornir
            logger.info("初始化 nornir...")
            nr = self.nornir_mgr.init_nornir(valid_devices)
            if not nr:
                logger.error("nornir 初始化失败")
                return
            
            try:
                # 执行备份
                logger.info("开始执行备份任务...")
                nr.run(
                    name="配置备份",
                    task=self.backup_config
                )
            except Exception as e:
                self.results = handle_error(logger, "全局", e, "配置备份")
        finally:
            self.is_running = False
            self.nornir_mgr.close()
            logger.info("备份操作完成") 