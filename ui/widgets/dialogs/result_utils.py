from PySide6.QtGui import QColor
import os
from PySide6.QtCore import QUrl

# 状态颜色常量
STATUS_COLORS = {
    "normal": "green",
    "abnormal": "orange",
    "error": "red",
    "warning": "#FFC107"  # 黄色
}

# 状态图标常量
STATUS_ICONS = {
    "normal": "✓",
    "abnormal": "!",
    "error": "✗",
    "warning": "⚠"
}

# 类别名称映射
CATEGORY_NAMES = {
    "cpu": "CPU",
    "memory": "内存",
    "power": "电源",
    "fan": "风扇",
    "ntp": "NTP",
    "interface_errors": "接口",
    "alarms": "告警",
    "temperature": "温度"
}

def get_status_color(status):
    """根据状态获取颜色"""
    if '错误' in status:
        return STATUS_COLORS["error"]
    elif '异常' in status:
        return STATUS_COLORS["abnormal"]
    elif '警告' in status:
        return STATUS_COLORS["warning"]
    elif '失败' in status:
        return STATUS_COLORS["error"]
    elif '成功' in status:
        return STATUS_COLORS["normal"]
    else:
        return "gray"

def get_status_qcolor(status):
    """根据状态获取QColor对象"""
    color_str = get_status_color(status)
    return QColor(color_str)

def get_category_name(category):
    """获取类别的显示名称"""
    category_lower = category.lower()
    if category_lower in CATEGORY_NAMES:
        return CATEGORY_NAMES[category_lower]
    return category.upper()

def get_status_icon(status):
    """根据状态获取图标"""
    if status == 'normal':
        return STATUS_ICONS["normal"]
    elif status == 'abnormal':
        return STATUS_ICONS["abnormal"]
    elif status == 'error':
        return STATUS_ICONS["error"]
    elif status == 'warning':
        return STATUS_ICONS["warning"]
    return ""

def get_status_text(status):
    """获取状态的显示文本"""
    if status == "normal":
        return "✓ 正常"
    elif status == "abnormal":
        return "! 异常"
    elif status == "error":
        return "✗ 错误"
    elif status == "warning":
        return "⚠ 警告"
    return status

def format_file_link(output_file):
    """格式化文件链接HTML"""
    if not output_file:
        return ""
    return f"<b>文件:</b> <a href='{QUrl.fromLocalFile(output_file).toString()}'>{os.path.basename(output_file)}</a>"

def calculate_status_counts(inspection_result):
    """计算状态统计"""
    status_counts = {"normal": 0, "abnormal": 0, "error": 0, "warning": 0}
    for item in inspection_result.values():
        item_status = item.get('status', 'unknown')
        if item_status in status_counts:
            status_counts[item_status] += 1
    return status_counts

def get_overall_status(status_counts):
    """根据状态计数确定总体状态"""
    if status_counts["error"] > 0:
        return "错误", STATUS_COLORS["error"]
    elif status_counts["abnormal"] > 0:
        return "异常", STATUS_COLORS["abnormal"]
    elif status_counts["warning"] > 0:
        return "警告", STATUS_COLORS["warning"]
    return "正常", STATUS_COLORS["normal"]

def format_status_stats_html(status_counts):
    """格式化状态统计HTML"""
    stats = []
    if status_counts["normal"] > 0:
        stats.append(f"<span style='color: {STATUS_COLORS['normal']};'>{status_counts['normal']}正常</span>")
    if status_counts["abnormal"] > 0:
        stats.append(f"<span style='color: {STATUS_COLORS['abnormal']};'>{status_counts['abnormal']}异常</span>")
    if status_counts["error"] > 0:
        stats.append(f"<span style='color: {STATUS_COLORS['error']};'>{status_counts['error']}错误</span>")
    if status_counts["warning"] > 0:
        stats.append(f"<span style='color: {STATUS_COLORS['warning']};'>{status_counts['warning']}警告</span>")
    return ", ".join(stats)
