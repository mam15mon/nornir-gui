"""
测试工具类
"""
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from pathlib import Path

class TestDatabaseHelper:
    """测试数据库助手类"""
    
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        self.db_path = os.path.join(temp_dir, "test.db")
        
    def create_test_database(self):
        """创建测试数据库"""
        from core.db.database import Database
        from core.db.models import Base
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 创建数据库实例
        db = Database()
        db._current_db = self.db_path
        db.engine = db.create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(db.engine)
        db.Session = db.sessionmaker(bind=db.engine)
        
        return db
    
    def cleanup(self):
        """清理测试数据库"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

class MockConfigHelper:
    """模拟配置助手类"""
    
    @staticmethod
    def create_mock_config():
        """创建模拟配置"""
        mock_config = MagicMock()
        mock_config.get_database_path.return_value = os.path.join(tempfile.gettempdir(), "test_databases")
        mock_config.get_last_used_db.return_value = "test"
        mock_config.get_proxy_settings.return_value = {
            "enabled": False,
            "host": "",
            "port": 8080,
            "username": "",
            "password": ""
        }
        return mock_config
    
    @staticmethod
    def patch_config_manager():
        """补丁配置管理器"""
        mock_config = MockConfigHelper.create_mock_config()
        return patch('core.config.user_config.ConfigManager', return_value=mock_config)

class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def generate_host_data(override=None):
        """生成主机数据"""
        data = {
            "name": "test-host-01",
            "hostname": "192.168.1.100",
            "username": "admin",
            "password": "password",
            "platform": "cisco_ios",
            "port": 22,
            "groups": "routers",
            "data": {"site": "site-1", "role": "edge"}
        }
        if override:
            data.update(override)
        return data
    
    @staticmethod
    def generate_hosts_data(count=3):
        """生成多个主机数据"""
        hosts = []
        for i in range(count):
            host = TestDataGenerator.generate_host_data({
                "name": f"test-host-{i:02d}",
                "hostname": f"192.168.1.{100+i}",
                "groups": f"group-{i%3}"
            })
            hosts.append(host)
        return hosts

class AssertionHelper:
    """断言助手类"""
    
    @staticmethod
    def assert_host_data_equal(actual, expected):
        """断言主机数据相等"""
        assert actual.name == expected["name"]
        assert actual.hostname == expected["hostname"]
        assert actual.username == expected["username"]
        assert actual.password == expected["password"]
        assert actual.platform == expected["platform"]
        assert actual.port == expected["port"]
        assert actual.groups == expected["groups"]
        
    @staticmethod
    def assert_dict_contains_subset(subset, superset):
        """断言字典包含子集"""
        for key, value in subset.items():
            assert key in superset, f"Key '{key}' not found in superset"
            assert superset[key] == value, f"Value for key '{key}' doesn't match"