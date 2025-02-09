from PySide6.QtWidgets import QFileDialog, QMessageBox
import pandas as pd
from typing import Tuple, List, Dict, Any
import os
from core.event_bus import event_bus
from ui.widgets.device_list.device_manager import DeviceManager

class DeviceImporter:
    """设备导入导出工具"""
    
    TEMPLATE_COLUMNS = [
        '设备名称', '主机名/IP', '平台类型', '用户名', '密码', 
        '端口', '站点', '设备类型', '设备型号'
    ]
    
    @staticmethod
    def import_devices(parent, db) -> Tuple[bool, int]:
        """通过文件对话框导入设备
        
        Returns:
            Tuple[bool, int]: (是否成功, 导入数量)
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "选择Excel文件",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if not file_path:
            return False, 0
            
        return DeviceImporter.import_from_file(file_path, db)
    
    @staticmethod
    def import_from_file(file_path: str, db) -> Tuple[bool, int]:
        """从指定文件导入设备
        
        Args:
            file_path: Excel文件路径
            db: 数据库实例
        
        Returns:
            Tuple[bool, int]: (是否成功, 导入/更新数量)
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            # 验证列名
            if not all(col in df.columns for col in DeviceImporter.TEMPLATE_COLUMNS):
                QMessageBox.warning(None, "导入失败", "Excel文件格式不正确，请使用正确的模板")
                return False, 0
            
            # 转换为设备数据
            devices = []
            for _, row in df.iterrows():
                device = {
                    'name': row['设备名称'],
                    'hostname': row['主机名/IP'],
                    'platform': row['平台类型'],
                    'username': row['用户名'],
                    'password': row['密码'],
                    'port': int(row['端口']) if pd.notna(row['端口']) else 22,
                    'site': row['站点'] if pd.notna(row['站点']) else None,
                    'device_type': row['设备类型'] if pd.notna(row['设备类型']) else None,
                    'device_model': row['设备型号'] if pd.notna(row['设备型号']) else None
                }
                devices.append(device)
            
            # 使用设备管理器的批量方法
            device_manager = DeviceManager(db)
            success_count, update_count = device_manager.batch_add_or_update_devices(devices)
            
            return (success_count + update_count) > 0, success_count + update_count
            
        except Exception as e:
            QMessageBox.critical(None, "导入失败", f"导入过程中发生错误：{str(e)}")
            return False, 0
    
    @staticmethod
    def export_devices(parent, devices: List[Dict[str, Any]]):
        """导出设备列表"""
        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "导出Excel文件",
            "devices.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
            
        try:
            # 转换为DataFrame
            data = []
            for device in devices:
                data.append({
                    '设备名称': device.name,
                    '主机名/IP': device.hostname,
                    '平台类型': device.platform,
                    '用户名': device.username,
                    '密码': device.password,
                    '端口': device.port,
                    '站点': device.site,
                    '设备类型': device.device_type,
                    '设备型号': device.device_model
                })
            
            df = pd.DataFrame(data)
            df = df[DeviceImporter.TEMPLATE_COLUMNS]  # 按模板列顺序排列
            df.to_excel(file_path, index=False)
            
            QMessageBox.information(parent, "导出成功", "设备数据已成功导出")
            
        except Exception as e:
            QMessageBox.critical(parent, "导出失败", f"导出过程中发生错误：{str(e)}")
    
    @staticmethod
    def export_template(parent):
        """导出空白模板"""
        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "导出模板文件",
            "device_template.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
            
        try:
            # 创建空白DataFrame
            df = pd.DataFrame(columns=DeviceImporter.TEMPLATE_COLUMNS)
            
            # 添加示例数据
            df.loc[0] = [
                'sw-core-01',  # 设备名称
                '192.168.1.1',  # 主机名/IP
                'huawei_vrpv8',  # 平台类型
                'admin',  # 用户名
                'password',  # 密码
                22,  # 端口
                '总部',  # 站点
                '核心交换机',  # 设备类型
                'S7800'  # 设备型号
            ]
            
            df.to_excel(file_path, index=False)
            
            QMessageBox.information(parent, "导出成功", "模板文件已成功导出")
            
        except Exception as e:
            QMessageBox.critical(parent, "导出失败", f"导出过程中发生错误：{str(e)}")