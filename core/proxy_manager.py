import socks
import socket
import logging
from typing import Optional, Dict, Any
from .db.database import Database

logger = logging.getLogger(__name__)

class ProxyManager:
    """代理管理器，用于管理全局代理设置"""
    
    _instance = None  # 单例实例
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self.db = Database()
        self._original_socket = socket.socket
        self.proxy_enabled = False
        self.proxy_host = None
        self.proxy_port = None
        
    def load_settings(self) -> None:
        """从数据库加载代理设置"""
        settings = self.db.get_settings()
        self.proxy_enabled = settings['proxy_enabled']
        self.proxy_host = settings['proxy_host']
        self.proxy_port = settings['proxy_port']
        
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