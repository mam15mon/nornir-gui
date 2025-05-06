from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QGroupBox, QApplication,
    QAbstractItemView
)
from PySide6.QtCore import QThread, Signal, QSize
from PySide6.QtGui import QColor, QFont, QPalette
from core.device_inspector import DeviceInspector

class InspectionWorker(QThread):
    """设备检测工作线程"""
    progress = Signal(int)
    result = Signal(dict)
    finished = Signal()
    error = Signal(str)

    def __init__(self, directory_path: str):
        super().__init__()
        self.directory_path = directory_path

    def run(self):
        try:
            results = DeviceInspector.read_files_in_directory(self.directory_path)
            for i, result in enumerate(results):
                self.result.emit(result)
                self.progress.emit(int((i + 1) / len(results) * 100))
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class DeviceInspectionPage(QWidget):
    """设备检测页面"""

    def __init__(self):
        super().__init__()
        self.is_dark_theme = self.detect_dark_theme()
        self.init_ui()

    def detect_dark_theme(self):
        """检测是否为暗色主题"""
        app = QApplication.instance()
        if app:
            palette = app.palette()
            bg_color = palette.color(QPalette.Window)
            # 如果背景色较暗，则认为是暗色主题
            return bg_color.lightness() < 128
        return False

    def init_ui(self):
        main_layout = QVBoxLayout()

        # 根据主题设置样式
        if self.is_dark_theme:
            # 暗色主题样式
            select_btn_style = "background-color: #388E3C; color: white; font-weight: bold;"
            start_btn_style = "background-color: #1976D2; color: white; font-weight: bold; min-height: 30px;"
            progress_bar_style = "QProgressBar {border: 1px solid #555; border-radius: 3px; text-align: center; background-color: #333;} " \
                                "QProgressBar::chunk {background-color: #1976D2;}"
            table_style = "alternate-background-color: #3A3A3A;"
            group_box_style = "QGroupBox {border: 1px solid #555; border-radius: 5px; margin-top: 1ex; padding: 10px;} " \
                             "QGroupBox::title {subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px;}"
        else:
            # 亮色主题样式
            select_btn_style = "background-color: #4CAF50; color: white; font-weight: bold;"
            start_btn_style = "background-color: #2196F3; color: white; font-weight: bold; min-height: 30px;"
            progress_bar_style = "QProgressBar {border: 1px solid grey; border-radius: 3px; text-align: center;} " \
                                "QProgressBar::chunk {background-color: #2196F3;}"
            table_style = "alternate-background-color: #f2f2f2;"
            group_box_style = "QGroupBox {border: 1px solid #ccc; border-radius: 5px; margin-top: 1ex; padding: 10px;} " \
                             "QGroupBox::title {subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px;}"

        # 顶部控制区域
        control_group = QGroupBox("控制面板")
        control_group.setStyleSheet(group_box_style)
        control_layout = QVBoxLayout()

        # 选择目录按钮
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("未选择目录")
        self.dir_label.setStyleSheet("font-weight: bold;")
        self.select_dir_btn = QPushButton("选择目录")
        self.select_dir_btn.setStyleSheet(select_btn_style)
        self.select_dir_btn.clicked.connect(self.select_directory)
        dir_layout.addWidget(QLabel("目录:"))
        dir_layout.addWidget(self.dir_label, 1)
        dir_layout.addWidget(self.select_dir_btn)
        control_layout.addLayout(dir_layout)

        # 开始检测按钮和进度条
        action_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始检测")
        self.start_btn.setStyleSheet(start_btn_style)
        self.start_btn.clicked.connect(self.start_inspection)
        self.start_btn.setEnabled(False)
        action_layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(progress_bar_style)
        action_layout.addWidget(self.progress_bar, 1)
        control_layout.addLayout(action_layout)

        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)

        # 结果显示区域
        results_group = QGroupBox("检测结果")
        results_group.setStyleSheet(group_box_style)
        results_layout = QVBoxLayout()

        # 使用选项卡组织结果
        self.results_tab = QTabWidget()

        # 摘要选项卡
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(4)
        self.summary_table.setHorizontalHeaderLabels(["文件", "设备类型", "状态", "详情"])
        self.summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.summary_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.summary_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.summary_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setStyleSheet(table_style)

        # 详细信息选项卡 - 使用QTreeWidget替代QTextBrowser
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["设备信息", "状态", "详情"])
        self.result_tree.setAlternatingRowColors(True)
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

        # 为暗色主题设置样式
        if self.is_dark_theme:
            self.result_tree.setStyleSheet("""
                QTreeWidget {
                    background-color: #2D2D2D;
                    color: #E0E0E0;
                    border: 1px solid #444;
                }
                QTreeWidget::item {
                    padding: 5px;
                    border-bottom: 1px solid #444;
                    min-height: 22px;
                }
                QTreeWidget::item:selected {
                    background-color: #37474F;
                }
                QTreeWidget QHeaderView::section {
                    background-color: #424242;
                    color: #E0E0E0;
                    padding: 5px;
                    border: 1px solid #555;
                }
                QScrollBar:vertical {
                    background: #2D2D2D;
                    width: 12px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #555;
                    min-height: 20px;
                    border-radius: 6px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)

        # 添加选项卡
        self.results_tab.addTab(self.summary_table, "摘要")
        self.results_tab.addTab(self.result_tree, "详细信息")

        results_layout.addWidget(self.results_tab)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group, 1)  # 让结果区域占据更多空间

        self.setLayout(main_layout)

    def select_directory(self):
        """选择要检测的目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择目录")
        if directory:
            self.dir_label.setText(directory)
            self.start_btn.setEnabled(True)

    def start_inspection(self):
        """开始检测"""
        directory = self.dir_label.text()
        if directory == "未选择目录":
            return

        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.start_btn.setText("检测中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # 清空之前的结果
        self.result_tree.clear()
        self.summary_table.setRowCount(0)

        # 检查是否已经存在"开始检测"节点，避免重复添加
        for i in range(self.result_tree.topLevelItemCount()):
            item = self.result_tree.topLevelItem(i)
            if item.text(0) == "开始检测":
                self.result_tree.takeTopLevelItem(i)
                break

        # 添加开始信息到树形视图
        start_item = QTreeWidgetItem(self.result_tree)
        start_item.setText(0, "开始检测")
        start_item.setText(2, f"目录: {directory}")

        # 添加扫描信息
        scan_item = QTreeWidgetItem(start_item)
        scan_item.setText(0, "状态")
        scan_item.setText(2, "正在扫描文件并执行设备检测，请稍候...")
        start_item.setExpanded(True)

        # 启动工作线程
        self.worker = InspectionWorker(directory)
        self.worker.progress.connect(self.update_progress)
        self.worker.result.connect(self.update_result)
        self.worker.finished.connect(self.inspection_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)

    def update_result(self, result):
        """更新检测结果"""
        file_path = result['file_path']
        device_type = result['device_type']

        # 计算总体状态
        status_counts = {"normal": 0, "abnormal": 0, "error": 0, "warning": 0}
        for category, inspection in result['results'].items():
            status = inspection.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1

        # 设置颜色方案（根据主题调整）
        if self.is_dark_theme:
            # 暗色主题颜色
            status_color_normal = QColor("#4CAF50")  # 深绿色
            status_color_warning = QColor("#FFC107")  # 黄色
            status_color_abnormal = QColor("#FF9800")  # 橙色
            status_color_error = QColor("#F44336")  # 红色

            h3c_color = QColor("#64B5F6")  # 浅蓝色
            huawei_color = QColor("#81C784")  # 浅绿色

            category_color = QColor("#BBDEFB")  # 浅蓝色类别
        else:
            # 亮色主题颜色
            status_color_normal = QColor("green")
            status_color_warning = QColor("#FFC107")  # 黄色
            status_color_abnormal = QColor("orange")
            status_color_error = QColor("red")

            h3c_color = QColor("#2196F3")  # 蓝色
            huawei_color = QColor("#4CAF50")  # 绿色

            category_color = QColor("#0D47A1")  # 深蓝色类别

        # 确定总体状态
        overall_status = "正常"
        status_color = status_color_normal
        if status_counts["error"] > 0:
            overall_status = "错误"
            status_color = status_color_error
        elif status_counts["abnormal"] > 0:
            overall_status = "异常"
            status_color = status_color_abnormal
        elif status_counts["warning"] > 0:
            overall_status = "警告"
            status_color = status_color_warning

        # 添加到摘要表格
        row_position = self.summary_table.rowCount()
        self.summary_table.insertRow(row_position)

        # 文件名（只显示文件名，不显示完整路径）
        file_name = file_path.split('\\')[-1]
        file_item = QTableWidgetItem(file_name)
        file_item.setToolTip(file_path)  # 完整路径显示为工具提示
        self.summary_table.setItem(row_position, 0, file_item)

        # 设备类型
        type_item = QTableWidgetItem(device_type)
        if device_type == "h3c":
            type_item.setForeground(h3c_color)
        elif device_type == "huawei":
            type_item.setForeground(huawei_color)
        self.summary_table.setItem(row_position, 1, type_item)

        # 状态
        status_item = QTableWidgetItem(overall_status)
        status_item.setForeground(status_color)
        status_item.setFont(QFont("Arial", 9, QFont.Bold))
        self.summary_table.setItem(row_position, 2, status_item)

        # 详情
        details = f"{status_counts['normal']}正常, {status_counts['abnormal']}异常, {status_counts['error']}错误, {status_counts['warning']}警告"
        self.summary_table.setItem(row_position, 3, QTableWidgetItem(details))

        # 更新树形视图 - 使用QTreeWidget显示结果
        device_color = h3c_color if device_type == "h3c" else (huawei_color if device_type == "huawei" else QColor("#888"))

        # 创建设备根节点
        device_item = QTreeWidgetItem(self.result_tree)
        device_item.setText(0, file_path)
        device_item.setText(1, device_type)
        device_item.setText(2, f"状态: {overall_status}")
        device_item.setForeground(0, device_color)
        device_item.setForeground(1, device_color)
        device_item.setForeground(2, status_color)
        device_item.setExpanded(True)  # 默认展开

        # 为每个类别创建子节点
        for category, inspection in result['results'].items():
            status = inspection.get('status', 'unknown')
            message = inspection.get('message', '')

            # 设置状态颜色和图标
            status_text = ""
            if status == "normal":
                status_text = "✓ 正常"
                status_item_color = status_color_normal
            elif status == "abnormal":
                status_text = "! 异常"
                status_item_color = status_color_abnormal
            elif status == "error":
                status_text = "✗ 错误"
                status_item_color = status_color_error
            elif status == "warning":
                status_text = "⚠ 警告"
                status_item_color = status_color_warning
            else:
                status_text = status
                status_item_color = QColor("#888")

            # 创建类别节点
            category_item = QTreeWidgetItem(device_item)
            category_item.setText(0, category)
            category_item.setText(1, status_text)
            category_item.setText(2, message)
            category_item.setForeground(0, category_color)
            category_item.setForeground(1, status_item_color)

            # 如果有详情，添加详情子节点
            if 'details' in inspection:
                details = inspection['details']

                # 对于告警，创建一个特殊的详情显示
                if category == "alarms" and status == "abnormal":
                    # 创建告警详情父节点
                    alarm_details_item = QTreeWidgetItem(category_item)
                    alarm_details_item.setText(0, "告警详情")
                    alarm_details_item.setForeground(0, QColor("#888"))

                    # 将告警内容按行分割，每行创建一个子节点
                    alarm_lines = str(details).split('\n')
                    for i, line in enumerate(alarm_lines):
                        if line.strip():  # 跳过空行
                            line_item = QTreeWidgetItem(alarm_details_item)
                            # 对于表头行或分隔线行，使用粗体显示
                            if '---' in line or 'Sequence' in line or 'AlarmId' in line or 'Severity' in line:
                                line_item.setFont(0, QFont("Arial", 9, QFont.Bold))
                            line_item.setText(0, line)

                    # 默认不展开告警详情，避免占用太多空间
                    alarm_details_item.setExpanded(False)
                else:
                    # 对于其他类别，如果详情是字典，为每个键值对创建子节点
                    if isinstance(details, dict):
                        for key, value in details.items():
                            details_item = QTreeWidgetItem(category_item)
                            details_item.setText(0, key)
                            details_item.setText(2, str(value))
                            details_item.setForeground(0, QColor("#888"))
                    else:
                        # 如果不是字典，直接添加详情
                        details_item = QTreeWidgetItem(category_item)
                        details_item.setText(0, "详情")
                        details_item.setText(2, str(details))
                        details_item.setForeground(0, QColor("#888"))

        # 自动调整列宽以适应内容
        self.result_tree.resizeColumnToContents(0)
        self.result_tree.resizeColumnToContents(1)

    def inspection_finished(self):
        """检测完成"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始检测")
        self.progress_bar.setVisible(False)

        # 根据主题设置颜色
        if self.is_dark_theme:
            normal_color = QColor("#4CAF50")  # 深绿色
            warning_color = QColor("#FFC107")  # 黄色
            abnormal_color = QColor("#FF9800")  # 橙色
            error_color = QColor("#F44336")  # 红色
        else:
            normal_color = QColor("green")
            warning_color = QColor("#FFC107")  # 黄色
            abnormal_color = QColor("orange")
            error_color = QColor("red")

        # 添加完成信息
        total_devices = self.summary_table.rowCount()

        # 检查是否已经存在"检测完成"节点，避免重复添加
        existing_summary = None
        for i in range(self.result_tree.topLevelItemCount()):
            item = self.result_tree.topLevelItem(i)
            if item.text(0) == "检测完成":
                existing_summary = item
                break

        # 如果已存在，则移除它
        if existing_summary:
            self.result_tree.takeTopLevelItem(self.result_tree.indexOfTopLevelItem(existing_summary))

        # 创建统计信息节点
        summary_item = QTreeWidgetItem(self.result_tree)
        summary_item.setText(0, "检测完成")
        summary_item.setText(2, f"共检测了 {total_devices} 个设备文件")
        summary_item.setForeground(0, normal_color)
        summary_item.setExpanded(True)

        # 统计各种状态的设备数量
        status_counts = {"正常": 0, "异常": 0, "错误": 0, "警告": 0}
        for row in range(total_devices):
            status_item = self.summary_table.item(row, 2)
            if status_item:
                status = status_item.text()
                if status in status_counts:
                    status_counts[status] += 1

        # 添加统计信息子节点
        normal_item = QTreeWidgetItem(summary_item)
        normal_item.setText(0, "正常")
        normal_item.setText(2, f"{status_counts['正常']}个设备")
        normal_item.setForeground(0, normal_color)

        abnormal_item = QTreeWidgetItem(summary_item)
        abnormal_item.setText(0, "异常")
        abnormal_item.setText(2, f"{status_counts['异常']}个设备")
        abnormal_item.setForeground(0, abnormal_color)

        error_item = QTreeWidgetItem(summary_item)
        error_item.setText(0, "错误")
        error_item.setText(2, f"{status_counts['错误']}个设备")
        error_item.setForeground(0, error_color)

        warning_item = QTreeWidgetItem(summary_item)
        warning_item.setText(0, "警告")
        warning_item.setText(2, f"{status_counts['警告']}个设备")
        warning_item.setForeground(0, warning_color)

        # 自动切换到详细信息选项卡
        self.results_tab.setCurrentIndex(1)

    def handle_error(self, error_msg):
        """处理错误"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始检测")
        self.progress_bar.setVisible(False)

        # 根据主题设置颜色
        if self.is_dark_theme:
            error_color = QColor("#F44336")  # 红色
        else:
            error_color = QColor("red")

        # 显示错误信息
        error_item = QTreeWidgetItem(self.result_tree)
        error_item.setText(0, "错误")
        error_item.setText(2, "检测过程中发生错误")
        error_item.setForeground(0, error_color)
        error_item.setForeground(2, error_color)
        error_item.setExpanded(True)

        # 添加错误详情
        details_item = QTreeWidgetItem(error_item)
        details_item.setText(0, "详情")
        details_item.setText(2, error_msg)

        # 自动切换到详细信息选项卡
        self.results_tab.setCurrentIndex(1)