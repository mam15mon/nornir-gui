"""
事件总线单元测试
"""
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 重置事件总线单例
if 'core.event_bus' in sys.modules:
    del sys.modules['core.event_bus']

from core.event_bus import EventBus

@pytest.mark.unit
class TestEventBus:
    """事件总线测试类"""
    
    def setup_method(self):
        """每个测试方法前重置事件总线"""
        # 重置单例
        EventBus._instance = None
    
    def test_event_bus_singleton(self):
        """测试事件总线单例模式"""
        # 创建两个事件总线实例
        bus1 = EventBus()
        bus2 = EventBus()
        
        # 验证它们是同一个实例
        assert bus1 is bus2
    
    def test_device_list_changed_signal(self):
        """测试设备列表变化信号"""
        event_bus = EventBus()
        
        # 创建模拟回调函数
        callback = MagicMock()
        
        # 连接信号
        event_bus.device_list_changed.connect(callback)
        
        # 发射信号
        event_bus.device_list_changed.emit()
        
        # 验证回调函数被调用
        callback.assert_called_once()
    
    def test_settings_changed_signal(self):
        """测试设置变化信号"""
        event_bus = EventBus()
        
        # 创建模拟回调函数
        callback = MagicMock()
        
        # 连接信号
        event_bus.settings_changed.connect(callback)
        
        # 发射信号
        event_bus.settings_changed.emit()
        
        # 验证回调函数被调用
        callback.assert_called_once()
    
    def test_multiple_signal_connections(self):
        """测试多个信号连接"""
        event_bus = EventBus()
        
        # 创建多个模拟回调函数
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        # 连接多个回调到同一信号
        event_bus.device_list_changed.connect(callback1)
        event_bus.device_list_changed.connect(callback2)
        
        # 发射信号
        event_bus.device_list_changed.emit()
        
        # 验证所有回调函数都被调用
        callback1.assert_called_once()
        callback2.assert_called_once()
    
    def test_signal_disconnection(self):
        """测试信号断开连接"""
        event_bus = EventBus()
        
        # 创建模拟回调函数
        callback = MagicMock()
        
        # 连接信号
        event_bus.device_list_changed.connect(callback)
        
        # 断开连接
        event_bus.device_list_changed.disconnect(callback)
        
        # 发射信号
        event_bus.device_list_changed.emit()
        
        # 验证回调函数未被调用
        callback.assert_not_called()
    
    def test_different_signals(self):
        """测试不同信号"""
        event_bus = EventBus()
        
        # 创建模拟回调函数
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        # 连接不同信号
        event_bus.device_list_changed.connect(callback1)
        event_bus.settings_changed.connect(callback2)
        
        # 发射不同信号
        event_bus.device_list_changed.emit()
        event_bus.settings_changed.emit()
        
        # 验证回调函数被正确调用
        callback1.assert_called_once()
        callback2.assert_called_once()
    
    def test_signal_with_exception(self):
        """测试信号处理中的异常"""
        event_bus = EventBus()
        
        # 创建会抛出异常的回调函数
        def failing_callback():
            raise Exception("Test exception")
        
        # 创建正常的回调函数
        normal_callback = MagicMock()
        
        # 连接回调函数
        event_bus.device_list_changed.connect(failing_callback)
        event_bus.device_list_changed.connect(normal_callback)
        
        # 发射信号
        event_bus.device_list_changed.emit()
        
        # 验证正常回调函数仍被调用
        normal_callback.assert_called_once()
    
    def test_disconnect_nonexistent(self):
        """测试断开不存在的连接"""
        event_bus = EventBus()
        
        # 创建模拟回调函数
        callback = MagicMock()
        
        # 尝试断开不存在的连接
        # 这应该不会抛出异常
        event_bus.device_list_changed.disconnect(callback)
        
        # 验证没有异常发生
        assert True
    
    def test_signal_count(self):
        """测试信号连接计数"""
        event_bus = EventBus()
        
        # 创建模拟回调函数
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        # 连接多个回调
        event_bus.device_list_changed.connect(callback1)
        event_bus.device_list_changed.connect(callback2)
        
        # 检查接收者数量（Qt的receivers方法）
        receiver_count = event_bus.device_list_changed.receivers()
        assert receiver_count >= 2  # Qt内部可能有额外的接收者
    
    def test_global_instance(self):
        """测试全局实例"""
        # 导入全局实例
        from core.event_bus import event_bus
        
        # 验证全局实例是EventBus类型
        assert isinstance(event_bus, EventBus)
        
        # 验证全局实例与创建的实例是同一个
        new_instance = EventBus()
        assert event_bus is new_instance