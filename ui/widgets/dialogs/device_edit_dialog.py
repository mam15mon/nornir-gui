from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QSpinBox, QComboBox, QPushButton,
                             QFormLayout, QMessageBox)
from PySide6.QtCore import Qt

class DeviceEditDialog(QDialog):
    """设备编辑对话框"""
    def __init__(self, device=None, parent=None):
        super().__init__(parent)
        self.device = device
        self.init_ui()
        if device:
            self.load_device_data()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑设备" if self.device else "添加设备")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft)
        
        # 创建所有表单项
        self.create_form_item(form_layout, "设备名称:", "name", QLineEdit(), enabled=not self.device)
        self.create_form_item(form_layout, "主机名/IP:", "hostname", QLineEdit())
        self.create_form_item(form_layout, "平台类型:", "platform", 
                            self.create_combo_box(['huawei','huawei_vrp', 'huawei_vrpv8', 'hp_comware']))
        self.create_form_item(form_layout, "用户名:", "username", QLineEdit())
        self.create_form_item(form_layout, "密码:", "password", self.create_password_input())
        self.create_form_item(form_layout, "端口:", "port", self.create_port_input())
        self.create_form_item(form_layout, "站点:", "site", QLineEdit())
        self.create_form_item(form_layout, "设备类型:", "device_type", 
                            self.create_combo_box(['交换机','核心交换机', '路由器', '防火墙']))
        self.create_form_item(form_layout, "设备型号:", "device_model", QLineEdit())
        
        layout.addLayout(form_layout)
        
        # 按钮组
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)

    def create_form_item(self, form_layout, label, field_name, widget, enabled=True):
        """创建统一的表单项布局"""
        layout = QHBoxLayout()
        layout.setSpacing(5)
        
        widget.setFixedWidth(200)
        widget.setEnabled(enabled)
        setattr(self, f"{field_name}_input", widget)
        
        layout.addWidget(widget)
        layout.addStretch()
        
        form_layout.addRow(label, layout)

    def create_combo_box(self, items):
        """创建下拉框"""
        combo = QComboBox()
        combo.addItems(items)
        return combo

    def create_password_input(self):
        """创建密码输入框"""
        password = QLineEdit()
        return password

    def create_port_input(self):
        """创建端口输入框"""
        port = QSpinBox()
        port.setRange(1, 65535)
        port.setValue(22)
        return port

    def load_device_data(self):
        """加载设备数据"""
        field_mappings = {
            'name': ('text', None),
            'hostname': ('text', None),
            'platform': ('setCurrentText', None),
            'username': ('text', None),
            'password': ('text', None),
            'port': ('setValue', None),
            'site': ('text', None),
            'device_type': ('setCurrentText', None),
            'device_model': ('text', None)
        }
        
        for field, (setter, _) in field_mappings.items():
            widget = getattr(self, f"{field}_input")
            value = getattr(self.device, field)
            if value is not None:
                if setter == 'text':
                    widget.setText(value)
                elif setter == 'setValue':
                    widget.setValue(value)
                elif setter == 'setCurrentText':
                    widget.setCurrentText(value)

    def get_device_data(self):
        """获取设备数据"""
        # 验证必填字段
        name = self.name_input.text().strip()
        hostname = self.hostname_input.text().strip()
        platform = self.platform_input.currentText()
        
        if not name:
            QMessageBox.warning(self, "错误", "设备名称不能为空")
            return None
            
        if not hostname:
            QMessageBox.warning(self, "错误", "主机名/IP不能为空")
            return None
            
        # 返回设备数据
        field_mappings = {
            'name': (self.name_input, 'text', 'strip'),
            'hostname': (self.hostname_input, 'text', 'strip'),
            'platform': (self.platform_input, 'currentText', None),
            'username': (self.username_input, 'text', 'strip'),
            'password': (self.password_input, 'text', None),
            'port': (self.port_input, 'value', None),
            'site': (self.site_input, 'text', 'strip'),
            'device_type': (self.device_type_input, 'currentText', None),
            'device_model': (self.device_model_input, 'text', 'strip')
        }
        
        device_data = {}
        for field, (widget, getter, processor) in field_mappings.items():
            value = getattr(widget, getter)()
            if processor:
                value = getattr(value, processor)()
            device_data[field] = value or None
                
        return device_data 