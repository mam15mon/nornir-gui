"""
测试框架示例测试
验证测试基础设施是否正常工作
"""
import pytest
import os
import tempfile
from pathlib import Path

class TestTestFramework:
    """测试框架基础设施测试"""
    
    def test_pytest_config(self):
        """测试pytest配置"""
        assert True  # 基础测试
    
    def test_temp_dir_fixture(self, temp_dir):
        """测试临时目录fixture"""
        assert os.path.exists(temp_dir)
        assert os.path.isdir(temp_dir)
    
    def test_sample_host_data_fixture(self, sample_host_data):
        """测试示例主机数据fixture"""
        assert "name" in sample_host_data
        assert "hostname" in sample_host_data
        assert sample_host_data["name"] == "test-host-01"
    
    def test_sample_hosts_data_fixture(self, sample_hosts_data):
        """测试示例主机列表数据fixture"""
        assert len(sample_hosts_data) == 3
        assert all("name" in host for host in sample_hosts_data)
    
    def test_test_database_fixture(self, test_database):
        """测试数据库fixture"""
        assert test_database is not None
        assert hasattr(test_database, 'engine')
        assert hasattr(test_database, 'Session')
    
    def test_database_operations(self, test_database, sample_host_data):
        """测试基本数据库操作"""
        # 测试添加主机
        result = test_database.add_host(sample_host_data)
        assert result is True
        
        # 测试获取主机
        host = test_database.get_host(sample_host_data["name"])
        assert host is not None
        assert host.name == sample_host_data["name"]
        
        # 测试更新主机
        update_data = {"hostname": "192.168.1.200"}
        result = test_database.update_host(sample_host_data["name"], update_data)
        assert result is True
        
        # 测试删除主机
        result = test_database.delete_host(sample_host_data["name"])
        assert result is True
    
    def test_batch_operations(self, test_database, sample_hosts_data):
        """测试批量操作"""
        # 批量添加
        added, updated = test_database.batch_add_or_update_hosts(sample_hosts_data)
        assert added == 3
        assert updated == 0
        
        # 获取所有主机
        all_hosts = test_database.get_all_hosts()
        assert len(all_hosts) == 3
        
        # 批量删除
        host_names = [host["name"] for host in sample_hosts_data]
        deleted = test_database.batch_delete_hosts(host_names)
        assert deleted == 3
    
    def test_path_imports(self):
        """测试路径导入"""
        # 测试核心模块导入
        from core.db.database import Database
        from core.db.models import Host, Defaults
        from core.config.user_config import UserConfigManager
        
        assert Database is not None
        assert Host is not None
        assert Defaults is not None
        assert UserConfigManager is not None
    
    def test_project_structure(self):
        """测试项目结构"""
        project_root = Path(__file__).parent.parent
        
        # 检查主要目录
        assert (project_root / "core").exists()
        assert (project_root / "ui").exists()
        assert (project_root / "tests").exists()
        assert (project_root / "databases").exists()
        
        # 检查测试目录结构
        tests_dir = project_root / "tests"
        assert (tests_dir / "unit").exists()
        assert (tests_dir / "integration").exists()
        assert (tests_dir / "ui").exists()
        assert (tests_dir / "fixtures").exists()