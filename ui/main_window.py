from PySide6.QtWidgets import QMainWindow, QTabWidget
from PySide6.QtCore import Qt

from .pages.inventory_page import InventoryPage
from .pages.operation_page import OperationPage
from .pages.settings_page import SettingsPage
from core.db.database import Database
from core.proxy_manager import ProxyManager
from core.event_bus import event_bus

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.proxy_manager = ProxyManager()
        self.init_ui()
        self.init_proxy()
        
        # 监听设置变化
        event_bus.settings_changed.connect(self.on_settings_changed)

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('Nornir GUI')
        self.setMinimumSize(800, 600)

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        # 添加样式表使标签居中
        self.tab_widget.setStyleSheet("QTabWidget::tab-bar { alignment: center; }")
        self.setCentralWidget(self.tab_widget)

        # 添加所有页面
        self.operation_page = OperationPage(self.db, self)
        self.tab_widget.addTab(self.operation_page, "设备操作")

        self.inventory_page = InventoryPage(self.db, self)
        self.tab_widget.addTab(self.inventory_page, "设备库存管理")

        self.settings_page = SettingsPage(self)
        self.tab_widget.addTab(self.settings_page, "系统设置")

        # 设置默认显示设备操作页
        self.tab_widget.setCurrentIndex(0)
        
    def init_proxy(self):
        """初始化代理设置"""
        self.proxy_manager.apply_proxy()
        
    def on_settings_changed(self):
        """设置变化时的处理"""
        self.proxy_manager.apply_proxy() 