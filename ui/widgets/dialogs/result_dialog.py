from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextBrowser, QTabWidget,
                             QWidget, QTableWidget, QTableWidgetItem)
from datetime import datetime
import os
from PySide6.QtCore import QUrl
import re
import subprocess
import sys

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
        self.init_ui()
        self.setup_hyperlink()

    def setup_hyperlink(self):
        """设置超链接点击事件"""
        self.overview_text.anchorClicked.connect(self.open_file)
        self.overview_text.setOpenLinks(False)
        self.details_text.anchorClicked.connect(self.open_file)
        self.details_text.setOpenLinks(False)

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

    def format_overview_content(self, device_name, result):
        """格式化概览内容"""
        status = result.get('status', 'Unknown')
        color = 'green' if '成功' in status else 'red'
        return f"设备: {device_name}<br>状态: <span style='color: {color};'>{status}</span><hr>"

    def format_details_content(self, device_name, result):
        """格式化详细内容"""
        status = result.get('status', 'Unknown')
        output_file = result.get('output_file')
        result_text = result.get('result', '')
        
        content = [
            f"{'='*50}",
            f"设备: {device_name}",
            f"状态: {'<span style=\"color: green;\">' + status + '</span>' if '成功' in status else '<span style=\"color: red;\">' + status + '</span>'}",
        ]
        
        # 如果有输出文件，添加文件链接
        if output_file:
            file_url = QUrl.fromLocalFile(output_file).toString()
            content.append(f"文件: <a href='{file_url}'>{os.path.basename(output_file)}</a>")
            
        # 处理命令执行结果
        if result_text:
            try:
                # 分割命令和输出
                lines = result_text.split('\n')
                in_commands = False
                in_output = False
                commands = []
                outputs = []
                current_output = []
                
                for line in lines:
                    if '执行的命令:' in line:
                        in_commands = True
                        in_output = False
                        continue
                    elif '命令输出:' in line:
                        in_commands = False
                        in_output = True
                        continue
                    elif line.startswith('命令: '):
                        # 如果有之前的输出，添加到outputs
                        if current_output:
                            outputs.extend(current_output)
                            current_output = []
                        in_commands = False
                        in_output = True
                        outputs.append(f"<br><b>{line}</b>")  # 加粗命令行
                        continue
                        
                    if in_commands and line.strip():
                        commands.append(line.strip())
                    elif in_output and line.strip():  # 只收集非空行
                        current_output.append(line)
                
                # 添加最后一个命令的输出
                if current_output:
                    outputs.extend(current_output)
                
                if commands:
                    content.append("<br>执行的命令:")
                    content.extend([f"  {cmd}" for cmd in commands])
                    content.append("")  # 添加一个空行分隔
                    
                if outputs:
                    content.append("命令输出:")
                    content.extend(outputs)
            except Exception as e:
                content.append("<br>结果解析失败，显示原始内容:<br>")
                content.append(result_text)
        
        content.extend([f"{'='*50}", ""])
        return "<br>".join(content)

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"{self.operation_name} - 结果")
        self.resize(800, 600)
        
        main_layout = QVBoxLayout(self)
        tab_widget = QTabWidget()
        
        # 概览选项卡
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        device_results = [result for result in self.results.values()]
        total_devices = len(device_results)
        success_count = sum(1 for result in device_results if '成功' in result.get('status', ''))
        failed_count = total_devices - success_count
        
        stats_layout.addWidget(QLabel(f"总设备数: {total_devices}"))
        stats_layout.addWidget(QLabel(f"成功: {success_count}"))
        stats_layout.addWidget(QLabel(f"失败: {failed_count}"))
        
        if self.start_time:
            duration = datetime.now() - self.start_time
            stats_layout.addWidget(QLabel(f"耗时: {duration.total_seconds():.2f}秒"))
        
        overview_layout.addLayout(stats_layout)
        
        # 概览显示
        self.overview_text = QTextBrowser()
        self.overview_text.setReadOnly(True)
        
        # 格式化概览内容
        overview_content = []
        for device_name, result in self.results.items():
            status = result.get('status', 'Unknown')
            output_file = result.get('output_file')
            
            content = []
            content.append(f"设备: {device_name}")
            
            # 添加状态，带颜色
            if '成功' in status:
                content.append(f"状态: <span style='color: green;'>{status}</span>")
            else:
                content.append(f"状态: <span style='color: red;'>{status}</span>")
                
            # 如果有输出文件，添加文件链接
            if output_file:
                file_url = QUrl.fromLocalFile(output_file).toString()
                content.append(f"文件: <a href='{file_url}'>{os.path.basename(output_file)}</a>")
                
            content.append("<hr>")
            overview_content.append("<br>".join(content))
        
        self.overview_text.setHtml("<br>".join(overview_content))
        overview_layout.addWidget(self.overview_text)
        
        tab_widget.addTab(overview_tab, "概览")
        
        # 详细信息选项卡
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        self.details_text = QTextBrowser()
        self.details_text.setReadOnly(True)
        
        details_content = [self.format_details_content(device_name, result) 
                         for device_name, result in self.results.items()]
        self.details_text.setHtml("<br>".join(details_content))
        details_layout.addWidget(self.details_text)
        
        tab_widget.addTab(details_tab, "详细信息")
        main_layout.addWidget(tab_widget)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button) 