from typing import List, Dict, Any
from PySide6.QtCore import QObject, Signal
import logging
from ..base.nornir_manager import NornirManager

logger = logging.getLogger(__name__)

class BaseOperation(QObject):
    """操作基类"""
    
    # 定义信号
    status_changed = Signal(str, str)  # (device_name, status)
    progress_updated = Signal(int, int)  # (current, total)
    operation_finished = Signal(bool)  # success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.nornir_mgr = NornirManager()
        self.results = {}  # 存储操作结果
        
    def _validate_device(self, device) -> bool:
        """验证设备数据是否完整"""
        required_fields = ['name', 'hostname', 'username', 'password']
        return all(hasattr(device, field) and getattr(device, field) for field in required_fields)
        
    def stop(self):
        """停止操作"""
        logger.info("停止操作")
        self.is_running = False
        if self.nornir_mgr:
            self.nornir_mgr.close()
            
    def get_results(self) -> Dict[str, Any]:
        """获取操作结果"""
        return self.results 