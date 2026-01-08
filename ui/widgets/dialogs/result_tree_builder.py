from PySide6.QtWidgets import QTreeWidgetItem, QTextBrowser, QWidget, QVBoxLayout
from PySide6.QtGui import QColor
import re
from .result_utils import (
    get_status_qcolor, get_status_text, get_overall_status, 
    calculate_status_counts
)

class ResultTreeBuilder:
    """结果树构建器"""
    
    def __init__(self, tree_widget):
        self.result_tree = tree_widget
        
    def add_results(self, results):
        """将结果添加到树形视图中"""
        # 设置状态颜色
        normal_color = QColor("green")
        abnormal_color = QColor("orange")
        error_color = QColor("red")
        warning_color = QColor("#FFC107")  # 黄色
        
        # 添加每个设备的结果
        for device_name, result in results.items():
            status = result.get('status', 'Unknown')
            output_file = result.get('output_file')
            result_text = result.get('result', '')
            inspection_result = result.get('inspection_result', {})
            
            # 如果是设备巡检结果，使用inspection_result
            if inspection_result:
                # 计算总体状态
                status_counts = calculate_status_counts(inspection_result)
                
                # 确定总体状态
                overall_status, _ = get_overall_status(status_counts)
                status_color = self._get_status_color(overall_status)
                
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
                    self._add_category_node(device_item, category, item)
                    
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
    
    def _get_status_color(self, status_text):
        """获取状态颜色"""
        if "错误" in status_text:
            return QColor("red")
        elif "异常" in status_text:
            return QColor("orange")
        elif "警告" in status_text:
            return QColor("#FFC107")
        return QColor("green")
    
    def _add_category_node(self, parent_item, category, item):
        """添加类别节点"""
        item_status = item.get('status', 'unknown')
        item_message = item.get('message', '')
        
        # 设置状态文本和颜色
        status_text = get_status_text(item_status)
        status_color = None
        if item_status == "normal":
            status_color = QColor("green")
        elif item_status == "abnormal":
            status_color = QColor("orange")
        elif item_status == "error":
            status_color = QColor("red")
        elif item_status == "warning":
            status_color = QColor("#FFC107")
        
        # 创建类别节点
        category_item = QTreeWidgetItem(parent_item)
        category_item.setText(0, category)
        category_item.setText(1, status_text)
        category_item.setText(2, item_message)
        # 设置状态颜色
        if status_color:
            category_item.setForeground(1, status_color)
        
        # 如果有详情，添加详情子节点
        if 'details' in item:
            details = item.get('details', '')
            
            # 对于告警，创建一个特殊的详情显示
            if category == "alarms" and item_status == "abnormal":
                self._add_alarm_details_node(category_item, details)
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
    
    def _add_alarm_details_node(self, parent_item, details):
        """添加告警详情节点"""
        # 创建告警详情父节点
        alarm_details_item = QTreeWidgetItem(parent_item)
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
