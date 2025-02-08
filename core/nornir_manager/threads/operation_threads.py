from .base import BaseOperationThread, BaseCommandThread, BaseMacIpThread
from ..operations.connection_test import ConnectionTest
from ..operations.config_backup import ConfigBackup
from ..operations.config_diff import ConfigDiff
from ..operations.config_save import ConfigSave
from ..operations.command_sender import CommandSender
from ..operations.dnat_query import DnatQuery
from ..operations.interface_query import InterfaceQuery
from ..operations.mac_ip_query import MacIpQuery


class TestThread(BaseOperationThread):
    """连接测试线程"""
    def __init__(self, parent=None):
        super().__init__(ConnectionTest(), parent)
        
    def stop(self):
        """停止测试操作"""
        if self.operation:
            self.operation.stop()
        super().stop()


class BackupThread(BaseOperationThread):
    """配置备份线程"""
    def __init__(self, parent=None):
        super().__init__(ConfigBackup(), parent)
        
    def stop(self):
        """停止备份"""
        if self.operation:
            self.operation.stop()
        super().stop()


class DiffThread(BaseOperationThread):
    """配置对比线程"""
    def __init__(self, parent=None):
        super().__init__(ConfigDiff(), parent)
        
    def stop(self):
        """停止对比"""
        if self.operation:
            self.operation.stop()
        super().stop()


class SaveThread(BaseOperationThread):
    """配置保存线程"""
    def __init__(self, parent=None):
        super().__init__(ConfigSave(), parent)
        
    def stop(self):
        """停止保存"""
        if self.operation:
            self.operation.stop()
        super().stop()


class DnatThread(BaseOperationThread):
    """DNAT查询线程"""
    def __init__(self, parent=None):
        super().__init__(DnatQuery(), parent)
        
    def stop(self):
        """停止查询"""
        if self.operation:
            self.operation.stop()
        super().stop()


class InterfaceThread(BaseOperationThread):
    """接口查询线程"""
    def __init__(self, parent=None):
        super().__init__(InterfaceQuery(), parent)
            
    def stop(self):
        """停止查询"""
        if self.operation:
            self.operation.stop()
        super().stop()


class MacIpThread(BaseMacIpThread):
    """MAC-IP查询线程"""
    def __init__(self, parent=None):
        super().__init__(MacIpQuery(), parent)
            
    def stop(self):
        """停止查询"""
        if self.operation:
            self.operation.stop()
        super().stop()


class CommandThread(BaseCommandThread):
    """命令发送线程"""
    def __init__(self, parent=None):
        super().__init__(CommandSender(), parent)
        
    def stop(self):
        """停止命令执行"""
        if self.operation:
            self.operation.stop()
        super().stop() 