from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QSpinBox, QComboBox, QPushButton, QGroupBox,
                             QFormLayout, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt

class BatchEditDialog(QDialog):
    """批量编辑对话框"""
    def __init__(self, device_names, parent=None):
        super().__init__(parent)
        self.device_names = device_names
        self.edited_fields = {}  # 存储要修改的字段
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"批量编辑 ({len(self.device_names)} 个设备)")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft)

        # 创建所有表单项
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

    def create_form_item(self, form_layout, label, field_name, widget):
        """创建统一的表单项布局"""
        layout = QHBoxLayout()
        layout.setSpacing(5)
        
        check = QCheckBox("修改")
        widget.setFixedWidth(200)
        widget.setEnabled(False)
        
        check.stateChanged.connect(lambda state: widget.setEnabled(bool(state)))
        setattr(self, f"{field_name}_check", check)
        setattr(self, f"{field_name}_input", widget)
        
        layout.addWidget(check)
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

    def get_edited_fields(self):
        """获取要修改的字段"""
        edited_fields = {}
        
        field_mappings = {
            'hostname': (self.hostname_check, self.hostname_input, 'text', 'strip'),
            'platform': (self.platform_check, self.platform_input, 'currentText', None),
            'username': (self.username_check, self.username_input, 'text', 'strip'),
            'password': (self.password_check, self.password_input, 'text', None),
            'port': (self.port_check, self.port_input, 'value', None),
            'site': (self.site_check, self.site_input, 'text', 'strip'),
            'device_type': (self.device_type_check, self.device_type_input, 'currentText', None),
            'device_model': (self.device_model_check, self.device_model_input, 'text', 'strip')
        }
        
        for field, (check, input_widget, getter, processor) in field_mappings.items():
            if check.isChecked():
                value = getattr(input_widget, getter)()
                if processor:
                    value = getattr(value, processor)()
                edited_fields[field] = value
                
        return edited_fields 