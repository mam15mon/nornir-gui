from PySide6.QtWidgets import QFileDialog, QMessageBox
import pandas as pd
from typing import Tuple, List, Dict, Any
import os
from core.event_bus import event_bus
from ui.widgets.device_list.device_manager import DeviceManager
import logging

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
            logging.info(f"开始从文件导入设备: {file_path}")
            df = pd.read_excel(file_path)
            logging.info(f"Excel文件读取成功，包含 {len(df)} 行数据")
            
            # 打印前几行数据用于调试
            if not df.empty:
                logging.debug(f"Excel数据前5行预览:\n{df.head(5)}")
            
            # 验证列名
            missing_columns = [col for col in DeviceImporter.TEMPLATE_COLUMNS if col not in df.columns]
            if missing_columns:
                error_msg = f"Excel文件格式不正确，缺少以下列：\n{', '.join(missing_columns)}\n\n请使用正确的模板"
                logging.error(error_msg)
                QMessageBox.warning(None, "导入失败", error_msg)
                return False, 0
            
            # 转换为设备数据
            devices = []
            row_errors = []
            
            # 检查是否有重复的设备名称
            device_names = df['设备名称'].dropna().astype(str).str.strip()
            
            # 查找重复项并记录它们的行号
            duplicate_info = {}
            for idx, name in enumerate(device_names):
                if name not in duplicate_info:
                    duplicate_info[name] = []
                duplicate_info[name].append(idx + 2)  # +2是因为Excel行号从1开始，而且还有标题行
            
            # 过滤出只有多个行号的项（即重复项）
            duplicate_details = {name: rows for name, rows in duplicate_info.items() if len(rows) > 1}
            
            if duplicate_details:
                duplicate_names = list(duplicate_details.keys())
                # 格式化显示重复项及其行号
                detail_msg = []
                for name, rows in duplicate_details.items():
                    detail_msg.append(f"设备名称 '{name}' 在以下行出现: {', '.join(map(str, rows))}")
                
                error_msg = f"Excel中存在重复的设备名称:\n" + "\n".join(detail_msg)
                logging.error(error_msg)
                
                # 添加自动修复选项
                reply = QMessageBox.question(
                    None, 
                    "发现重复设备名称", 
                    error_msg + "\n\n是否要自动添加后缀修复重复名称？\n(例：重复名称会变为name-1, name-2等)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 自动修复重复名称
                    logging.info("用户选择自动修复重复设备名称")
                    for name, rows in duplicate_details.items():
                        # 跳过第一个出现的名称，从第二个开始添加后缀
                        for i, row_idx in enumerate(rows[1:], 1):  
                            # 因为从第二个开始，所以索引从1开始
                            new_name = f"{name}-{i}"
                            logging.info(f"自动修改第{row_idx}行设备名称: {name} -> {new_name}")
                            # 在Pandas DataFrame中行索引要减2(Excel首行是1，有标题行)
                            df.at[row_idx-2, '设备名称'] = new_name
                    # 更新device_names，重新检测是否还有重复
                    device_names = df['设备名称'].dropna().astype(str).str.strip()
                    # 查找重复项
                    remaining_duplicates = device_names[device_names.duplicated()].unique().tolist()
                    if remaining_duplicates:
                        # 如果仍有重复，可能是自动修复后产生的新重复，再次警告
                        error_msg = f"自动修复后仍有重复设备名称，请手动修改Excel文件: {', '.join(remaining_duplicates)}"
                        logging.error(error_msg)
                        QMessageBox.warning(None, "修复失败", error_msg)
                        return False, 0
                else:
                    # 用户选择不修复，终止导入
                    return False, 0
            
            for idx, row in df.iterrows():
                # 先检查必填字段
                required_fields = [('设备名称', 'name'), ('主机名/IP', 'hostname'), ('平台类型', 'platform')]
                row_valid = True
                
                for field_name, _ in required_fields:
                    if pd.isna(row[field_name]) or str(row[field_name]).strip() == '':
                        row_errors.append(f"第{idx+2}行: 缺少必填字段 '{field_name}'")
                        row_valid = False
                        break
                
                if not row_valid:
                    continue
                
                device = {
                    'name': str(row['设备名称']).strip(),
                    'hostname': str(row['主机名/IP']).strip(),
                    'platform': str(row['平台类型']).strip(),
                    'username': str(row['用户名']).strip() if pd.notna(row['用户名']) else None,
                    'password': str(row['密码']).strip() if pd.notna(row['密码']) else None,
                    'port': int(row['端口']) if pd.notna(row['端口']) else 22,
                    'site': str(row['站点']).strip() if pd.notna(row['站点']) else None,
                    'device_type': str(row['设备类型']).strip() if pd.notna(row['设备类型']) else None,
                    'device_model': str(row['设备型号']).strip() if pd.notna(row['设备型号']) else None
                }
                devices.append(device)
                logging.debug(f"已处理第{idx+2}行: {device['name']}")
            
            # 如果所有行都有错误，直接显示错误并返回
            if not devices and row_errors:
                error_message = "导入失败，数据验证错误：\n" + "\n".join(row_errors)
                logging.error(error_message)
                QMessageBox.warning(None, "数据验证错误", error_message)
                return False, 0
            
            logging.info(f"Excel数据处理完成，有效设备数量: {len(devices)}")
            
            # 检查是否有设备名称已存在
            device_manager = DeviceManager(db)
            existing_names = []
            for device in devices:
                if device_manager.db.get_host(device['name']):
                    existing_names.append(device['name'])
            
            if existing_names:
                logging.info(f"发现{len(existing_names)}个已存在的设备名称")
            
            # 如果有设备名称已存在，询问用户是更新还是跳过
            update_mode = False
            if existing_names:
                logging.debug(f"已存在的设备名称列表: {existing_names}")
                # 使用自定义对话框来提供三个选项
                msg_box = QMessageBox()
                msg_box.setWindowTitle("设备名称已存在")
                msg_box.setText(f"发现{len(existing_names)}个设备名称已存在于数据库中。\n\n您希望如何处理？")
                msg_box.setIcon(QMessageBox.Icon.Question)
                
                update_btn = msg_box.addButton("更新现有设备", QMessageBox.ButtonRole.AcceptRole)
                add_new_btn = msg_box.addButton("仅添加新设备", QMessageBox.ButtonRole.ActionRole)
                cancel_btn = msg_box.addButton("取消导入", QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(update_btn)
                
                msg_box.exec()
                clicked_button = msg_box.clickedButton()
                
                if clicked_button == cancel_btn:
                    logging.info("用户取消了导入操作")
                    return False, 0
                update_mode = (clicked_button == update_btn)
                logging.info(f"用户选择{'更新现有设备' if update_mode else '仅添加新设备'}")
                
                # 设置更新模式标记
                class ImportContext:
                    def __init__(self):
                        self.is_update_mode = update_mode
                
                context = ImportContext()
                
                # 使用设备管理器的批量方法
                success_count, update_count = device_manager.batch_add_or_update_devices(devices, context)
            else:
                logging.info("没有发现已存在的设备名称，直接导入")
                # 使用设备管理器的批量方法
                success_count, update_count = device_manager.batch_add_or_update_devices(devices)
            
            # 合并所有错误信息
            if row_errors:
                combined_message = f"处理完成\n新增: {success_count} 个\n更新: {update_count} 个\n\n以下行数据有错误:\n" + "\n".join(row_errors)
                QMessageBox.warning(None, "部分数据导入成功", combined_message)
            
            logging.info(f"导入处理完成，新增: {success_count}，更新: {update_count}")
            return (success_count + update_count) > 0, success_count + update_count
            
        except Exception as e:
            error_msg = f"导入过程中发生错误：{str(e)}"
            logging.exception(error_msg)
            QMessageBox.critical(None, "导入失败", error_msg)
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