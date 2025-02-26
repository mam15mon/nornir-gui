from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox
from core.event_bus import event_bus
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class DeviceManager(QObject):
    """设备管理器，处理设备的增删改查操作"""
    
    # 定义信号
    device_updated = Signal()  # 设备数据更新信号
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        
    def batch_edit_devices(self, device_names, edited_fields, parent=None):
        """批量编辑设备"""
        if not edited_fields:
            QMessageBox.warning(parent, "警告", "没有选择要修改的字段")
            return False

        try:
            # 使用优化的批量更新
            success_count = self.db.batch_edit_devices(device_names, edited_fields)
            
            # 显示结果
            message = f"批量编辑完成\n成功: {success_count} 个\n失败: {len(device_names) - success_count} 个"
            
            if success_count < len(device_names):
                QMessageBox.warning(parent, "完成", message)
            else:
                QMessageBox.information(parent, "完成", message)

            if success_count > 0:
                # 发送更新信号
                self.device_updated.emit()
                event_bus.device_list_changed.emit()
                
            return success_count > 0
            
        except Exception as e:
            error_msg = f"批量编辑失败: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(parent, "错误", error_msg)
            return False

    def batch_delete_devices(self, device_names, parent=None):
        """批量删除设备"""
        if not device_names:
            return False
        
        logger.info(f"开始批量删除 {len(device_names)} 个设备")
        
        reply = QMessageBox.question(
            parent, 
            "确认批量删除", 
            f"确定要删除选中的 {len(device_names)} 个设备吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 使用优化的批量删除
                success_count = self.db.batch_delete_hosts(device_names)
                
                # 显示结果
                message = f"删除完成\n成功: {success_count} 个\n失败: {len(device_names) - success_count} 个"
                
                if success_count < len(device_names):
                    QMessageBox.warning(parent, "完成", message)
                else:
                    QMessageBox.information(parent, "完成", message)
                
                if success_count > 0:
                    # 发送更新信号
                    self.device_updated.emit()
                    event_bus.device_list_changed.emit()
                    
                return success_count > 0
                
            except Exception as e:
                error_msg = f"批量删除失败: {str(e)}"
                logger.error(error_msg)
                QMessageBox.critical(parent, "错误", error_msg)
                return False
        
        return False

    def get_all_devices(self):
        """获取所有设备"""
        devices = self.db.get_all_hosts()
        # 确保返回的是列表
        if devices is None:
            return []
        return devices

    def get_device_by_name(self, name):
        """根据名称获取设备"""
        device = self.db.get_host(name)
        # 确保返回的是字典或 None
        if device is None:
            return None
        return device

    def add_device(self, device_data):
        """添加设备"""
        success = self.db.add_host(device_data)
        if success:
            self.device_updated.emit()
            event_bus.device_list_changed.emit()  # 发送全局通知
        return success

    def update_device(self, name, device_data):
        """更新设备"""
        success = self.db.update_host(name, device_data)
        if success:
            self.device_updated.emit()
            event_bus.device_list_changed.emit()  # 发送全局通知
        return success

    def delete_device(self, name):
        """删除设备"""
        success = self.db.delete_host(name)
        if success:
            self.device_updated.emit()
            event_bus.device_list_changed.emit()  # 添加全局通知
        return success

    def _validate_device_data(self, device: Dict) -> Tuple[bool, str]:
        """验证设备数据
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        # 检查必填字段
        required_fields = {'name': '设备名称', 'hostname': '主机名/IP', 'platform': '平台类型'}
        for field, field_name in required_fields.items():
            if not device.get(field):
                return False, f"缺少必要字段: {field_name}"
        
        # 验证设备名称格式
        name = device.get('name', '')
        # 检查设备名称是否包含无效字符
        invalid_name_chars = set("<>\"'();$|[]{}\\")  # 允许使用&符号，因为实际数据中有使用
        if any(c in invalid_name_chars for c in name):
            return False, f"设备名称包含无效字符: {name}"
        
        # 验证端口范围
        port = device.get('port', 22)
        try:
            port = int(port)
            if not (0 < port < 65536):
                return False, f"端口号无效 (必须在1-65535范围内): {port}"
        except (ValueError, TypeError):
            return False, f"端口号格式错误: {port}"
        
        # 验证主机名/IP地址格式
        hostname = device.get('hostname', '')
        if not hostname:
            return False, "主机名/IP不能为空"
        
        # 判断是否为IP地址格式 (如果全是数字和点，则认为是IP地址)
        if hostname and all(c.isdigit() or c == '.' for c in hostname):
            # 看起来像IP地址，验证IP格式
            parts = hostname.split('.')
            if len(parts) != 4:
                return False, f"IP地址格式错误，应为4段式IP: {hostname}"
            
            for part in parts:
                try:
                    num = int(part)
                    if not (0 <= num <= 255):
                        return False, f"IP地址每段必须在0-255范围内: {hostname}"
                except ValueError:
                    return False, f"IP地址格式错误: {hostname}"
        else:
            # 非IP格式，认为是域名或主机名，做简单的有效性检查
            # 检查是否包含无效字符
            invalid_chars = set("<>\"'();$|[]{}\\")  # 允许使用&符号
            if any(c in invalid_chars for c in hostname):
                return False, f"主机名包含无效字符: {hostname}"
                
            # 检查主机名/域名长度
            if len(hostname) > 255:
                return False, f"主机名/域名长度超过255个字符: {hostname}"
            
            # 检查每段域名部分长度
            parts = hostname.split('.')
            for part in parts:
                if len(part) > 63:
                    return False, f"主机名/域名的每一段不能超过63个字符: {part}"
                
                # 检查域名段首尾不能为连字符
                if part.startswith('-') or part.endswith('-'):
                    return False, f"主机名/域名段不能以连字符(-)开头或结尾: {part}"
        
        # 验证平台类型是否支持
        supported_platforms = ['huawei','huawei_vrp','huawei_vrpv8', 'hp_comware']
        platform = device.get('platform', '').lower()
        if platform and platform not in supported_platforms:
            return False, f"不支持的平台类型: {platform}，支持的平台包括: {', '.join(supported_platforms)}"
        
        return True, ""

    def batch_add_or_update_devices(self, devices: List[Dict], parent=None) -> Tuple[int, int]:
        """批量添加或更新设备"""
        logger.info(f"开始批量处理 {len(devices)} 个设备")
        error_messages = []
        valid_devices = []
        
        # 检查重复名称
        name_counts = {}
        duplicate_names = []
        duplicate_details = {}
        
        # 确保比较时去除空白字符
        for idx, device in enumerate(devices):
            name = device.get('name', '').strip() if device.get('name') else ''
            if name:
                if name not in duplicate_details:
                    duplicate_details[name] = []
                duplicate_details[name].append(idx + 1)  # 记录设备在列表中的序号
                name_counts[name] = name_counts.get(name, 0) + 1
        
        # 记录所有出现次数及重复项
        logger.debug(f"设备名称计数: {name_counts}")
        
        # 过滤出只有多个序号的项（即重复项）
        duplicate_details = {name: indices for name, indices in duplicate_details.items() if len(indices) > 1}
        
        for name, count in name_counts.items():
            if count > 1:
                duplicate_names.append(name)
                logger.warning(f"发现重复的设备名称: {name}, 出现 {count} 次，位于索引 {duplicate_details[name]}")
                
        if duplicate_names:
            # 格式化显示重复项及其序号
            detail_msg = []
            for name, indices in duplicate_details.items():
                detail_msg.append(f"设备名称 '{name}' 在以下位置出现: {', '.join(map(str, indices))}")
            
            error_msg = f"导入数据中存在重复的设备名称:\n" + "\n".join(detail_msg)
            logger.error(error_msg)
            QMessageBox.warning(parent, "数据错误", error_msg)
            return 0, 0

        # 验证数据
        for device in devices:
            is_valid, error_msg = self._validate_device_data(device)
            if is_valid:
                # 检查名称是否已存在于数据库中
                name = device.get('name')
                existing_device = self.db.get_host(name)
                if existing_device and not getattr(parent, 'is_update_mode', False):  # 如果不是显式的更新模式
                    logger.info(f"跳过已存在的设备名称: {name}")
                    error_messages.append(f"设备名称已存在: {name}")
                else:
                    valid_devices.append(device)
            else:
                logger.warning(f"设备数据验证失败: {device.get('name', 'Unknown')} - {error_msg}")
                error_messages.append(f"设备 {device.get('name', 'Unknown')} 数据无效: {error_msg}")

        # 如果没有有效设备但有错误信息，直接显示错误
        if not valid_devices and error_messages:
            message = "数据验证失败，无法导入设备:\n" + "\n".join(error_messages)
            logger.error(message)
            QMessageBox.warning(parent, "验证失败", message)
            return 0, 0
            
        # 批量处理有效的设备
        try:
            success_count, update_count = self.db.batch_add_or_update_hosts(valid_devices)
            logger.info(f"批量处理完成，新增: {success_count}，更新: {update_count}")
            
            # 显示结果
            message = f"处理完成\n新增: {success_count} 个\n更新: {update_count} 个"
            if error_messages:
                message += "\n\n验证错误:\n" + "\n".join(error_messages)
            
            if error_messages:
                QMessageBox.warning(parent, "完成", message)
            else:
                QMessageBox.information(parent, "完成", message)
                
            # 发送更新信号
            if success_count > 0 or update_count > 0:
                self.device_updated.emit()
                event_bus.device_list_changed.emit()
                
            return success_count, update_count
            
        except Exception as e:
            error_msg = f"批量处理设备失败: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(parent, "数据库错误", error_msg)
            return 0, 0 