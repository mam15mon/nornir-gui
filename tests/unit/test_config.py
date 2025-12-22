"""
配置管理单元测试
"""
import pytest
import os
import tempfile
import configparser
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from core.config.user_config import UserConfigManager

@pytest.mark.unit
class TestUserConfigManager:
    """用户配置管理器测试类"""
    
    def test_init_with_default_config(self, temp_dir):
        """测试使用默认配置初始化"""
        # 创建临时配置目录
        config_dir = os.path.join(temp_dir, ".nornir-gui")
        os.makedirs(config_dir, exist_ok=True)
        
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 验证配置文件路径
            expected_config_path = os.path.join(config_dir, "config.ini")
            assert config_manager.config_file == expected_config_path
            
            # 验证默认配置
            assert config_manager.config.has_section('database')
            assert config_manager.config.has_section('proxy')
            assert config_manager.config.has_section('ui')
    
    def test_load_existing_config(self, temp_dir):
        """测试加载现有配置"""
        # 创建测试配置文件
        config_dir = os.path.join(temp_dir, ".nornir-gui")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "config.ini")
        
        # 写入测试配置
        config = configparser.ConfigParser()
        config['database'] = {
            'path': '/custom/path',
            'last_used': 'custom_db'
        }
        config['proxy'] = {
            'enabled': 'true',
            'host': 'proxy.example.com',
            'port': '8080'
        }
        with open(config_file, 'w') as f:
            config.write(f)
        
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 验证配置加载
            assert config_manager.get_database_path() == '/custom/path'
            assert config_manager.get_last_used_db() == 'custom_db'
            assert config_manager.get_proxy_settings()['enabled'] is True
    
    def test_get_database_path(self, temp_dir):
        """测试获取数据库路径"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 测试默认路径
            default_path = config_manager.get_database_path()
            assert "databases" in default_path
    
    def test_set_database_path(self, temp_dir):
        """测试设置数据库路径"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 设置新路径
            new_path = "/custom/database/path"
            config_manager.set_database_path(new_path)
            
            # 验证路径已更新
            assert config_manager.get_database_path() == new_path

    def test_get_log_path(self, temp_dir):
        """测试获取日志路径"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()

            log_path = config_manager.get_log_path()
            assert os.path.isabs(log_path)
            assert log_path.endswith("logs")

    def test_set_log_path(self, temp_dir):
        """测试设置日志路径"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()

            custom_log_path = os.path.join(temp_dir, "custom_logs")
            config_manager.set_log_path(custom_log_path)

            assert config_manager.get_log_path() == custom_log_path
    
    def test_get_last_used_db(self, temp_dir):
        """测试获取上次使用的数据库"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 测试默认值
            last_db = config_manager.get_last_used_db()
            assert last_db == "default"
    
    def test_set_last_used_db(self, temp_dir):
        """测试设置上次使用的数据库"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 设置新数据库名称
            new_db = "test_database"
            config_manager.set_last_used_db(new_db)
            
            # 验证名称已更新
            assert config_manager.get_last_used_db() == new_db
    
    def test_get_proxy_settings(self, temp_dir):
        """测试获取代理设置"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 测试默认代理设置
            proxy_settings = config_manager.get_proxy_settings()
            assert 'enabled' in proxy_settings
            assert 'host' in proxy_settings
            assert 'port' in proxy_settings
            assert 'username' in proxy_settings
            assert 'password' in proxy_settings
    
    def test_set_proxy_settings(self, temp_dir):
        """测试设置代理设置"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 设置新的代理设置
            new_settings = {
                'enabled': True,
                'host': 'proxy.example.com',
                'port': 8080,
                'username': 'proxy_user',
                'password': 'proxy_pass'
            }
            config_manager.set_proxy_settings(new_settings)
            
            # 验证设置已更新
            current_settings = config_manager.get_proxy_settings()
            assert current_settings['enabled'] is True
            assert current_settings['host'] == 'proxy.example.com'
            assert current_settings['port'] == 8080
            assert current_settings['username'] == 'proxy_user'
            assert current_settings['password'] == 'proxy_pass'
    
    def test_get_ui_settings(self, temp_dir):
        """测试获取UI设置"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 测试默认UI设置
            ui_settings = config_manager.get_ui_settings()
            assert 'theme' in ui_settings
            assert 'window_size' in ui_settings
            assert 'window_position' in ui_settings
    
    def test_set_ui_settings(self, temp_dir):
        """测试设置UI设置"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 设置新的UI设置
            new_settings = {
                'theme': 'dark',
                'window_size': '1200x800',
                'window_position': '100,100'
            }
            config_manager.set_ui_settings(new_settings)
            
            # 验证设置已更新
            current_settings = config_manager.get_ui_settings()
            assert current_settings['theme'] == 'dark'
            assert current_settings['window_size'] == '1200x800'
            assert current_settings['window_position'] == '100,100'
    
    def test_save_config(self, temp_dir):
        """测试保存配置"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 修改一些设置
            config_manager.set_database_path("/custom/path")
            config_manager.set_last_used_db("test_db")
            
            # 保存配置
            config_manager.save_config()
            
            # 验证配置文件已创建
            config_file = os.path.join(temp_dir, ".nornir-gui", "config.ini")
            assert os.path.exists(config_file)
            
            # 验证配置内容
            config = configparser.ConfigParser()
            config.read(config_file)
            assert config['database']['path'] == "/custom/path"
            assert config['database']['last_used'] == "test_db"
    
    def test_config_file_creation(self, temp_dir):
        """测试配置文件自动创建"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 配置文件应该自动创建
            config_file = os.path.join(temp_dir, ".nornir-gui", "config.ini")
            assert os.path.exists(config_file)
    
    def test_config_directory_creation(self, temp_dir):
        """测试配置目录自动创建"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 配置目录应该自动创建
            config_dir = os.path.join(temp_dir, ".nornir-gui")
            assert os.path.exists(config_dir)
            assert os.path.isdir(config_dir)
    
    def test_config_validation(self, temp_dir):
        """测试配置验证"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 测试有效的代理端口
            config_manager.set_proxy_settings({
                'enabled': True,
                'host': 'proxy.example.com',
                'port': 8080,
                'username': '',
                'password': ''
            })
            
            # 验证配置有效
            proxy_settings = config_manager.get_proxy_settings()
            assert proxy_settings['port'] == 8080
    
    def test_config_migration(self, temp_dir):
        """测试配置迁移"""
        # 创建旧版本的配置文件
        config_dir = os.path.join(temp_dir, ".nornir-gui")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "config.ini")
        
        # 写入旧版本配置（缺少某些字段）
        config = configparser.ConfigParser()
        config['database'] = {
            'path': '/old/path'
        }
        # 缺少 proxy 和 ui 部分
        with open(config_file, 'w') as f:
            config.write(f)
        
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 验证配置已迁移（缺少的部分被添加）
            assert config_manager.config.has_section('proxy')
            assert config_manager.config.has_section('ui')
    
    def test_get_config_value(self, temp_dir):
        """测试获取配置值"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 测试获取存在的值
            db_path = config_manager.get_config_value('database', 'path')
            assert db_path is not None
            
            # 测试获取不存在的值
            non_existent = config_manager.get_config_value('non_existent', 'key')
            assert non_existent is None
    
    def test_set_config_value(self, temp_dir):
        """测试设置配置值"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 设置新值
            config_manager.set_config_value('test_section', 'test_key', 'test_value')
            
            # 验证值已设置
            value = config_manager.get_config_value('test_section', 'test_key')
            assert value == 'test_value'
    
    def test_remove_config_value(self, temp_dir):
        """测试删除配置值"""
        with patch('os.path.expanduser', return_value=temp_dir):
            config_manager = UserConfigManager()
            
            # 设置值
            config_manager.set_config_value('test_section', 'test_key', 'test_value')
            
            # 删除值
            config_manager.remove_config_value('test_section', 'test_key')
            
            # 验证值已删除
            value = config_manager.get_config_value('test_section', 'test_key')
            assert value is None
