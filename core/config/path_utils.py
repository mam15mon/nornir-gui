"""路径工具模块

提供统一的路径获取功能，支持从用户配置文件和数据库获取路径
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_archive_base_path(db_instance=None) -> str:
    """获取存档基础路径
    
    优先级：用户配置文件 > 数据库配置 > 默认路径
    
    Args:
        db_instance: 数据库实例，可选
        
    Returns:
        str: 存档基础路径
    """
    try:
        # 尝试从数据库获取配置管理器
        if db_instance:
            config_manager = db_instance.get_config_manager()
            if config_manager:
                return config_manager.get_archive_base_path()
        
        # 如果没有数据库实例，尝试直接创建配置管理器
        from .config_migrator import ConfigManager
        config_manager = ConfigManager()
        return config_manager.get_archive_base_path()
        
    except Exception as e:
        logger.warning(f"获取存档路径失败，使用默认路径: {e}")
        # 返回默认路径
        from pathlib import Path
        return str(Path.home() / "nornir-gui-files")


def get_archive_subdir_path(subdir_name: str, db_instance=None) -> str:
    """获取存档子目录路径
    
    Args:
        subdir_name: 子目录名称，如 "备份", "对比", "DNAT查询" 等
        db_instance: 数据库实例，可选
        
    Returns:
        str: 存档子目录路径
    """
    base_path = get_archive_base_path(db_instance)
    subdir_path = os.path.normpath(os.path.join(base_path, subdir_name))
    
    # 确保目录存在
    try:
        os.makedirs(subdir_path, exist_ok=True)
    except OSError as e:
        logger.error(f"创建目录失败: {subdir_path}, 错误: {e}")
        raise
    
    return subdir_path


def ensure_archive_subdirs(db_instance=None):
    """确保所有必要的存档子目录存在
    
    Args:
        db_instance: 数据库实例，可选
    """
    subdirs = ["备份", "对比", "DNAT查询", "接口查询", "MAC-IP查询", "巡检结果"]
    
    for subdir in subdirs:
        try:
            get_archive_subdir_path(subdir, db_instance)
        except Exception as e:
            logger.error(f"创建子目录 {subdir} 失败: {e}")


def migrate_old_archive_path(old_path: str, db_instance=None) -> bool:
    """迁移旧的存档路径到新的用户配置
    
    Args:
        old_path: 旧的存档路径
        db_instance: 数据库实例，可选
        
    Returns:
        bool: 迁移是否成功
    """
    try:
        if not os.path.exists(old_path):
            return True  # 旧路径不存在，无需迁移
        
        # 获取配置管理器
        if db_instance:
            config_manager = db_instance.get_config_manager()
        else:
            from .config_migrator import ConfigManager
            config_manager = ConfigManager()
        
        if not config_manager:
            return False
        
        # 设置新的存档路径
        config_manager.set_archive_base_path(old_path)
        logger.info(f"已迁移存档路径: {old_path}")
        return True
        
    except Exception as e:
        logger.error(f"迁移存档路径失败: {e}")
        return False
