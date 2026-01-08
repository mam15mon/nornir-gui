"""
统一的单例模式基类
"""

from typing import TypeVar, Type, Any
import threading

T = TypeVar('T', bound='SingletonBase')

class SingletonBase:
    """单例模式基类"""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if getattr(self, '_initialized', False):
            return
        
        self._initialized = True
        self._initialize(*args, **kwargs)
    
    def _initialize(self, *args: Any, **kwargs: Any) -> None:
        """子类需要重写此方法进行初始化"""
        pass
    
    @classmethod
    def get_instance(cls: Type[T]) -> T:
        """获取单例实例"""
        if cls._instance is None:
            cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls: Type[T]) -> None:
        """重置单例实例（主要用于测试）"""
        with cls._lock:
            cls._instance = None
            cls._initialized = False