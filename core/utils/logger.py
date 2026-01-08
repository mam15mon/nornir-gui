import os
import logging
import sys
import time
from datetime import datetime
from functools import wraps
from typing import Callable, Any
from core.db.database import Database
import tempfile
from logging.handlers import RotatingFileHandler
import glob

def get_log_level(level_name: str) -> int:
    """获取日志级别"""
    return getattr(logging, level_name.upper(), logging.INFO)

def log_operation(operation_name: str) -> Callable:
    """操作日志装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(args[0].__class__.__module__)
            start_time = time.time()
            
            try:
                logger.info(f"开始执行{operation_name}操作")
                if 'devices' in kwargs:
                    logger.info(f"设备数量: {len(kwargs['devices'])}")
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                logger.info(f"{operation_name}操作完成，耗时: {elapsed_time:.2f}秒")
                return result
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(
                    f"{operation_name}操作失败: {str(e)}, 耗时: {elapsed_time:.2f}秒",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator

def cleanup_old_logs(log_dir: str, days: int = 7):
    """清理旧的日志文件
    
    Args:
        log_dir: 日志目录
        days: 保留天数
    """
    try:
        # 获取所有日志文件
        log_files = glob.glob(os.path.join(log_dir, "nornir_gui_*.log*"))
        current_date = datetime.now()
        
        for log_file in log_files:
            # 获取文件修改时间
            file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
            # 如果文件超过指定天数，删除
            if (current_date - file_mtime).days > days:
                try:
                    os.remove(log_file)
                except Exception as e:
                    print(f"删除旧日志文件失败 {log_file}: {e}")
    except Exception as e:
        print(f"清理旧日志文件时发生错误: {e}")

def setup_logging():
    """配置日志系统"""
    # 默认日志目录与级别
    log_dir = os.path.abspath('logs')
    log_level = logging.INFO

    # 从用户配置读取日志目录与级别
    try:
        from core.config.user_config import UserConfigManager
        user_config = UserConfigManager()

        try:
            configured_log_dir = user_config.get_log_path()
            if configured_log_dir:
                log_dir = configured_log_dir
        except Exception as e:
            print(f"读取日志路径设置失败: {e}")

        try:
            log_level_str = user_config.get_log_level()
            log_level = get_log_level(log_level_str)
        except Exception as e:
            print(f"读取日志级别设置失败: {e}")

    except Exception as e:
        print(f"读取用户配置失败: {e}")

    # 确保日志目录存在
    try:
        os.makedirs(log_dir, mode=0o777, exist_ok=True)
    except Exception as e:
        # 如果无法写入指定目录，使用临时目录
        print(f"无法写入日志目录 {log_dir}: {e}")
        log_dir = os.path.join(tempfile.gettempdir(), 'nornir_gui_logs')
        os.makedirs(log_dir, exist_ok=True)

    # 清理旧日志文件
    cleanup_old_logs(log_dir)

    # 生成带日期的日志文件路径
    current_date = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f'nornir_gui_{current_date}.log')

    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    try:
        # 创建文件处理器 - 使用 RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,  # 每天最多10个文件，超过会自动删除最旧的
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)

        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)

        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # 清除现有处理器
        root_logger.handlers.clear()

        # 添加新的处理器
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        root_logger.info(f"日志系统初始化成功，日志文件: {log_file}，日志级别: {logging.getLevelName(log_level)}")

    except Exception as e:
        print(f"日志系统初始化失败: {e}")
        # 仅使用控制台日志
        logging.basicConfig(
            level=logging.INFO,
            format=formatter._fmt,
            handlers=[console_handler]
        )

def handle_error(logger: logging.Logger, device_name: str, error: Exception, operation: str) -> dict:
    """统一的错误处理方法
    
    Args:
        logger: 日志记录器
        device_name: 设备名称
        error: 异常对象
        operation: 操作名称
        
    Returns:
        dict: 包含错误信息的字典
    """
    error_msg = f"{operation}失败: {str(error)}"
    logger.error(f"{device_name} - {error_msg}", exc_info=True)
    return {
        'status': error_msg,
        'result': str(error),
        'output_file': None
    } 
