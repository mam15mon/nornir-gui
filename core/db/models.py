from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Host(Base):
    """设备表"""
    __tablename__ = 'hosts'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # 设备名称
    hostname = Column(String, nullable=False)  # 主机名/IP
    platform = Column(String, nullable=False)  # 平台类型
    username = Column(String)  # 用户名
    password = Column(String)  # 密码
    port = Column(Integer, default=22)  # 端口号
    site = Column(String)  # 站点
    device_type = Column(String)  # 设备类型
    device_model = Column(String)  # 设备型号
    created_at = Column(DateTime, default=datetime.now)  # 创建时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 更新时间

class Settings(Base):
    """系统设置表"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    proxy_enabled = Column(Boolean, default=False)  # 代理启用状态
    proxy_host = Column(String)  # 代理服务器地址
    proxy_port = Column(Integer)  # 代理服务器端口
    config_base_path = Column(String)  # 配置文件基础路径
    last_used_db = Column(String, default='default')  # 上次使用的数据库
    created_at = Column(DateTime, default=datetime.now)  # 创建时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 更新时间
    log_file_level = Column(String, default='INFO')  # 统一的日志级别

class Defaults(Base):
    """默认连接设置表"""
    __tablename__ = 'defaults'

    id = Column(Integer, primary_key=True)
    timeout = Column(Integer, default=60)  # 连接超时时间
    global_delay_factor = Column(Float, default=2.0)  # 全局延迟因子
    fast_cli = Column(Boolean, default=False)  # 快速CLI模式
    num_workers = Column(Integer, default=30)  # 并发工作线程数
    created_at = Column(DateTime, default=datetime.now)  # 创建时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 更新时间 