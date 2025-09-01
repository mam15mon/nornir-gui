from typing import Dict, List
from nornir import InitNornir
from nornir.core.plugins.inventory import InventoryPluginRegister
from sqlalchemy.orm import Session
from core.db.database import Database
from core.db.models import Defaults
from core.base.singleton import SingletonBase
from .inventory import FlatDataInventory
import logging
import sys
from functools import wraps
from nornir.core.task import Task, Result

logger = logging.getLogger(__name__)

def encode_task_name(task_function):
    """装饰器：确保任务名称使用正确的编码"""
    @wraps(task_function)
    def wrapper(*args, **kwargs):
        # 如果第一个参数是 Task 对象
        if args and isinstance(args[0], Task):
            task = args[0]
            # 任务名称和主机名称编码已在数据层面处理
            # 不需要在这里进行编码转换
        return task_function(*args, **kwargs)
    return wrapper

class NornirManager(SingletonBase):
    """Nornir管理器基础类"""
    
    def _initialize(self):
        """初始化Nornir管理器"""
        self.nr = None  # nornir 实例
        self.db = Database()  # 数据库实例
        
    def _get_defaults(self) -> Dict:
        """获取默认连接设置"""
        with Session(self.db.engine) as session:
            defaults = session.query(Defaults).first()
            if not defaults:
                defaults = Defaults()
                session.add(defaults)
                session.commit()
            
            return {
                "timeout": defaults.timeout,  # 命令执行超时时间
                "global_delay_factor": defaults.global_delay_factor,  # 全局延迟因子
                "fast_cli": defaults.fast_cli,  # 快速CLI模式
                "read_timeout_override": defaults.read_timeout,  # 读取超时时间
                "num_workers": defaults.num_workers  # 并发工作线程数
            }
        
    def init_nornir(self, devices: List) -> None:
        """初始化 nornir"""
        try:
            defaults = self._get_defaults()
            
            # 注册自定义清单插件
            InventoryPluginRegister.register("FlatDataInventory", FlatDataInventory)
            
            # 初始化 nornir
            self.nr = InitNornir(
                runner={
                    "plugin": "threaded",
                    "options": {
                        "num_workers": defaults['num_workers'],
                    },
                },
                inventory={
                    "plugin": "FlatDataInventory",
                    "options": {
                        "data": devices,
                        "connection_options": defaults
                    }
                },
                logging={
                    "enabled": False  # 禁用 Nornir 的日志配置，使用全局配置
                }
            )
            
            # 修改 Nornir 内部任务名称
            from nornir.core.task import Task  # 修改这里的导入
            original_task = Task.copy
            def wrapped_copy(self, *args, **kwargs):
                result = original_task(self, *args, **kwargs)
                # 任务名称编码已在数据层面处理，不需要在这里转换
                return result
            Task.copy = wrapped_copy
            
            # 修改关闭连接任务的名称
            self.nr.close_connections_task = "关闭连接"
            
            return self.nr
        except Exception as e:
            logger.error(f"初始化 nornir 失败: {str(e)}")
            return None
    
    def _wrap_close_connections(self, close_func):
        """包装 close_connections 函数"""
        @wraps(close_func)
        def wrapper(*args, **kwargs):
            # 主机名编码已在数据层面处理，不需要在这里转换
            return close_func(*args, **kwargs)
        return wrapper
    
    def get_nornir(self):
        """获取 nornir 实例"""
        if not self.nr:
            raise RuntimeError("Nornir 尚未初始化")
        return self.nr
    
    def close(self):
        """关闭 nornir 连接"""
        if self.nr:
            # 主机名编码已在数据层面处理，不需要在这里转换
            self.nr.close_connections()
            self.nr = None 