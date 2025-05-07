from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTextBrowser, QTabWidget,
                             QWidget, QScrollArea, QTreeWidget, QHeaderView,
                             QAbstractItemView)
from PySide6.QtCore import QUrl, Qt, QTimer, QSize
from PySide6.QtGui import QColor, QFont
from datetime import datetime

from .result_tree_builder import ResultTreeBuilder
from .overview_formatter import OverviewFormatter
from .file_handler import FileHandler

class ResultDialog(QDialog):
    """结果统计对话框"""

    def __init__(self, operation_name: str, results: dict, start_time: datetime, parent=None):
        """
        Args:
            operation_name: 操作名称（如"连接测试"）
            results: 结果字典 {device_name: {'status': str, 'result': str, 'output_file': str}}
            start_time: 开始时间
            parent: 父窗口
        """
        super().__init__(parent)
        self.operation_name = operation_name
        self.results = results
        self.start_time = start_time
        self.overview_text = QTextBrowser()  # 创建概览文本浏览器
        self.init_ui()
        self.setup_hyperlink()

    def setup_hyperlink(self):
        """设置超链接点击事件"""
        self.overview_text.anchorClicked.connect(self.on_anchor_clicked)
        self.overview_text.setOpenLinks(False)

    def on_anchor_clicked(self, url):
        """处理锚点点击事件"""
        url_str = url.toString()

        # 如果是文件链接，打开文件
        if url_str.startswith("file:"):
            FileHandler.open_file(url.toLocalFile())
            return

        # 如果是设备链接，跳转到详细信息
        if url_str.startswith("device:"):
            device_name = url_str.replace("device:", "")
            self.jump_to_device_details(device_name)
            return

    def jump_to_device_details(self, device_name):
        """跳转到设备详细信息"""
        # 切换到详细信息选项卡
        tab_widget = self.findChild(QTabWidget)
        if tab_widget:
            tab_widget.setCurrentIndex(1)  # 详细信息选项卡的索引

        # 查找对应的设备节点
        for i in range(self.result_tree.topLevelItemCount()):
            item = self.result_tree.topLevelItem(i)
            if item.text(0) == device_name:
                # 选中并滚动到该节点
                self.result_tree.setCurrentItem(item)
                self.result_tree.scrollToItem(item, QAbstractItemView.PositionAtTop)
                item.setExpanded(True)

                # 显示一个临时高亮效果
                original_bg = item.background(0)
                highlight_color = QColor("#E8F5E9")  # 浅绿色高亮
                for col in range(3):
                    item.setBackground(col, highlight_color)

                # 使用QTimer在一段时间后恢复原来的背景色
                QTimer.singleShot(1500, lambda: self.reset_highlight(item, original_bg))
                break

    def reset_highlight(self, item, original_bg):
        """重置高亮效果"""
        for col in range(3):
            item.setBackground(col, original_bg)

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"{self.operation_name} - 结果")
        self.resize(1000, 800)  # 增加默认窗口大小

        main_layout = QVBoxLayout(self)
        tab_widget = QTabWidget()

        # 概览选项卡
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)

        # 统计信息
        stats_layout = QHBoxLayout()

        # 统计所有设备的结果
        total_devices = len(self.results)
        success_count = sum(1 for result in self.results.values() if '成功' in result.get('status', ''))
        failed_count = total_devices - success_count

        stats_layout.addWidget(QLabel(f"总设备数: {total_devices}"))
        stats_layout.addWidget(QLabel(f"成功: {success_count}"))
        stats_layout.addWidget(QLabel(f"失败: {failed_count}"))

        if self.start_time:
            duration = datetime.now() - self.start_time
            stats_layout.addWidget(QLabel(f"耗时: {duration.total_seconds():.2f}秒"))

        overview_layout.addLayout(stats_layout)

        # 创建概览的滚动区域
        overview_scroll = QScrollArea()
        overview_scroll.setWidgetResizable(True)
        overview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        overview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建概览内容容器
        overview_content_widget = QWidget()
        overview_content_layout = QVBoxLayout(overview_content_widget)

        # 概览显示 - 显示所有设备
        self.overview_text.setReadOnly(True)
        self.overview_text.setMinimumHeight(400)  # 设置最小高度

        # 格式化概览内容 - 显示所有设备
        overview_html = OverviewFormatter.format_all_devices(self.results)
        self.overview_text.setHtml(overview_html)

        overview_content_layout.addWidget(self.overview_text)

        # 设置滚动区域的内容
        overview_scroll.setWidget(overview_content_widget)
        overview_layout.addWidget(overview_scroll)

        tab_widget.addTab(overview_tab, "概览")

        # 详细信息选项卡
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)

        # 创建树形视图
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["设备信息", "状态", "详情"])
        self.result_tree.setColumnCount(3)

        # 设置列宽
        header = self.result_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        # 设置行高和字体
        self.result_tree.setFont(QFont("Arial", 9))
        self.result_tree.setIconSize(QSize(16, 16))
        self.result_tree.setUniformRowHeights(False)  # 允许不同行高
        self.result_tree.setWordWrap(True)  # 启用自动换行

        # 设置滚动行为
        self.result_tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.result_tree.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        # 添加设备结果到树形视图
        tree_builder = ResultTreeBuilder(self.result_tree)
        tree_builder.add_results(self.results)

        details_layout.addWidget(self.result_tree)

        tab_widget.addTab(details_tab, "详细信息")
        main_layout.addWidget(tab_widget)

        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button)
