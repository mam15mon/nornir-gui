from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QGroupBox, QLabel, QStatusBar)
from ..widgets.device_list.device_table import DeviceTable
from ..widgets.device_list.device_manager import DeviceManager
from ..widgets.filters.filter_bar import FilterBar
from ..widgets.filters.search_bar import SearchBar
from ..widgets.dialogs.batch_edit_dialog import BatchEditDialog
from ..widgets.dialogs.device_edit_dialog import DeviceEditDialog
from ..widgets.dialogs.import_dialog import ImportDialog
from ..widgets.importers.device_importer import DeviceImporter
from core.event_bus import event_bus

class InventoryPage(QWidget):
    """库存管理页面"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.device_manager = DeviceManager(db, self)
        self.init_ui()
        self.load_data()
        
        # 监听设备列表变化
        event_bus.device_list_changed.connect(self.load_data)
        self.device_manager.device_updated.connect(self.load_data)

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        # 左侧：搜索框
        self.search_bar = SearchBar()
        self.search_bar.textChanged.connect(self.on_search)
        toolbar.addWidget(self.search_bar)

        # 右侧：筛选栏
        self.filter_bar = FilterBar()
        self.filter_bar.filterChanged.connect(self.on_filter)
        toolbar.addWidget(self.filter_bar)

        # 右侧：按钮组
        button_layout = QHBoxLayout()
        toolbar.addLayout(button_layout)
        
        # 设备操作组
        device_group = QGroupBox("")
        device_layout = QHBoxLayout(device_group)
        self.add_btn = QPushButton("添加设备")
        self.batch_edit_btn = QPushButton("批量编辑")
        self.batch_delete_btn = QPushButton("批量删除")
        device_layout.addWidget(self.add_btn)
        device_layout.addWidget(self.batch_edit_btn)
        device_layout.addWidget(self.batch_delete_btn)
        button_layout.addWidget(device_group)
        
        # 数据操作组
        data_group = QGroupBox("")
        data_layout = QHBoxLayout(data_group)
        self.import_btn = QPushButton("导入")
        self.export_btn = QPushButton("导出")
        data_layout.addWidget(self.import_btn)
        data_layout.addWidget(self.export_btn)
        button_layout.addWidget(data_group)

        # 设置按钮点击事件
        self.add_btn.clicked.connect(self.on_add_device)
        self.batch_edit_btn.clicked.connect(self.on_batch_edit)
        self.batch_delete_btn.clicked.connect(self.on_batch_delete)
        self.import_btn.clicked.connect(self.on_import_devices)
        self.export_btn.clicked.connect(self.on_export_devices)

        # 初始化禁用按钮
        self.batch_edit_btn.setEnabled(False)
        self.batch_delete_btn.setEnabled(False)

        # 设备表格
        self.device_table = DeviceTable(show_status=False)
        self.device_table.device_double_clicked.connect(self.on_device_double_clicked)
        self.device_table.devices_checked.connect(self.on_devices_checked)
        layout.addWidget(self.device_table)
        
        # 添加状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)  # 禁用右下角大小调整控件
        layout.addWidget(self.status_bar)
        
        # 状态栏标签
        self.device_stats_label = QLabel("总设备: 0 | 已选择: 0")
        self.status_bar.addWidget(self.device_stats_label)
        
        # 连接设备表格的stats_changed信号
        self.device_table.stats_changed.connect(self.update_status_bar)

    def update_status_bar(self, total_devices, checked_devices):
        """更新状态栏信息"""
        self.device_stats_label.setText(f"总设备: {total_devices} | 已选择: {checked_devices}")

    def load_data(self):
        """加载设备数据"""
        devices = self.device_manager.get_all_devices()
        self.device_table.update_data(devices)
        
        # 更新筛选选项
        sites = [device.site for device in devices if device.site]
        device_types = [device.device_type for device in devices if device.device_type]
        platforms = [device.platform for device in devices if device.platform]
        
        self.filter_bar.update_filter_items('site', list(set(sites)))
        self.filter_bar.update_filter_items('device_type', list(set(device_types)))
        self.filter_bar.update_filter_items('platform', list(set(platforms)))

    def on_search(self, text):
        """搜索功能"""
        self.device_table.set_search_text(text)

    def on_filter(self, filter_type, value):
        """筛选条件改变"""
        self.device_table.apply_filters(self.filter_bar.get_filter_values())

    def on_device_double_clicked(self, device_name):
        """设备双击事件"""
        device = self.device_manager.get_device_by_name(device_name)
        if device:
            dialog = DeviceEditDialog(device, self)
            if dialog.exec():
                device_data = dialog.get_device_data()
                if device_data:
                    self.device_manager.update_device(device_name, device_data)

    def on_devices_checked(self, device_names):
        """设备勾选事件"""
        has_checked = len(device_names) > 0
        self.batch_edit_btn.setEnabled(has_checked)
        self.batch_delete_btn.setEnabled(has_checked)

    def on_add_device(self):
        """添加设备"""
        dialog = DeviceEditDialog(parent=self)
        if dialog.exec():
            device_data = dialog.get_device_data()
            if device_data:
                self.device_manager.add_device(device_data)

    def on_batch_edit(self):
        """批量编辑设备"""
        device_names = self.device_table.get_checked_devices()
        if device_names:
            dialog = BatchEditDialog(device_names, self)
            if dialog.exec():
                edited_fields = dialog.get_edited_fields()
                self.device_manager.batch_edit_devices(device_names, edited_fields, self)

    def on_batch_delete(self):
        """批量删除设备"""
        device_names = self.device_table.get_checked_devices()
        if device_names:
            self.device_manager.batch_delete_devices(device_names, self)

    def on_import_devices(self):
        """导入设备"""
        dialog = ImportDialog(self.device_manager.db, self)
        if dialog.exec():
            self.load_data()

    def on_export_devices(self):
        """导出设备"""
        devices = self.device_manager.get_all_devices()
        DeviceImporter.export_devices(self, devices) 