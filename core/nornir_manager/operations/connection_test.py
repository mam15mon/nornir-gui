from typing import List
import logging
from nornir.core.task import Task, Result
from nornir_utils.plugins.tasks.networking import tcp_ping
from core.utils.logger import log_operation, handle_error
from ..base.nornir_manager import encode_task_name
from .base import BaseOperation

logger = logging.getLogger(__name__)

class ConnectionTest(BaseOperation):
    """连接测试操作类"""
    
    @encode_task_name
    def test_connection(self, task: Task) -> Result:
        """单个设备的连接测试任务"""
        if not self.is_running:
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )

        device = task.host
        device_name = device.name
        logger.info(f"开始测试设备: {device_name}")
        
        # 1. 使用tcp_ping测试端口连通性
        self.status_changed.emit(device_name, "正在测试端口连通性...")
        logger.info(f"{device_name} - 测试端口连通性...")
        result = task.run(
            task=tcp_ping,
            ports=[device.port or 22],  # SSH端口
            timeout=5
        )
        
        if not result[0].result[device.port or 22]:
            status = "失败：端口不可达"
            logger.error(f"{device_name} - {status}")
            self.status_changed.emit(device_name, status)
            self.results[device_name] = {
                'status': status,
                'result': status,
                'output_file': None
            }
            raise Exception("端口不可达")
        
        logger.info(f"{device_name} - 端口连通性测试成功")
        self.status_changed.emit(device_name, "连通性ok，正在测试登录...")
        
        if not self.is_running:  # 再次检查是否被停止
            logger.info(f"{device_name} - 测试已停止，中止任务")
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )

        # 2. 测试 SSH 登录
        try:
            # 尝试建立 SSH 连接
            logger.info(f"{device_name} - 尝试建立 SSH 连接...")
            conn = device.get_connection("netmiko", task.nornir.config)
            # 如果没有抛出异常，说明连接成功
            status = "成功: 登录测试完成"
            logger.info(f"{device_name} - {status}")
            self.status_changed.emit(device_name, status)
            self.results[device_name] = {
                'status': status,
                'result': status,
                'output_file': None
            }
            return Result(
                host=device,
                result=f"设备 {device_name} 连接测试成功"
            )
        except Exception as e:
            status = f"失败: 登录测试出错 - {str(e)}"
            logger.error(f"{device_name} - {status}")
            self.status_changed.emit(device_name, status)
            self.results[device_name] = {
                'status': status,
                'result': str(e),
                'output_file': None
            }
            raise
    
    def _validate_device(self, device) -> bool:
        """验证设备数据是否完整"""
        required_fields = ['name', 'hostname', 'username', 'password']
        return all(hasattr(device, field) and getattr(device, field) for field in required_fields)
    
    @log_operation("连接测试")
    def start(self, devices: List):
        """开始连接测试"""
        logger.info("开始连接测试操作")
        self.is_running = True
        self.results.clear()
        
        try:
            # 过滤无效设备
            valid_devices = [device for device in devices if self._validate_device(device)]
            logger.info(f"有效设备数量: {len(valid_devices)}")
            if not valid_devices:
                logger.warning("没有有效的设备可以测试")
                self.results = {"error": "没有有效的设备可以测试"}
                return
            
            # 初始化nornir
            logger.info("初始化 nornir...")
            nr = self.nornir_mgr.init_nornir(valid_devices)
            if not nr:
                logger.error("nornir 初始化失败")
                self.results = {"error": "nornir 初始化失败"}
                return
            
            try:
                # 执行测试，使用中文任务名
                logger.info("开始执行测试任务...")
                results = nr.run(
                    name="连接测试任务",  # 使用中文任务名
                    task=self.test_connection
                )
                logger.info(f"测试任务执行完成，结果: {results}")
            except Exception as e:
                error_msg = f"连接测试出错: {str(e)}"
                logger.error(error_msg)
                self.results = handle_error(logger, "全局", e, "连接测试")
        finally:
            self.is_running = False
            self.nornir_mgr.close()
            logger.info(f"测试完成，results: {self.results}") 