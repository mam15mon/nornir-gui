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

    def is_mac_ip_query(self, result_text: str) -> bool:
        """判断是否为MAC-IP查询操作"""
        return any(keyword in result_text for keyword in ['MAC地址:', 'IP地址:', '接入接口:', '所属VLAN:'])

    def format_overview_content(self, device_name, result):
        """格式化概览内容"""
        status = result.get('status', 'Unknown')
        result_text = result.get('result', '')
        output_file = result.get('output_file')
        
        # 如果是空结果，直接返回
        if not result_text:
            return ''
        
        # MAC-IP查询结果的特殊处理
        if self.is_mac_ip_query(result_text):
            if '未找到MAC地址表项' in result_text or '未在ARP表中找到对应条目' in result_text:
                return ''  # 不显示无结果的设备
        
        # 显示设备名称、状态和文件链接
        content = [
            f"设备: {device_name}",
            f"状态: <span style='color: {'green' if '成功' in status else 'red'};'>{status}</span>"
        ]
        
        # 如果有输出文件，添加文件链接
        if output_file:
            file_url = QUrl.fromLocalFile(output_file).toString()
            content.append(f"文件: <a href='{file_url}'>{os.path.basename(output_file)}</a>")
        
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
            
        # MAC-IP查询结果的特殊处理
        if self.is_mac_ip_query(result_text):
            if '未找到MAC地址表项' in result_text or '未在ARP表中找到对应条目' in result_text:
                return ''  # 不显示无结果的设备
            
            # 分行处理MAC-IP查询结果
            content = [
                f"设备: {device_name}",
                f"状态: {'<span style=\"color: green;\">' + status + '</span>' if '成功' in status else '<span style=\"color: red;\">' + status + '</span>'}",
            ]
            
            # 如果有输出文件,添加文件链接
            if output_file:
                file_url = QUrl.fromLocalFile(output_file).toString()
                content.append(f"文件: <a href='{file_url}'>{os.path.basename(output_file)}</a>")
            
            content.append("")  # 在设备信息后添加一个空行
            
            # 提取查询条件
            query_match = re.search(r'查询条件: (.*?) 找到MAC地址:', result_text)
            if query_match:
                content.append(f"查询条件: {query_match.group(1)}")
                content.append("")  # 空行
                
            # 提取命令信息
            cmd_match = re.search(r'执行命令: (.*?) 详细结果:', result_text)
            if cmd_match:
                content.append("执行的命令:")
                for cmd in cmd_match.group(1).split(', '):
                    content.append(f"  {cmd}")
                content.append("")  # 空行
                
            # 提取并格式化详细结果
            content.append("详细结果:")
            results_text = result_text.split('详细结果:')[1] if '详细结果:' in result_text else result_text
            
            # 分别处理每个MAC地址条目
            mac_entries = re.findall(r'MAC地址:.*?(?=MAC地址:|$)', results_text, re.DOTALL)
            if not mac_entries:  # 如果没有匹配到多条目格式，将整个结果作为一个条目
                mac_entries = [results_text]
            
            for entry in mac_entries:
                entry = entry.strip()
                if not entry:
                    continue
                
                # 提取并格式化每个字段
                mac_match = re.search(r'MAC地址: ([0-9a-fA-F-]+)', entry)
                ip_match = re.search(r'IP地址: ([^接]+)', entry)
                interface_match = re.search(r'接入接口: ([^所]+)', entry)
                vlan_match = re.search(r'所属VLAN: (\d+)', entry)
                
                if mac_match:
                    content.append(f"  MAC地址: {mac_match.group(1)}")
                if ip_match:
                    # 去重IP地址
                    ips = list(set(ip_match.group(1).strip().split(', ')))
                    content.append(f"  IP地址: {', '.join(ips)}")
                if interface_match:
                    content.append(f"  接入接口: {interface_match.group(1).strip()}")
                if vlan_match:
                    content.append(f"  所属VLAN: {vlan_match.group(1)}")
                content.append("")  # 每个条目之间添加空行
        else:
            # 其他操作的通用处理
            content = [
                f"设备: {device_name}",
                f"状态: {'<span style=\"color: green;\">' + status + '</span>' if '成功' in status else '<span style=\"color: red;\">' + status + '</span>'}",
            ]
            
            # 如果有输出文件,添加文件链接
            if output_file:
                file_url = QUrl.fromLocalFile(output_file).toString()
                content.append(f"文件: <a href='{file_url}'>{os.path.basename(output_file)}</a>")
            
            content.append("")  # 在设备信息后添加一个空行
            
            # 添加完整的结果内容
            if result_text:
                # 尝试提取和格式化命令输出
                if isinstance(result_text, str):
                    # 分析结果文本结构
                    lines = result_text.split('\n')
                    current_section = None
                    command_output = []
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        if '执行的命令:' in line:
                            current_section = 'commands'
                            content.append("执行的命令:")
                            continue
                        elif '命令: ' in line:
                            current_section = 'output'
                            command = line.replace('命令: ', '').strip()
                            content.append("")  # 空行
                            content.append(f"命令: {command}")
                            content.append("输出:")
                            continue
                        elif '命令输出:' in line:
                            current_section = 'output'
                            continue
                            
                        if current_section == 'commands':
                            content.append(f"  {line}")
                        elif current_section == 'output':
                            content.append(f"  {line}")
                else:
                    content.append(str(result_text))
        
        content.append("<hr>")  # 使用与概览相同的分割线
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
        
        # 根据操作类型过滤有效结果
        valid_results = []
        for result in self.results.values():
            result_text = result.get('result', '')
            if not result_text:
                continue
                
            if self.is_mac_ip_query(result_text):
                if '未找到MAC地址表项' not in result_text and '未在ARP表中找到对应条目' not in result_text:
                    valid_results.append(result)
            else:
                valid_results.append(result)
        
        total_devices = len(valid_results)
        success_count = sum(1 for result in valid_results if '成功' in result.get('status', ''))
        failed_count = total_devices - success_count
        
        stats_layout.addWidget(QLabel(f"有效结果设备数: {total_devices}"))
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
            content = self.format_overview_content(device_name, result)
            if content:  # 只添加有内容的结果
                overview_content.append(content)
        
        self.overview_text.setHtml("<br>".join(overview_content))
        overview_layout.addWidget(self.overview_text)
        
        tab_widget.addTab(overview_tab, "概览")
        
        # 详细信息选项卡
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        self.details_text = QTextBrowser()
        self.details_text.setReadOnly(True)
        
        details_content = []
        for device_name, result in self.results.items():
            content = self.format_details_content(device_name, result)
            if content:  # 只添加有内容的结果
                details_content.append(content)
        
        self.details_text.setHtml("<br>".join(details_content))
        details_layout.addWidget(self.details_text)
        
        tab_widget.addTab(details_tab, "详细信息")
        main_layout.addWidget(tab_widget)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button) 