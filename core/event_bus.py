from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    """全局事件总线"""
    
    # 定义信号
    device_list_changed = Signal()  # 设备列表变化信号
    settings_changed = Signal()  # 设置变化信号
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

# 创建全局实例
event_bus = EventBus() 