"""用户配置管理模块

支持跨平台用户配置文件的读写，配置文件位于用户主目录下的 .nornir-gui/config.ini
"""

import os
import sys
import logging
import configparser
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class UserConfigManager:
    """用户配置管理器
    
    管理用户级配置文件，支持 Windows、macOS 和 Linux 平台
    配置文件位置：~/.nornir-gui/config.ini
    """
    
    def __init__(self):
        self._config_dir = self._get_config_dir()
        self._config_file = self._config_dir / "config.ini"
        self._config = configparser.ConfigParser()
        self._ensure_config_dir()
        self._load_config()

        self._batch_depth = 0
        self._pending_save = False

    def _get_default_log_path(self) -> str:
        """获取默认日志目录路径"""
        try:
            project_root = Path(__file__).resolve().parents[2]
        except Exception:
            project_root = Path.cwd()

        return str((project_root / "logs").resolve())
    
    def _get_config_dir(self) -> Path:
        """获取配置目录路径，支持跨平台"""
        if sys.platform == "win32":
            # Windows: 使用用户主目录
            home = Path.home()
        elif sys.platform == "darwin":
            # macOS: 使用用户主目录
            home = Path.home()
        else:
            # Linux: 使用用户主目录
            home = Path.home()
        
        return home / ".nornir-gui"
    
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"配置目录已创建或已存在: {self._config_dir}")
        except OSError as e:
            logger.error(f"创建配置目录失败: {e}")
            raise
    
    def _load_config(self):
        """加载配置文件"""
        if self._config_file.exists():
            try:
                # 检查文件权限
                if not os.access(self._config_file, os.R_OK):
                    raise PermissionError(f"没有读取配置文件的权限: {self._config_file}")

                # 检查文件大小（防止异常大的文件）
                file_size = self._config_file.stat().st_size
                if file_size > 1024 * 1024:  # 1MB
                    raise ValueError(f"配置文件过大: {file_size} bytes")

                # 尝试读取配置文件
                self._config.read(self._config_file, encoding='utf-8')

                # 验证配置文件结构
                if not self._validate_config():
                    logger.warning("配置文件结构无效，重新创建默认配置")
                    self._backup_corrupted_config()
                    self._create_default_config()
                else:
                    logger.info(f"配置文件已加载: {self._config_file}")

            except (configparser.Error, UnicodeDecodeError) as e:
                logger.error(f"配置文件格式错误: {e}")
                self._backup_corrupted_config()
                self._create_default_config()
            except PermissionError as e:
                logger.error(f"配置文件权限错误: {e}")
                raise
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                self._backup_corrupted_config()
                self._create_default_config()
        else:
            # 配置文件不存在，创建默认配置
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self._config.clear()
        
        # 代理设置
        self._config.add_section('proxy')
        self._config.set('proxy', 'enabled', 'false')
        self._config.set('proxy', 'host', '')
        self._config.set('proxy', 'port', '8080')
        
        # 路径设置
        self._config.add_section('paths')
        # 默认存档路径在用户主目录下
        default_archive_path = str(Path.home() / "nornir-gui-files")
        self._config.set('paths', 'archive_base_path', default_archive_path)
        # 默认数据库路径在用户配置目录下
        default_db_path = str(self._config_dir / "databases")
        self._config.set('paths', 'database_path', default_db_path)
        # 默认日志路径位于项目 logs 目录
        default_log_path = self._get_default_log_path()
        self._config.set('paths', 'log_path', default_log_path)
        
        # 应用设置
        self._config.add_section('app')
        self._config.set('app', 'last_used_db', 'default')
        self._config.set('app', 'log_level', 'INFO')
        
        self._save_config()
        logger.info("已创建默认配置文件")

    def _validate_config(self) -> bool:
        """验证配置文件结构"""
        try:
            # 检查必需的节
            required_sections = ['proxy', 'paths', 'app']
            for section in required_sections:
                if not self._config.has_section(section):
                    logger.warning(f"配置文件缺少必需的节: {section}")
                    return False

            # 检查代理设置
            if self._config.has_option('proxy', 'enabled'):
                enabled = self._config.get('proxy', 'enabled').lower()
                if enabled not in ['true', 'false']:
                    logger.warning("代理启用设置值无效")
                    return False

            # 检查端口号
            if self._config.has_option('proxy', 'port'):
                try:
                    port = self._config.getint('proxy', 'port')
                    if not (1 <= port <= 65535):
                        logger.warning(f"代理端口号无效: {port}")
                        return False
                except ValueError:
                    logger.warning("代理端口号格式无效")
                    return False

            # 检查路径设置
            if self._config.has_option('paths', 'archive_base_path'):
                archive_path = self._config.get('paths', 'archive_base_path')
                if archive_path and not os.path.isabs(archive_path):
                    logger.warning(f"存档路径不是绝对路径: {archive_path}")
                    # 这不是致命错误，只是警告

            if self._config.has_option('paths', 'log_path'):
                log_path = self._config.get('paths', 'log_path')
                if log_path and not os.path.isabs(log_path):
                    logger.warning(f"日志路径不是绝对路径: {log_path}")

            return True

        except Exception as e:
            logger.error(f"验证配置文件时发生错误: {e}")
            return False

    def _backup_corrupted_config(self):
        """备份损坏的配置文件"""
        try:
            if self._config_file.exists():
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self._config_file.with_suffix(f'.corrupted_{timestamp}.bak')

                import shutil
                shutil.copy2(self._config_file, backup_path)
                logger.info(f"损坏的配置文件已备份到: {backup_path}")

        except Exception as e:
            logger.error(f"备份损坏的配置文件失败: {e}")
    
    def _save_config(self):
        """保存配置文件"""
        if self._batch_depth > 0:
            self._pending_save = True
            return

        self._write_config_to_disk()

    def _write_config_to_disk(self):
        """实际写入配置到磁盘"""
        try:
            # 检查目录权限
            if not os.access(self._config_dir, os.W_OK):
                raise PermissionError(f"没有写入配置目录的权限: {self._config_dir}")

            # 创建临时文件，先写入临时文件，验证成功后再替换原始文件
            temp_file = self._config_file.with_suffix('.tmp')

            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    self._config.write(f)

                # 验证临时文件
                temp_config = configparser.ConfigParser()
                temp_config.read(temp_file, encoding='utf-8')

                # 验证通过后替换原始文件
                if temp_file.exists():
                    temp_file.replace(self._config_file)
                    logger.info(f"配置文件已保存: {self._config_file}")
                    self._pending_save = False

            except Exception as e:
                # 清理临时文件
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
                raise e

        except PermissionError as e:
            logger.error(f"配置文件权限错误: {e}")
            raise
        except OSError as e:
            logger.error(f"配置文件系统错误: {e}")
            raise
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise
    @contextmanager
    def batch_update(self):
        """批量更新配置，统一落盘"""
        self._batch_depth += 1
        try:
            yield
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0 and self._pending_save:
                self._write_config_to_disk()

    def get_config_file_path(self) -> str:
        """获取配置文件路径"""
        return str(self._config_file)
    
    def get_config_dir_path(self) -> str:
        """获取配置目录路径"""
        return str(self._config_dir)
    
    # 代理设置相关方法
    def get_proxy_settings(self) -> Dict[str, Any]:
        """获取代理设置"""
        return {
            'enabled': self._config.getboolean('proxy', 'enabled', fallback=False),
            'host': self._config.get('proxy', 'host', fallback=''),
            'port': self._config.getint('proxy', 'port', fallback=8080)
        }
    
    def set_proxy_settings(self, enabled: bool, host: str = '', port: int = 8080):
        """设置代理配置"""
        if not self._config.has_section('proxy'):
            self._config.add_section('proxy')
        
        self._config.set('proxy', 'enabled', str(enabled).lower())
        self._config.set('proxy', 'host', host)
        self._config.set('proxy', 'port', str(port))
        self._save_config()
    
    # 路径设置相关方法
    def get_archive_base_path(self) -> str:
        """获取存档基础路径"""
        return self._config.get('paths', 'archive_base_path', 
                               fallback=str(Path.home() / "nornir-gui-files"))

    def set_archive_base_path(self, path: str):
        """设置存档基础路径"""
        if not self._config.has_section('paths'):
            self._config.add_section('paths')
        
        self._config.set('paths', 'archive_base_path', path)
        self._save_config()
    
    def get_database_path(self) -> str:
        """获取数据库路径"""
        return self._config.get('paths', 'database_path',
                               fallback=str(self._config_dir / "databases"))

    def set_database_path(self, path: str):
        """设置数据库路径"""
        if not self._config.has_section('paths'):
            self._config.add_section('paths')

        self._config.set('paths', 'database_path', path)
        self._save_config()

    def get_log_path(self) -> str:
        """获取日志输出路径"""
        log_path = self._config.get('paths', 'log_path', fallback=self._get_default_log_path())
        return os.path.abspath(log_path)

    def set_log_path(self, path: str):
        """设置日志输出路径"""
        if not self._config.has_section('paths'):
            self._config.add_section('paths')

        normalized_path = os.path.abspath(path)

        self._config.set('paths', 'log_path', normalized_path)
        self._save_config()
    
    # 应用设置相关方法
    def get_last_used_db(self) -> str:
        """获取上次使用的数据库名称"""
        return self._config.get('app', 'last_used_db', fallback='default')
    
    def set_last_used_db(self, db_name: str):
        """设置上次使用的数据库名称"""
        if not self._config.has_section('app'):
            self._config.add_section('app')
        
        self._config.set('app', 'last_used_db', db_name)
        self._save_config()
    
    def get_log_level(self) -> str:
        """获取日志级别"""
        return self._config.get('app', 'log_level', fallback='INFO')
    
    def set_log_level(self, level: str):
        """设置日志级别"""
        if not self._config.has_section('app'):
            self._config.add_section('app')
        
        self._config.set('app', 'log_level', level)
        self._save_config()
    
    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """获取所有设置"""
        settings = {}
        for section_name in self._config.sections():
            settings[section_name] = dict(self._config.items(section_name))
        return settings
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self._create_default_config()
        logger.info("配置已重置为默认值")
    
    def config_exists(self) -> bool:
        """检查配置文件是否存在"""
        return self._config_file.exists()
    
    def backup_config(self, backup_path: Optional[str] = None) -> str:
        """备份配置文件"""
        if backup_path is None:
            backup_path = str(self._config_file.with_suffix('.ini.backup'))
        
        try:
            import shutil
            shutil.copy2(self._config_file, backup_path)
            logger.info(f"配置文件已备份到: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"备份配置文件失败: {e}")
            raise
    
    def restore_config(self, backup_path: str):
        """从备份恢复配置文件"""
        try:
            # 验证备份文件
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"备份文件不存在: {backup_path}")

            if not os.access(backup_path, os.R_OK):
                raise PermissionError(f"没有读取备份文件的权限: {backup_path}")

            # 验证备份文件格式
            test_config = configparser.ConfigParser()
            test_config.read(backup_path, encoding='utf-8')

            # 备份当前配置文件
            if self._config_file.exists():
                current_backup = self._config_file.with_suffix('.before_restore.bak')
                import shutil
                shutil.copy2(self._config_file, current_backup)
                logger.info(f"当前配置已备份到: {current_backup}")

            # 恢复配置文件
            import shutil
            shutil.copy2(backup_path, self._config_file)
            self._load_config()
            logger.info(f"配置文件已从备份恢复: {backup_path}")

        except configparser.Error as e:
            logger.error(f"备份文件格式无效: {e}")
            raise ValueError(f"备份文件格式无效: {e}")
        except Exception as e:
            logger.error(f"恢复配置文件失败: {e}")
            raise

    def repair_config(self) -> bool:
        """尝试修复损坏的配置文件"""
        try:
            logger.info("尝试修复配置文件")

            # 创建新的配置对象
            new_config = configparser.ConfigParser()

            # 尝试从当前配置中恢复有效的设置
            recovered_settings = {}

            if self._config.has_section('proxy'):
                try:
                    proxy_enabled = self._config.getboolean('proxy', 'enabled', fallback=False)
                    proxy_host = self._config.get('proxy', 'host', fallback='')
                    proxy_port = self._config.getint('proxy', 'port', fallback=8080)

                    # 验证端口范围
                    if not (1 <= proxy_port <= 65535):
                        proxy_port = 8080

                    recovered_settings['proxy'] = {
                        'enabled': proxy_enabled,
                        'host': proxy_host,
                        'port': proxy_port
                    }
                except:
                    pass

            if self._config.has_section('paths'):
                try:
                    archive_path = self._config.get('paths', 'archive_base_path', fallback='')
                    db_path = self._config.get('paths', 'database_path', fallback='')

                    log_path = self._config.get('paths', 'log_path', fallback='')

                    recovered_settings['paths'] = {
                        'archive_base_path': archive_path,
                        'database_path': db_path,
                        'log_path': log_path
                    }
                except:
                    pass

            if self._config.has_section('app'):
                try:
                    last_db = self._config.get('app', 'last_used_db', fallback='default')
                    log_level = self._config.get('app', 'log_level', fallback='INFO')

                    recovered_settings['app'] = {
                        'last_used_db': last_db,
                        'log_level': log_level
                    }
                except:
                    pass

            # 重新创建配置文件
            self._config = new_config
            self._create_default_config()

            # 应用恢复的设置
            for section, settings in recovered_settings.items():
                if section == 'proxy' and 'enabled' in settings:
                    self.set_proxy_settings(
                        settings['enabled'],
                        settings.get('host', ''),
                        settings.get('port', 8080)
                    )
                elif section == 'paths':
                    if settings.get('archive_base_path'):
                        self.set_archive_base_path(settings['archive_base_path'])
                    if settings.get('database_path'):
                        self.set_database_path(settings['database_path'])
                    if settings.get('log_path'):
                        self.set_log_path(settings['log_path'])
                elif section == 'app':
                    if settings.get('last_used_db'):
                        self.set_last_used_db(settings['last_used_db'])
                    if settings.get('log_level'):
                        self.set_log_level(settings['log_level'])

            logger.info("配置文件修复完成")
            return True

        except Exception as e:
            logger.error(f"修复配置文件失败: {e}")
            return False
