import logging
import pandas as pd
from typing import List, Any
from PySide6.QtCore import QObject, Signal
from nornir_netmiko import netmiko_send_command
from nornir.core.task import Task, Result
from ..base.nornir_manager import NornirManager
import re
from core.utils.logger import log_operation, handle_error
from core.db.database import Database
from core.db.models import Settings
import os

logger = logging.getLogger(__name__)

def parse_trunk_ports(trunk_output: str, platform: str) -> dict:
    """解析trunk端口信息"""
    trunk_info = {}
    current_interface = None
    
    if platform == 'hp_comware':
        interface_pattern = r'^(\S+)\s+\d+\s+(.+)$'
        
        for line in trunk_output.splitlines():
            match = re.match(interface_pattern, line.strip())
            if match:
                interface, vlan_info = match.groups()
                trunk_info[interface] = vlan_info.strip()
                current_interface = interface
            elif line.strip().startswith(' ') and current_interface:  
                trunk_info[current_interface] += ' ' + line.strip()
    else:  # 华为设备
        interface_pattern = r'^(\S+)\s+trunk\s+\d+\s+(.+?)\s+\S'
        for line in trunk_output.splitlines():
            match = re.match(interface_pattern, line.strip())
            if match:
                interface, vlan_info = match.groups()
                trunk_info[interface] = vlan_info.strip()
                
    return trunk_info

def parse_lagg_members(lagg_output: str, platform: str) -> list:
    """解析链路聚合成员端口"""
    members = []
    
    if platform == 'hp_comware':
        # 找到Local部分
        in_local_section = False
        for line in lagg_output.splitlines():
            if 'Local:' in line:
                in_local_section = True
                continue
            if 'Remote:' in line:
                break
                
            if in_local_section and line.strip():
                # 跳过表头
                if 'Port' in line and 'Status' in line:
                    continue
                # 解析端口行
                fields = [f for f in line.split() if f]
                if fields and 'S' in line:  # 确保是Selected状态
                    port = fields[0].split('(')[0]  # 去掉(R)标记
                    members.append(port)
    else:  # 华为设备
        # 找到Local部分的成员端口
        in_local_section = False
        for line in lagg_output.splitlines():
            if 'Local:' in line:
                in_local_section = True
                continue
            if 'Partner:' in line:
                break
            
            if in_local_section and line.strip() and not '---' in line:
                # 跳过表头
                if 'ActorPortName' in line:
                    continue
                # 解析端口行
                fields = [f for f in line.split() if f]
                if len(fields) >= 2:
                    port = fields[0].split('(')[0]  # 去掉(r)或(hr)标记
                    if 'Selected' in line:  # 只添加Selected状态的端口
                        members.append(port)
    
    logger.debug(f"解析到的聚合口成员: {members}")
    return members

def parse_arp_output(arp_output: str, platform: str, ip_to_match: str = None) -> list:
    """解析ARP表输出，返回所有匹配的条目"""
    entries = []
    
    if platform == 'hp_comware':
        # H3C设备的ARP解析
        arp_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4})\s+(\d+)\s+(\S+)\s+\d+\s+\w'
        matches = re.finditer(arp_pattern, arp_output)
        for match in matches:
            ip, mac, vlan, interface = match.groups()
            if not ip_to_match or ip == ip_to_match:  # 只返回匹配的IP
                entries.append({
                    'ip': ip,
                    'mac': mac,
                    'vlan': vlan,
                    'interface': interface
                })
    else:  # 华为设备
        # 跳过表头
        lines = arp_output.splitlines()
        for line in lines:
            if not line.strip() or '-----------' in line:
                continue
            if any(header in line for header in ['ARP Entry Types', 'EXP', 'IP ADDRESS', 'Total']):
                continue
            
            fields = [f for f in line.split() if f]
            if len(fields) >= 5:
                try:
                    ip = fields[0]
                    mac = fields[1]
                    # 只返回匹配的IP的条目，或者如果是MAC查询则返回所有条目
                    if not ip_to_match or ip == ip_to_match:
                        entries.append({
                            'ip': ip,
                            'mac': mac,
                            'vlan': fields[3].split('/')[1] if '/' in fields[3] else fields[3],
                            'interface': fields[4]
                        })
                except Exception as e:
                    logger.debug(f"解析ARP行失败: {line}, 错误: {str(e)}")
                    continue
    
    return entries

def parse_mac_address(mac_output: str, platform: str) -> list:
    """解析MAC地址表输出"""
    results = []
    
    if platform == 'hp_comware':
        mac_pattern = r'([0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4})\s+(\d+)\s+\w+\s+(\S+)\s+\w'
        
        matches = re.finditer(mac_pattern, mac_output)
        for match in matches:
            mac, vlan, interface = match.groups()
            results.append({
                'mac': mac,
                'vlan': vlan,
                'interface': interface
            })
    else:  # 华为设备
        # 跳过表头和分隔线
        found_data_section = False  # 标记是否已经找到数据部分
        
        for line in mac_output.splitlines():
            # 找到数据部分的开始（第二个分隔线之后）
            if '---------------' in line:
                if not found_data_section:
                    found_data_section = True
                continue
                
            # 跳过表头和注释
            if not found_data_section or not line.strip():
                continue
            if 'Total items' in line:
                break
                
            # 解析MAC地址表项
            fields = [f for f in line.split() if f]
            if len(fields) >= 4 and '-' in fields[0]:  # 确保是MAC地址格式
                mac = fields[0]
                vlan = fields[1].split('/')[0]  # 从 '10/-' 获取 '10'
                interface = fields[2]
                
                results.append({
                    'mac': mac,
                    'vlan': vlan,
                    'interface': interface
                })
    
    return results

class MacIpQuery(QObject):
    """MAC-IP 查询操作类"""
    
    # 定义信号
    status_changed = Signal(str, str)  # (device_name, status)
    progress_updated = Signal(int, int)  # (current, total)
    operation_finished = Signal(bool)  # success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.nornir_mgr = NornirManager()
        self.results = {}  # 存储查询结果
        self.found_mac_addresses = set()  # 清除之前可能存在的MAC地址
        
        # 获取基础路径
        with Database().get_session() as session:
            settings = session.query(Settings).first()
            self.base_path = settings.config_base_path if settings and settings.config_base_path else os.path.join(os.getcwd(), "配置文件")
        
        # 创建查询结果目录
        self.query_path = os.path.normpath(os.path.join(self.base_path, "MAC-IP查询"))
        os.makedirs(self.query_path, exist_ok=True)
        
    @log_operation("MAC-IP查询")
    def start(self, devices: List[Any], mac_or_ip: str) -> None:
        """开始查询 MAC-IP 信息"""
        self.is_running = True
        self.results.clear()
        self.found_mac_addresses = set()
        
        try:
            # 过滤无效设备
            valid_devices = [device for device in devices if self._validate_device(device)]
            if not valid_devices:
                self.operation_finished.emit(False)
                return
            
            # 初始化nornir
            nr = self.nornir_mgr.init_nornir(valid_devices)
            if not nr:
                self.operation_finished.emit(False)
                return
            
            try:
                if not ':' in mac_or_ip and not '-' in mac_or_ip:  # IP地址查询
                    # 1. 先在所有设备上查询ARP
                    arp_results = nr.run(
                        name="ARP查询",
                        task=self.query_arp,
                        mac_or_ip=mac_or_ip
                    )
                    
                    # 保存所有设备的查询结果，但只显示找到的
                    for device_name, multi_result in arp_results.items():
                        self.status_changed.emit(device_name, "查询成功")
                        if "未在ARP表中找到对应条目" not in multi_result[0].result:
                            self.results[device_name] = {
                                'status': "成功: 查询成功",
                                'result': multi_result[0].result,
                                'output_file': None
                            }
                    
                    # 2. 如果找到了MAC地址，对每个MAC地址都进行查询
                    if self.found_mac_addresses:
                        for mac in self.found_mac_addresses:
                            mac_results = nr.run(
                                name="MAC查询",
                                task=self.query_mac,
                                mac=mac
                            )
                            
                            # 保存所有设备的查询结果，但只显示找到的
                            for device_name, multi_result in mac_results.items():
                                self.status_changed.emit(device_name, "查询成功")
                                if "未找到MAC地址表项" not in multi_result[0].result:
                                    # 如果设备已经有结果，追加新结果
                                    if device_name in self.results:
                                        self.results[device_name]['result'] += "\n" + multi_result[0].result
                                    else:
                                        self.results[device_name] = {
                                            'status': "成功: 查询成功",
                                            'result': multi_result[0].result,
                                            'output_file': None
                                        }
                else:  # MAC地址查询
                    # 直接在所有设备上查询MAC
                    mac_results = nr.run(
                        name="MAC查询",
                        task=self.query_mac,
                        mac=mac_or_ip
                    )
                    
                    # 保存所有设备的查询结果，但只显示找到的
                    for device_name, multi_result in mac_results.items():
                        self.status_changed.emit(device_name, "查询成功")  # 统一状态显示
                        if "未找到MAC地址表项" not in multi_result[0].result:
                            self.results[device_name] = {
                                'status': "成功: 查询成功",
                                'result': multi_result[0].result,
                                'output_file': None
                            }
                
                self.operation_finished.emit(True)
                
            except Exception as e:
                logger.error(f"MAC-IP查询出错: {str(e)}")
                self.operation_finished.emit(False)
        finally:
            self.is_running = False
            self.nornir_mgr.close()  # 确保关闭连接
            
    def stop(self):
        """停止MAC-IP查询"""
        self.is_running = False
        if self.nornir_mgr:
            self.nornir_mgr.close()
            
    def query_arp(self, task: Task, mac_or_ip: str) -> Result:
        """只查询ARP的任务"""
        try:
            name = task.host.name
            platform = task.host.platform
            
            self.status_changed.emit(name, "正在查询ARP...")
            
            if platform not in ['hp_comware', 'huawei', 'huawei_vrpv8', 'huawei_vrp']:
                raise Exception('暂不支持的platform平台')

            # 查询ARP表
            if platform == 'hp_comware':
                arp_cmd = f'display arp {mac_or_ip}'
            else:  # 华为设备
                arp_cmd = f'display arp | include {mac_or_ip}'
            
            logger.debug(f"执行ARP查询命令: {arp_cmd}")
            arp_result = task.run(
                task=netmiko_send_command,
                command_string=arp_cmd,
                severity_level=logging.DEBUG
            )
            
            # 传入要匹配的IP地址
            arp_entries = parse_arp_output(arp_result[0].result, platform, mac_or_ip)
            if not arp_entries:
                return Result(
                    host=task.host,
                    result=f"查询条件: IP地址 = {mac_or_ip}\n详细结果: 未在ARP表中找到对应条目",
                    failed=False
                )
            
            # 保存找到的MAC地址
            self.found_mac_addresses.add(arp_entries[0]['mac'])
            
            return Result(
                host=task.host,
                result=f"查询条件: IP地址 = {mac_or_ip}\n找到MAC地址: {arp_entries[0]['mac']}",
                failed=False
            )
            
        except Exception as e:
            error_msg = f"ARP查询失败: {str(e)}"
            logger.error(f"{name} - {error_msg}")
            self.status_changed.emit(name, "失败: " + error_msg)
            return Result(
                host=task.host,
                result=error_msg,
                failed=True
            )

    def query_mac(self, task: Task, mac: str) -> Result:
        """只查询MAC的任务"""
        try:
            name = task.host.name
            platform = task.host.platform
            
            self.status_changed.emit(name, "正在查询MAC...")
            
            if platform not in ['hp_comware', 'huawei', 'huawei_vrpv8', 'huawei_vrp']:
                raise Exception('暂不支持的platform平台')

            # 1. 获取trunk接口信息
            self.status_changed.emit(name, "正在获取Trunk信息...")
            if platform == 'hp_comware':
                trunk_cmd = 'display port trunk'
            else:  # 华为设备
                trunk_cmd = 'display port vlan'
            
            trunk_result = task.run(
                task=netmiko_send_command,
                command_string=trunk_cmd,
                severity_level=logging.DEBUG
            )
            trunk_info = parse_trunk_ports(trunk_result[0].result, platform)
            
            # 标准化MAC地址格式
            formatted_mac = mac.replace(':', '').replace('-', '')
            formatted_mac = '-'.join(formatted_mac[i:i+4] for i in range(0, len(formatted_mac), 4))
            
            # 2. 查询ARP表获取IP信息
            self.status_changed.emit(name, "正在查询ARP信息...")
            arp_cmd = f'display arp | include {formatted_mac}'
            logger.debug(f"执行ARP查询命令: {arp_cmd}")
            arp_result = task.run(
                task=netmiko_send_command,
                command_string=arp_cmd,
                severity_level=logging.DEBUG
            )
            
            # 解析ARP结果，获取所有匹配的IP
            ip_addresses = []
            if arp_result[0].result.strip():
                # 解析所有匹配的ARP条目
                arp_entries = parse_arp_output(arp_result[0].result, platform)
                if arp_entries:
                    ip_addresses = [entry['ip'] for entry in arp_entries]
            
            # 3. 查询MAC地址表
            self.status_changed.emit(name, "正在查询MAC地址表...")
            if platform == 'hp_comware':
                mac_cmd = f'display mac-address {formatted_mac}'
            else:  # 华为设备
                mac_cmd = f'display mac-address {formatted_mac}'  # 华为设备也是直接查询MAC地址
            
            logger.debug(f"执行MAC查询命令: {mac_cmd}")
            
            mac_result = task.run(
                task=netmiko_send_command,
                command_string=mac_cmd,
                severity_level=logging.DEBUG
            )
            
            logger.debug(f"MAC查询结果: {mac_result[0].result}")
            mac_entries = parse_mac_address(mac_result[0].result, platform)
            results = []
            
            for mac_entry in mac_entries:
                interface = mac_entry['interface']
                lagg_cmd = None  # 初始化变量
                
                # 如果是聚合口，获取成员端口信息
                if platform == 'hp_comware' and (interface.startswith('BAGG') or interface.startswith('Bridge-Aggregation')):
                    lagg_num = re.search(r'\d+', interface).group()
                    lagg_cmd = f'display link-aggregation verbose Bridge-Aggregation {lagg_num}'
                elif platform in ['huawei', 'huawei_vrpv8', 'huawei_vrp'] and interface.startswith('Eth-Trunk'):
                    lagg_num = re.search(r'\d+', interface).group()
                    lagg_cmd = f'display eth-trunk {lagg_num}'
                
                # 如果是聚合口，查询成员端口
                if lagg_cmd:  # 只有在是聚合口的情况下才执行查询
                    logger.debug(f"执行聚合口查询命令: {lagg_cmd}")
                    
                    lagg_result = task.run(
                        task=netmiko_send_command,
                        command_string=lagg_cmd,
                        severity_level=logging.DEBUG
                    )
                    
                    logger.debug(f"聚合口查询结果: {lagg_result[0].result}")
                    members = parse_lagg_members(lagg_result[0].result, platform)
                    
                    if members:
                        physical_ports = f"({', '.join(members)})"
                        interface = f"{interface}{physical_ports}"
                    else:
                        logger.warning(f"未能解析到聚合口 {interface} 的成员端口")

                # 判断接口类型
                port_type = 'trunk' if interface.split('(')[0] in trunk_info else 'access'
                
                # 如果有多个IP地址，为每个IP创建一个结果
                if ip_addresses:
                    for ip in ip_addresses:
                        results.append({
                            'mac': mac_entry['mac'],
                            'ip': ip,
                            'interface': interface,
                            'port_type': port_type,
                            'vlan': mac_entry['vlan']
                        })
                else:
                    # 没有IP地址时只添加一个结果
                    results.append({
                        'mac': mac_entry['mac'],
                        'ip': None,
                        'interface': interface,
                        'port_type': port_type,
                        'vlan': mac_entry['vlan']
                    })
            
            if results:
                # 使用pandas处理结果
                df = pd.DataFrame(results)
                # 去重，保留所有IP地址
                df = df.drop_duplicates(subset=['mac', 'ip', 'interface', 'vlan'])
                
                # 按设备分组整理结果
                output_lines = [
                    f"查询条件: MAC地址 = {formatted_mac}",
                    f"执行命令: {arp_cmd}, {mac_cmd}",
                    "详细结果:"
                ]
                
                # 如果有多个IP，只显示一次MAC和接口信息
                unique_interfaces = df[['mac', 'interface', 'port_type', 'vlan']].drop_duplicates()
                for _, row in unique_interfaces.iterrows():
                    # 获取这个MAC地址的所有IP
                    ip_addresses = df[df['mac'] == row['mac']]['ip'].dropna().tolist()
                    ip_str = ', '.join(ip_addresses) if ip_addresses else 'N/A'
                    
                    output_lines.extend([
                        f"MAC地址: {row['mac']}",
                        f"IP地址: {ip_str}",
                        f"接入接口: {row['interface']} ({row['port_type']})",
                        f"所属VLAN: {row['vlan']}"
                    ])
                
                self.status_changed.emit(name, "查询成功")
                return Result(
                    host=task.host,
                    result="\n".join(output_lines),
                    failed=False
                )
            
            return Result(
                host=task.host,
                result=f"查询条件: MAC地址 = {formatted_mac}\n详细结果: 未找到MAC地址表项",
                failed=False
            )
            
        except Exception as e:
            error_msg = f"查询失败: {str(e)}"
            logger.error(f"{name} - {error_msg}")
            self.status_changed.emit(name, f"失败: {str(e)}")
            return Result(
                host=task.host,
                result=error_msg,
                failed=True
            )
    
    def _validate_device(self, device) -> bool:
        """验证设备数据是否完整"""
        required_fields = ['name', 'hostname', 'username', 'password', 'device_type']
        return all(hasattr(device, field) and getattr(device, field) for field in required_fields)
    
    def get_results(self) -> dict:
        """获取查询结果"""
        return self.results
