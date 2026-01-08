import logging
import pandas as pd
from typing import List, Any, Dict
from nornir_netmiko import netmiko_send_command
from nornir.core.task import Task, Result
import os
import re
from textfsm import TextFSM
from io import StringIO
from core.utils.logger import log_operation, handle_error
from .base import BaseOperation

logger = logging.getLogger(__name__)

class MacIpQueryNew(BaseOperation):
    """MAC-IP 查询操作类 - 使用TextFSM解析"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.found_mac_addresses = set()
        self.trunk_info = {}  # 存储trunk端口信息
        self.lagg_info = {}   # 存储聚合口信息

        # 命令映射
        self.commands = {
            'huawei_vrp': {
                'arp': 'display arp all',
                'mac': 'display mac-address',
                'trunk': 'display port vlan',
                'lagg': 'display eth-trunk'
            },
            'huawei_vrpv8': {
                'arp': 'display arp',
                'mac': 'display mac-address',
                'trunk': 'display port vlan',
                'lagg': 'display eth-trunk'
            },
            'hp_comware': {
                'arp': 'display arp',
                'mac': 'display mac-address',
                'trunk': 'display port trunk',
                'lagg': 'display link-aggregation verbose Bridge-Aggregation'
            }
        }
        
        # 字段名映射
        self.field_maps = {
            'huawei_vrp': {
                'mac_address': ['DESTINATION_ADDRESS', 'MAC_ADDRESS'],
                'interface': ['DESTINATION_PORT', 'INTERFACE'],
                'vlan': ['VLAN_ID']
            },
            'huawei_vrpv8': {
                'mac_address': ['DESTINATION_ADDRESS', 'MAC_ADDRESS'],
                'interface': ['DESTINATION_PORT', 'INTERFACE'],
                'vlan': ['VLAN_ID']
            },
            'hp_comware': {
                'mac_address': ['MAC_ADDRESS'],
                'interface': ['INTERFACE'],
                'vlan': ['VLAN_ID']
            }
        }

    def _handle_empty_result(self, device_name: str, status: str, message: str = None):
        """处理空结果"""
        self.status_changed.emit(device_name, status)
        self.results[device_name] = {
            'status': status,
            'result': message or "未找到匹配记录",
            'output_file': None
        }

    @log_operation("MAC-IP查询")
    def start(self, devices: List[Any], mac_or_ip: str) -> None:
        """开始查询 MAC-IP 信息"""
        self.is_running = True
        self.results.clear()
        self.found_mac_addresses.clear()
        self.trunk_info.clear()
        self.lagg_info.clear()
        
        try:
            # 过滤无效设备
            valid_devices = [device for device in devices if self._validate_device(device)]
            if not valid_devices:
                logger.warning("没有有效的设备可以查询")
                return
            
            # 初始化nornir
            logger.info("初始化 nornir...")
            nr = self.nornir_mgr.init_nornir(valid_devices)
            if not nr:
                logger.error("nornir 初始化失败")
                return
            
            try:
                # 先获取trunk和聚合口信息
                logger.info("获取trunk和聚合口信息...")
                for device in valid_devices:
                    self.status_changed.emit(device.name, "状态: 正在获取接口信息")
                
                # 并行获取trunk信息
                self.status_changed.emit("全局", "状态: 正在获取Trunk端口信息")
                trunk_results = nr.run(task=self._get_trunk_info)
                for device_name, result in trunk_results.items():
                    if not result.failed:
                        self.trunk_info[device_name] = result[0].result
                
                # 并行获取聚合口信息
                self.status_changed.emit("全局", "状态: 正在获取聚合口信息")
                lagg_results = nr.run(task=self._get_lagg_info)
                for device_name, result in lagg_results.items():
                    if not result.failed:
                        self.lagg_info[device_name] = result[0].result

                # 执行查询
                logger.info("开始执行查询任务...")
                
                # 1. 并行查询所有设备的ARP信息
                self.status_changed.emit("全局", "状态: 正在查询ARP表")
                arp_results = nr.run(
                    name="ARP查询",
                    task=self.query_arp,
                    mac_or_ip=mac_or_ip
                )
                
                # 2. 如果是IP查询且找到了MAC地址，继续查询所有设备的MAC地址表
                if '.' in mac_or_ip and self.found_mac_addresses:  # IP地址查询且找到了MAC
                    for mac in self.found_mac_addresses:
                        self.status_changed.emit("全局", f"状态: 正在查询MAC地址 {mac}")
                        mac_results = nr.run(
                            name="MAC查询",
                            task=self.query_mac,
                            mac=mac
                        )
                        
                        # 处理MAC查询结果
                        for device_name, multi_result in mac_results.items():
                            if not multi_result.failed and "未找到MAC地址表项" not in multi_result[0].result:
                                if device_name in self.results:
                                    # 如果设备已有结果，追加MAC查询结果
                                    self.results[device_name]['result'] += "\n\nMAC地址表中的信息:\n" + multi_result[0].result
                                else:
                                    # 如果设备还没有结果，创建新结果
                                    self.results[device_name] = {
                                        'status': "成功: 查询完成",
                                        'result': "MAC地址表中的信息:\n" + multi_result[0].result
                                    }
                else:  # MAC地址查询
                    self.status_changed.emit("全局", "状态: 正在查询MAC地址表")
                    mac_results = nr.run(
                        name="MAC查询",
                        task=self.query_mac,
                        mac=mac_or_ip
                    )
                    
                    # 处理MAC查询结果
                    for device_name, multi_result in mac_results.items():
                        if not multi_result.failed and "未找到MAC地址表项" not in multi_result[0].result:
                            if device_name in self.results:
                                self.results[device_name]['result'] += "\n\nMAC地址表中的信息:\n" + multi_result[0].result
                            else:
                                self.results[device_name] = {
                                    'status': "成功: 查询完成",
                                    'result': "MAC地址表中的信息:\n" + multi_result[0].result
                                }
                
                # 3. 处理最终结果
                for device_name in set(list(arp_results.keys()) + list(mac_results.keys() if 'mac_results' in locals() else [])):
                    if device_name not in self.results:
                        # 如果设备没有任何结果，检查是否有错误
                        if device_name in arp_results and arp_results[device_name].failed:
                            error_msg = arp_results[device_name][0].result
                            self._handle_empty_result(device_name, f"失败: {error_msg}", error_msg)
                        elif 'mac_results' in locals() and device_name in mac_results and mac_results[device_name].failed:
                            error_msg = mac_results[device_name][0].result
                            self._handle_empty_result(device_name, f"失败: {error_msg}", error_msg)
                        else:
                            # 如果没有找到任何记录
                            self._handle_empty_result(device_name, "成功: 未找到匹配记录", "未找到任何匹配记录")
                    else:
                        # 更新状态为查询完成
                        result_lines = self.results[device_name]['result'].count('\n') + 1
                        self.status_changed.emit(device_name, f"成功: 找到{result_lines}条记录")
                
            except Exception as e:
                self.results = handle_error(logger, "全局", e, "MAC-IP查询")
                # 更新所有设备状态为失败
                for device in valid_devices:
                    self._handle_empty_result(device.name, f"失败: {str(e)}", str(e))
        finally:
            self.is_running = False
            self.nornir_mgr.close()
            logger.info("查询操作完成")

    def query_arp(self, task: Task, mac_or_ip: str) -> Result:
        """ARP查询任务"""
        try:
            name = task.host.name
            platform = task.host.platform
            
            self.status_changed.emit(name, "状态: 正在查询ARP表")
            
            if platform not in self.commands:
                raise Exception('暂不支持的platform平台')

            # 获取命令和模板路径
            arp_cmd = self.commands[platform]['arp']
            template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
            
            if platform == 'hp_comware':
                template_path = os.path.join(template_dir, 'hp_comware', 'h3c_display_arp.textfsm')
            elif platform == 'huawei_vrp':
                template_path = os.path.join(template_dir, 'huawei_vrp', 'huawei_display_arp_all.textfsm')
            elif platform == 'huawei_vrpv8':
                template_path = os.path.join(template_dir, 'huawei_vrpv8', 'huawei_display_arp.textfsm')
            else:
                raise Exception(f'未找到平台 {platform} 的 ARP 解析模板')

            # 执行命令
            logger.debug(f"执行ARP查询命令: {arp_cmd}")
            arp_result = task.run(
                task=netmiko_send_command,
                command_string=arp_cmd,
                severity_level=logging.DEBUG
            )
            
            # 记录原始输出
            raw_output = arp_result[0].result
            logger.debug(f"{name} - 原始输出:\n{raw_output}")
            
            # 使用 TextFSM 解析输出
            try:
                from textfsm import TextFSM
                from io import StringIO
                
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                logger.debug(f"{name} - 使用的模板内容:\n{template_content}")
                
                template = TextFSM(StringIO(template_content))
                parsed_result = template.ParseText(raw_output)
                
                if not parsed_result:
                    logger.warning(f"{name} - 解析结果为空")
                    return Result(
                        host=task.host,
                        result=f"查询条件: {'IP地址' if '.' in mac_or_ip else 'MAC地址'} = {mac_or_ip}\n详细结果: 未在ARP表中找到对应条目",
                        failed=False
                    )
                    
                # 将解析结果转换为字典列表
                arp_entries = [dict(zip(template.header, row)) for row in parsed_result]
                logger.debug(f"{name} - 解析结果:\n{arp_entries}")
                
                # 根据查询条件过滤结果
                if '.' in mac_or_ip:  # IP地址查询
                    filtered_entries = [entry for entry in arp_entries if entry.get('IP_ADDRESS') == mac_or_ip]
                else:  # MAC地址查询
                    # 标准化MAC地址格式
                    formatted_mac = mac_or_ip.replace(':', '').replace('-', '')
                    formatted_mac = '-'.join(formatted_mac[i:i+4] for i in range(0, len(formatted_mac), 4))
                    filtered_entries = [entry for entry in arp_entries if entry.get('MAC_ADDRESS') == formatted_mac]
                
                # 保存找到的MAC地址（用于后续查询）
                for entry in filtered_entries:
                    if entry.get('MAC_ADDRESS'):
                        self.found_mac_addresses.add(entry['MAC_ADDRESS'])
                
                # 格式化输出
                output_lines = [
                    f"查询条件: {'IP地址' if '.' in mac_or_ip else 'MAC地址'} = {mac_or_ip}",
                    "详细结果:"
                ]
                
                if not filtered_entries:
                    output_lines.append("未在ARP表中找到对应条目")
                else:
                    for entry in filtered_entries:
                        interface = entry.get('INTERFACE', 'N/A')
                        output_lines.extend([
                            f"IP地址: {entry.get('IP_ADDRESS', 'N/A')}",
                            f"MAC地址: {entry.get('MAC_ADDRESS', 'N/A')}",
                            f"接口: {interface}"
                        ])
                        
                        # 添加聚合口成员端口信息
                        if interface.startswith(('Eth-Trunk', 'BAGG', 'Bridge-Aggregation')):
                            try:
                                lagg_num = re.search(r'\d+', interface).group()
                                if name in self.lagg_info and lagg_num in self.lagg_info[name]:
                                    member_ports = self.lagg_info[name][lagg_num]
                                    if isinstance(member_ports, list):
                                        member_ports = ', '.join(member_ports)
                                    output_lines.append(f"成员端口: {member_ports}")
                            except Exception as e:
                                logger.warning(f"处理聚合口成员信息失败: {interface}, {str(e)}")
                        
                        # 添加trunk信息
                        if name in self.trunk_info and interface in self.trunk_info[name]:
                            output_lines.append("端口类型: Trunk")
                        
                        output_lines.extend([
                            f"VLAN: {entry.get('VLAN_ID', '')}",
                            "---"
                        ])
                
                return Result(
                    host=task.host,
                    result="\n".join(output_lines),
                    failed=False
                )
                
            except Exception as parse_error:
                logger.error(f"{name} - TextFSM解析失败: {str(parse_error)}")
                raise Exception(f"TextFSM解析失败: {str(parse_error)}")
            
        except Exception as e:
            error_msg = f"ARP查询失败: {str(e)}"
            logger.error(f"{name} - {error_msg}")
            self.status_changed.emit(name, "失败: " + error_msg)
            return Result(
                host=task.host,
                result=error_msg,
                failed=True
            )

    def _get_field_value(self, entry: Dict[str, str], field_type: str, platform: str) -> str:
        """从字典中获取字段值，处理不同设备的字段名差异"""
        field_names = self.field_maps[platform][field_type]
        for field_name in field_names:
            if field_name in entry:
                return entry[field_name]
        return 'N/A'

    def query_mac(self, task: Task, mac: str) -> Result:
        """MAC查询任务"""
        try:
            name = task.host.name
            platform = task.host.platform
            
            self.status_changed.emit(name, "状态: 正在查询MAC地址表")
            
            if platform not in self.commands:
                raise Exception('暂不支持的platform平台')

            # 标准化MAC地址格式
            formatted_mac = mac.replace(':', '').replace('-', '')
            formatted_mac = '-'.join(formatted_mac[i:i+4] for i in range(0, len(formatted_mac), 4))
            
            # 获取命令和模板路径
            mac_cmd = self.commands[platform]['mac']  # 查询所有MAC地址表
            template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
            
            if platform == 'hp_comware':
                template_path = os.path.join(template_dir, 'hp_comware', 'h3c_display_mac-address.textfsm')
            elif platform == 'huawei_vrp':
                template_path = os.path.join(template_dir, 'huawei_vrp', 'huawei_display_mac-address.textfsm')
            elif platform == 'huawei_vrpv8':
                template_path = os.path.join(template_dir, 'huawei_vrpv8', 'huawei_display_mac-address.textfsm')
            else:
                raise Exception(f'未找到平台 {platform} 的 MAC 解析模板')

            # 执行命令
            logger.debug(f"执行MAC查询命令: {mac_cmd}")
            mac_result = task.run(
                task=netmiko_send_command,
                command_string=mac_cmd,
                severity_level=logging.DEBUG
            )
            
            # 记录原始输出
            raw_output = mac_result[0].result
            logger.debug(f"{name} - 原始输出:\n{raw_output}")
            
            # 使用 TextFSM 解析输出
            try:
                from textfsm import TextFSM
                from io import StringIO
                
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                logger.debug(f"{name} - 使用的模板内容:\n{template_content}")
                
                template = TextFSM(StringIO(template_content))
                parsed_result = template.ParseText(raw_output)
                
                if not parsed_result:
                    logger.warning(f"{name} - 解析结果为空")
                    return Result(
                        host=task.host,
                        result=f"查询条件: MAC地址 = {formatted_mac}\n详细结果: 未找到MAC地址表项",
                        failed=False
                    )
                    
                # 将解析结果转换为字典列表
                mac_entries = [dict(zip(template.header, row)) for row in parsed_result]
                logger.debug(f"{name} - 解析结果:\n{mac_entries}")
                
                # 过滤出匹配的MAC地址条目
                filtered_entries = []
                for entry in mac_entries:
                    entry_mac = self._get_field_value(entry, 'mac_address', platform)
                    if entry_mac == formatted_mac:
                        filtered_entries.append(entry)
                
                # 格式化输出
                output_lines = [
                    f"查询条件: MAC地址 = {formatted_mac}",
                    "详细结果:"
                ]
                
                if not filtered_entries:
                    output_lines.append("未找到MAC地址表项")
                else:
                    for entry in filtered_entries:
                        interface = self._get_field_value(entry, 'interface', platform)
                        vlan = self._get_field_value(entry, 'vlan', platform)
                        mac_addr = self._get_field_value(entry, 'mac_address', platform)
                        
                        output_lines.extend([
                            f"MAC地址: {mac_addr}",
                            f"接口: {interface}",
                            f"VLAN: {vlan}"
                        ])
                        
                        # 添加聚合口成员端口信息
                        if interface.startswith(('Eth-Trunk', 'BAGG', 'Bridge-Aggregation')):
                            try:
                                lagg_num = re.search(r'\d+', interface).group()
                                if name in self.lagg_info and lagg_num in self.lagg_info[name]:
                                    member_ports = self.lagg_info[name][lagg_num]
                                    if isinstance(member_ports, list):
                                        member_ports = ', '.join(member_ports)
                                    output_lines.append(f"成员端口: {member_ports}")
                            except Exception as e:
                                logger.warning(f"处理聚合口成员信息失败: {interface}, {str(e)}")
                        
                        # 添加trunk信息
                        if name in self.trunk_info and interface in self.trunk_info[name]:
                            output_lines.append("端口类型: Trunk")
                        
                        output_lines.append("---")
                
                return Result(
                    host=task.host,
                    result="\n".join(output_lines),
                    failed=False
                )
                
            except Exception as parse_error:
                logger.error(f"{name} - TextFSM解析失败: {str(parse_error)}")
                raise Exception(f"TextFSM解析失败: {str(parse_error)}")
            
        except Exception as e:
            error_msg = f"MAC查询失败: {str(e)}"
            logger.error(f"{name} - {error_msg}")
            self.status_changed.emit(name, "失败: " + error_msg)
            return Result(
                host=task.host,
                result=error_msg,
                failed=True
            )

    def _get_trunk_info(self, task: Task) -> dict:
        """获取设备的trunk端口信息"""
        try:
            name = task.host.name
            platform = task.host.platform
            
            if platform not in self.commands:
                return {}

            # 获取trunk信息
            trunk_cmd = self.commands[platform]['trunk']
            self.status_changed.emit(name, "状态: 正在执行命令 " + trunk_cmd)
            trunk_result = task.run(
                task=netmiko_send_command,
                command_string=trunk_cmd,
                severity_level=logging.DEBUG
            )
            
            self.status_changed.emit(name, "状态: 正在解析Trunk端口信息")
            # 解析trunk端口信息
            template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
            trunk_template_path = None
            if platform == 'hp_comware':
                trunk_template_path = os.path.join(template_dir, 'hp_comware', 'h3c_display_port_trunk.textfsm')
            elif platform in ['huawei_vrp', 'huawei_vrpv8']:
                trunk_template_path = os.path.join(template_dir, platform, 'huawei_display_port_vlan.textfsm')
            
            trunk_info = {}
            if trunk_template_path:
                with open(trunk_template_path, 'r', encoding='utf-8') as f:
                    trunk_template = TextFSM(StringIO(f.read()))
                trunk_parsed = trunk_template.ParseText(trunk_result[0].result)
                trunk_info = {entry[0]: entry[1:] for entry in trunk_parsed}
            
            return trunk_info
            
        except Exception as e:
            logger.warning(f"{name} - 获取trunk信息失败: {str(e)}")
            self.status_changed.emit(name, f"获取Trunk信息失败: {str(e)}")
            return {}

    def _get_lagg_info(self, task: Task) -> dict:
        """获取设备的聚合口信息"""
        try:
            name = task.host.name
            platform = task.host.platform
            
            if platform not in self.commands:
                return {}

            # 执行聚合口查询命令
            lagg_cmd = self.commands[platform]['lagg']
            self.status_changed.emit(name, "状态: 正在执行命令 " + lagg_cmd)
            lagg_result = task.run(
                task=netmiko_send_command,
                command_string=lagg_cmd,
                severity_level=logging.DEBUG
            )
            
            # 添加原始输出的日志
            logger.debug(f"{name} - 聚合口查询原始输出:\n{lagg_result[0].result}")
            
            self.status_changed.emit(name, "状态: 正在解析聚合口信息")
            # 解析聚合口成员
            template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
            lagg_template_path = None
            if platform == 'hp_comware':
                lagg_template_path = os.path.join(template_dir, 'hp_comware', 'h3c_display_link-aggregation_verbose_Bridge-Aggregation')
            elif platform == 'huawei_vrp':
                lagg_template_path = os.path.join(template_dir, 'huawei_vrp', 'huawei_display_eth-trunk.textfsm')
            elif platform == 'huawei_vrpv8':
                lagg_template_path = os.path.join(template_dir, 'huawei_vrpv8', 'huawei_display_eth-trunk.textfsm')
            
            # 添加模板路径日志
            logger.debug(f"{name} - 使用模板文件: {lagg_template_path}")
            
            lagg_info = {}
            if lagg_template_path:
                with open(lagg_template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                    # 添加模板内容日志
                    logger.debug(f"{name} - 模板内容:\n{template_content}")
                    
                    lagg_template = TextFSM(StringIO(template_content))
                    lagg_parsed = lagg_template.ParseText(lagg_result[0].result)
                    
                    # 添加解析结果日志
                    logger.debug(f"{name} - TextFSM解析结果:\n{lagg_parsed}")
                    
                    if lagg_parsed:
                        for member in lagg_parsed:
                            if platform == 'hp_comware':
                                lagg_num = re.search(r'\d+', member[0]).group()
                                member_ports = member[1]  # PHYSICAL_PORTS字段
                            else:  # huawei平台
                                lagg_num = re.search(r'\d+', member[0]).group()
                                member_ports = member[1]  # MEMBER_PORTS字段
                            if member_ports:  # 只有当有成员端口时才添加
                                lagg_info[lagg_num] = member_ports
                                # 添加每个聚合口信息的日志
                                logger.debug(f"{name} - 解析到聚合口 {lagg_num} 的成员端口: {member_ports}")
            
            # 添加最终结果日志
            logger.debug(f"{name} - 最终的聚合口信息字典:\n{lagg_info}")
            return lagg_info
            
        except Exception as e:
            logger.warning(f"{name} - 获取聚合口信息失败: {str(e)}")
            self.status_changed.emit(name, f"获取聚合口信息失败: {str(e)}")
            return {} 