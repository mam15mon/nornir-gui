from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QDialog, QGroupBox, QLabel, QStatusBar)
from datetime import datetime
import logging

from ..widgets.device_list.device_table import DeviceTable

logger = logging.getLogger(__name__)
from ..widgets.filters.filter_bar import FilterBar
from ..widgets.filters.search_bar import SearchBar
from ..widgets.device_list.device_manager import DeviceManager
from ..widgets.dialogs.operation_dialog import OperationDialog
from ..widgets.dialogs.result_dialog import ResultDialog
from ..widgets.thread_manager import ThreadManager
from core.event_bus import event_bus

class OperationPage(QWidget):
    """设备操作页面"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.device_manager = DeviceManager(db, self)
        self.device_status = {}  # 存储设备状态
        self.thread_manager = ThreadManager(self)  # 线程管理器
        self.init_ui()
        self.load_data()

        # 监听设备列表变化
        event_bus.device_list_changed.connect(self.load_data)

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

        # 右侧：操作按钮组
        operation_group = QGroupBox("")
        operation_layout = QHBoxLayout(operation_group)

        self.operate_btn = QPushButton("操作")
        self.operate_btn.clicked.connect(self.show_operation_dialog)
        self.operate_btn.setEnabled(False)  # 初始禁用

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_operations)
        self.stop_btn.setEnabled(False)  # 初始禁用

        operation_layout.addWidget(self.operate_btn)
        operation_layout.addWidget(self.stop_btn)
        toolbar.addWidget(operation_group)

        # 设备表格
        self.device_table = DeviceTable(
            columns=[
                ('checkbox', '选择'),
                ('name', '设备名称'),
                ('hostname', '主机名/IP'),
                ('platform', '平台类型'),
                ('site', '站点'),
                ('device_type', '设备类型'),
                ('device_model', '设备型号'),
                ('status', '状态')
            ],
            show_status=True
        )
        layout.addWidget(self.device_table)

        # 连接表格信号
        self.device_table.device_double_clicked.connect(self.on_device_double_clicked)
        self.device_table.devices_checked.connect(self.on_devices_checked)

        # 连接设备管理器信号
        self.device_manager.device_updated.connect(self.load_data)

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

    def reset_device_status(self):
        """重置所有设备状态"""
        self.device_status.clear()
        self.device_table.update_device_statuses({})

    def show_operation_dialog(self):
        """显示操作对话框"""
        device_names = self.device_table.get_checked_devices()
        if device_names:
            self.clear_all_status()  # 确保在打开对话框前清空状态
            dialog = OperationDialog(self.device_manager, device_names, self)
            if dialog.exec() == QDialog.Accepted:
                self.stop_btn.setEnabled(True)

    def show_result_dialog(self, operation_name: str, results: dict, start_time: datetime):
        """显示结果对话框"""
        try:
            dialog = ResultDialog(operation_name, results, start_time, self)
            dialog.exec()
        except KeyboardInterrupt:
            logger.info("操作被用户中断")
        except Exception as e:
            logger.error(f"显示结果对话框时发生错误: {str(e)}")
        if not self.thread_manager.has_running_threads():
            self.stop_btn.setEnabled(False)

    def update_device_status(self, device_name: str, status: str):
        """更新设备状态"""
        self.device_status[device_name] = status
        # 刷新表格以显示新状态
        self.device_table.update_device_statuses(self.device_status)

    def load_data(self):
        """加载设备数据"""
        devices = self.device_manager.get_all_devices()

        # 更新表格数据
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
        pass

    def on_devices_checked(self, device_names):
        """设备勾选事件"""
        self.operate_btn.setEnabled(len(device_names) > 0)

    def stop_operations(self):
        """停止所有操作"""
        self.thread_manager.stop_all_threads()
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        """页面关闭事件"""
        self.thread_manager.cleanup()
        event.accept()

    def clear_all_status(self):
        """清空所有设备状态显示"""
        # 清空页面和表格的状态存储
        self.device_status.clear()
        self.device_table.device_status_map.clear()  # 直接操作表格内部状态存储

        # 强制更新表格状态列
        self.device_table.update_device_statuses({})

        # 立即刷新界面
        self.device_table.viewport().update()