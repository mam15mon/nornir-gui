import socks
import socket
import logging
from typing import Optional, Dict, Any
from .db.database import Database

logger = logging.getLogger(__name__)

class ProxyManager:
    """代理管理器，用于管理全局代理设置"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        # 确保_initialized属性存在
        elif not hasattr(cls._instance, '_initialized'):
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db=None):
        if getattr(self, '_initialized', False):
            return

        self._initialized = True
        self.db = db if db is not None else Database()
        self._original_socket = socket.socket
        self.proxy_enabled = False
        self.proxy_host = None
        self.proxy_port = None

    def load_settings(self) -> None:
        """优先从用户配置文件加载代理设置，回退到数据库"""
        try:
            # 尝试从用户配置文件读取
            config_manager = self.db.get_config_manager()
            if config_manager:
                proxy_settings = config_manager.get_proxy_settings()
                self.proxy_enabled = proxy_settings['enabled']
                self.proxy_host = proxy_settings['host']
                self.proxy_port = proxy_settings['port']
                return
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"从用户配置读取代理设置失败，回退到数据库: {e}")

        # 回退到数据库设置
        try:
            settings = self.db.get_settings()
            self.proxy_enabled = settings['proxy_enabled']
            self.proxy_host = settings['proxy_host']
            self.proxy_port = settings['proxy_port']
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"从数据库读取代理设置也失败: {e}")
            # 使用默认值
            self.proxy_enabled = False
            self.proxy_host = None
            self.proxy_port = None
        
    def apply_proxy(self) -> None:
        """应用代理设置"""
        self.load_settings()
        
        if self.proxy_enabled and self.proxy_host and self.proxy_port:
            try:
                # 设置全局代理
                socks.set_default_proxy(
                    proxy_type=socks.SOCKS5,
                    addr=self.proxy_host,
                    port=self.proxy_port
                )
                # 替换默认的socket
                socket.socket = socks.socksocket
                logger.info(f"已启用代理: {self.proxy_host}:{self.proxy_port}")
            except Exception as e:
                logger.error(f"设置代理失败: {str(e)}")
                self.disable_proxy()
        else:
            self.disable_proxy()
            
    def disable_proxy(self) -> None:
        """禁用代理"""
        socket.socket = self._original_socket
        socks.set_default_proxy()
        logger.info("已禁用代理")
        
    def save_settings(self, enabled: bool, host: str = '', port: int = 8080) -> None:
        """保存代理设置到用户配置文件"""
        try:
            # 优先保存到用户配置文件
            config_manager = self.db.get_config_manager()
            if config_manager:
                config_manager.set_proxy_settings(enabled, host, port)
                logger.info("代理设置已保存到用户配置文件")
            else:
                # 回退到数据库保存
                logger.warning("用户配置管理器不可用，保存到数据库")
                # 这里可以添加数据库保存逻辑，但现在优先使用用户配置

        except Exception as e:
            logger.error(f"保存代理设置失败: {e}")
            raise

    def get_proxy_settings(self) -> Dict[str, Any]:
        """获取当前代理设置"""
        return {
            'proxy_enabled': self.proxy_enabled,
            'proxy_host': self.proxy_host,
            'proxy_port': self.proxy_port
        }
        
    def __del__(self):
        """析构时恢复原始socket设置"""
        self.disable_proxy() 