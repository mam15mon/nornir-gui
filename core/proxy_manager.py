import socks
import socket
import logging
from typing import Optional, Dict, Any
from .db.database import Database
from .base.singleton import SingletonBase

logger = logging.getLogger(__name__)

class ProxyManager(SingletonBase):
    """代理管理器，用于管理全局代理设置"""
    
    def _initialize(self, db=None):
        """初始化代理管理器"""
        self.db = db if db is not None else Database()
        self._original_socket = socket.socket
        self.proxy_enabled = False
        self.proxy_host = None
        self.proxy_port = None
        self._config_manager = None

    def load_settings(self) -> None:
        """从用户配置文件加载代理设置"""
        try:
            # 获取配置管理器
            if self._config_manager is None:
                self._config_manager = self.db.get_config_manager()
            
            if self._config_manager:
                proxy_settings = self._config_manager.get_proxy_settings()
                self.proxy_enabled = proxy_settings['enabled']
                self.proxy_host = proxy_settings['host']
                self.proxy_port = proxy_settings['port']
                logger.info(f"从用户配置加载代理设置: enabled={self.proxy_enabled}, host={self.proxy_host}, port={self.proxy_port}")
            else:
                logger.warning("配置管理器不可用，使用默认代理设置")
                self._reset_to_defaults()
                
        except Exception as e:
            logger.error(f"加载代理设置失败，使用默认值: {e}")
            self._reset_to_defaults()
        
    def _reset_to_defaults(self):
        """重置为默认代理设置"""
        self.proxy_enabled = False
        self.proxy_host = None
        self.proxy_port = None
        logger.info("代理设置已重置为默认值")
        
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
            # 获取配置管理器
            if self._config_manager is None:
                self._config_manager = self.db.get_config_manager()
            
            if self._config_manager:
                self._config_manager.set_proxy_settings(enabled, host, port)
                logger.info("代理设置已保存到用户配置文件")
                # 更新内存中的设置
                self.proxy_enabled = enabled
                self.proxy_host = host
                self.proxy_port = port
            else:
                logger.error("配置管理器不可用，无法保存代理设置")
                raise RuntimeError("配置管理器不可用")

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