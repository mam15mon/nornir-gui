from typing import List
import logging
from PySide6.QtCore import QObject, Signal
from nornir.core.task import Task, Result
from nornir_netmiko.tasks import netmiko_save_config
from ..base.nornir_manager import NornirManager
from core.utils.logger import log_operation, handle_error

logger = logging.getLogger(__name__)

class ConfigSave(QObject):
    """配置保存操作类"""
    
    # 定义信号
    status_changed = Signal(str, str)  # (device_name, status)
    progress_updated = Signal(int, int)  # (current, total)
    operation_finished = Signal(bool)  # success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.nornir_mgr = NornirManager()
        self.results = {}  # 存储保存结果
    
    def save_config(self, task: Task) -> Result:
        """保存单个设备的配置"""
        if not self.is_running:
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )
            
        device = task.host
        device_name = device.name
        
        logger.info(f"{device_name} - 开始保存配置")
        
        try:
            # 更新状态为正在保存
            self.status_changed.emit(device_name, "正在保存...")
            
            # 执行保存命令
            logger.debug(f"{device_name} - 执行配置保存命令")
            result = task.run(
                task=netmiko_save_config,
            )
            
            status = "成功: 配置已保存"
            logger.info(f"{device_name} - 配置已保存")
            self.status_changed.emit(device_name, status)
            self.results[device_name] = {
                'status': status,
                'result': "配置已保存到启动配置",
                'output_file': None
            }
            
            return Result(
                host=device,
                result=f"设备 {device_name} 配置保存成功"
            )
            
        except Exception as e:
            return Result(
                host=device,
                result=handle_error(logger, device_name, e, "配置保存")
            )
    
    def _validate_device(self, device) -> bool:
        """验证设备数据是否完整"""
        required_fields = ['name', 'hostname', 'username', 'password']
        return all(hasattr(device, field) and getattr(device, field) for field in required_fields)
    
    @log_operation("配置保存")
    def start(self, devices: List[str]) -> None:
        """开始保存配置"""
        self.is_running = True
        self.results.clear()
        
        try:
            # 过滤无效设备
            valid_devices = [device for device in devices if self._validate_device(device)]
            if not valid_devices:
                logger.warning("没有有效的设备可以保存配置")
                return
            
            # 初始化nornir
            logger.info("初始化 nornir...")
            nr = self.nornir_mgr.init_nornir(valid_devices)
            if not nr:
                logger.error("nornir 初始化失败")
                return
            
            try:
                # 执行保存
                logger.info("开始执行保存任务...")
                nr.run(
                    name="保存配置",
                    task=self.save_config
                )
            except Exception as e:
                self.results = handle_error(logger, "全局", e, "配置保存")
        finally:
            self.is_running = False
            self.nornir_mgr.close()
            logger.info("保存操作完成")
            
    def stop(self):
        """停止保存"""
        logger.info("停止保存操作")
        self.is_running = False
        if self.nornir_mgr:
            self.nornir_mgr.close()
    
    def get_results(self) -> dict:
        """获取保存结果"""
        return self.results 