# 标准库导入
import logging
import os
from typing import List, Dict, Any, Optional
from ipaddress import IPv4Network, AddressValueError

# 第三方库导入
from nornir.core.task import Task, Result
from nornir_netmiko.tasks import netmiko_send_config, netmiko_send_command
from PySide6.QtCore import QObject, Signal
import re

# 本地导入
from .base import BaseOperation
from ..base.nornir_manager import NornirManager
from ...utils.logger import log_operation

logger = logging.getLogger(__name__)

class FirewallAddressGroupOperation(BaseOperation):
    """防火墙地址组操作类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.group_name = "BlackList-nornir"  # 默认地址组名称
        
    def validate_ip_address(self, ip_address: str) -> bool:
        """验证IP地址格式"""
        try:
            # 支持 IP/mask 格式，如 10.10.1.2/32
            if '/' in ip_address:
                IPv4Network(ip_address, strict=False)
            else:
                # 如果没有掩码，默认为/32
                IPv4Network(f"{ip_address}/32", strict=False)
            return True
        except (AddressValueError, ValueError) as e:
            logger.error(f"IP地址格式错误: {ip_address}, 错误: {str(e)}")
            return False
    
    def parse_ip_address(self, ip_address: str) -> tuple:
        """解析IP地址，返回(ip, mask)元组"""
        try:
            if '/' in ip_address:
                network = IPv4Network(ip_address, strict=False)
                return str(network.network_address), str(network.prefixlen)
            else:
                # 默认为/32
                return ip_address, "32"
        except (AddressValueError, ValueError):
            return None, None
    
    def generate_huawei_commands(self, operation: str, ip_addresses: List[str],
                                group_name: str = None, config_output: str = None) -> List[str]:
        """生成华为防火墙命令"""
        if not group_name:
            group_name = self.group_name

        commands = [f"ip address-set {group_name} type group"]

        if operation == "add":
            for ip_addr in ip_addresses:
                ip, mask = self.parse_ip_address(ip_addr)
                if ip and mask:
                    commands.append(f"address {ip} mask {mask}")
        elif operation == "delete":
            # 对于删除操作，解析现有配置并生成删除命令
            if config_output:
                delete_commands = self.parse_huawei_address_group(config_output, ip_addresses, group_name)
                commands.extend(delete_commands)
            else:
                # 如果没有配置输出，生成注释说明
                for ip_addr in ip_addresses:
                    ip, mask = self.parse_ip_address(ip_addr)
                    if ip and mask:
                        commands.append(f"# 需要删除的地址: {ip} mask {mask} (需要先查询序号)")

        return commands
    
    def generate_h3c_commands(self, operation: str, ip_addresses: List[str],
                             group_name: str = None, config_output: str = None) -> List[str]:
        """生成H3C防火墙命令"""
        if not group_name:
            group_name = self.group_name

        commands = [f"object-group ip address {group_name}"]

        if operation == "add":
            for ip_addr in ip_addresses:
                ip, mask = self.parse_ip_address(ip_addr)
                if ip and mask:
                    if mask == "32":
                        # 主机地址
                        commands.append(f"network host address {ip}")
                    else:
                        # 网络地址，需要转换掩码格式
                        subnet_mask = str(IPv4Network(f"0.0.0.0/{mask}").netmask)
                        commands.append(f"network subnet {ip} {subnet_mask}")
        elif operation == "delete":
            # 对于删除操作，解析现有配置并生成删除命令
            if config_output:
                delete_commands = self.parse_h3c_address_group(config_output, ip_addresses)
                commands.extend(delete_commands)
            else:
                # 如果没有配置输出，生成注释说明
                for ip_addr in ip_addresses:
                    ip, mask = self.parse_ip_address(ip_addr)
                    if ip and mask:
                        commands.append(f"# 需要删除的地址: {ip}/{mask} (需要先查询序号)")

        return commands

    def query_address_group_config(self, task: Task, group_name: str, platform: str) -> str:
        """查询地址组配置"""
        try:
            if platform in ["huawei"]:
                # 华为设备查询命令 - 查询所有地址组
                query_cmd = "display ip address-set type group"
            elif platform == "hp_comware":
                # H3C设备查询命令
                query_cmd = f"display object-group ip address name {group_name}"
            else:
                return ""

            # 执行查询命令
            result = task.run(
                task=netmiko_send_command,
                command_string=query_cmd,
                name=f"query_address_group_{task.host.name}"
            )

            return str(result.result) if result.result else ""

        except Exception as e:
            logger.error(f"查询地址组配置失败: {str(e)}")
            return ""

    def parse_huawei_address_group(self, config_output: str, target_ips: List[str], group_name: str) -> List[str]:
        """解析华为地址组配置，返回要删除的序号对应的命令"""
        delete_commands = []

        logger.info(f"开始解析华为地址组配置，目标组: {group_name}, 目标IP: {target_ips}")
        logger.info(f"配置输出长度: {len(config_output)} 字符")

        # 华为地址组输出格式：
        # Address-set: BlackList-nornir
        # Type: group
        # Item number(s): 3
        # Reference number(s): 0
        # Item(s):
        #  address 0 10.10.5.5 mask 32
        #  address 1 10.20.5.5 mask 32
        #  address 2 10.10.6.6 mask 32

        lines = config_output.split('\n')
        logger.info(f"配置分割为 {len(lines)} 行")

        # 查找目标地址组
        in_target_group = False
        in_items_section = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            logger.debug(f"处理第{i+1}行: '{line_stripped}'")

            # 检查是否是地址组名称行
            if line_stripped.startswith("Address-set:"):
                current_group = line_stripped.replace("Address-set:", "").strip()
                in_target_group = (current_group == group_name)
                in_items_section = False
                logger.info(f"找到地址组: {current_group}, 是否目标组: {in_target_group}")
                continue

            # 如果不在目标组中，跳过
            if not in_target_group:
                continue

            # 检查是否进入Items部分
            if line_stripped == "Item(s):":
                in_items_section = True
                logger.info(f"进入地址组 {group_name} 的Items部分")
                continue

            # 如果在Items部分，解析地址条目
            if in_items_section and line_stripped:
                # 如果遇到下一个地址组，退出
                if line_stripped.startswith("Address-set:"):
                    break

                # 匹配地址条目：address 序号 IP mask 掩码
                match = re.match(r'address\s+(\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+mask\s+(\d+)', line_stripped)
                if match:
                    index, ip, mask = match.groups()
                    logger.info(f"找到地址条目: 序号={index}, IP={ip}, 掩码={mask}")

                    # 检查这个IP是否在要删除的列表中
                    for target_ip in target_ips:
                        target_ip_parsed, target_mask = self.parse_ip_address(target_ip)
                        logger.info(f"比较目标IP: {target_ip} -> 解析为 {target_ip_parsed}/{target_mask}")
                        logger.info(f"匹配检查: IP匹配={ip == target_ip_parsed}, 掩码匹配={mask == target_mask}")

                        if target_ip_parsed and ip == target_ip_parsed and mask == target_mask:
                            delete_commands.append(f"undo address {index}")
                            logger.info(f"✓ 找到要删除的华为地址条目: {ip}/{mask} (序号: {index})")
                            break
                        else:
                            logger.debug(f"✗ 不匹配: {target_ip}")
                else:
                    logger.debug(f"行不匹配地址格式: '{line_stripped}'")

        logger.info(f"解析完成，生成删除命令: {delete_commands}")
        return delete_commands

    def parse_h3c_address_group(self, config_output: str, target_ips: List[str]) -> List[str]:
        """解析H3C地址组配置，返回要删除的序号对应的命令"""
        delete_commands = []

        logger.info(f"开始解析H3C地址组配置，目标IP: {target_ips}")
        logger.info(f"配置输出内容:\n{repr(config_output)}")

        # H3C地址组输出格式示例：
        # Ip address object group BlackList-nornir: 1 object(out of use)
        #  0 network host address 10.10.5.5
        #  1 network subnet 192.168.1.0 255.255.255.0

        lines = config_output.split('\n')
        logger.info(f"配置分割为 {len(lines)} 行")

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            logger.debug(f"处理第{i+1}行: '{line_stripped}'")

            # 匹配主机地址：序号 network host address IP
            host_match = re.match(r'(\d+)\s+network\s+host\s+address\s+(\d+\.\d+\.\d+\.\d+)', line_stripped)
            if host_match:
                index, ip = host_match.groups()
                logger.info(f"找到H3C主机地址条目: 序号={index}, IP={ip}")

                # 检查这个IP是否在要删除的列表中
                for target_ip in target_ips:
                    target_ip_parsed, target_mask = self.parse_ip_address(target_ip)
                    logger.info(f"比较目标IP: {target_ip} -> 解析为 {target_ip_parsed}/{target_mask}")
                    logger.info(f"匹配检查: IP匹配={ip == target_ip_parsed}, 掩码匹配={target_mask == '32'}")

                    if target_ip_parsed and ip == target_ip_parsed and target_mask == "32":
                        delete_commands.append(f"undo {index}")
                        logger.info(f"✓ 找到要删除的H3C主机地址条目: {ip} (序号: {index})")
                        break
                    else:
                        logger.debug(f"✗ 不匹配: {target_ip}")
                continue

            # 匹配网络地址：序号 network subnet IP 掩码
            subnet_match = re.match(r'(\d+)\s+network\s+subnet\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)', line_stripped)
            if subnet_match:
                index, ip, netmask = subnet_match.groups()
                logger.info(f"找到H3C网络地址条目: 序号={index}, IP={ip}, 掩码={netmask}")

                # 将点分十进制掩码转换为CIDR格式
                try:
                    cidr_mask = str(IPv4Network(f"0.0.0.0/{netmask}").prefixlen)
                    logger.debug(f"掩码转换: {netmask} -> /{cidr_mask}")
                except Exception as e:
                    logger.warning(f"掩码转换失败: {netmask}, 错误: {str(e)}")
                    continue

                # 检查这个网络是否在要删除的列表中
                for target_ip in target_ips:
                    target_ip_parsed, target_mask = self.parse_ip_address(target_ip)
                    logger.info(f"比较目标IP: {target_ip} -> 解析为 {target_ip_parsed}/{target_mask}")
                    logger.info(f"匹配检查: IP匹配={ip == target_ip_parsed}, 掩码匹配={cidr_mask == target_mask}")

                    if target_ip_parsed and ip == target_ip_parsed and cidr_mask == target_mask:
                        delete_commands.append(f"undo {index}")
                        logger.info(f"✓ 找到要删除的H3C网络地址条目: {ip}/{target_mask} (序号: {index})")
                        break
                    else:
                        logger.debug(f"✗ 不匹配: {target_ip}")
            else:
                logger.debug(f"行不匹配地址格式: '{line_stripped}'")

        logger.info(f"H3C解析完成，生成删除命令: {delete_commands}")
        return delete_commands

    def manage_address_group(self, task: Task, operation: str, ip_addresses: List[str],
                           group_name: str = None) -> Result:
        """管理地址组的核心任务"""
        if not self.is_running:
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )

        try:
            device = task.host
            device_name = device.name
            site = device.data.get('site', "未分类")
            platform = device.platform

            logger.info(f"开始地址组操作 - 设备: {device_name}, 站点: {site}, 平台: {platform}")
            logger.info(f"操作类型: {operation}, 地址组: {group_name or self.group_name}")
            logger.info(f"IP地址列表: {ip_addresses}")

            # 更新状态
            self.status_changed.emit(device_name, f"正在执行{operation}操作...")

            # 验证IP地址
            valid_ips = []
            for ip_addr in ip_addresses:
                if self.validate_ip_address(ip_addr):
                    valid_ips.append(ip_addr)
                else:
                    logger.warning(f"{device_name} - 跳过无效IP地址: {ip_addr}")

            if not valid_ips:
                error_msg = "没有有效的IP地址"
                logger.error(f"{device_name} - {error_msg}")
                self.status_changed.emit(device_name, f"错误: {error_msg}")
                return Result(
                    host=device,
                    result=error_msg,
                    failed=True
                )

            # 对于删除操作，先查询现有配置
            config_output = ""
            if operation == "delete":
                logger.info(f"{device_name} - 删除操作，先查询地址组配置")
                self.status_changed.emit(device_name, "正在查询地址组配置...")
                config_output = self.query_address_group_config(task, group_name or self.group_name, platform)

                if not config_output or "not exist" in config_output.lower() or "not found" in config_output.lower():
                    error_msg = f"地址组 '{group_name or self.group_name}' 不存在或为空"
                    logger.warning(f"{device_name} - {error_msg}")
                    self.status_changed.emit(device_name, f"警告: {error_msg}")
                    return Result(
                        host=device,
                        result=error_msg,
                        failed=False  # 不算失败，只是警告
                    )

                logger.info(f"{device_name} - 查询到的配置:\n{config_output}")
                logger.info(f"{device_name} - 配置输出长度: {len(config_output)} 字符")

            # 根据平台生成命令
            if platform in ["huawei"]:
                commands = self.generate_huawei_commands(operation, valid_ips, group_name, config_output)
            elif platform == "hp_comware":
                commands = self.generate_h3c_commands(operation, valid_ips, group_name, config_output)
            else:
                error_msg = f"不支持的设备平台: {platform}"
                logger.error(f"{device_name} - {error_msg}")
                self.status_changed.emit(device_name, f"错误: {error_msg}")
                return Result(
                    host=device,
                    result=error_msg,
                    failed=True
                )

            # 检查删除操作是否找到了要删除的条目
            if operation == "delete":
                actual_delete_commands = [cmd for cmd in commands if cmd.startswith("undo")]
                if not actual_delete_commands:
                    error_msg = f"在地址组中未找到要删除的IP地址: {', '.join(valid_ips)}"
                    logger.warning(f"{device_name} - {error_msg}")
                    self.status_changed.emit(device_name, f"警告: {error_msg}")
                    return Result(
                        host=device,
                        result=error_msg,
                        failed=False  # 不算失败，只是警告
                    )
                else:
                    logger.info(f"{device_name} - 找到 {len(actual_delete_commands)} 个要删除的条目")

            logger.info(f"{device_name} - 生成的命令: {commands}")

            # 执行配置命令
            result = task.run(
                task=netmiko_send_config,
                config_commands=commands,
                name=f"address_group_{operation}_to_{device_name}"
            )

            # 检查执行结果
            if result.failed:
                error_msg = f"命令执行失败: {str(result.exception)}"
                logger.error(f"{device_name} - {error_msg}")
                self.status_changed.emit(device_name, f"错误: {error_msg}")
                return Result(
                    host=device,
                    result=error_msg,
                    failed=True
                )

            # 保存输出到文件
            output_content = str(result.result)
            output_file = self._save_output(device_name, site, operation, commands, output_content)

            success_msg = f"成功: {operation}操作完成"
            logger.info(f"{device_name} - {success_msg}")
            self.status_changed.emit(device_name, success_msg)

            # 存储结果
            self.results[device_name] = {
                'status': success_msg,
                'operation': operation,
                'ip_addresses': valid_ips,
                'group_name': group_name or self.group_name,
                'commands': commands,
                'output': output_content,
                'output_file': output_file
            }

            return Result(
                host=device,
                result=success_msg
            )

        except Exception as e:
            error_msg = f"地址组操作异常: {str(e)}"
            logger.error(f"{device_name} - {error_msg}", exc_info=True)
            self.status_changed.emit(device_name, f"错误: {error_msg}")
            self.results[device_name] = {
                'status': f"错误: {error_msg}",
                'operation': operation,
                'ip_addresses': valid_ips if 'valid_ips' in locals() else ip_addresses,
                'group_name': group_name or self.group_name,
                'error': str(e),
                'failed': True
            }
            return Result(
                host=device,
                result=error_msg,
                failed=True
            )

    def _save_output(self, device_name: str, site: str, operation: str,
                    commands: List[str], output: str) -> str:
        """保存命令输出到文件"""
        try:
            # 创建输出目录
            base_path = os.path.join(os.getcwd(), "输出文件")
            output_path = os.path.join(base_path, "防火墙地址组管理")
            site_path = os.path.join(output_path, site)
            os.makedirs(site_path, exist_ok=True)

            # 创建输出文件
            output_file = os.path.join(site_path, f'{device_name}-address-group-{operation}.txt')

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"防火墙地址组{operation}操作结果\n")
                f.write(f"设备: {device_name}\n")
                f.write(f"站点: {site}\n")
                f.write(f"操作时间: {self._get_current_time()}\n")
                f.write("=" * 50 + "\n\n")

                f.write("执行的命令:\n")
                for cmd in commands:
                    f.write(f"  {cmd}\n")
                f.write("\n" + "=" * 50 + "\n\n")

                f.write("命令输出:\n")
                f.write(output)

            return output_file

        except Exception as e:
            logger.error(f"保存输出文件失败: {str(e)}")
            return None

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @log_operation("防火墙地址组管理")
    def start(self, devices: List[str], operation: str, ip_addresses: List[str],
             group_name: str = None) -> None:
        """开始地址组管理操作"""
        self.is_running = True
        self.results.clear()

        try:
            # 过滤无效设备
            valid_devices = [device for device in devices if self._validate_device(device)]
            if not valid_devices:
                logger.warning("没有有效的设备可以操作")
                return

            # 初始化nornir
            logger.info("初始化 nornir...")
            nr = self.nornir_mgr.init_nornir(valid_devices)
            if not nr:
                logger.error("nornir 初始化失败")
                return

            try:
                # 执行地址组管理操作
                logger.info(f"开始执行地址组{operation}操作...")
                nr.run(
                    name=f"防火墙地址组{operation}",
                    task=self.manage_address_group,
                    operation=operation,
                    ip_addresses=ip_addresses,
                    group_name=group_name
                )
            except Exception as e:
                logger.error(f"地址组{operation}操作全局异常: {str(e)}", exc_info=True)
                self.results = {
                    'global_error': f"地址组{operation}操作失败: {str(e)}",
                    'failed': True
                }
        finally:
            self.is_running = False
            self.nornir_mgr.close()
            logger.info(f"地址组{operation}操作完成")
