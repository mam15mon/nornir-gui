"""
测试配置文件
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def temp_dir():
    """创建临时目录用于测试"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture(scope="session")
def test_db_path(temp_dir):
    """创建测试数据库路径"""
    return os.path.join(temp_dir, "test.db")

@pytest.fixture
def mock_config_manager():
    """模拟配置管理器"""
    from unittest.mock import MagicMock
    mock_config = MagicMock()
    mock_config.get_database_path.return_value = os.path.join(tempfile.gettempdir(), "test_databases")
    mock_config.get_last_used_db.return_value = "test"
    return mock_config

@pytest.fixture
def test_database(test_db_path, mock_config_manager):
    """创建测试数据库"""
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
    
    # 模拟配置管理器
    import core.config.user_config
    original_config = getattr(core.config.user_config, '_config_manager', None)
    core.config.user_config._config_manager = mock_config_manager
    
    # 导入并初始化数据库
    from core.db.database import Database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.db.models import Base
    
    # 重置单例
    Database._instances = {}
    
    # 创建数据库实例
    db = Database()
    
    # 设置测试数据库路径
    db._current_db = test_db_path
    db.engine = create_engine(f'sqlite:///{test_db_path}')
    Base.metadata.create_all(db.engine)
    db.Session = sessionmaker(bind=db.engine)
    
    yield db
    
    # 清理
    if original_config:
        core.config.user_config._config_manager = original_config
    
    # 删除测试数据库
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except PermissionError:
        # 忽略权限错误，测试数据库会在临时目录清理时被删除
        pass

@pytest.fixture
def sample_host_data():
    """示例主机数据"""
    return {
        "name": "test-host-01",
        "hostname": "192.168.1.100",
        "username": "admin",
        "password": "password",
        "platform": "cisco_ios",
        "port": 22,
        "site": "site-1",
        "device_type": "router"
    }

@pytest.fixture
def sample_hosts_data():
    """示例主机列表数据"""
    return [
        {
            "name": "router-01",
            "hostname": "192.168.1.1",
            "username": "admin",
            "password": "password",
            "platform": "cisco_ios",
            "port": 22,
            "site": "site-1",
            "device_type": "router"
        },
        {
            "name": "switch-01",
            "hostname": "192.168.1.2",
            "username": "admin",
            "password": "password",
            "platform": "cisco_ios",
            "port": 22,
            "site": "site-1",
            "device_type": "switch"
        },
        {
            "name": "firewall-01",
            "hostname": "192.168.1.3",
            "username": "admin",
            "password": "password",
            "platform": "fortinet",
            "port": 22,
            "site": "site-1",
            "device_type": "firewall"
        }
    ]