"""
数据库操作单元测试
"""
import pytest
from unittest.mock import MagicMock, patch
from core.db.database import Database
from core.db.models import Host, Defaults

@pytest.mark.unit
class TestDatabase:
    """数据库操作测试类"""
    
    def test_add_host_success(self, test_database, sample_host_data):
        """测试成功添加主机"""
        result = test_database.add_host(sample_host_data)
        assert result is True
        
        # 验证主机是否被添加
        host = test_database.get_host(sample_host_data["name"])
        assert host is not None
        assert host.name == sample_host_data["name"]
        assert host.hostname == sample_host_data["hostname"]
    
    def test_add_host_duplicate(self, test_database, sample_host_data):
        """测试添加重复主机"""
        # 先添加一个主机
        test_database.add_host(sample_host_data)
        
        # 尝试添加同名主机
        result = test_database.add_host(sample_host_data)
        assert result is False
    
    def test_get_host_not_exists(self, test_database):
        """测试获取不存在的主机"""
        host = test_database.get_host("non-existent-host")
        assert host is None
    
    def test_get_all_hosts_empty(self, test_database):
        """测试获取空主机列表"""
        hosts = test_database.get_all_hosts()
        assert len(hosts) == 0
    
    def test_get_all_hosts_with_data(self, test_database, sample_hosts_data):
        """测试获取有数据的主机列表"""
        # 添加多个主机
        for host_data in sample_hosts_data:
            test_database.add_host(host_data)
        
        hosts = test_database.get_all_hosts()
        assert len(hosts) == len(sample_hosts_data)
        
        # 验证主机名称
        host_names = [host.name for host in hosts]
        expected_names = [host_data["name"] for host_data in sample_hosts_data]
        assert set(host_names) == set(expected_names)
    
    def test_update_host_success(self, test_database, sample_host_data):
        """测试成功更新主机"""
        # 先添加主机
        test_database.add_host(sample_host_data)
        
        # 更新主机信息
        update_data = {
            "hostname": "192.168.1.200",
            "username": "new_user",
            "site": "new_site"
        }
        result = test_database.update_host(sample_host_data["name"], update_data)
        assert result is True
        
        # 验证更新结果
        host = test_database.get_host(sample_host_data["name"])
        assert host.hostname == "192.168.1.200"
        assert host.username == "new_user"
        assert host.site == "new_site"
    
    def test_update_host_not_exists(self, test_database):
        """测试更新不存在的主机"""
        update_data = {"hostname": "192.168.1.200"}
        result = test_database.update_host("non-existent-host", update_data)
        assert result is False
    
    def test_delete_host_success(self, test_database, sample_host_data):
        """测试成功删除主机"""
        # 先添加主机
        test_database.add_host(sample_host_data)
        
        # 删除主机
        result = test_database.delete_host(sample_host_data["name"])
        assert result is True
        
        # 验证主机已被删除
        host = test_database.get_host(sample_host_data["name"])
        assert host is None
    
    def test_delete_host_not_exists(self, test_database):
        """测试删除不存在的主机"""
        result = test_database.delete_host("non-existent-host")
        assert result is False
    
    def test_batch_delete_hosts(self, test_database, sample_hosts_data):
        """测试批量删除主机"""
        # 添加多个主机
        for host_data in sample_hosts_data:
            test_database.add_host(host_data)
        
        # 批量删除
        host_names = [host_data["name"] for host_data in sample_hosts_data]
        deleted_count = test_database.batch_delete_hosts(host_names)
        assert deleted_count == len(sample_hosts_data)
        
        # 验证所有主机都被删除
        for host_name in host_names:
            host = test_database.get_host(host_name)
            assert host is None
    
    def test_batch_delete_partial(self, test_database, sample_hosts_data):
        """测试批量删除部分主机"""
        # 添加多个主机
        for host_data in sample_hosts_data:
            test_database.add_host(host_data)
        
        # 删除部分主机
        host_names = [sample_hosts_data[0]["name"], sample_hosts_data[1]["name"]]
        deleted_count = test_database.batch_delete_hosts(host_names)
        assert deleted_count == 2
        
        # 验证只有指定主机被删除
        assert test_database.get_host(host_names[0]) is None
        assert test_database.get_host(host_names[1]) is None
        assert test_database.get_host(sample_hosts_data[2]["name"]) is not None
    
    def test_batch_add_or_update_hosts_new(self, test_database, sample_hosts_data):
        """测试批量添加新主机"""
        added, updated = test_database.batch_add_or_update_hosts(sample_hosts_data)
        assert added == len(sample_hosts_data)
        assert updated == 0
        
        # 验证所有主机都被添加
        hosts = test_database.get_all_hosts()
        assert len(hosts) == len(sample_hosts_data)
    
    def test_batch_add_or_update_hosts_mixed(self, test_database, sample_hosts_data):
        """测试批量添加和更新混合操作"""
        # 先添加部分主机
        initial_hosts = sample_hosts_data[:1]
        for host_data in initial_hosts:
            test_database.add_host(host_data)
        
        # 准备混合数据（新主机+更新主机）
        mixed_data = sample_hosts_data.copy()
        mixed_data[0]["hostname"] = "192.168.1.100"  # 更新现有主机
        
        added, updated = test_database.batch_add_or_update_hosts(mixed_data)
        assert added == len(sample_hosts_data) - 1
        assert updated == 1
        
        # 验证更新结果
        updated_host = test_database.get_host(mixed_data[0]["name"])
        assert updated_host.hostname == "192.168.1.100"
    
    def test_batch_edit_devices(self, test_database, sample_hosts_data):
        """测试批量编辑设备"""
        # 添加多个主机
        for host_data in sample_hosts_data:
            test_database.add_host(host_data)
        
        # 批量编辑
        device_names = [host_data["name"] for host_data in sample_hosts_data[:2]]
        edited_fields = {
            "username": "new_admin",
            "site": "new_site"
        }
        updated_count = test_database.batch_edit_devices(device_names, edited_fields)
        assert updated_count == 2
        
        # 验证编辑结果
        for name in device_names:
            host = test_database.get_host(name)
            assert host.username == "new_admin"
            assert host.site == "new_site"
        
        # 验证未编辑的主机保持不变
        unchanged_host = test_database.get_host(sample_hosts_data[2]["name"])
        assert unchanged_host.username == sample_hosts_data[2]["username"]
    
    def test_get_defaults(self, test_database):
        """测试获取默认配置"""
        defaults = test_database.get_defaults()
        assert "timeout" in defaults
        assert "global_delay_factor" in defaults
        assert "fast_cli" in defaults
        assert isinstance(defaults["timeout"], int)
        assert isinstance(defaults["global_delay_factor"], float)
        assert isinstance(defaults["fast_cli"], bool)
    
    def test_update_defaults(self, test_database):
        """测试更新默认配置"""
        new_defaults = {
            "timeout": 120,
            "global_delay_factor": 1.5,
            "fast_cli": True
        }
        result = test_database.update_defaults(new_defaults)
        assert result is True
        
        # 验证更新结果
        defaults = test_database.get_defaults()
        assert defaults["timeout"] == 120
        assert defaults["global_delay_factor"] == 1.5
        assert defaults["fast_cli"] is True
    
    def test_get_session(self, test_database):
        """测试获取数据库会话"""
        session = test_database.get_session()
        assert session is not None
        session.close()
    
    def test_switch_database(self, test_database, sample_host_data, temp_dir):
        """测试切换数据库"""
        # 先添加主机到当前数据库
        test_database.add_host(sample_host_data)
        
        # 切换到新数据库
        new_db_name = "test_switch"
        result = test_database.switch_database(new_db_name)
        assert result is True
        
        # 验证新数据库为空
        hosts = test_database.get_all_hosts()
        assert len(hosts) == 0
        
        # 验证数据库名称已更新
        assert test_database.get_current_db_name() == new_db_name
    
    def test_database_singleton(self):
        """测试数据库单例模式"""
        # 创建两个数据库实例
        db1 = Database()
        db2 = Database()
        
        # 验证它们是同一个实例
        assert db1 is db2