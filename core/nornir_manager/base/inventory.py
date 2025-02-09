import logging
from math import isnan
from typing import Any, Dict, List

from nornir.core.inventory import (
    Inventory,
    Host,
    Defaults,
    ConnectionOptions,
)

logger = logging.getLogger(__name__)

def _empty(x: Any) -> bool:
    """检查 x 是否为 NaN 或 None/空字符串"""
    return x is None or (isinstance(x, float) and isnan(x)) or x == ""

def _get_connection_options(data: Dict[str, Any]) -> Dict[str, ConnectionOptions]:
    """获取连接选项"""
    cp = {}
    for cn, c in data.items():
        cp[cn] = ConnectionOptions(
            hostname=c.get("hostname"),
            port=c.get("port"),
            username=c.get("username"),
            password=c.get("password"),
            platform=c.get("platform"),
            extras=c.get("extras"),
        )
    return cp

def _get_host_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """获取主机数据"""
    no_data_fields = ['name', 'hostname', 'port', 'username', 'password', 'platform']
    resp_data = {}
    netmiko_prefix = 'netmiko_'
    for k, v in data.items():
        if (k not in no_data_fields) and (netmiko_prefix not in k):
            resp_data[k] = v if not _empty(v) else None
    return resp_data

def _get_host_netmiko_options(data: Dict[str, Any]) -> Dict[str, Any]:
    """获取主机的 netmiko 选项"""
    netmiko_options = {
        'netmiko': {
            'extras': {}
        }
    }
    
    # 定义需要特殊处理的键
    option_mappings = {
        'netmiko_timeout': 'timeout',
        'netmiko_global_delay_factor': 'global_delay_factor',
        'netmiko_fast_cli': 'fast_cli'
    }
    
    # 处理所有 netmiko_ 开头的选项
    for key, value in data.items():
        if key in option_mappings:
            # 跳过空值
            if _empty(value):
                continue
                
            option_key = option_mappings[key]
            if option_key == 'timeout':
                netmiko_options['netmiko']['extras'][option_key] = int(value)
            elif option_key == 'fast_cli':
                netmiko_options['netmiko']['extras'][option_key] = str(value).lower() not in ['0', 'false', 'none']
            elif option_key == 'global_delay_factor':
                netmiko_options['netmiko']['extras'][option_key] = float(value)
    
    return _get_connection_options(netmiko_options) if netmiko_options['netmiko']['extras'] else {}

def _get_host_obj(data: Dict[str, Any]) -> Host:
    """创建主机对象
    
    Args:
        data: 设备数据字典
        
    Returns:
        Host: Nornir 主机对象
        
    Raises:
        ValueError: 当必要的字段为空时
    """
    # 必要字段检查和转换
    if _empty(data.get('name')):
        raise ValueError('主机名不能为空')
    if _empty(data.get('hostname')):
        raise ValueError('主机地址不能为空')
        
    # 确保名称使用正确的编码
    name = str(data['name']).encode('utf-8').decode('utf-8')
    hostname = str(data['hostname']).encode('utf-8').decode('utf-8')
    port = int(data['port']) if not _empty(data.get('port')) else 22
    username = str(data['username']) if not _empty(data.get('username')) else None
    password = str(data['password']) if not _empty(data.get('password')) else None
    platform = str(data['platform']) if not _empty(data.get('platform')) else None
    
    # 创建主机对象
    host = Host(
        name=name,
        hostname=hostname,
        port=port,
        username=username,
        password=password,
        platform=platform,
        data=_get_host_data(data),
        groups=None,
        defaults={},
        connection_options=_get_host_netmiko_options(data),
    )
    
    # 当需要写入文件时，确保使用 utf-8 编码
    filename = f"{name}_host_data.txt"
    content = f"Name: {name}\nHostname: {hostname}\nPort: {port}\nUsername: {username}\nPassword: {password}\nPlatform: {platform}\nData: {_get_host_data(data)}"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return host

class FlatDataInventory:
    """扁平数据清单插件"""
    
    def __init__(self, data: List = None, connection_options: Dict = None) -> None:
        """初始化
        
        Args:
            data: 设备列表（SQLAlchemy Host 对象列表）
            connection_options: 连接选项配置
        """
        self.data = data or []
        self.connection_options = connection_options or {
            "timeout": 10,
            "global_delay_factor": 1,
            "fast_cli": False
        }

    def load(self) -> Inventory:
        """加载清单"""
        hosts = {}
        groups = {}
        defaults = Defaults()

        for device in self.data:
            try:
                # 确保所有文本数据使用正确的编码
                device_name = device.name.encode('utf-8').decode('utf-8')
                hostname = device.hostname.encode('utf-8').decode('utf-8')
                platform = device.platform.encode('utf-8').decode('utf-8') if device.platform else None
                site = device.site.encode('utf-8').decode('utf-8') if device.site else None
                device_type = device.device_type.encode('utf-8').decode('utf-8') if device.device_type else None
                device_model = device.device_model.encode('utf-8').decode('utf-8') if device.device_model else None
                
                # 创建连接选项
                connection_options = {
                    "netmiko": ConnectionOptions(
                        platform=platform,
                        hostname=hostname,
                        username=device.username,
                        password=device.password,
                        port=device.port,
                        extras={
                            "timeout": self.connection_options["timeout"],
                            "global_delay_factor": self.connection_options["global_delay_factor"],
                            "fast_cli": self.connection_options["fast_cli"]
                        }
                    )
                }
                
                # 创建主机对象
                hosts[device_name] = Host(
                    name=device_name,
                    hostname=hostname,
                    platform=platform,
                    username=device.username,
                    password=device.password,
                    port=device.port,
                    connection_options=connection_options,
                    data={
                        'site': site,
                        'device_type': device_type,
                        'device_model': device_model
                    },
                    groups=[]
                )
            except Exception as e:
                logger.error(f"处理设备数据时出错: {str(e)}")
                continue

        return Inventory(hosts=hosts, groups=groups, defaults=defaults) 