# Nornir GUI

一个简单的网络自动化小工具，基于 Nornir 和 PySide6 开发。刚学习 Python 不久，代码写得比较粗糙，功能也在完善中，欢迎大家一起交流学习。

## 界面预览

![设备管理界面](assets/device_manager.png)

## 目前实现的功能

- 简单的图形界面
- 批量配置和命令下发
- 配置备份和对比
- 一些基础查询功能
  - 接口信息
  - MAC/IP
  - DNAT
- 配置保存

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
