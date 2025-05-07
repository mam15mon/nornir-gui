import re
from typing import Dict
from .base import DeviceInspector

class H3CInspector(DeviceInspector):
    """H3C设备检测类"""

    def cpu_inspect(self, content: str) -> Dict:
        cpu_abnormal = {}
        if not re.search("display cpu", content):
            return {"status": "error", "message": "请检查是否运行display cpu命令"}

        pattern = re.compile(r'Slot (\d+) CPU (\d+) CPU usage:\s*'
                           r'(\d+)% in last 5 seconds\s*'
                           r'(\d+)% in last 1 minute\s*'
                           r'(\d+)% in last 5 minutes')
        matches = pattern.finditer(content)
        for match in matches:
            if match and match.groups():
                cpu_name = f"Slot {match.group(1)} CPU {match.group(2)}"
                if int(match.group(3)) >= 80 or int(match.group(4)) >= 80 or int(match.group(5)) >= 80:
                    current_usage = f"5秒钟:{match.group(3)}%; 1分钟:{match.group(4)}%; 5分钟:{match.group(5)}%;"
                    cpu_abnormal[cpu_name] = current_usage

        if not cpu_abnormal:
            return {"status": "normal", "message": "CPU状态:正常"}
        return {"status": "abnormal", "message": "CPU状态:异常", "details": cpu_abnormal}

    def mem_inspect(self, content: str) -> Dict:
        if not re.search("display memory", content):
            return {"status": "error", "message": "请检查是否运行display memory命令"}

        # 尝试匹配老H3C格式 (System Total Memory/Used Rate格式)
        old_h3c_pattern = re.compile(r'System Total Memory\(bytes\):\s+(\d+)\s+Total Used Memory\(bytes\):\s+(\d+)\s+Used Rate:\s+(\d+)%', re.DOTALL)
        old_h3c_match = old_h3c_pattern.search(content)

        if old_h3c_match:
            # 直接从输出中获取使用率
            usage_ratio = float(old_h3c_match.group(3))

            if usage_ratio >= 80.0:
                return {"status": "abnormal", "message": f"内存状态:异常, 内存使用率:{usage_ratio:.1f}%"}
            return {"status": "normal", "message": f"内存状态:正常, 内存使用率:{usage_ratio:.1f}%"}

        # 尝试匹配另一种老H3C格式
        alt_old_h3c_pattern = re.compile(r'System Total Memory\(bytes\):\s+(\d+).*?Total Used Memory\(bytes\):\s+(\d+)', re.DOTALL)
        alt_old_h3c_match = alt_old_h3c_pattern.search(content)

        if alt_old_h3c_match:
            # 计算使用率
            total_memory = float(alt_old_h3c_match.group(1))
            used_memory = float(alt_old_h3c_match.group(2))

            if total_memory > 0:
                usage_ratio = (used_memory / total_memory) * 100

                if usage_ratio >= 80.0:
                    return {"status": "abnormal", "message": f"内存状态:异常, 内存使用率:{usage_ratio:.1f}%"}
                return {"status": "normal", "message": f"内存状态:正常, 内存使用率:{usage_ratio:.1f}%"}

        # 尝试匹配FreeRatio格式 (新H3C格式)
        freeratio_pattern = re.compile(r'Mem:\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+\.\d+)%')
        freeratio_match = freeratio_pattern.search(content)

        if freeratio_match:
            free_ratio = float(freeratio_match.group(1))
            usage_ratio = 100.0 - free_ratio

            if usage_ratio >= 80.0:
                return {"status": "abnormal", "message": f"内存状态:异常, 内存使用率:{usage_ratio:.1f}%"}
            return {"status": "normal", "message": f"内存状态:正常, 内存使用率:{usage_ratio:.1f}%"}

        # 尝试匹配其他旧格式
        old_pattern = re.compile(r'Mem:\s+(?:\d+\s+)*(\d+\.\d+)%')
        old_matches = old_pattern.findall(content)

        if old_matches:
            percentages = [float(match) for match in old_matches]
            adjusted_values = [100 - percentage for percentage in percentages]
            max_usage = max(adjusted_values)

            if max_usage >= 80.0:
                return {"status": "abnormal", "message": f"内存状态:异常, 内存使用率:{max_usage:.1f}%"}
            return {"status": "normal", "message": f"内存状态:正常, 内存使用率:{max_usage:.1f}%"}

        return {"status": "error", "message": "无法获取内存使用率"}

    def power_inspect(self, content: str) -> Dict:
        power_abnormal = {}
        if not re.search(r"display power|display device", content, re.IGNORECASE):
            return {"status": "error", "message": "请检查是否运行display device命令"}

        # 匹配H3C电源输出格式
        pattern = re.compile(r'^\s*(\d+)\s+(\S+)\s+', re.MULTILINE)
        matches = pattern.findall(content)
        for match in matches:
            if match and len(match) >= 2:
                if match[1] != "Normal":
                    power_name = f"电源{match[0]}"
                    power_abnormal[power_name] = match[1]

        # 检查display device输出中的电源状态
        if not power_abnormal:
            # 如果是S5560X等型号，通常只显示设备状态而不单独显示电源状态
            device_pattern = re.compile(r'Slot\s+Type\s+State\s+Subslot', re.MULTILINE)
            if device_pattern.search(content):
                # 检查设备状态是否正常
                device_state_pattern = re.compile(r'(\d+)\s+(\S+)\s+(\w+)\s+', re.MULTILINE)
                device_matches = device_state_pattern.findall(content)
                for match in device_matches:
                    if match and len(match) >= 3:
                        # 如果设备状态正常，则认为电源也正常
                        if match[2] == "Master" or match[2] == "Normal":
                            return {"status": "normal", "message": "电源状态:正常"}

        if not power_abnormal:
            return {"status": "normal", "message": "电源状态:正常"}
        return {"status": "abnormal", "message": "电源状态:异常", "details": power_abnormal}

    def fan_inspect(self, content: str) -> Dict:
        fan_abnormal = {}
        if not re.search(r"display fan|display device", content, re.IGNORECASE):
            return {"status": "error", "message": "请检查是否运行display device命令"}

        # 匹配 "Fan X:" 和 "State    : XXX" 格式
        pattern = re.compile(r'Fan (\d+):\s+\n\s+State\s+:\s+(\S+)', re.MULTILINE)
        matches = pattern.finditer(content)

        for match in matches:
            if match and match.groups():
                fan_id = match.group(1)
                state = match.group(2)
                if state != "Normal":
                    fan_abnormal[f"Fan {fan_id}"] = state

        # 如果没有匹配到，尝试旧格式
        if not matches:
            old_pattern = re.compile(r'^.(Fan Frame+\s+\d)\s+.*?\s+State:\s+(\S+)', re.MULTILINE)
            old_matches = old_pattern.findall(content)
            for match in old_matches:
                if match and len(match) >= 2:
                    if match[1] != "Normal":
                        fan_abnormal[match[0]] = match[1]

        if not fan_abnormal:
            return {"status": "normal", "message": "风扇状态:正常"}
        return {"status": "abnormal", "message": "风扇状态:异常", "details": fan_abnormal}

    def ntp_inspect(self, content: str) -> Dict:
        if not re.search(r"display ntp status", content, re.IGNORECASE):
            return {"status": "error", "message": "请检查是否运行display ntp status命令"}

        # 检查是否配置了NTP
        not_configured = re.search(r'NTP is not configured|NTP service is disabled', content, re.IGNORECASE)
        if not_configured:
            return {"status": "warning", "message": "NTP未配置"}

        # 检查NTP状态 - 标准格式
        ntp_match = re.search(r' Clock status:\s*(\w+)', content)
        if ntp_match and ntp_match.group(1).lower() == "synchronized":
            return {"status": "normal", "message": "NTP状态:正常"}

        # 检查NTP状态 - H3C ntp-service格式
        ntp_service_match = re.search(r'Clock\s+status\s*:\s*(\w+)', content, re.IGNORECASE)
        if ntp_service_match and ntp_service_match.group(1).lower() == "synchronized":
            return {"status": "normal", "message": "NTP状态:正常"}

        # 检查NTP状态 - 另一种H3C格式
        alt_ntp_match = re.search(r'synchronization\s+status\s*:\s*(\w+)', content, re.IGNORECASE)
        if alt_ntp_match and alt_ntp_match.group(1).lower() in ["synchronized", "synced"]:
            return {"status": "normal", "message": "NTP状态:正常"}

        # 如果没有找到状态信息，但有NTP相关输出
        if re.search(r'display ntp status\n输出:|display ntp-service status\n输出:', content, re.IGNORECASE):
            return {"status": "abnormal", "message": "NTP状态:异常，未同步"}

        return {"status": "abnormal", "message": f"NTP状态:异常，当前状态:{ntp_match.group(1) if ntp_match else '未知'}"}

    def int_error_inspect(self, content: str) -> Dict:
        int_error_abnormal = {}
        if not re.search(r"display counters", content, re.IGNORECASE):
            return {"status": "error", "message": "请检查是否运行display counters inbound interface和display counters outbound interface命令"}

        # 匹配更多的接口类型，包括GE、XGE、BAGG等
        pattern = re.compile(r'^(GE\d+\/\d+\/\d+|XGE\d+\/\d+\/\d+|FGE\d+\/\d+\/\d+|BAGG\d+|RAGG\d+|RAGG\d+\.+\d*?)\s+.*?\s+(\d+)$', re.MULTILINE)

        # 查找错包数据
        # 首先检查inbound
        inbound_section = re.search(r'display counters inbound interface\n输出:.*?(?=--------------------------------------------------)', content, re.DOTALL)
        if inbound_section:
            matches = pattern.findall(inbound_section.group(0))
            for match in matches:
                if match and len(match) >= 2:
                    if int(match[1]) > 0:
                        interface = f"接口:{match[0]}"
                        error_num = f"入方向错包数:{match[1]}"
                        int_error_abnormal[interface] = error_num

        # 然后检查outbound
        outbound_section = re.search(r'display counters outbound interface\n输出:.*?(?=--------------------------------------------------)', content, re.DOTALL)
        if outbound_section:
            matches = pattern.findall(outbound_section.group(0))
            for match in matches:
                if match and len(match) >= 2:
                    if int(match[1]) > 0:
                        interface = f"接口:{match[0]}"
                        if interface in int_error_abnormal:
                            int_error_abnormal[interface] += f", 出方向错包数:{match[1]}"
                        else:
                            int_error_abnormal[interface] = f"出方向错包数:{match[1]}"

        # 我们不再使用display interface brief命令检测接口状态
        # 只使用display counters命令检测错包

        if not int_error_abnormal:
            return {"status": "normal", "message": "接口状态:无错包"}
        return {"status": "abnormal", "message": "接口错报状态:有错包", "details": int_error_abnormal}

    def alarm_inspect(self, content: str) -> Dict:
        # 检查是否执行了告警命令或日志命令
        if not re.search(r"display alarm|display logbuffer", content, re.IGNORECASE):
            return {"status": "error", "message": "请检查是否运行display logbuffer命令"}

        # 检查命令是否被识别
        unrecognized = re.search(r'% Unrecognized command found at', content)
        if unrecognized:
            # 尝试查找日志信息
            logbuffer_pattern = r'命令:\s*display logbuffer\s*\n输出:\s*\n(.*?)(?=\n-{10,}\s*\n命令:|\n-{10,}\s*$|$)'
            logbuffer_match = re.search(logbuffer_pattern, content, re.DOTALL)

            if logbuffer_match:
                log_output = logbuffer_match.group(1).strip()

                # 检查日志中是否有严重错误或告警
                error_keywords = ['CRITICAL', 'MAJOR', 'MINOR', 'WARNING', 'Error', 'Failure', 'Failed', 'Alarm', 'Alert']
                has_error = any(keyword.lower() in log_output.lower() for keyword in error_keywords)

                if has_error:
                    # 提取包含错误关键词的行
                    error_lines = []
                    for line in log_output.split('\n'):
                        if any(keyword.lower() in line.lower() for keyword in error_keywords):
                            error_lines.append(line.strip())

                    if error_lines:
                        return {"status": "abnormal", "message": "日志中发现错误", "details": '\n'.join(error_lines)}

                return {"status": "normal", "message": "日志中未发现严重错误"}

            return {"status": "warning", "message": "设备不支持display alarm命令，无法检测告警状态"}

        # 检查是否包含设备状态信息（通常来自display device命令）
        is_device_status = bool(re.search(r'Device status|Slot\s+Sub\s+Type\s+Online\s+Power\s+Register\s+Status', content, re.IGNORECASE))
        if is_device_status:
            return {"status": "normal", "message": "无活动告警"}

        # 提取告警命令输出部分
        alarm_section_pattern = r'命令:\s*display alarm\s*\n输出:\s*\n(.*?)(?=\n-{10,}\s*\n命令:|\n-{10,}\s*$|$)'
        alarm_section_match = re.search(alarm_section_pattern, content, re.DOTALL)

        if alarm_section_match:
            alarm_output = alarm_section_match.group(1).strip()

            # 如果输出为空或只有空白字符，表示没有告警
            if not alarm_output:
                return {"status": "normal", "message": "无活动告警"}

            # 检查是否包含"No alarm"或类似信息
            if re.search(r'No alarm|No active alarm|No alarm information', alarm_output, re.IGNORECASE):
                return {"status": "normal", "message": "无活动告警"}

            # 检查是否包含告警关键词
            alarm_keywords = ['CRITICAL', 'MAJOR', 'MINOR', 'WARNING', 'Error', 'Failure', 'Failed', 'Alarm', 'Alert']
            has_alarm_keyword = any(keyword.lower() in alarm_output.lower() for keyword in alarm_keywords)

            if has_alarm_keyword:
                return {"status": "abnormal", "message": "有活动告警", "details": alarm_output}

        # 检查日志缓冲区
        logbuffer_pattern = r'命令:\s*display logbuffer\s*\n输出:\s*\n(.*?)(?=\n-{10,}\s*\n命令:|\n-{10,}\s*$|$)'
        logbuffer_match = re.search(logbuffer_pattern, content, re.DOTALL)

        if logbuffer_match:
            log_output = logbuffer_match.group(1).strip()

            # 检查日志中是否有严重错误或告警
            error_keywords = ['CRITICAL', 'MAJOR', 'MINOR', 'WARNING', 'Error', 'Failure', 'Failed', 'Alarm', 'Alert']
            has_error = any(keyword.lower() in log_output.lower() for keyword in error_keywords)

            if has_error:
                # 提取包含错误关键词的行
                error_lines = []
                for line in log_output.split('\n'):
                    if any(keyword.lower() in line.lower() for keyword in error_keywords):
                        error_lines.append(line.strip())

                if error_lines:
                    return {"status": "abnormal", "message": "日志中发现错误", "details": '\n'.join(error_lines)}

        # 正常情况下的告警检测 - 尝试匹配表格结构
        alarm_table = re.search(
            r'(?<=display alarm\n输出:\n)\n*(-+)\n(.*?)\n(-+)\n(.*?)\n(-+)(\n=+)?',
            content,
            re.DOTALL
        )

        if alarm_table and alarm_table.group(0):
            # 检查表格内容是否为空或只有表头
            table_content = alarm_table.group(0).strip()
            table_lines = [line.strip() for line in table_content.split('\n') if line.strip() and not line.strip().startswith('-')]

            if len(table_lines) > 2:  # 有表头，所以大于2行表示有告警
                return {"status": "abnormal", "message": "有活动告警", "details": table_content}

        return {"status": "normal", "message": "无活动告警"}