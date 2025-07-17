from .base import BaseOperationThread, BaseCommandThread, BaseMacIpThread
from ..operations.connection_test import ConnectionTest
from ..operations.config_backup import ConfigBackup
from ..operations.config_diff import ConfigDiff
from ..operations.config_save import ConfigSave
from ..operations.command_sender import CommandSender
from ..operations.dnat_query import DnatQuery
from ..operations.interface_query import InterfaceQuery
from ..operations.device_inspection import DeviceInspection
from core.nornir_manager.operations.mac_ip_query import MacIpQueryNew
from ..operations.firewall_address_group import FirewallAddressGroupOperation


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


class DeviceInspectionThread(BaseOperationThread):
    """设备巡检线程"""
    def __init__(self, parent=None):
        super().__init__(DeviceInspection(), parent)


class FirewallAddressGroupThread(BaseOperationThread):
    """防火墙地址组管理线程"""
    def __init__(self, parent=None):
        super().__init__(FirewallAddressGroupOperation(), parent)
        self.operation_type = None
        self.ip_addresses = None
        self.group_name = None

    def setup(self, devices, operation_type, ip_addresses, group_name=None, status_callback=None):
        """设置防火墙地址组操作参数"""
        super().setup(devices, status_callback)
        self.operation_type = operation_type
        self.ip_addresses = ip_addresses
        self.group_name = group_name

    def _execute_operation(self):
        """执行防火墙地址组操作"""
        if hasattr(self.operation, 'start'):
            self.operation.start(
                self.devices,
                self.operation_type,
                self.ip_addresses,
                self.group_name
            )