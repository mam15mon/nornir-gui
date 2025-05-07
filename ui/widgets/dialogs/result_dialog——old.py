from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTextBrowser, QTabWidget,
                             QWidget, QFrame, QScrollArea, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QAbstractItemView, QMenu)
from PySide6.QtCore import QUrl, Qt, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QAction
from datetime import datetime
import os
import re
import subprocess
import sys

class DeviceResultWidget(QFrame):
    """单个设备结果显示组件"""

    def __init__(self, device_name, result, parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self.result = result
        self.inspection_result = result.get('inspection_result', {})

        # 如果是巡检结果，使用特殊处理
        if self.inspection_result:
            self.full_text = self._format_inspection_result()
        else:
            self.full_text = result.get('result', '')

        self.lines = self.full_text.split('\n') if self.full_text else []
        self.current_line = 200  # 初始显示行数

        # 创建UI组件
        self.text_browser = QTextBrowser()
        self.line_info = QLabel()

        # 初始化UI
        self.init_ui()

        # 设置超链接点击事件
        self.text_browser.setOpenExternalLinks(True)

    def _format_inspection_result(self):
        """格式化巡检结果为文本"""
        lines = []
        lines.append("巡检结果详情:")
        lines.append("")

        # 添加状态统计
        status_counts = {"normal": 0, "abnormal": 0, "error": 0, "warning": 0}
        for item in self.inspection_result.values():
            item_status = item.get('status', 'unknown')
            if item_status in status_counts:
                status_counts[item_status] += 1

        lines.append(f"状态统计: {status_counts['normal']}正常, {status_counts['abnormal']}异常, {status_counts['error']}错误, {status_counts['warning']}警告")
        lines.append("")

        # 添加各项检查结果
        for category, item in self.inspection_result.items():
            status = item.get('status', 'unknown')
            message = item.get('message', '')

            # 设置状态图标
            status_icon = "✓"
            if status == 'abnormal':
                status_icon = "!"
            elif status == 'error':
                status_icon = "✗"
            elif status == 'warning':
                status_icon = "⚠"

            # 格式化类别名称
            category_name = category.upper()
            if category.lower() == 'cpu':
                category_name = "CPU"
            elif category.lower() == 'memory':
                category_name = "内存"
            elif category.lower() == 'power':
                category_name = "电源"
            elif category.lower() == 'fan':
                category_name = "风扇"
            elif category.lower() == 'ntp':
                category_name = "NTP"
            elif category.lower() == 'interface_errors':
                category_name = "接口"
            elif category.lower() == 'alarms':
                category_name = "告警"

            # 添加状态和消息
            lines.append(f"{category_name}:")
            lines.append(f"状态: {status_icon} {status}")
            lines.append(f"信息: {message}")

            # 如果有详情，添加详情
            if 'details' in item:
                details = item.get('details', '')
                if details:
                    lines.append("详情:")
                    if isinstance(details, str):
                        for detail_line in details.split('\n'):
                            lines.append(f"  {detail_line}")
                    elif isinstance(details, dict):
                        for key, value in details.items():
                            lines.append(f"  {key}: {value}")

            lines.append("-" * 30)

        return '\n'.join(lines)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # 稍微增加边距
        layout.setSpacing(5)  # 增加间距

        # 设备信息头部
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        status = self.result.get('status', 'Unknown')

        # 设置状态颜色
        status_color = "green"
        if '错误' in status:
            status_color = "red"
        elif '异常' in status:
            status_color = "orange"
        elif '警告' in status:
            status_color = "#FFC107"  # 黄色
        elif '失败' in status:
            status_color = "red"
        elif not '成功' in status:
            status_color = "gray"

        # 创建带样式的标签
        device_label = QLabel(f"<b>设备:</b> {self.device_name}")
        status_label = QLabel(f"<b>状态:</b> <span style='color: {status_color}; font-weight: bold;'>{status}</span>")

        header_layout.addWidget(device_label)
        header_layout.addWidget(status_label)

        # 如果有输出文件，添加文件链接
        output_file = self.result.get('output_file')
        if output_file:
            file_link = QLabel(f"<b>文件:</b> <a href='{QUrl.fromLocalFile(output_file).toString()}'>{os.path.basename(output_file)}</a>")
            file_link.setOpenExternalLinks(True)
            header_layout.addWidget(file_link)

        # 添加行数信息到头部
        self.line_info.setStyleSheet("color: #666;")
        header_layout.addWidget(self.line_info)
        header_layout.addStretch()

        # 只有当总行数超过初始显示行数时才显示按钮
        if len(self.lines) > self.current_line:
            load_more_btn = QPushButton("加载更多")
            load_more_btn.setFixedWidth(80)
            load_more_btn.clicked.connect(self.load_more)
            header_layout.addWidget(load_more_btn)

            load_all_btn = QPushButton("全部")
            load_all_btn.setFixedWidth(50)
            load_all_btn.clicked.connect(self.load_all)
            header_layout.addWidget(load_all_btn)

        layout.addLayout(header_layout)

        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 结果文本显示
        self.text_browser.setReadOnly(True)

        # 设置文本浏览器样式
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """)

        if self.full_text:
            content_lines = min(len(self.lines), self.current_line)
            line_height = 18  # 增加行高
            self.text_browser.setMinimumHeight(min(content_lines * line_height, 400))  # 增加最大高度
        else:
            self.text_browser.hide()

        layout.addWidget(self.text_browser)

        # 更新文本显示
        self.update_text()

    def update_text(self):
        """更新文本显示"""
        if not self.full_text:
            return

        displayed_lines = []
        for line in self.lines[:self.current_line]:
            if '输出文件:' not in line and 'file:///' not in line:
                displayed_lines.append(line)

        # 将文本转换为HTML格式，添加颜色和样式
        html_text = []
        in_details = False

        for line in displayed_lines:
            # 跳过空行
            if not line.strip():
                html_text.append("<br>")
                continue

            # 处理标题行
            if line.strip() == "巡检结果详情:":
                html_text.append(f"<h3 style='margin: 5px 0;'>{line}</h3>")
                continue

            # 处理状态统计行
            if line.strip().startswith("状态统计:"):
                stats_parts = []
                if "正常" in line:
                    count = line.split("正常")[0].split()[-1]
                    stats_parts.append(f"<span style='color: green;'>{count}正常</span>")
                if "异常" in line:
                    count = line.split("异常")[0].split()[-1]
                    stats_parts.append(f"<span style='color: orange;'>{count}异常</span>")
                if "错误" in line:
                    count = line.split("错误")[0].split()[-1]
                    stats_parts.append(f"<span style='color: red;'>{count}错误</span>")
                if "警告" in line:
                    count = line.split("警告")[0].split()[-1]
                    stats_parts.append(f"<span style='color: #FFC107;'>{count}警告</span>")

                html_text.append(f"<p><b>状态统计:</b> {', '.join(stats_parts)}</p>")
                continue

            # 处理分隔线
            if line.strip() and all(c == '-' for c in line.strip()):
                html_text.append("<hr style='margin: 10px 0; border: 0; border-top: 1px solid #eee;'>")
                in_details = False
                continue

            # 处理类别标题行
            if line.endswith(":") and not line.startswith(" ") and not "状态:" in line and not "信息:" in line and not "详情:" in line:
                html_text.append(f"<h4 style='margin: 10px 0 5px 0; color: #333;'>{line}</h4>")
                continue

            # 处理状态行
            if line.strip().startswith("状态:"):
                status_text = line.strip()[3:].strip()
                color = "green"
                if "abnormal" in status_text:
                    color = "orange"
                elif "error" in status_text:
                    color = "red"
                elif "warning" in status_text:
                    color = "#FFC107"

                # 提取状态图标并添加到显示中
                icon = ""
                if "✓" in status_text:
                    icon = "✓ "
                elif "!" in status_text:
                    icon = "! "
                elif "✗" in status_text:
                    icon = "✗ "
                elif "⚠" in status_text:
                    icon = "⚠ "

                # 移除原始图标，使用我们的格式化图标
                status_display = status_text
                for symbol in ["✓", "!", "✗", "⚠"]:
                    status_display = status_display.replace(symbol, "").strip()

                html_text.append(f"<p><b>状态:</b> <span style='color: {color};'>{icon}{status_display}</span></p>")
                continue

            # 处理信息行
            if line.strip().startswith("信息:"):
                info_text = line.strip()[3:].strip()
                html_text.append(f"<p><b>信息:</b> {info_text}</p>")
                continue

            # 处理详情标题行
            if line.strip() == "详情:":
                in_details = True
                html_text.append("<p><b>详情:</b></p>")
                html_text.append("<div style='margin-left: 20px; background-color: #f5f5f5; padding: 10px; border-radius: 4px;'>")
                continue

            # 处理详情内容
            if in_details and line.strip().startswith("  "):
                html_text.append(f"<p style='margin: 2px 0;'>{line}</p>")
                continue

            # 其他行
            html_text.append(f"<p>{line}</p>")

        # 如果详情区域没有关闭，关闭它
        if in_details:
            html_text.append("</div>")

        self.text_browser.setHtml("".join(html_text))
        self.line_info.setText(f"{min(self.current_line, len(self.lines))}/{len(self.lines)}行")

        # 动态调整高度，但限制最大高度
        content_lines = min(len(self.lines), self.current_line)
        line_height = 18  # 增加行高
        self.text_browser.setMinimumHeight(min(content_lines * line_height, 400))  # 增加最大高度

    def load_more(self):
        """加载更多行"""
        self.current_line += 200
        self.update_text()

    def load_all(self):
        """加载所有行"""
        self.current_line = len(self.lines)
        self.update_text()

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

    def open_file(self, link):
        """打开文件"""
        try:
            file_path = link.toLocalFile()
            if os.path.exists(file_path):
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                else:  # macOS/Linux
                    subprocess.run(['open', file_path] if sys.platform == 'darwin' else ['xdg-open', file_path])
        except Exception as e:
            print(f"打开文件失败: {str(e)}")

    def is_mac_ip_query(self, result_text: str) -> bool:
        """判断是否为MAC-IP查询操作"""
        return any(keyword in result_text for keyword in ['MAC地址:', 'IP地址:', 'VLAN:', '接口:'])

    def on_anchor_clicked(self, url):
        """处理锚点点击事件"""
        url_str = url.toString()

        # 如果是文件链接，打开文件
        if url_str.startswith("file:"):
            self.open_file(url)
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

    def format_overview_content(self, device_name, result):
        """格式化概览内容"""
        status = result.get('status', 'Unknown')
        result_text = result.get('result', '')
        output_file = result.get('output_file')
        inspection_result = result.get('inspection_result', {})

        # 设置状态颜色
        status_color = 'green'
        if '错误' in status:
            status_color = 'red'
        elif '异常' in status:
            status_color = 'orange'
        elif '警告' in status:
            status_color = '#FFC107'  # 黄色
        elif '失败' in status:
            status_color = 'red'
        elif not '成功' in status:
            status_color = 'gray'

        # 如果是设备巡检结果，使用inspection_result
        if inspection_result and not result_text:
            # 显示设备名称和状态（添加可点击链接）
            content = [
                f"设备: <a href='device:{device_name}' style='text-decoration: none; color: inherit;'><b>{device_name}</b></a>",
                f"状态: <a href='device:{device_name}' style='text-decoration: none;'><span style='color: {status_color}; font-weight: bold;'>{status}</span></a>"
            ]

            # 如果有输出文件，添加文件链接
            if output_file:
                content.append(f"文件: <a href='{QUrl.fromLocalFile(output_file).toString()}'>{os.path.basename(output_file)}</a>")

            # 添加巡检结果摘要
            if inspection_result:
                content.append("<br><b>巡检结果摘要:</b>")

                # 计算状态统计
                status_counts = {"normal": 0, "abnormal": 0, "error": 0, "warning": 0}
                for item in inspection_result.values():
                    item_status = item.get('status', 'unknown')
                    if item_status in status_counts:
                        status_counts[item_status] += 1

                # 添加状态统计
                stats = []
                if status_counts["normal"] > 0:
                    stats.append(f"<span style='color: green;'>{status_counts['normal']}正常</span>")
                if status_counts["abnormal"] > 0:
                    stats.append(f"<span style='color: orange;'>{status_counts['abnormal']}异常</span>")
                if status_counts["error"] > 0:
                    stats.append(f"<span style='color: red;'>{status_counts['error']}错误</span>")
                if status_counts["warning"] > 0:
                    stats.append(f"<span style='color: #FFC107;'>{status_counts['warning']}警告</span>")

                content.append(f"状态统计: {', '.join(stats)}")
                content.append("<br>")

                # 添加各项检查结果
                for category, item in inspection_result.items():
                    item_status = item.get('status', 'unknown')
                    item_message = item.get('message', '')

                    # 设置状态颜色和图标
                    icon = "✓"
                    color = 'green'
                    if item_status == 'abnormal':
                        icon = "!"
                        color = 'orange'
                    elif item_status == 'error':
                        icon = "✗"
                        color = 'red'
                    elif item_status == 'warning':
                        icon = "⚠"
                        color = '#FFC107'

                    # 格式化类别名称
                    category_name = category.upper()
                    if category.lower() == 'cpu':
                        category_name = "CPU"
                    elif category.lower() == 'memory':
                        category_name = "内存"
                    elif category.lower() == 'power':
                        category_name = "电源"
                    elif category.lower() == 'fan':
                        category_name = "风扇"
                    elif category.lower() == 'ntp':
                        category_name = "NTP"
                    elif category.lower() == 'interface_errors':
                        category_name = "接口"
                    elif category.lower() == 'alarms':
                        category_name = "告警"

                    content.append(f"<span style='color: {color};'>{icon} {category_name}: {item_message}</span>")

            content.append("<hr>")
            return "<br>".join(content)

        # 如果是空结果，直接返回
        if not result_text:
            return ''

        # 显示设备名称和状态（添加可点击链接）
        content = [
            f"设备: <a href='device:{device_name}' style='text-decoration: none; color: inherit;'><b>{device_name}</b></a>",
            f"状态: <a href='device:{device_name}' style='text-decoration: none;'><span style='color: {status_color}; font-weight: bold;'>{status}</span></a>"
        ]

        # 如果有输出文件，添加文件链接
        if output_file:
            content.append(f"文件: <a href='{QUrl.fromLocalFile(output_file).toString()}'>{os.path.basename(output_file)}</a>")

        content.append("<hr>")
        return "<br>".join(content)

    def add_results_to_tree(self):
        """将结果添加到树形视图中"""
        # 设置状态颜色
        normal_color = QColor("green")
        abnormal_color = QColor("orange")
        error_color = QColor("red")
        warning_color = QColor("#FFC107")  # 黄色

        # 添加每个设备的结果
        for device_name, result in self.results.items():
            status = result.get('status', 'Unknown')
            output_file = result.get('output_file')
            result_text = result.get('result', '')
            inspection_result = result.get('inspection_result', {})

            # 如果是设备巡检结果，使用inspection_result
            if inspection_result:
                # 计算总体状态
                status_counts = {"normal": 0, "abnormal": 0, "error": 0, "warning": 0}
                for category, item in inspection_result.items():
                    item_status = item.get('status', 'unknown')
                    if item_status in status_counts:
                        status_counts[item_status] += 1

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

                # 创建设备根节点
                device_item = QTreeWidgetItem(self.result_tree)
                device_item.setText(0, device_name)
                device_item.setText(1, overall_status)
                device_item.setText(2, f"状态: {overall_status}")
                # 设置状态颜色
                device_item.setForeground(1, status_color)
                device_item.setExpanded(True)  # 默认展开

                # 为每个类别创建子节点
                for category, item in inspection_result.items():
                    item_status = item.get('status', 'unknown')
                    item_message = item.get('message', '')

                    # 设置状态文本和颜色
                    status_text = ""
                    status_item_color = None
                    if item_status == "normal":
                        status_text = "✓ 正常"
                        status_item_color = normal_color
                    elif item_status == "abnormal":
                        status_text = "! 异常"
                        status_item_color = abnormal_color
                    elif item_status == "error":
                        status_text = "✗ 错误"
                        status_item_color = error_color
                    elif item_status == "warning":
                        status_text = "⚠ 警告"
                        status_item_color = warning_color
                    else:
                        status_text = item_status

                    # 创建类别节点
                    category_item = QTreeWidgetItem(device_item)
                    category_item.setText(0, category)
                    category_item.setText(1, status_text)
                    category_item.setText(2, item_message)
                    # 设置状态颜色
                    if status_item_color:
                        category_item.setForeground(1, status_item_color)

                    # 如果有详情，添加详情子节点
                    if 'details' in item:
                        details = item.get('details', '')

                        # 对于告警，创建一个特殊的详情显示
                        if category == "alarms" and item_status == "abnormal":
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

            # 如果是普通结果，直接显示
            elif result_text:
                # 创建设备根节点
                device_item = QTreeWidgetItem(self.result_tree)
                device_item.setText(0, device_name)
                device_item.setText(1, status)
                device_item.setText(2, result_text[:100] + "..." if len(result_text) > 100 else result_text)
                device_item.setExpanded(False)  # 默认不展开

                # 添加详情子节点
                details_item = QTreeWidgetItem(device_item)
                details_item.setText(0, "详情")
                details_item.setText(2, result_text)

        # 自动调整列宽以适应内容
        self.result_tree.resizeColumnToContents(0)
        self.result_tree.resizeColumnToContents(1)

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
        overview_content = []
        for device_name, result in self.results.items():
            content = self.format_overview_content(device_name, result)
            if content:  # 只添加有内容的结果
                overview_content.append(content)

        self.overview_text.setHtml("<br>".join(overview_content))
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
        self.add_results_to_tree()

        details_layout.addWidget(self.result_tree)

        # 不再使用DeviceResultWidget，直接使用QTextBrowser显示详细信息
        # 设置滚动区域的内容
        # scroll_area.setWidget(scroll_content)

        # 将滚动区域添加到详细信息标签页
        # details_layout.addWidget(scroll_area)

        tab_widget.addTab(details_tab, "详细信息")
        main_layout.addWidget(tab_widget)

        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button)