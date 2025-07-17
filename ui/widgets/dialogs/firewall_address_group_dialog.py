from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QPushButton, QLabel, QTextEdit, QLineEdit, QComboBox,
                             QGroupBox, QMessageBox, QButtonGroup, QRadioButton)
from PySide6.QtCore import Qt, Signal
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class FirewallAddressGroupDialog(QDialog):
    """防火墙地址组管理对话框"""
    
    # 定义信号
    operation_requested = Signal(str, list, str)  # (operation_type, ip_addresses, group_name)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("防火墙地址组管理")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 操作类型选择
        operation_group = QGroupBox("操作类型")
        operation_layout = QHBoxLayout(operation_group)
        
        self.operation_group = QButtonGroup()
        
        self.add_radio = QRadioButton("添加地址")
        self.add_radio.setChecked(True)  # 默认选中
        self.operation_group.addButton(self.add_radio, 0)
        operation_layout.addWidget(self.add_radio)
        
        self.delete_radio = QRadioButton("删除地址")
        self.operation_group.addButton(self.delete_radio, 1)
        operation_layout.addWidget(self.delete_radio)
        
        operation_layout.addStretch()
        layout.addWidget(operation_group)
        
        # 地址组名称
        form_layout = QFormLayout()
        
        self.group_name_edit = QLineEdit()
        self.group_name_edit.setText("BlackList-nornir")  # 默认值
        self.group_name_edit.setPlaceholderText("输入地址组名称")
        form_layout.addRow("地址组名称:", self.group_name_edit)
        
        layout.addLayout(form_layout)
        
        # IP地址输入区域
        ip_group = QGroupBox("IP地址列表")
        ip_layout = QVBoxLayout(ip_group)
        
        # 说明标签
        help_label = QLabel(
            "请输入IP地址，每行一个。支持以下格式：\n"
            "• 单个IP：10.10.1.2\n"
            "• 带掩码：10.10.1.2/32\n"
            "• 网段：10.10.1.0/24"
        )
        help_label.setStyleSheet("color: #666; font-size: 12px;")
        ip_layout.addWidget(help_label)
        
        # IP地址输入框
        self.ip_text_edit = QTextEdit()
        self.ip_text_edit.setPlaceholderText(
            "示例：\n"
            "10.10.1.2\n"
            "10.10.1.3/32\n"
            "192.168.1.0/24"
        )
        self.ip_text_edit.setMinimumHeight(150)
        ip_layout.addWidget(self.ip_text_edit)
        
        layout.addWidget(ip_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept_operation)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        self.operation_group.buttonClicked.connect(self.on_operation_changed)
        
    def on_operation_changed(self):
        """操作类型改变时的处理"""
        if self.add_radio.isChecked():
            self.setWindowTitle("防火墙地址组管理 - 添加地址")
            self.ok_button.setText("添加")
        else:
            self.setWindowTitle("防火墙地址组管理 - 删除地址")
            self.ok_button.setText("删除")
    
    def validate_inputs(self) -> Tuple[bool, str]:
        """验证输入"""
        # 检查地址组名称
        group_name = self.group_name_edit.text().strip()
        if not group_name:
            return False, "请输入地址组名称"
        
        # 检查IP地址
        ip_text = self.ip_text_edit.toPlainText().strip()
        if not ip_text:
            return False, "请输入至少一个IP地址"
        
        # 解析IP地址
        ip_addresses = []
        lines = ip_text.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # 简单的IP地址格式验证
            if not self._is_valid_ip_format(line):
                return False, f"第{i}行IP地址格式错误: {line}"
            
            ip_addresses.append(line)
        
        if not ip_addresses:
            return False, "没有找到有效的IP地址"
        
        return True, ""
    
    def _is_valid_ip_format(self, ip_str: str) -> bool:
        """简单的IP地址格式验证"""
        try:
            from ipaddress import IPv4Network
            
            if '/' in ip_str:
                # 网络地址格式
                IPv4Network(ip_str, strict=False)
            else:
                # 单个IP地址
                IPv4Network(f"{ip_str}/32", strict=False)
            return True
        except:
            return False
    
    def get_ip_addresses(self) -> List[str]:
        """获取IP地址列表"""
        ip_text = self.ip_text_edit.toPlainText().strip()
        ip_addresses = []
        
        for line in ip_text.split('\n'):
            line = line.strip()
            if line and self._is_valid_ip_format(line):
                ip_addresses.append(line)
        
        return ip_addresses
    
    def get_operation_type(self) -> str:
        """获取操作类型"""
        return "add" if self.add_radio.isChecked() else "delete"
    
    def get_group_name(self) -> str:
        """获取地址组名称"""
        return self.group_name_edit.text().strip()
    
    def accept_operation(self):
        """确认操作"""
        # 验证输入
        is_valid, error_msg = self.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return
        
        # 获取参数
        operation_type = self.get_operation_type()
        ip_addresses = self.get_ip_addresses()
        group_name = self.get_group_name()
        
        # 确认操作
        operation_text = "添加" if operation_type == "add" else "删除"
        confirm_msg = (
            f"确认要{operation_text}以下IP地址到地址组 '{group_name}' 吗？\n\n"
            f"IP地址列表：\n" + "\n".join(f"• {ip}" for ip in ip_addresses)
        )
        
        reply = QMessageBox.question(
            self, 
            f"确认{operation_text}操作", 
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 发送信号
            self.operation_requested.emit(operation_type, ip_addresses, group_name)
            self.accept()
    
    def show_example(self):
        """显示示例"""
        example_text = (
            "# 示例IP地址\n"
            "10.10.1.2\n"
            "10.10.1.3/32\n"
            "192.168.1.0/24\n"
            "172.16.0.0/16"
        )
        self.ip_text_edit.setPlainText(example_text)
