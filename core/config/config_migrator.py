"""配置迁移模块

负责从数据库配置迁移到用户配置文件，确保向后兼容性
"""

import os
import logging
from typing import Dict, Any, Optional
from .user_config import UserConfigManager

logger = logging.getLogger(__name__)


class ConfigMigrator:
    """配置迁移器
    
    负责从数据库配置迁移到用户配置文件
    """
    
    def __init__(self, user_config: UserConfigManager):
        self.user_config = user_config
    
    def migrate_from_database(self, db_settings: Dict[str, Any]) -> bool:
        """从数据库设置迁移到用户配置文件
        
        Args:
            db_settings: 数据库中的设置字典
            
        Returns:
            bool: 迁移是否成功
        """
        try:
            logger.info("开始从数据库迁移配置到用户配置文件")
            
            # 迁移代理设置
            if 'proxy_enabled' in db_settings:
                proxy_enabled = db_settings.get('proxy_enabled', False)
                proxy_host = db_settings.get('proxy_host', '')
                proxy_port = db_settings.get('proxy_port', 8080)
                
                self.user_config.set_proxy_settings(
                    enabled=proxy_enabled,
                    host=proxy_host or '',
                    port=proxy_port or 8080
                )
                logger.info("代理设置已迁移")
            
            # 迁移存档路径
            if 'config_base_path' in db_settings:
                archive_path = db_settings.get('config_base_path')
                if archive_path:
                    self.user_config.set_archive_base_path(archive_path)
                    logger.info(f"存档路径已迁移: {archive_path}")
            
            # 迁移上次使用的数据库
            if 'last_used_db' in db_settings:
                last_db = db_settings.get('last_used_db', 'default')
                self.user_config.set_last_used_db(last_db)
                logger.info(f"上次使用的数据库已迁移: {last_db}")
            
            # 迁移日志级别
            if 'log_file_level' in db_settings:
                log_level = db_settings.get('log_file_level', 'INFO')
                self.user_config.set_log_level(log_level)
                logger.info(f"日志级别已迁移: {log_level}")
            
            logger.info("配置迁移完成")
            return True
            
        except Exception as e:
            logger.error(f"配置迁移失败: {e}")
            return False
    
    def should_migrate(self) -> bool:
        """检查是否需要迁移
        
        Returns:
            bool: 如果用户配置文件不存在，则需要迁移
        """
        return not self.user_config.config_exists()


class ConfigManager:
    """统一配置管理器
    
    提供统一的配置访问接口，支持从用户配置文件和数据库读取配置
    优先级：用户配置文件 > 数据库配置 > 默认值
    """
    
    def __init__(self):
        self.user_config = UserConfigManager()
        self.migrator = ConfigMigrator(self.user_config)
        self._db_fallback = None
    
    def set_database_fallback(self, db_instance):
        """设置数据库回退实例"""
        self._db_fallback = db_instance
    
    def get_proxy_settings(self) -> Dict[str, Any]:
        """获取代理设置，优先从用户配置文件读取"""
        try:
            return self.user_config.get_proxy_settings()
        except Exception as e:
            logger.warning(f"从用户配置读取代理设置失败，尝试修复配置: {e}")

            # 尝试修复配置文件
            if hasattr(self.user_config, 'repair_config'):
                try:
                    if self.user_config.repair_config():
                        return self.user_config.get_proxy_settings()
                except Exception as repair_e:
                    logger.error(f"修复配置文件失败: {repair_e}")

            # 尝试从数据库读取
            if self._db_fallback:
                try:
                    db_settings = self._db_fallback.get_settings()
                    proxy_settings = {
                        'enabled': db_settings.get('proxy_enabled', False),
                        'host': db_settings.get('proxy_host', ''),
                        'port': db_settings.get('proxy_port', 8080)
                    }

                    # 尝试保存到用户配置文件
                    try:
                        self.user_config.set_proxy_settings(
                            proxy_settings['enabled'],
                            proxy_settings['host'],
                            proxy_settings['port']
                        )
                        logger.info("已从数据库恢复代理设置到用户配置文件")
                    except:
                        pass  # 保存失败不影响返回值

                    return proxy_settings

                except Exception as db_e:
                    logger.error(f"从数据库读取代理设置也失败: {db_e}")

            # 返回默认值
            return {'enabled': False, 'host': '', 'port': 8080}
    
    def set_proxy_settings(self, enabled: bool, host: str = '', port: int = 8080):
        """设置代理配置"""
        self.user_config.set_proxy_settings(enabled, host, port)
    
    def get_archive_base_path(self) -> str:
        """获取存档基础路径"""
        try:
            return self.user_config.get_archive_base_path()
        except Exception as e:
            logger.warning(f"从用户配置读取存档路径失败，尝试恢复: {e}")

            # 尝试修复配置文件
            if hasattr(self.user_config, 'repair_config'):
                try:
                    if self.user_config.repair_config():
                        return self.user_config.get_archive_base_path()
                except Exception as repair_e:
                    logger.error(f"修复配置文件失败: {repair_e}")

            # 尝试从数据库读取
            default_path = str(self.user_config._config_dir.parent / "nornir-gui-files")
            if self._db_fallback:
                try:
                    db_settings = self._db_fallback.get_settings()
                    archive_path = db_settings.get('config_base_path', default_path)

                    # 尝试保存到用户配置文件
                    try:
                        self.user_config.set_archive_base_path(archive_path)
                        logger.info("已从数据库恢复存档路径到用户配置文件")
                    except:
                        pass

                    return archive_path

                except Exception as db_e:
                    logger.error(f"从数据库读取存档路径也失败: {db_e}")

            # 返回默认值
            return default_path
    
    def set_archive_base_path(self, path: str):
        """设置存档基础路径"""
        self.user_config.set_archive_base_path(path)
    
    def get_database_path(self) -> str:
        """获取数据库路径"""
        return self.user_config.get_database_path()
    
    def set_database_path(self, path: str):
        """设置数据库路径"""
        self.user_config.set_database_path(path)
    
    def get_last_used_db(self) -> str:
        """获取上次使用的数据库名称"""
        try:
            return self.user_config.get_last_used_db()
        except Exception as e:
            logger.warning(f"从用户配置读取数据库名称失败: {e}")
            return 'default'
    
    def set_last_used_db(self, db_name: str):
        """设置上次使用的数据库名称"""
        self.user_config.set_last_used_db(db_name)
    
    def get_log_level(self) -> str:
        """获取日志级别"""
        try:
            return self.user_config.get_log_level()
        except Exception as e:
            logger.warning(f"从用户配置读取日志级别失败: {e}")
            return 'INFO'
    
    def set_log_level(self, level: str):
        """设置日志级别"""
        self.user_config.set_log_level(level)
    
    def migrate_from_database_if_needed(self, db_settings: Dict[str, Any]) -> bool:
        """如果需要，从数据库迁移配置"""
        if self.migrator.should_migrate():
            return self.migrator.migrate_from_database(db_settings)
        return True
    
    def get_config_file_path(self) -> str:
        """获取配置文件路径"""
        return self.user_config.get_config_file_path()
    
    def get_config_dir_path(self) -> str:
        """获取配置目录路径"""
        return self.user_config.get_config_dir_path()
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self.user_config.reset_to_defaults()
    
    def backup_config(self, backup_path: Optional[str] = None) -> str:
        """备份配置文件"""
        return self.user_config.backup_config(backup_path)
    
    def restore_config(self, backup_path: str):
        """从备份恢复配置文件"""
        self.user_config.restore_config(backup_path)

    def check_config_health(self) -> Dict[str, Any]:
        """检查配置文件健康状态"""
        health_status = {
            'overall_status': 'healthy',
            'issues': [],
            'warnings': [],
            'config_file_exists': False,
            'config_file_readable': False,
            'config_file_writable': False,
            'config_dir_writable': False,
            'sections_valid': True,
            'values_valid': True
        }

        try:
            config_file_path = self.user_config._config_file
            config_dir_path = self.user_config._config_dir

            # 检查配置文件是否存在
            health_status['config_file_exists'] = config_file_path.exists()

            if health_status['config_file_exists']:
                # 检查文件权限
                health_status['config_file_readable'] = os.access(config_file_path, os.R_OK)
                health_status['config_file_writable'] = os.access(config_file_path, os.W_OK)

                if not health_status['config_file_readable']:
                    health_status['issues'].append("配置文件不可读")
                    health_status['overall_status'] = 'error'

                if not health_status['config_file_writable']:
                    health_status['warnings'].append("配置文件不可写")
                    if health_status['overall_status'] == 'healthy':
                        health_status['overall_status'] = 'warning'
            else:
                health_status['warnings'].append("配置文件不存在")
                if health_status['overall_status'] == 'healthy':
                    health_status['overall_status'] = 'warning'

            # 检查配置目录权限
            health_status['config_dir_writable'] = os.access(config_dir_path, os.W_OK)
            if not health_status['config_dir_writable']:
                health_status['issues'].append("配置目录不可写")
                health_status['overall_status'] = 'error'

            # 检查配置文件结构
            if hasattr(self.user_config, '_validate_config'):
                try:
                    health_status['sections_valid'] = self.user_config._validate_config()
                    if not health_status['sections_valid']:
                        health_status['issues'].append("配置文件结构无效")
                        health_status['overall_status'] = 'error'
                except Exception as e:
                    health_status['issues'].append(f"验证配置文件时出错: {e}")
                    health_status['overall_status'] = 'error'

            # 检查配置值
            try:
                # 测试读取各种配置
                self.get_proxy_settings()
                self.get_archive_base_path()
                self.get_database_path()
                self.get_last_used_db()
                self.get_log_level()
            except Exception as e:
                health_status['issues'].append(f"读取配置值时出错: {e}")
                health_status['values_valid'] = False
                health_status['overall_status'] = 'error'

        except Exception as e:
            health_status['issues'].append(f"健康检查时发生未知错误: {e}")
            health_status['overall_status'] = 'error'

        return health_status

    def auto_repair_config(self) -> bool:
        """自动修复配置问题"""
        try:
            health_status = self.check_config_health()

            if health_status['overall_status'] == 'healthy':
                logger.info("配置文件健康，无需修复")
                return True

            logger.info("检测到配置问题，开始自动修复")

            # 如果配置文件不存在或结构无效，尝试修复
            if not health_status['config_file_exists'] or not health_status['sections_valid']:
                if hasattr(self.user_config, 'repair_config'):
                    if self.user_config.repair_config():
                        logger.info("配置文件修复成功")
                        return True
                    else:
                        logger.error("配置文件修复失败")
                        return False

            # 如果有权限问题，记录但不能自动修复
            if not health_status['config_dir_writable'] or not health_status['config_file_writable']:
                logger.error("检测到权限问题，需要手动解决")
                return False

            return True

        except Exception as e:
            logger.error(f"自动修复配置时发生错误: {e}")
            return False
