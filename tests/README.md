# 测试框架使用指南

## 测试框架结构

```
tests/
├── conftest.py              # pytest配置和共享fixtures
├── test_helpers.py          # 测试工具类
├── test_framework.py        # 测试框架验证测试
├── unit/                    # 单元测试
│   ├── test_database.py     # 数据库操作测试
│   ├── test_config.py       # 配置管理测试
│   └── test_nornir.py       # Nornir管理测试
├── integration/             # 集成测试
│   ├── test_device_ops.py   # 设备操作集成测试
│   └── test_workflow.py     # 工作流测试
├── ui/                      # UI测试
│   ├── test_main_window.py  # 主窗口测试
│   └── test_dialogs.py      # 对话框测试
└── fixtures/                # 测试数据
    ├── sample_data.json     # 示例数据
    └── mock_responses.json  # 模拟响应数据
```

## 安装测试依赖

```bash
pip install -r requirements-dev.txt
```

## 运行测试

### 运行所有测试
```bash
python run_tests.py
# 或者
pytest
```

### 运行特定类型测试
```bash
# 单元测试
python run_tests.py unit
pytest -m unit

# 集成测试
python run_tests.py integration
pytest -m integration

# UI测试
python run_tests.py ui
pytest -m ui
```

### 运行带覆盖率的测试
```bash
python run_tests.py coverage
pytest --cov=core --cov=ui --cov-report=html
```

### 运行特定测试文件
```bash
pytest tests/unit/test_database.py
```

### 运行特定测试函数
```bash
pytest tests/unit/test_database.py::TestDatabase::test_add_host
```

## 测试标记

- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.ui`: UI测试
- `@pytest.mark.slow`: 慢速测试
- `@pytest.mark.database`: 数据库相关测试
- `@pytest.mark.network`: 网络相关测试

## 可用的Fixtures

### 数据库相关
- `test_database`: 创建测试数据库实例
- `test_db_path`: 测试数据库文件路径
- `sample_host_data`: 单个主机示例数据
- `sample_hosts_data`: 多个主机示例数据

### 配置相关
- `mock_config_manager`: 模拟配置管理器
- `temp_dir`: 临时目录

### 使用示例

```python
def test_database_operations(test_database, sample_host_data):
    # 测试添加主机
    result = test_database.add_host(sample_host_data)
    assert result is True
    
    # 测试获取主机
    host = test_database.get_host(sample_host_data["name"])
    assert host is not None
    assert host.name == sample_host_data["name"]
```

## 测试工具类

### TestDatabaseHelper
```python
from tests.test_helpers import TestDatabaseHelper

helper = TestDatabaseHelper(temp_dir)
db = helper.create_test_database()
helper.cleanup()
```

### MockConfigHelper
```python
from tests.test_helpers import MockConfigHelper

with MockConfigHelper.patch_config_manager():
    # 测试代码
    pass
```

### TestDataGenerator
```python
from tests.test_helpers import TestDataGenerator

# 生成单个主机数据
host_data = TestDataGenerator.generate_host_data()

# 生成多个主机数据
hosts_data = TestDataGenerator.generate_hosts_data(count=5)
```

## 编写新测试

### 1. 单元测试示例

```python
import pytest
from core.db.database import Database

@pytest.mark.unit
class TestDatabase:
    def test_add_host(self, test_database, sample_host_data):
        result = test_database.add_host(sample_host_data)
        assert result is True
        
        host = test_database.get_host(sample_host_data["name"])
        assert host is not None
```

### 2. 集成测试示例

```python
import pytest
from core.nornir_manager.nornir_manager import NornirManager

@pytest.mark.integration
class TestNornirIntegration:
    def test_device_connection(self, test_database, sample_host_data):
        # 添加测试设备
        test_database.add_host(sample_host_data)
        
        # 测试连接
        manager = NornirManager()
        result = manager.test_connection(sample_host_data["name"])
        assert result is True
```

### 3. UI测试示例

```python
import pytest
from pytestqt.qtbot import QtBot
from ui.main_window import MainWindow

@pytest.mark.ui
class TestMainWindow:
    def test_main_window_creation(self, qtbot):
        window = MainWindow()
        qtbot.addWidget(window)
        
        assert window is not None
        assert window.windowTitle() != ""
```

## 测试最佳实践

1. **测试命名**: 使用`test_`前缀，描述性强
2. **测试隔离**: 每个测试应该独立运行
3. **断言清晰**: 使用明确的断言消息
4. **清理资源**: 使用fixtures自动清理测试数据
5. **模拟外部依赖**: 使用mock对象隔离外部依赖
6. **覆盖边界情况**: 测试正常和异常情况

## 故障排除

### 常见问题

1. **ImportError**: 确保项目根目录在PYTHONPATH中
2. **数据库错误**: 检查测试数据库路径和权限
3. **UI测试失败**: 确保测试环境支持GUI

### 调试测试

```bash
# 运行测试并进入调试模式
pytest --pdb tests/unit/test_database.py::TestDatabase::test_add_host

# 只运行失败的测试
pytest --lf

# 显示详细的测试输出
pytest -v -s
```

## 持续集成

测试框架支持CI/CD集成，详见`.github/workflows/`目录下的配置文件。