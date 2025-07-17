from PySide6.QtCore import QUrl
import os
from .result_utils import (
    get_status_color, get_status_icon, get_category_name,
    calculate_status_counts, format_status_stats_html
)

class OverviewFormatter:
    """概览格式化器"""
    
    @staticmethod
    def format_device_content(device_name, result):
        """格式化设备概览内容"""
        status = result.get('status', 'Unknown')
        result_text = result.get('result', '')
        output_file = result.get('output_file')
        inspection_result = result.get('inspection_result', {})

        # 检查是否是防火墙地址组操作结果
        operation = result.get('operation')
        ip_addresses = result.get('ip_addresses')
        group_name = result.get('group_name')
        commands = result.get('commands')

        # 设置状态颜色
        status_color = get_status_color(status)

        # 如果是防火墙地址组操作结果
        if operation in ['add', 'delete']:
            content = [
                f"设备: <a href='device:{device_name}' style='text-decoration: none; color: inherit;'><b>{device_name}</b></a>",
                f"状态: <a href='device:{device_name}' style='text-decoration: none;'><span style='color: {status_color}; font-weight: bold;'>{status}</span></a>"
            ]

            # 添加操作详情
            operation_text = "添加地址" if operation == "add" else "删除地址"
            content.append(f"<br><b>操作类型:</b> {operation_text}")

            if group_name:
                content.append(f"<b>地址组:</b> {group_name}")

            if ip_addresses:
                content.append(f"<b>IP地址:</b> {', '.join(ip_addresses)}")

            # 如果操作失败，显示错误信息
            if result.get('failed') or '错误' in status:
                error_msg = result.get('error', '未知错误')
                content.append(f"<br><b>错误信息:</b> <span style='color: red;'>{error_msg}</span>")
            else:
                # 显示执行的命令（仅在成功时）
                if commands:
                    content.append("<br><b>执行的命令:</b>")
                    for cmd in commands:
                        if not cmd.startswith('#'):  # 跳过注释行
                            content.append(f"<code style='background-color: #f0f0f0; padding: 2px 4px; font-family: monospace;'>{cmd}</code>")

                # 如果有输出文件，添加文件链接（仅在成功时）
                if output_file:
                    content.append(f"<br><b>输出文件:</b> <a href='{QUrl.fromLocalFile(output_file).toString()}'>{os.path.basename(output_file)}</a>")

            content.append("<hr>")
            return "<br>".join(content)

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
                status_counts = calculate_status_counts(inspection_result)
                
                # 添加状态统计
                content.append(f"状态统计: {format_status_stats_html(status_counts)}")
                content.append("<br>")
                
                # 添加各项检查结果
                for category, item in inspection_result.items():
                    item_status = item.get('status', 'unknown')
                    item_message = item.get('message', '')
                    
                    # 设置状态颜色和图标
                    icon = get_status_icon(item_status)
                    color = get_status_color(item_status)
                    
                    # 格式化类别名称
                    category_name = get_category_name(category)
                    
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
    
    @staticmethod
    def format_all_devices(results):
        """格式化所有设备的概览内容"""
        overview_content = []
        for device_name, result in results.items():
            content = OverviewFormatter.format_device_content(device_name, result)
            if content:  # 只添加有内容的结果
                overview_content.append(content)
        
        return "<br>".join(overview_content)
