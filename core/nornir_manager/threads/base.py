from PySide6.QtCore import QThread, Signal
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
import logging


class BaseOperationThread(QThread):
    """基础操作线程类"""
    finished = Signal(dict, datetime)  # 发送结果和开始时间
    
    def __init__(self, operation_instance: Any, parent: Optional[QThread] = None):
        super().__init__(parent)
        self.operation = operation_instance
        self.devices: Optional[List[Any]] = None
        self.start_time: Optional[datetime] = None
        
    def setup(self, devices: List[Any], status_callback: Callable[[Dict[str, Any]], None]) -> None:
        """设置基本参数"""
        logging.info("设置线程参数")
        self.devices = devices
        # 连接状态更新信号
        self.operation.status_changed.connect(status_callback)
        self.start_time = datetime.now()
        logging.info(f"线程参数设置完成，设备数量: {len(devices)}")
        
    def run(self) -> None:
        """运行操作"""
        logging.info("线程开始运行")
        if self.devices:
            try:
                self._execute_operation()
                # 发送结果信号
                results = self.operation.get_results()
                logging.info(f"操作完成，结果: {results}")
                self.finished.emit(results, self.start_time)
            except Exception as e:
                logging.error(f"线程运行出错: {str(e)}")
                raise
        else:
            logging.warning("没有设备可执行操作")
            
    def _execute_operation(self) -> None:
        """执行具体操作，子类可以重写此方法"""
        logging.info("执行操作")
        if hasattr(self.operation, 'start'):
            self.operation.start(self.devices)
            logging.info("操作已启动")
        else:
            logging.warning("操作实例没有 start 方法")
            
    def stop(self) -> None:
        """停止操作"""
        logging.info("停止操作")
        if self.operation and hasattr(self.operation, 'stop'):
            self.operation.stop()
            logging.info("操作已停止")
        else:
            logging.warning("操作实例没有 stop 方法")
            
        # 确保关闭nornir连接
        if hasattr(self.operation, 'nornir_mgr'):
            self.operation.nornir_mgr.close()
            logging.info("Nornir连接已关闭")


class BaseMacIpThread(BaseOperationThread):
    """MAC-IP查询线程基类"""
    def __init__(self, operation_instance: Any, parent: Optional[QThread] = None):
        super().__init__(operation_instance, parent)
        self.mac_or_ip: Optional[str] = None
        
    def setup(self, devices: List[Any], status_callback: Callable[[Dict[str, Any]], None], mac_or_ip: str) -> None:
        """设置MAC-IP查询参数"""
        super().setup(devices, status_callback)
        self.mac_or_ip = mac_or_ip
        
    def _execute_operation(self) -> None:
        """执行MAC-IP查询操作"""
        if self.devices and self.mac_or_ip:
            self.operation.start(self.devices, self.mac_or_ip)


class BaseCommandThread(BaseOperationThread):
    """命令线程基类"""
    def __init__(self, operation_instance: Any, parent: Optional[QThread] = None):
        super().__init__(operation_instance, parent)
        self.command: Optional[str] = None
        self.mode: Optional[str] = None
        self.use_timing: Optional[bool] = None
        
    def setup(self, devices: List[Any], command: str, mode: str, use_timing: bool, 
             status_callback: Callable[[Dict[str, Any]], None]) -> None:
        """设置命令参数"""
        super().setup(devices, status_callback)
        self.command = command
        self.mode = mode
        self.use_timing = use_timing
        
    def _execute_operation(self) -> None:
        """执行命令操作"""
        if self.devices and self.command:
            self.operation.start_command(self.devices, self.command, self.mode, self.use_timing) 