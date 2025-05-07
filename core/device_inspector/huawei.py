import re
from typing import Dict
from .base import DeviceInspector

class HuaweiInspector(DeviceInspector):
    """华为设备检测类"""

    def cpu_inspect(self, content: str) -> Dict:
        cpu_abnormal = {}

        # 检查是否包含display cpu命令
        if not re.search(r"display cpu", content, re.IGNORECASE):
            return {"status": "error", "message": "请检查是否运行display cpu命令"}

        # 尝试匹配华为设备的多种CPU输出格式

        # 格式1: CPU Usage: xx% Max: xx%
        usage_match = re.search(r'CPU Usage\s+:\s+(\d+)%\s+Max:\s+(\d+)%', content)
        if usage_match:
            current_usage = int(usage_match.group(1))
            max_usage = int(usage_match.group(2))

            if current_usage >= 80 or max_usage >= 90:
                cpu_abnormal["CPU"] = f"当前使用率:{current_usage}%, 最大使用率:{max_usage}%"

        # 格式2: CPU utilization for five seconds: xx%: one minute: xx%: five minutes: xx%
        util_match = re.search(r'CPU utilization for five seconds:\s+(\d+)%:\s+one minute:\s+(\d+)%:\s+five minutes:\s+(\d+)%', content)
        if util_match:
            five_sec = int(util_match.group(1))
            one_min = int(util_match.group(2))
            five_min = int(util_match.group(3))

            if five_sec >= 80 or one_min >= 80 or five_min >= 80:
                cpu_abnormal["CPU"] = f"5秒:{five_sec}%, 1分钟:{one_min}%, 5分钟:{five_min}%"

        # 格式3: 旧格式，按行匹配CPU使用率
        if not cpu_abnormal:
            for line in content.strip().split('\n'):
                match = re.match(r'^(cpu\d+)\s+(\d+)%', line, re.MULTILINE)
                if match and match.groups():
                    if int(match.group(2)) >= 80:
                        cpu_name = match.group(1)
                        current_usage = match.group(2) + '%'
                        cpu_abnormal[cpu_name] = current_usage

        # 如果没有找到异常，返回正常状态
        if not cpu_abnormal:
            return {"status": "normal", "message": "CPU状态:正常"}

        return {"status": "abnormal", "message": "CPU状态:异常", "details": cpu_abnormal}

    def mem_inspect(self, content: str) -> Dict:
        # 检查是否包含display memory命令
        if not re.search(r"display memory", content, re.IGNORECASE):
            return {"status": "error", "message": "请检查是否运行display memory命令"}

        # 尝试匹配多种内存输出格式

        # 格式1: Memory Using Percentage: xx%
        memory_match1 = re.search(r'Memory Using Percentage:\s*(\d+)%', content)
        if memory_match1:
            usage = int(memory_match1.group(1))
            if usage >= 80:
                return {"status": "abnormal", "message": f"内存状态:异常, 内存使用率:{usage}%"}
            return {"status": "normal", "message": f"内存状态:正常, 内存使用率:{usage}%"}

        # 格式2: Memory Using Percentage Is: xx%
        memory_match2 = re.search(r'Memory Using Percentage Is:\s*(\d+)%', content)
        if memory_match2:
            usage = int(memory_match2.group(1))
            if usage >= 80:
                return {"status": "abnormal", "message": f"内存状态:异常, 内存使用率:{usage}%"}
            return {"status": "normal", "message": f"内存状态:正常, 内存使用率:{usage}%"}

        # 格式3: 计算使用百分比
        total_match = re.search(r'System Total Memory Is:\s*(\d+)\s*bytes', content)
        used_match = re.search(r'Total Memory Used Is:\s*(\d+)\s*bytes', content)

        if total_match and used_match:
            total_mem = int(total_match.group(1))
            used_mem = int(used_match.group(1))

            if total_mem > 0:
                usage_percent = round((used_mem / total_mem) * 100)
                if usage_percent >= 80:
                    return {"status": "abnormal", "message": f"内存状态:异常, 内存使用率:{usage_percent}%"}
                return {"status": "normal", "message": f"内存状态:正常, 内存使用率:{usage_percent}%"}

        # 如果所有格式都不匹配
        return {"status": "error", "message": "无法获取内存使用率"}

    def power_inspect(self, content: str) -> Dict:
        power_abnormal = {}
        if not re.search("display device", content):
            return {"status": "error", "message": "请检查是否运行display device命令"}

        pattern = re.compile(r'^(PWR\d)+\s+.*?\s+Registered\s+(\S+)', re.MULTILINE)
        matches = pattern.findall(content)
        for match in matches:
            if match and len(match) >= 2:
                if match[1] != "Normal":
                    power_abnormal[match[0]] = match[1]

        if not power_abnormal:
            return {"status": "normal", "message": "电源状态:正常"}
        return {"status": "abnormal", "message": "电源状态:异常", "details": power_abnormal}

    def fan_inspect(self, content: str) -> Dict:
        fan_abnormal = {}
        if not re.search("display device", content):
            return {"status": "error", "message": "请检查是否运行display device命令"}

        pattern = re.compile(r'^(FAN\d)+\s+.*?\s+Registered\s+(\S+)', re.MULTILINE)
        matches = pattern.findall(content)
        for match in matches:
            if match and len(match) >= 2:
                if match[1] != "Normal":
                    fan_abnormal[match[0]] = match[1]

        if not fan_abnormal:
            return {"status": "normal", "message": "风扇状态:正常"}
        return {"status": "abnormal", "message": "风扇状态:异常", "details": fan_abnormal}

    def ntp_inspect(self, content: str) -> Dict:
        if not re.search("display ntp status", content):
            return {"status": "error", "message": "请检查是否运行display ntp status命令"}

        ntp_match = re.search(r'clock status:\s*(\w+)', content)
        if ntp_match and ntp_match.group(1) == "synchronized":
            return {"status": "normal", "message": "NTP状态:正常"}
        return {"status": "abnormal", "message": f"NTP状态:异常，NTP状态:{ntp_match.group(1) if ntp_match else '未知'}"}

    def int_error_inspect(self, content: str) -> Dict:
        int_error_abnormal = {}
        if not re.search("display interface brief", content):
            return {"status": "error", "message": "请检查是否运行display interface brief命令"}

        pattern = re.compile(r'^(100GE\d+\/\d+\/\d+|10GE\d+\/\d+\/\d+|Eth-Trunk\d+|Eth-Trunk\d+\.+\d*?)\s+.*?\s+(\d+)$', re.MULTILINE)
        matches = pattern.findall(content)
        for match in matches:
            if match and len(match) >= 2:
                if int(match[1]) > 0:
                    interface = f"接口:{match[0]}"
                    error_num = f"错包数:{match[1]}"
                    int_error_abnormal[interface] = error_num

        if not int_error_abnormal:
            return {"status": "normal", "message": "接口状态:无错包"}
        return {"status": "abnormal", "message": "接口错报状态:有错包", "details": int_error_abnormal}

    def alarm_inspect(self, content: str) -> Dict:
        # 检查是否包含display alarm active命令
        if not re.search(r"display alarm active", content, re.IGNORECASE):
            return {"status": "error", "message": "请检查是否运行display alarm active命令"}

        # 提取完整的告警输出部分
        # 首先尝试精确匹配命令和输出部分
        alarm_section_pattern = r'命令:\s*display alarm active\s*\n输出:\s*\n(.*?)(?=\n-{10,}\s*\n命令:|\n-{10,}\s*$|$)'
        alarm_section_match = re.search(alarm_section_pattern, content, re.DOTALL)

        if alarm_section_match:
            # 获取输出内容并去除前后空白
            alarm_output = alarm_section_match.group(1).strip()

            # 如果输出为空或只有空白字符，表示没有告警
            if not alarm_output:
                return {"status": "normal", "message": "无活动告警"}

            # 检查是否包含"No active alarm"或类似信息
            if re.search(r'No active alarm|No alarm|No alarm information|No active alarms', alarm_output, re.IGNORECASE):
                return {"status": "normal", "message": "无活动告警"}

            # 检查是否包含实际的告警信息（不是空行或只有分隔符）
            # 只有包含特定告警关键词的内容才被视为告警
            alarm_keywords = [
                'CRITICAL', 'MAJOR', 'MINOR', 'WARNING',
                'Error', 'Failure', 'Failed', 'Alarm', 'Alert'
            ]

            # 检查是否包含告警关键词
            has_alarm_keyword = any(keyword.lower() in alarm_output.lower() for keyword in alarm_keywords)

            # 检查是否包含告警表格头部（通常表示有告警表格）
            has_alarm_table = bool(re.search(r'Sequence\s+AlarmId\s+Severity', alarm_output, re.IGNORECASE))

            # 检查是否包含设备状态信息（通常来自display device命令）
            is_device_status = bool(re.search(r'Device status|Slot\s+Sub\s+Type\s+Online\s+Power\s+Register\s+Status', alarm_output, re.IGNORECASE))

            # 如果包含设备状态信息，不认为是告警
            if is_device_status:
                return {"status": "normal", "message": "无活动告警"}

            # 如果包含告警关键词或告警表格，认为有告警
            if has_alarm_keyword or has_alarm_table:
                # 提取完整的告警内容
                full_alarm_content = alarm_output

                # 如果告警内容被截断，尝试提取更完整的内容
                if "..." in full_alarm_content:
                    # 尝试提取从命令到下一个命令之间的所有内容
                    full_section_match = re.search(
                        r'命令:\s*display alarm active\s*\n输出:\s*\n(.*?)(?=\n-{10,}\s*\n命令:|\n-{10,}\s*$|$)',
                        content,
                        re.DOTALL
                    )
                    if full_section_match:
                        full_alarm_content = full_section_match.group(1).strip()

                return {"status": "abnormal", "message": "有活动告警", "details": full_alarm_content}
            else:
                # 如果没有找到告警关键词或表格，认为没有告警
                return {"status": "normal", "message": "无活动告警"}

        # 如果使用上面的模式无法匹配，尝试更宽松的匹配
        # 这是为了兼容不同格式的输出
        alt_pattern = r'命令:\s*display alarm active\s*\n输出:.*?(?=\n-{10,}\s*\n命令:|\n-{10,}\s*$|$)'
        alt_match = re.search(alt_pattern, content, re.DOTALL)

        if alt_match:
            alarm_text = alt_match.group(0)
            # 检查是否有空输出（只有命令和分隔符）
            output_lines = [line.strip() for line in alarm_text.split('\n') if line.strip()]
            # 如果只有命令行和输出:，没有实际内容
            if len(output_lines) <= 2:  # 命令行 + 输出:
                return {"status": "normal", "message": "无活动告警"}

            # 检查是否包含"No active alarm"或类似信息
            if re.search(r'No active alarm|No alarm|No alarm information|No active alarms', alarm_text, re.IGNORECASE):
                return {"status": "normal", "message": "无活动告警"}

            # 检查是否包含设备状态信息（通常来自display device命令）
            if re.search(r'Device status|Slot\s+Sub\s+Type\s+Online\s+Power\s+Register\s+Status', alarm_text, re.IGNORECASE):
                return {"status": "normal", "message": "无活动告警"}

            # 检查是否有实际的告警内容
            alarm_keywords = ['CRITICAL', 'MAJOR', 'MINOR', 'WARNING', 'Error', 'Failure', 'Failed', 'Alarm']
            if any(keyword.lower() in alarm_text.lower() for keyword in alarm_keywords):
                # 提取输出部分
                output_match = re.search(r'输出:\s*\n(.*?)(?=\n-{10,}\s*\n命令:|\n-{10,}\s*$|$)', alarm_text, re.DOTALL)
                if output_match:
                    alarm_content = output_match.group(1).strip()
                    return {"status": "abnormal", "message": "有活动告警", "details": alarm_content}
                return {"status": "abnormal", "message": "有活动告警", "details": alarm_text}

        # 默认情况下，如果没有找到明确的告警信息，认为没有告警
        return {"status": "normal", "message": "无活动告警"}