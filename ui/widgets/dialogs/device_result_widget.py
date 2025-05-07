from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTextBrowser)
from PySide6.QtCore import QUrl
import os

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
