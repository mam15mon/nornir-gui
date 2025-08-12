from typing import List, Dict, Any, Optional
import logging
import os
from PySide6.QtCore import QObject, Signal
from nornir_netmiko.tasks import netmiko_send_command
from ..base.nornir_manager import NornirManager
from core.db.database import Database

from nornir.core.task import Result
from core.device_inspector import DeviceInspector
from datetime import datetime

logger = logging.getLogger(__name__)

class DeviceInspection(QObject):
    """设备巡检操作类"""

    # 定义信号
    status_changed = Signal(str, str)  # (device_name, status)
    progress_updated = Signal(int, int)  # (current, total)
    operation_finished = Signal(bool)  # success

    def __init__(self):
        super().__init__()
        self.nornir_mgr = NornirManager()
        self.db = Database()
        self.is_running = False
        self.results = {}
        self.base_path = ""
        self.output_path = ""
        self._init_paths()

    def _init_paths(self):
        """初始化输出路径"""
        # 使用统一的路径获取方法
        from core.config.path_utils import get_archive_subdir_path
        self.output_path = get_archive_subdir_path("巡检结果", self.db)

    def _validate_device(self, device):
        """验证设备数据是否完整"""
        required_attrs = ['name', 'hostname', 'platform', 'username', 'password']
        return all(hasattr(device, attr) and getattr(device, attr) for attr in required_attrs)

    def get_inspection_commands(self, platform: str) -> List[str]:
        """根据平台类型获取巡检命令"""
        # 华为设备巡检命令
        huawei_commands = [
            "display version",
            "display cpu",
            "display memory",
            "display alarm active",
            "display device",
            "display interface brief",
            "display clock",
            "display ntp status"
        ]

        # H3C设备巡检命令
        h3c_commands = [
            "display version",
            "display cpu",
            "display memory",
            "display power",
            "display fan",
            "display alarm",
            "display environment",  # 添加温度检测命令
            "display counters inbound interface",
            "display counters outbound interface",
            "display clock",
            "display ntp status"
        ]

        # 根据平台返回对应命令
        if "huawei" in platform.lower() or "vrp" in platform.lower():
            return huawei_commands
        elif "h3c" in platform.lower() or "hp" in platform.lower() or "comware" in platform.lower():
            return h3c_commands
        else:
            # 尝试通过平台名称判断
            if platform.lower() in ["huawei_vrpv8", "huawei_vrp", "huawei"]:
                return huawei_commands
            elif platform.lower() in ["hp_comware", "h3c", "h3c_comware", "comware"]:
                return h3c_commands
            else:
                # 默认返回华为命令
                return huawei_commands

    def run_inspection(self, task, device_command_map: Dict[str, List[str]]) -> Result:
        """执行巡检命令"""
        if not self.is_running:
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )

        # 获取当前设备的命令列表
        device_name = task.host.name
        commands = device_command_map.get(device_name, [])

        try:
            device = task.host
            device_name = device.name
            site = device.data.get('site', "未分类")
            platform = device.platform

            logger.info(f"开始执行巡检 - 设备: {device_name}, 站点: {site}, 平台: {platform}")

            # 更新状态为正在执行
            self.status_changed.emit(device_name, "正在执行巡检...")

            # 创建站点输出目录
            site_path = os.path.join(self.output_path, site)
            os.makedirs(site_path, exist_ok=True)

            # 创建设备输出文件
            output_file = os.path.join(site_path, f'{device_name}-inspection.txt')
            combined_output = []

            # 执行每个巡检命令
            all_outputs = []
            for cmd in commands:
                output = task.run(
                    task=netmiko_send_command,
                    command_string=cmd,
                    name=f"inspection_cmd_to_{device_name}"
                )
                all_outputs.append((cmd, str(output.result)))

            # 写入命令和输出
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"设备巡检执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"设备名称: {device_name}\n")
                f.write(f"设备平台: {platform}\n")
                f.write(f"站点: {site}\n\n")

                for cmd, out in all_outputs:
                    f.write(f"\n命令:\n{cmd}\n")
                    f.write(f"输出:\n{out}\n")
                    f.write("-" * 50 + "\n")
                    combined_output.append(f"{cmd}\n{out}")

            # 分析巡检结果
            combined_content = "\n".join(combined_output)
            device_type = DeviceInspector.detect_device_type(combined_content)
            inspector = DeviceInspector.create_inspector(device_type)

            inspection_result = {}
            if inspector:
                # 为了更好地处理命令输出，我们为每个命令添加标准格式
                formatted_content = ""
                for cmd, out in all_outputs:
                    formatted_content += f"命令:\n{cmd}\n输出:\n{out}\n{'-' * 50}\n"

                inspection_result = inspector.inspect_all(formatted_content)

                # 将分析结果写入文件
                with open(output_file, 'a', encoding='utf-8') as f:
                    f.write("\n\n" + "=" * 50 + "\n")
                    f.write("巡检分析结果:\n")
                    f.write("=" * 50 + "\n\n")

                    for category, result in inspection_result.items():
                        f.write(f"{category.upper()}:\n")
                        f.write(f"状态: {result.get('status', 'unknown')}\n")
                        f.write(f"信息: {result.get('message', '')}\n")
                        if 'details' in result:
                            f.write(f"详情: {result.get('details', '')}\n")
                        f.write("-" * 30 + "\n")

            # 检查是否有异常状态
            has_abnormal = any(item.get("status") == "abnormal" for item in inspection_result.values())
            has_error = any(item.get("status") == "error" for item in inspection_result.values())

            # 设置状态文本
            if has_error:
                status = "成功: 发现错误"
            elif has_abnormal:
                status = "成功: 发现异常"
            else:
                status = "成功: 设备正常"

            self.status_changed.emit(device_name, status)

            # 返回结果
            return Result(
                host=task.host,
                result={
                    "output_file": output_file,
                    "inspection_result": inspection_result,
                    "device_type": device_type
                }
            )

        except Exception as e:
            error_msg = f"巡检出错: {str(e)}"
            logger.error(f"{device_name} - {error_msg}")
            self.status_changed.emit(device_name, f"错误: {str(e)}")
            return Result(
                host=task.host,
                result=error_msg,
                failed=True
            )

    def start(self, devices: List[Any]) -> None:
        """开始设备巡检"""
        self.is_running = True
        self.results = {}  # 重置结果
        total = len(devices)
        completed = 0
        logger.info(f"开始对 {total} 个设备执行巡检")

        try:
            # 验证设备数据
            for device in devices:
                if not self._validate_device(device):
                    name = getattr(device, 'name', 'Unknown')
                    raise ValueError(f"设备 {name} 数据不完整")

            # 使用 NornirManager 初始化
            self.nornir_mgr.init_nornir(devices)
            nr = self.nornir_mgr.get_nornir()

            # 创建设备命令映射
            device_command_map = {}
            for device in devices:
                device_command_map[device.name] = self.get_inspection_commands(device.platform)

            # 执行并行巡检 - 一次性对所有设备执行
            logger.info(f"开始并行巡检 {len(devices)} 个设备")
            results = nr.run(
                task=self.run_inspection,
                device_command_map=device_command_map
            )

            # 处理结果
            for device_name, multi_result in results.items():
                if not self.is_running:
                    logger.info("巡检被中止")
                    break

                if not multi_result.failed:
                    # 检查是否有异常状态
                    inspection_result = multi_result.result.get("inspection_result", {})
                    has_abnormal = any(item.get("status") == "abnormal" for item in inspection_result.values())
                    has_error = any(item.get("status") == "error" for item in inspection_result.values())

                    # 设置状态文本
                    if has_error:
                        status_text = "成功: 发现错误"
                    elif has_abnormal:
                        status_text = "成功: 发现异常"
                    else:
                        status_text = "成功: 设备正常"

                    self.results[device_name] = {
                        "status": status_text,
                        "output_file": multi_result.result.get("output_file", ""),
                        "inspection_result": inspection_result,
                        "device_type": multi_result.result.get("device_type", "unknown")
                    }
                else:
                    error_msg = "巡检失败"
                    if hasattr(multi_result, 'exception') and multi_result.exception:
                        error_msg = str(multi_result.exception)
                    elif hasattr(multi_result, 'result') and multi_result.result:
                        error_msg = str(multi_result.result)

                    self.results[device_name] = {
                        "status": f"失败: {error_msg}",
                        "error": error_msg
                    }

                # 更新进度
                completed += 1
                self.progress_updated.emit(completed, total)

            logger.info("巡检完成")
            self.operation_finished.emit(True)

        except Exception as e:
            logger.error(f"巡检过程出错: {str(e)}")
            self.operation_finished.emit(False)

        finally:
            self.is_running = False

    def stop(self) -> None:
        """停止巡检"""
        logger.info("停止巡检")
        self.is_running = False

    def get_results(self) -> Dict:
        """获取巡检结果"""
        return self.results

