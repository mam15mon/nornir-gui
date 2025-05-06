import re
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QGroupBox,
    QAbstractItemView, QMenu, QTextBrowser
)
from PySide6.QtCore import QThread, Signal, QSize, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QAction
from core.device_inspector import DeviceInspector

class InspectionWorker(QThread):
    """设备检测工作线程"""
    progress = Signal(int)
    result = Signal(dict)
    finished = Signal()
    error = Signal(str)
    file_count = Signal(int)  # 新增信号：文件总数

    def __init__(self, directory_path: str, max_workers: int = None):
        super().__init__()
        self.directory_path = directory_path
        self.max_workers = max_workers
        self.processed_count = 0
        self.total_files = 0

    def run(self):
        try:
            # 首先计算文件总数
            file_paths = []
            for root, _, files in os.walk(self.directory_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_paths.append(file_path)

            self.total_files = len(file_paths)
            self.file_count.emit(self.total_files)

            if self.total_files == 0:
                self.finished.emit()
                return

            # 使用线程池处理文件
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 创建一个字典，将 Future 对象映射到文件路径
                future_to_file = {
                    executor.submit(DeviceInspector.process_file, file_path): file_path
                    for file_path in file_paths
                }

                # 处理完成的任务
                for future in concurrent.futures.as_completed(future_to_file):
                    result = future.result()
                    self.processed_count += 1

                    # 更新进度
                    progress_value = int(self.processed_count / self.total_files * 100)
                    self.progress.emit(progress_value)

                    # 如果处理成功，发送结果
                    if result.get("success", False):
                        self.result.emit(result)

            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class DeviceInspectionPage(QWidget):
    """设备检测页面"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # 顶部控制区域
        control_group = QGroupBox("控制面板")
        control_layout = QVBoxLayout()

        # 选择目录按钮
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("未选择目录")
        self.select_dir_btn = QPushButton("选择目录")
        self.select_dir_btn.clicked.connect(self.select_directory)
        dir_layout.addWidget(QLabel("目录:"))
        dir_layout.addWidget(self.dir_label, 1)
        dir_layout.addWidget(self.select_dir_btn)
        control_layout.addLayout(dir_layout)

        # 开始检测按钮和进度条
        action_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始检测")
        self.start_btn.clicked.connect(self.start_inspection)
        self.start_btn.setEnabled(False)
        action_layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        action_layout.addWidget(self.progress_bar, 1)
        control_layout.addLayout(action_layout)

        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)

        # 结果显示区域
        results_group = QGroupBox("检测结果")
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
        # 使用默认行颜色

        # 详细信息选项卡 - 使用QTreeWidget替代QTextBrowser
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["设备信息", "状态", "详情"])
        # 使用默认行颜色
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



        # 添加选项卡
        self.results_tab.addTab(self.summary_table, "摘要")
        self.results_tab.addTab(self.result_tree, "详细信息")

        # 连接摘要表格的双击事件
        self.summary_table.cellDoubleClicked.connect(self.on_summary_double_clicked)

        # 启用右键菜单
        self.summary_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.summary_table.customContextMenuRequested.connect(self.show_summary_context_menu)

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
        self.progress_bar.setFormat("准备中... %p%")  # 显示百分比和文本

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

        # 启动工作线程 - 使用线程池
        self.worker = InspectionWorker(directory, max_workers=None)  # None表示使用默认线程数
        self.worker.progress.connect(self.update_progress)
        self.worker.result.connect(self.update_result)
        self.worker.finished.connect(self.inspection_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.file_count.connect(self.update_file_count)
        self.worker.start()

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        # 更新进度条格式，显示已处理文件数和总文件数
        if hasattr(self.worker, 'processed_count') and hasattr(self.worker, 'total_files'):
            self.progress_bar.setFormat(f"处理中... {self.worker.processed_count}/{self.worker.total_files} 文件 (%p%)")

    def update_file_count(self, count):
        """更新文件计数"""
        if count == 0:
            # 没有文件可处理
            scan_item = None
            for i in range(self.result_tree.topLevelItemCount()):
                item = self.result_tree.topLevelItem(i)
                if item.text(0) == "开始检测":
                    for j in range(item.childCount()):
                        child = item.child(j)
                        if child.text(0) == "状态":
                            scan_item = child
                            break
                    break

            if scan_item:
                scan_item.setText(2, "目录中没有找到可处理的文件")
            return

        # 更新扫描状态信息
        scan_item = None
        for i in range(self.result_tree.topLevelItemCount()):
            item = self.result_tree.topLevelItem(i)
            if item.text(0) == "开始检测":
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.text(0) == "状态":
                        scan_item = child
                        break
                break

        if scan_item:
            scan_item.setText(2, f"找到 {count} 个文件，正在并行处理...")

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

        # 设置状态颜色
        normal_color = QColor("green")
        abnormal_color = QColor("orange")
        error_color = QColor("red")
        warning_color = QColor("#FFC107")  # 黄色

        # 确定总体状态
        overall_status = "正常"
        status_color = normal_color
        if status_counts["error"] > 0:
            overall_status = "错误"
            status_color = error_color
        elif status_counts["abnormal"] > 0:
            overall_status = "异常"
            status_color = abnormal_color
        elif status_counts["warning"] > 0:
            overall_status = "警告"
            status_color = warning_color

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
        self.summary_table.setItem(row_position, 1, type_item)

        # 状态
        status_item = QTableWidgetItem(overall_status)
        status_item.setFont(QFont("Arial", 9, QFont.Bold))
        # 设置状态颜色
        if status_color:
            status_item.setForeground(status_color)
        self.summary_table.setItem(row_position, 2, status_item)

        # 详情
        details = f"{status_counts['normal']}正常, {status_counts['abnormal']}异常, {status_counts['error']}错误, {status_counts['warning']}警告"
        self.summary_table.setItem(row_position, 3, QTableWidgetItem(details))

        # 更新树形视图 - 使用QTreeWidget显示结果
        # 创建设备根节点
        device_item = QTreeWidgetItem(self.result_tree)
        device_item.setText(0, file_path)
        device_item.setText(1, device_type)
        device_item.setText(2, f"状态: {overall_status}")
        # 设置状态颜色
        if status_color:
            device_item.setForeground(2, status_color)
        device_item.setExpanded(True)  # 默认展开

        # 存储文件路径作为数据，方便后续查找
        device_item.setData(0, Qt.UserRole, file_path)

        # 为每个类别创建子节点
        for category, inspection in result['results'].items():
            status = inspection.get('status', 'unknown')
            message = inspection.get('message', '')

            # 设置状态文本和颜色
            status_text = ""
            status_item_color = None
            if status == "normal":
                status_text = "✓ 正常"
                status_item_color = normal_color
            elif status == "abnormal":
                status_text = "! 异常"
                status_item_color = abnormal_color
            elif status == "error":
                status_text = "✗ 错误"
                status_item_color = error_color
            elif status == "warning":
                status_text = "⚠ 警告"
                status_item_color = warning_color
            else:
                status_text = status

            # 创建类别节点
            category_item = QTreeWidgetItem(device_item)
            category_item.setText(0, category)
            category_item.setText(1, status_text)
            category_item.setText(2, message)
            # 设置状态颜色
            if status_item_color:
                category_item.setForeground(1, status_item_color)

            # 如果有详情，添加详情子节点
            if 'details' in inspection:
                details = inspection['details']

                # 对于告警，创建一个特殊的详情显示
                if category == "alarms" and status == "abnormal":
                    # 创建告警详情父节点
                    alarm_details_item = QTreeWidgetItem(category_item)
                    alarm_details_item.setText(0, "告警详情")

                    # 获取告警文本
                    alarm_text = str(details)

                    # 创建一个纯文本显示，保持原始格式
                    text_browser = QTextBrowser()
                    text_browser.setReadOnly(True)
                    text_browser.setOpenExternalLinks(False)



                    # 直接使用原始文本，但添加HTML格式以保持格式并高亮显示
                    html_text = "<pre style='margin: 0; white-space: pre-wrap;'>"

                    # 处理文本行
                    lines = alarm_text.split('\n')

                    for line in lines:
                        # 检测表头行
                        if 'Sequence' in line and 'AlarmId' in line and 'Severity' in line:
                            html_text += f"<b>{line}</b>\n"
                        # 检测分隔线
                        elif re.match(r'^-+$', line.strip()) or re.match(r'^=+$', line.strip()):
                            html_text += f"<span style='color: #888;'>{line}</span>\n"
                        # 检测数据行（以数字开头）
                        elif re.match(r'^\d+\s+', line.strip()):
                            # 尝试高亮显示严重性级别
                            if 'Warning' in line:
                                line = line.replace('Warning', '<span style="color: #FFC107; font-weight: bold;">Warning</span>')
                            elif 'Critical' in line:
                                line = line.replace('Critical', '<span style="color: #F44336; font-weight: bold;">Critical</span>')
                            elif 'Major' in line:
                                line = line.replace('Major', '<span style="color: #FF9800; font-weight: bold;">Major</span>')
                            elif 'Minor' in line:
                                line = line.replace('Minor', '<span style="color: #8BC34A; font-weight: bold;">Minor</span>')

                            html_text += f"{line}\n"
                        # 其他行
                        else:
                            html_text += f"{line}\n"

                    html_text += "</pre>"

                    # 设置HTML文本
                    text_browser.setHtml(html_text)

                    # 设置固定高度
                    text_browser.setFixedHeight(300)  # 增加高度以显示更多内容

                    # 创建一个容器widget来放置文本浏览器
                    container = QWidget()
                    layout = QVBoxLayout(container)
                    layout.addWidget(text_browser)
                    layout.setContentsMargins(0, 0, 0, 0)
                    container.setLayout(layout)

                    # 将容器设置为树节点的widget
                    self.result_tree.setItemWidget(alarm_details_item, 2, container)

                    # 默认不展开告警详情，避免占用太多空间
                    alarm_details_item.setExpanded(False)
                else:
                    # 对于其他类别，如果详情是字典，为每个键值对创建子节点
                    if isinstance(details, dict):
                        for key, value in details.items():
                            details_item = QTreeWidgetItem(category_item)
                            details_item.setText(0, key)
                            details_item.setText(2, str(value))
                    else:
                        # 如果不是字典，直接添加详情
                        details_item = QTreeWidgetItem(category_item)
                        details_item.setText(0, "详情")
                        details_item.setText(2, str(details))

        # 自动调整列宽以适应内容
        self.result_tree.resizeColumnToContents(0)
        self.result_tree.resizeColumnToContents(1)

    def inspection_finished(self):
        """检测完成"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始检测")
        self.progress_bar.setVisible(False)

        # 设置状态颜色
        normal_color = QColor("green")
        abnormal_color = QColor("orange")
        error_color = QColor("red")
        warning_color = QColor("#FFC107")  # 黄色

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

    def on_summary_double_clicked(self, row, _):
        """处理摘要表格的双击事件，跳转到对应的详细信息"""
        # 获取文件名
        file_item = self.summary_table.item(row, 0)
        if not file_item:
            return

        file_name = file_item.text()
        file_path = file_item.toolTip()  # 完整路径存储在工具提示中

        # 切换到详细信息选项卡
        self.results_tab.setCurrentIndex(1)

        # 查找对应的设备节点
        found_item = None
        for i in range(self.result_tree.topLevelItemCount()):
            item = self.result_tree.topLevelItem(i)
            # 检查是否是设备节点（通过存储的数据或文本内容）
            if (item.data(0, Qt.UserRole) == file_path or
                item.text(0) == file_path or
                file_name in item.text(0)):
                found_item = item
                break

        # 如果找到了对应的节点，选中并滚动到该节点
        if found_item:
            self.result_tree.setCurrentItem(found_item)
            self.result_tree.scrollToItem(found_item, QAbstractItemView.PositionAtTop)
            found_item.setExpanded(True)

            # 显示一个临时高亮效果
            original_bg = found_item.background(0)
            highlight_color = QColor("#E8F5E9")  # 浅绿色高亮
            for col in range(3):
                found_item.setBackground(col, highlight_color)

            # 使用QTimer在一段时间后恢复原来的背景色
            QTimer.singleShot(1500, lambda: self.reset_highlight(found_item, original_bg))

    def show_summary_context_menu(self, position):
        """显示摘要表格的右键菜单"""
        # 获取当前选中的行
        row = self.summary_table.rowAt(position.y())
        if row < 0:
            return

        # 创建右键菜单
        menu = QMenu(self)

        # 添加跳转到详情的操作
        view_details_action = QAction("查看详细信息", self)
        view_details_action.triggered.connect(lambda: self.on_summary_double_clicked(row, 0))
        menu.addAction(view_details_action)

        # 显示菜单
        menu.exec_(self.summary_table.mapToGlobal(position))

    def reset_highlight(self, item, original_bg):
        """重置高亮效果"""
        for col in range(3):
            item.setBackground(col, original_bg)

    def handle_error(self, error_msg):
        """处理错误"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始检测")
        self.progress_bar.setVisible(False)

        # 显示错误信息
        error_item = QTreeWidgetItem(self.result_tree)
        error_item.setText(0, "错误")
        error_item.setText(2, "检测过程中发生错误")
        error_item.setExpanded(True)

        # 添加错误详情
        details_item = QTreeWidgetItem(error_item)
        details_item.setText(0, "详情")
        details_item.setText(2, error_msg)

        # 自动切换到详细信息选项卡
        self.results_tab.setCurrentIndex(1)