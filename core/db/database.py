from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List, Dict, Any, Tuple, Callable
import logging
import os

from .models import Base, Host, Settings, Defaults

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    _instance = None  # 单例实例
    _current_db = None  # 当前数据库路径

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # 先初始化默认数据库连接，用于读取设置
        default_db_path = os.path.join(os.getcwd(), 'databases', 'default.db')
        os.makedirs(os.path.dirname(default_db_path), exist_ok=True)
        temp_engine = create_engine(f'sqlite:///{default_db_path}')
        Base.metadata.create_all(temp_engine)
        
        # 获取上次使用的数据库
        with sessionmaker(bind=temp_engine)() as session:
            settings = session.query(Settings).first()
            if not settings:
                # 如果 settings 不存在，创建并设置默认值
                settings = Settings(last_used_db='default')
                session.add(settings)
                session.commit()
            last_used_db = settings.last_used_db
        
        # 关闭临时连接
        temp_engine.dispose()
        
        # 初始化实际使用的数据库
        db_path = os.path.join(os.getcwd(), 'databases', f'{last_used_db}.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._current_db = db_path
        self.engine = create_engine(f'sqlite:///{self._current_db}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.init_db()
        self._callbacks = []  # 用于存储回调函数

    def register_callback(self, callback: Callable):
        """注册数据库切换回调"""
        self._callbacks.append(callback)

    def switch_database(self, db_name: str) -> bool:
        """切换数据库
        Args:
            db_name: 数据库名称（不带.db后缀）
        Returns:
            bool: 是否切换成功
        """
        try:
            # 关闭当前连接
            self.engine.dispose()
            
            # 构建新数据库路径
            new_db_path = os.path.join(os.getcwd(), 'databases', f'{db_name}.db')
            
            # 如果数据库不存在，则创建
            if not os.path.exists(new_db_path):
                os.makedirs(os.path.dirname(new_db_path), exist_ok=True)
                temp_engine = create_engine(f'sqlite:///{new_db_path}')
                Base.metadata.create_all(temp_engine)
                temp_engine.dispose()
            
            # 切换到新数据库
            self._current_db = new_db_path
            self.engine = create_engine(f'sqlite:///{self._current_db}')
            self.Session = sessionmaker(bind=self.engine)
            
            # 更新所有数据库的 last_used_db
            self.update_last_used_db(db_name)
            
            # 切换成功后调用所有回调
            for callback in self._callbacks:
                callback()
                
            logger.info(f"成功切换到数据库: {db_name}")
            return True
        except Exception as e:
            logger.error(f"切换数据库失败: {str(e)}")
            self._recover_to_default()
            return False

    def _recover_to_default(self):
        """恢复到默认数据库"""
        default_db_path = os.path.join(os.getcwd(), 'databases', 'default.db')
        self.engine = create_engine(f'sqlite:///{default_db_path}')
        self.Session = sessionmaker(bind=self.engine)
        self._current_db = default_db_path
        logger.info("已恢复到默认数据库")

    def get_current_db_name(self) -> str:
        """获取当前数据库名称"""
        return os.path.basename(self._current_db).replace('.db', '')

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.Session()

    def init_db(self):
        """初始化数据库表"""
        try:
            Base.metadata.create_all(self.engine)
            with self.get_session() as session:
                # 初始化默认配置
                if not session.query(Defaults).first():
                    defaults = Defaults()
                    session.add(defaults)
                # 初始化程序设置
                if not session.query(Settings).first():
                    settings = Settings(last_used_db='default')  # 确保设置默认值
                    session.add(settings)
                session.commit()
            logger.info("数据库初始化成功")
        except SQLAlchemyError as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise

    # Host表操作
    def add_host(self, host_data: Dict[str, Any]) -> bool:
        """添加新设备"""
        try:
            with self.get_session() as session:
                host = Host(**host_data)
                session.add(host)
                session.commit()
                logger.info(f"添加设备成功: {host.name}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"添加设备失败: {str(e)}")
            return False

    def get_host(self, name: str) -> Optional[Host]:
        """获取单个设备信息"""
        with self.get_session() as session:
            return session.query(Host).filter_by(name=name).first()

    def get_all_hosts(self) -> List[Host]:
        """获取所有设备"""
        with self.get_session() as session:
            return session.query(Host).all()

    def update_host(self, name: str, host_data: Dict[str, Any]) -> bool:
        """更新设备信息"""
        try:
            with self.get_session() as session:
                host = session.query(Host).filter_by(name=name).first()
                if host:
                    for key, value in host_data.items():
                        setattr(host, key, value)
                    session.commit()
                    logger.info(f"更新设备成功: {name}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"更新设备失败: {str(e)}")
            return False

    def delete_host(self, name: str) -> bool:
        """删除设备"""
        try:
            with self.get_session() as session:
                host = session.query(Host).filter_by(name=name).first()
                if host:
                    session.delete(host)
                    session.commit()
                    logger.info(f"删除设备成功: {name}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"删除设备失败: {str(e)}")
            return False

    def batch_delete_hosts(self, names: List[str]) -> int:
        """批量删除设备
        
        Args:
            names: 要删除的设备名称列表
            
        Returns:
            int: 成功删除的数量
        """
        try:
            with Session(self.engine) as session:
                result = session.query(Host).filter(Host.name.in_(names)).delete(synchronize_session=False)
                session.commit()
                return result
        except Exception as e:
            logger.error(f"批量删除设备失败: {str(e)}")
            return 0

    def batch_add_or_update_hosts(self, host_data_list: List[Dict[str, Any]]) -> Tuple[int, int]:
        """批量添加或更新设备，使用批量操作优化性能"""
        try:
            with self.get_session() as session:
                # 获取现有设备
                existing_names = {host.name: host for host in 
                                session.query(Host).filter(
                                    Host.name.in_([data['name'] for data in host_data_list])
                                ).all()}
                
                # 分离新增和更新
                to_update = []
                to_insert = []
                for data in host_data_list:
                    if data['name'] in existing_names:
                        to_update.append(data)
                    else:
                        to_insert.append(data)
                
                # 批量插入新设备
                if to_insert:
                    session.bulk_insert_mappings(Host, to_insert)
                
                # 批量更新现有设备
                if to_update:
                    for data in to_update:
                        host = existing_names[data['name']]
                        for key, value in data.items():
                            setattr(host, key, value)
                
                session.commit()
                logger.info(f"批量处理完成 - 新增: {len(to_insert)}, 更新: {len(to_update)}")
                return len(to_insert), len(to_update)
                
        except SQLAlchemyError as e:
            logger.error(f"批量处理设备失败: {str(e)}")
            session.rollback()
            return 0, 0

    def batch_edit_devices(self, device_names: List[str], edited_fields: Dict[str, Any]) -> int:
        """批量编辑设备，使用单次更新操作"""
        try:
            with self.get_session() as session:
                result = session.query(Host).filter(
                    Host.name.in_(device_names)
                ).update(
                    edited_fields,
                    synchronize_session=False
                )
                session.commit()
                logger.info(f"批量更新完成 - 更新: {result} 个设备")
                return result
        except SQLAlchemyError as e:
            logger.error(f"批量更新设备失败: {str(e)}")
            session.rollback()
            return 0

    # Settings表操作
    def get_settings(self) -> Dict[str, Any]:
        """获取程序设置"""
        with self.get_session() as session:
            settings = session.query(Settings).first()
            if not settings:
                settings = Settings()
                session.add(settings)
                session.commit()
            return {
                'proxy_enabled': settings.proxy_enabled,
                'proxy_host': settings.proxy_host,
                'proxy_port': settings.proxy_port,
                'config_base_path': settings.config_base_path
            }

    def update_settings(self, settings_data: Dict[str, Any]) -> bool:
        """更新程序设置"""
        try:
            with self.get_session() as session:
                settings = session.query(Settings).first()
                if not settings:
                    settings = Settings()
                    session.add(settings)
                
                for key, value in settings_data.items():
                    setattr(settings, key, value)
                session.commit()
                logger.info("更新程序设置成功")
                return True
        except SQLAlchemyError as e:
            logger.error(f"更新程序设置失败: {str(e)}")
            return False

    # Defaults表操作
    def get_defaults(self) -> Dict[str, Any]:
        """获取默认配置"""
        with self.get_session() as session:
            defaults = session.query(Defaults).first()
            if not defaults:
                defaults = Defaults()
                session.add(defaults)
                session.commit()
            return {
                'timeout': defaults.timeout,
                'global_delay_factor': defaults.global_delay_factor,
                'fast_cli': defaults.fast_cli
            }

    def update_defaults(self, defaults_data: Dict[str, Any]) -> bool:
        """更新默认配置"""
        try:
            with self.get_session() as session:
                defaults = session.query(Defaults).first()
                if not defaults:
                    defaults = Defaults()
                    session.add(defaults)
                
                for key, value in defaults_data.items():
                    setattr(defaults, key, value)
                session.commit()
                logger.info("更新默认配置成功")
                return True
        except SQLAlchemyError as e:
            logger.error(f"更新默认配置失败: {str(e)}")
            return False

    def update_last_used_db(self, db_name: str) -> bool:
        """更新所有数据库中的最后使用数据库设置"""
        try:
            # 获取所有数据库文件
            db_dir = os.path.join(os.getcwd(), 'databases')
            db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
            
            for db_file in db_files:
                db_path = os.path.join(db_dir, db_file)
                engine = create_engine(f'sqlite:///{db_path}')
                with sessionmaker(bind=engine)() as session:
                    settings = session.query(Settings).first()
                    if not settings:
                        settings = Settings()
                        session.add(settings)
                    settings.last_used_db = db_name
                    session.commit()
                engine.dispose()
            
            return True
        except Exception as e:
            logger.error(f"更新最后使用的数据库失败: {str(e)}")
            return False

    def ensure_initialized(self):
        """确保数据库已初始化"""
        try:
            with self.get_session() as session:
                # 检查设置表是否存在
                settings = session.query(Settings).first()
                if not settings:
                    # 创建默认设置
                    default_settings = Settings(
                        config_base_path=os.path.join(os.getcwd(), "配置文件")
                    )
                    session.add(default_settings)
                    session.commit()
        except Exception as e:
            logger.error(f"数据库初始化检查失败: {str(e)}")
            # 确保数据库文件和表结构存在
            self.create_all() 