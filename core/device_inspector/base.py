import re
import os
import concurrent.futures
import logging
from typing import Dict, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class DeviceInspector(ABC):
    """设备检测基类"""

    @staticmethod
    def detect_device_type(content: str) -> str:
        """检测设备类型"""
        try:
            # 首先检查厂商特定标识，这些是最可靠的
            # 华为设备标识 - 扩展匹配模式
            huawei_brands = [
                r'Huawei',
                r'HUAWEI',
                r'Huawei Versatile Routing Platform',
                r'VRP \(R\) software',
                r'HUAWEI \S+ (Routing Switch|Switch)'
            ]

            for pattern in huawei_brands:
                if re.search(pattern, content):
                    return "huawei"

            # H3C设备标识
            h3c_brands = [
                r'H3C Comware',
                r'H3C S\d+',
                r'hp_comware',
                r'HPE Comware'
            ]

            for pattern in h3c_brands:
                if re.search(pattern, content, re.IGNORECASE):
                    return "h3c"

            # 如果没有找到厂商标识，则检查命令特征
            # 华为特有命令特征
            huawei_specific = [
                r'CPU Usage\s+:\s+\d+%\s+Max:\s+\d+%',
                r'CPU utilization for five seconds:',
                r'Memory Using Percentage Is:',
                r'System Total Memory Is:.*\nTotal Memory Used Is:',
                r'Slot\s+Sub\s+Type\s+Online\s+Power\s+Register\s+Status\s+Role'
            ]

            # H3C特有命令特征
            h3c_specific = [
                r'Slot \d+ CPU \d+ CPU usage',
                r'Memory statistics are measured in KB',
                r'FreeRatio',
                r'PowerID State\s+Mode\s+Current'
            ]

            # 检查华为特有特征
            for pattern in huawei_specific:
                if re.search(pattern, content, re.IGNORECASE):
                    return "huawei"

            # 检查H3C特有特征
            for pattern in h3c_specific:
                if re.search(pattern, content, re.IGNORECASE):
                    return "h3c"

            # 如果仍然无法确定，尝试通过命令输出格式判断
            # 这部分不太可靠，但作为最后的尝试

            # 如果包含这些命令，更可能是H3C设备
            h3c_commands = [
                r'display cpu\n输出:',
                r'display memory\n输出:',
                r'display fan\n输出:'
            ]

            # 如果包含这些命令，更可能是华为设备
            huawei_commands = [
                r'display device\n输出:',
                r'display interface brief\n输出:',
                r'InUti/OutUti: input utility/output utility'
            ]

            # 计算匹配的命令数量
            h3c_matches = sum(1 for pattern in h3c_commands if re.search(pattern, content))
            huawei_matches = sum(1 for pattern in huawei_commands if re.search(pattern, content))

            # 根据匹配数量决定设备类型
            if h3c_matches > huawei_matches:
                return "h3c"
            elif huawei_matches > h3c_matches:
                return "huawei"

            # 如果匹配数量相同，默认为未知
            return "unknown"

        except Exception as e:
            logger.error(f"设备类型检测出错: {e}")
            return "unknown"

    @staticmethod
    def create_inspector(device_type: str):
        """创建对应的检测器实例"""
        try:
            if device_type == "huawei":
                from .huawei import HuaweiInspector
                return HuaweiInspector()
            elif device_type == "h3c":
                from .h3c import H3CInspector
                return H3CInspector()
            return None
        except Exception as e:
            logger.error(f"创建检测器实例出错: {e}")
            return None

    @staticmethod
    def read_files_in_directory(directory_path: str) -> List[Dict]:
        """读取目录下的所有文件并执行检测 (单线程版本)

        Args:
            directory_path: 要处理的目录路径

        Returns:
            List[Dict]: 每个文件的检测结果列表
        """
        results = []
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()

                        # 检测设备类型
                        device_type = DeviceInspector.detect_device_type(content)
                        logger.debug(f"文件: {file_path}, 检测到设备类型: {device_type}")

                        # 创建对应的检测器
                        inspector = DeviceInspector.create_inspector(device_type)

                        if inspector:
                            # 执行检测
                            result = inspector.inspect_all(content)
                            results.append({
                                "file_path": file_path,
                                "device_type": device_type,
                                "results": result
                            })
                        else:
                            logger.debug(f"设备非华为、H3C设备: {file_path}")

                except Exception as e:
                    logger.error(f"无法读取文件 {file_path}: {e}")

        return results

    @staticmethod
    def process_file(file_path: str) -> Dict:
        """处理单个文件并返回检测结果

        Args:
            file_path: 文件路径

        Returns:
            Dict: 文件检测结果
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

                # 检测设备类型
                device_type = DeviceInspector.detect_device_type(content)
                logger.debug(f"文件: {file_path}, 检测到设备类型: {device_type}")

                # 创建对应的检测器
                inspector = DeviceInspector.create_inspector(device_type)

                if inspector:
                    # 执行检测
                    result = inspector.inspect_all(content)
                    return {
                        "file_path": file_path,
                        "device_type": device_type,
                        "results": result,
                        "success": True
                    }
                else:
                    logger.debug(f"设备非华为、H3C设备: {file_path}")
                    return {
                        "file_path": file_path,
                        "device_type": "unknown",
                        "success": False,
                        "error": "不支持的设备类型"
                    }

        except Exception as e:
            error_msg = f"无法读取文件 {file_path}: {e}"
            logger.error(error_msg)
            return {
                "file_path": file_path,
                "device_type": "unknown",
                "success": False,
                "error": error_msg
            }

    @staticmethod
    def read_files_with_threadpool(directory_path: str, max_workers: int = None) -> List[Dict]:
        """使用线程池读取目录下的所有文件并执行检测

        Args:
            directory_path: 要处理的目录路径
            max_workers: 最大工作线程数，默认为None（由系统决定）

        Returns:
            List[Dict]: 每个文件的检测结果列表
        """
        # 收集所有文件路径
        file_paths = []
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                file_paths.append(file_path)

        # 如果没有文件，直接返回空列表
        if not file_paths:
            return []

        # 使用线程池并行处理文件
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(DeviceInspector.process_file, file_path): file_path
                for file_path in file_paths
            }

            # 收集结果（按完成顺序）
            for future in concurrent.futures.as_completed(future_to_file):
                result = future.result()
                if result.get("success", False):
                    results.append(result)

        return results

    @abstractmethod
    def cpu_inspect(self, content: str) -> Dict:
        """CPU检测"""
        pass

    @abstractmethod
    def mem_inspect(self, content: str) -> Dict:
        """内存检测"""
        pass

    @abstractmethod
    def power_inspect(self, content: str) -> Dict:
        """电源检测"""
        pass

    @abstractmethod
    def fan_inspect(self, content: str) -> Dict:
        """风扇检测"""
        pass

    @abstractmethod
    def ntp_inspect(self, content: str) -> Dict:
        """NTP检测"""
        pass

    @abstractmethod
    def int_error_inspect(self, content: str) -> Dict:
        """接口错误检测"""
        pass

    @abstractmethod
    def alarm_inspect(self, content: str) -> Dict:
        """告警检测"""
        pass

    @abstractmethod
    def temperature_inspect(self, content: str) -> Dict:
        """温度检测"""
        pass

    def inspect_all(self, content: str) -> Dict:
        """执行所有检测"""
        return {
            "cpu": self.cpu_inspect(content),
            "memory": self.mem_inspect(content),
            "power": self.power_inspect(content),
            "fan": self.fan_inspect(content),
            "ntp": self.ntp_inspect(content),
            "interface_errors": self.int_error_inspect(content),
            "alarms": self.alarm_inspect(content),
            "temperature": self.temperature_inspect(content)
        }