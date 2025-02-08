# Nornir GUI

一个简单的网络自动化小工具，基于 Nornir 和 PySide6 开发。刚学习 Python 不久，代码写得比较粗糙，功能也在完善中，欢迎大家一起交流学习。

## 目前实现的功能

- 简单的图形界面（虽然不太好看😅）
- 批量配置和命令下发（偶尔会出bug）
- 配置备份和对比
- 一些基础查询功能
  - 接口信息
  - MAC/IP
  - DNAT
- 配置保存

## 已知问题
- 部分功能还不够稳定
- 代码结构需要优化
- 可能还有很多未发现的bug...

## 安装要求

- Python 3.8+
- PySide6
- Nornir 及相关插件
- 其他依赖见 requirements.txt

## 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/mam15mon/nornir_gui.git
cd nornir-gui
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行程序：
```bash
python main.py
```

## 使用说明

1. 首次运行时，需要配置设备信息
2. 在主界面选择要执行的操作
3. 根据提示输入必要参数
4. 查看执行结果

## 配置文件

- 日志文件位于 `logs/` 目录
- 数据库文件位于 `databases/` 目录

## 注意事项

- 建议在测试环境下使用
- 重要操作前请一定要备份配置
- 如果遇到问题，欢迎提 Issue

## 关于作者

网络自动化初学者，正在学习 Python 和网络自动化。代码水平有限，欢迎大家指出问题，一起学习进步！

## 贡献指南

项目还很粗糙，欢迎大家：
- 提交 Issue 反馈问题
- 提交 PR 改进代码
- 提供建议和想法
- 一起学习交流

## 许可证

MIT License 
