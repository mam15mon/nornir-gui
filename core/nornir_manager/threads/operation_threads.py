from .base import BaseOperationThread, BaseCommandThread, BaseMacIpThread
from ..operations.connection_test import ConnectionTest
from ..operations.config_backup import ConfigBackup
from ..operations.config_diff import ConfigDiff
from ..operations.config_save import ConfigSave
from ..operations.command_sender import CommandSender
from ..operations.dnat_query import DnatQuery
from ..operations.interface_query import InterfaceQuery
from core.nornir_manager.operations.mac_ip_query_new import MacIpQueryNew


class TestThread(BaseOperationThread):
    """连接测试线程"""
    def __init__(self, parent=None):
        super().__init__(ConnectionTest(), parent)


class BackupThread(BaseOperationThread):
    """配置备份线程"""
    def __init__(self, parent=None):
        super().__init__(ConfigBackup(), parent)


class DiffThread(BaseOperationThread):
    """配置对比线程"""
    def __init__(self, parent=None):
        super().__init__(ConfigDiff(), parent)


class SaveThread(BaseOperationThread):
    """配置保存线程"""
    def __init__(self, parent=None):
        super().__init__(ConfigSave(), parent)


class DnatThread(BaseOperationThread):
    """DNAT查询线程"""
    def __init__(self, parent=None):
        super().__init__(DnatQuery(), parent)


class InterfaceThread(BaseOperationThread):
    """接口查询线程"""
    def __init__(self, parent=None):
        super().__init__(InterfaceQuery(), parent)


class MacIpNewThread(BaseMacIpThread):
    """MAC-IP查询线程"""
    def __init__(self, parent=None):
        super().__init__(MacIpQueryNew(), parent)


class CommandThread(BaseCommandThread):
    """命令发送线程"""
    def __init__(self, parent=None):
        super().__init__(CommandSender(), parent) 