from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextBrowser, QTabWidget,
                             QWidget, QTableWidget, QTableWidgetItem, QFrame)
from datetime import datetime
import os
from PySide6.QtCore import QUrl, Qt
import re
import subprocess
import sys

class DeviceResultWidget(QFrame):
    """单个设备结果显示组件"""
    
    def __init__(self, device_name, result, parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self.result = result
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
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 设备信息头部
        header_layout = QHBoxLayout()
        status = self.result.get('status', 'Unknown')
        header_layout.addWidget(QLabel(f"设备: {self.device_name}"))
        status_label = QLabel(f"状态: {status}")
        status_label.setStyleSheet(f"color: {'green' if '成功' in status else 'red'};")
        header_layout.addWidget(status_label)
        
        # 如果有输出文件，添加文件链接
        output_file = self.result.get('output_file')
        if output_file:
            file_link = QLabel(f"文件: <a href='{QUrl.fromLocalFile(output_file).toString()}'>{os.path.basename(output_file)}</a>")
            file_link.setOpenExternalLinks(True)
            header_layout.addWidget(file_link)
            
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 结果文本显示
        self.text_browser.setReadOnly(True)
        layout.addWidget(self.text_browser)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 显示行数信息
        button_layout.addWidget(self.line_info)
        
        button_layout.addStretch()
        
        # 只有当总行数超过初始显示行数时才显示按钮
        if len(self.lines) > self.current_line:
            load_more_btn = QPushButton("加载更多(200行)")
            load_more_btn.clicked.connect(self.load_more)
            button_layout.addWidget(load_more_btn)
            
            load_all_btn = QPushButton("加载全部")
            load_all_btn.clicked.connect(self.load_all)
            button_layout.addWidget(load_all_btn)
        
        layout.addLayout(button_layout)
        
        # 添加分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 更新文本显示
        self.update_text()
        
    def update_text(self):
        """更新文本显示"""
        displayed_lines = []
        for line in self.lines[:self.current_line]:
            # 跳过包含文件链接的行
            if '输出文件:' not in line and 'file:///' not in line:
                displayed_lines.append(line)
        
        self.text_browser.setText('\n'.join(displayed_lines))
        self.line_info.setText(f"显示 {min(self.current_line, len(self.lines))}/{len(self.lines)} 行")
        
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
        self.overview_text.anchorClicked.connect(self.open_file)
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

    def format_overview_content(self, device_name, result):
        """格式化概览内容"""
        status = result.get('status', 'Unknown')
        result_text = result.get('result', '')
        output_file = result.get('output_file')
        
        # 如果是空结果，直接返回
        if not result_text:
            return ''
        
        # 显示设备名称和状态
        content = [
            f"设备: {device_name}",
            f"状态: <span style='color: {'green' if '成功' in status else 'red'};'>{status}</span>"
        ]
        
        # 如果有输出文件，添加文件链接
        if output_file:
            content.append(f"文件: <a href='{QUrl.fromLocalFile(output_file).toString()}'>{os.path.basename(output_file)}</a>")
        
        content.append("<hr>")
        return "<br>".join(content)

    def format_details_content(self, device_name, result):
        """格式化详细内容"""
        status = result.get('status', 'Unknown')
        output_file = result.get('output_file')
        result_text = result.get('result', '')
        
        # 如果是空结果，直接返回
        if not result_text:
            return ''
            
        # 分行处理结果
        content = [
            f"设备: {device_name}",
            f"状态: {'<span style=\"color: green;\">' + status + '</span>' if '成功' in status else '<span style=\"color: red;\">' + status + '</span>'}",
        ]
        
        content.append("")  # 在设备信息后添加一个空行
        
        # 添加详细结果
        content.append("详细结果:")
        for line in result_text.split('\n'):
            if line.strip():
                content.append(f"  {line.strip()}")
        
        content.append("<hr>")  # 使用与概览相同的分割线
        return "<br>".join(content)

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
        
        # 概览显示 - 显示所有设备
        self.overview_text.setReadOnly(True)
        
        # 格式化概览内容 - 显示所有设备
        overview_content = []
        for device_name, result in self.results.items():
            content = self.format_overview_content(device_name, result)
            if content:  # 只添加有内容的结果
                overview_content.append(content)
        
        self.overview_text.setHtml("<br>".join(overview_content))
        overview_layout.addWidget(self.overview_text)
        
        tab_widget.addTab(overview_tab, "概览")
        
        # 详细信息选项卡
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        
        # 创建滚动区域容器
        scroll_area = QWidget()
        scroll_layout = QVBoxLayout(scroll_area)
        
        # 过滤结果：对于MAC-IP查询只保留有效结果，其他命令显示所有结果
        valid_results = {}
        for device_name, result in self.results.items():
            result_text = result.get('result', '')
            if not result_text:
                continue
                
            if self.is_mac_ip_query(result_text):
                # 对于MAC-IP查询，只保留找到MAC地址的设备
                if 'MAC地址:' in result_text and '未找到' not in result_text:
                    valid_results[device_name] = result
            else:
                # 其他命令的结果全部显示
                valid_results[device_name] = result
        
        # 为每个设备创建独立的结果显示组件
        for device_name, result in valid_results.items():
            device_widget = DeviceResultWidget(device_name, result)
            scroll_layout.addWidget(device_widget)
        
        scroll_layout.addStretch()
        
        # 将滚动区域添加到详细信息标签页
        details_layout.addWidget(scroll_area)
        
        tab_widget.addTab(details_tab, "详细信息")
        main_layout.addWidget(tab_widget)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button) 