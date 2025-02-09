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
        required_fields = ['name', 'hostname', 'platform']
        for field in required_fields:
            if not device.get(field):
                return False, f"缺少必要字段: {field}"
            
        # 验证端口范围
        port = device.get('port', 22)
        if not (0 < port < 65536):
            return False, f"端口号无效: {port}"
        
        return True, ""

    def batch_add_or_update_devices(self, devices: List[Dict], parent=None) -> Tuple[int, int]:
        """批量添加或更新设备"""
        logger.info(f"开始批量处理 {len(devices)} 个设备")
        error_messages = []
        valid_devices = []

        # 验证数据
        for device in devices:
            is_valid, error_msg = self._validate_device_data(device)
            if is_valid:
                valid_devices.append(device)
            else:
                error_messages.append(f"设备 {device.get('name', 'Unknown')} 数据无效: {error_msg}")

        # 批量处理有效的设备
        success_count, update_count = self.db.batch_add_or_update_hosts(valid_devices)

        # 显示结果
        if success_count > 0 or update_count > 0:
            message = f"处理完成\n新增: {success_count} 个\n更新: {update_count} 个"
            if error_messages:
                message += "\n\n验证错误:\n" + "\n".join(error_messages)
            
            if error_messages:
                QMessageBox.warning(parent, "完成", message)
            else:
                QMessageBox.information(parent, "完成", message)
                
            # 发送更新信号
            self.device_updated.emit()
            event_bus.device_list_changed.emit()
            
        return success_count, update_count 