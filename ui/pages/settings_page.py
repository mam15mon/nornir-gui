from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QGroupBox,
                             QFormLayout, QMessageBox, QGridLayout, QFileDialog, QComboBox, QInputDialog)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
import os
from sqlalchemy import create_engine

from core.db.database import Database
from core.db.models import Defaults, Settings, Base
from core.proxy_manager import ProxyManager
from core.event_bus import event_bus

class SettingsPage(QWidget):
    """设置页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.db.register_callback(self.on_database_changed)  # 注册回调
        self.proxy_manager = ProxyManager()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # 创建左右两栏布局
        h_layout = QHBoxLayout()
        left_column = QVBoxLayout()
        right_column = QVBoxLayout()

        # === 左列 ===
        # 1. 连接设置组
        conn_group = self._create_connection_group()
        left_column.addWidget(conn_group)

        # 2. 代理设置组
        proxy_group = self._create_proxy_group()
        left_column.addWidget(proxy_group)

        # 3. 日志设置组
        log_group = self._create_log_group()
        left_column.addWidget(log_group)

        # === 右列 ===
        # 1. 数据库设置组
        db_group = self._create_database_group()
        right_column.addWidget(db_group)

        # 2. 存档设置组
        config_group = self._create_config_group()
        right_column.addWidget(config_group)

        # 添加弹性空间
        left_column.addStretch()
        right_column.addStretch()

        # 将左右列添加到水平布局
        h_layout.addLayout(left_column)
        h_layout.addLayout(right_column)

        # 添加主布局
        main_layout.addLayout(h_layout)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("保存设置")
        self.save_btn.setFixedWidth(120)  # 固定按钮宽度
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)

    def _create_connection_group(self):
        """创建连接设置组"""
        group = QGroupBox("连接设置")
        layout = QFormLayout()
        layout.setSpacing(10)

        # 超时时间
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(60)
        layout.addRow("超时时间(秒):", self.timeout_spin)

        # 延迟因子
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.1, 10.0)
        self.delay_spin.setValue(2.0)
        self.delay_spin.setSingleStep(0.1)
        layout.addRow("延迟因子:", self.delay_spin)

        # 并发数
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 100)
        self.workers_spin.setValue(10)
        layout.addRow("并发数:", self.workers_spin)

        # 快速CLI模式
        self.fast_cli_check = QCheckBox("启用快速CLI模式")
        layout.addRow("", self.fast_cli_check)

        group.setLayout(layout)
        return group

    def _create_proxy_group(self):
        """创建代理设置组"""
        group = QGroupBox("代理设置")
        layout = QFormLayout()
        layout.setSpacing(10)

        # 启用代理
        self.enable_proxy = QCheckBox("启用代理")
        self.enable_proxy.stateChanged.connect(self.on_proxy_enabled)
        layout.addRow("", self.enable_proxy)

        # 服务器地址
        self.proxy_host = QLineEdit()
        layout.addRow("服务器地址:", self.proxy_host)

        # 端口
        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(1080)
        layout.addRow("端口:", self.proxy_port)

        group.setLayout(layout)
        return group

    def _create_log_group(self):
        """创建日志设置组"""
        group = QGroupBox("日志设置")
        layout = QFormLayout()
        layout.setSpacing(10)

        # 日志级别
        self.file_log_combo = QComboBox()
        self.file_log_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        layout.addRow("日志级别:", self.file_log_combo)

        group.setLayout(layout)
        return group

    def _create_database_group(self):
        """创建数据库设置组"""
        group = QGroupBox("数据库设置")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 数据库选择
        db_layout = QHBoxLayout()
        db_layout.addWidget(QLabel("当前数据库:"))
        self.db_combo = QComboBox()
        self._load_databases()
        db_layout.addWidget(self.db_combo)
        layout.addLayout(db_layout)

        # 按钮组
        btn_layout = QHBoxLayout()
        self.new_db_btn = QPushButton("新建")
        self.delete_db_btn = QPushButton("删除")
        self.switch_db_btn = QPushButton("切换")
        
        for btn in [self.new_db_btn, self.delete_db_btn, self.switch_db_btn]:
            btn.setFixedWidth(80)
            btn_layout.addWidget(btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 连接信号
        self.new_db_btn.clicked.connect(self._on_new_db)
        self.delete_db_btn.clicked.connect(self._on_delete_db)
        self.switch_db_btn.clicked.connect(self._on_switch_db)

        group.setLayout(layout)
        return group

    def _create_config_group(self):
        """创建存档设置组"""
        group = QGroupBox("存档设置")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("基础路径:"))
        self.config_base_path = QLineEdit()
        self.config_base_path.setPlaceholderText("选择存储的基础路径")
        path_layout.addWidget(self.config_base_path)

        self.select_path_btn = QPushButton("浏览...")
        self.select_path_btn.setFixedWidth(80)
        self.select_path_btn.clicked.connect(self.select_config_path)
        path_layout.addWidget(self.select_path_btn)

        layout.addLayout(path_layout)
        group.setLayout(layout)
        return group

    def select_config_path(self):
        """选择配置文件基础路径"""
        path = QFileDialog.getExistingDirectory(
            self,
            "选择配置文件基础路径",
            self.config_base_path.text() or os.getcwd(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if path:
            self.config_base_path.setText(path)

    def load_settings(self):
        """加载设置"""
        try:
            with Session(self.db.engine) as session:
                # 设置当前数据库显示
                current_db = self.db.get_current_db_name()
                self.db_combo.setCurrentText(current_db)
                
                # 加载代理设置
                settings = session.query(Settings).first()
                if settings:
                    self.enable_proxy.setChecked(settings.proxy_enabled)
                    if settings.proxy_host:
                        self.proxy_host.setText(settings.proxy_host)
                    if settings.proxy_port:
                        self.proxy_port.setValue(settings.proxy_port)
                    if settings.config_base_path:
                        self.config_base_path.setText(settings.config_base_path)
                    self.file_log_combo.setCurrentText(settings.log_file_level)
                
                # 加载连接设置
                defaults = session.query(Defaults).first()
                if defaults:
                    self.timeout_spin.setValue(defaults.timeout)
                    self.delay_spin.setValue(defaults.global_delay_factor)
                    self.fast_cli_check.setChecked(defaults.fast_cli)
                    if hasattr(defaults, 'num_workers'):
                        self.workers_spin.setValue(defaults.num_workers)
                
                # 更新代理控件状态
                self.on_proxy_enabled(self.enable_proxy.isChecked())
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载设置失败: {str(e)}")

    def save_settings(self):
        """保存设置"""
        try:
            with Session(self.db.engine) as session:
                # 保存代理设置
                settings = session.query(Settings).first()
                if not settings:
                    settings = Settings()
                    session.add(settings)
                
                # 获取并规范化基础路径
                base_path = os.path.normpath(self.config_base_path.text().strip())
                
                # 创建基础目录
                os.makedirs(base_path, exist_ok=True)
                
                # 创建必要的子目录
                subdirs = ["备份", "对比", "DNAT查询", "接口查询", "MAC-IP查询"]
                for subdir in subdirs:
                    dir_path = os.path.normpath(os.path.join(base_path, subdir))
                    os.makedirs(dir_path, exist_ok=True)
                
                # 保存存档路径
                settings.config_base_path = base_path or None
                
                # 保存代理设置
                if self.enable_proxy.isChecked():
                    proxy_host = self.proxy_host.text().strip()
                    proxy_port = self.proxy_port.value()
                    
                    if not proxy_host:
                        QMessageBox.warning(self, "错误", "请输入代理服务器地址")
                        self.proxy_host.setFocus()
                        return
                        
                    if proxy_port <= 0:
                        QMessageBox.warning(self, "错误", "请输入有效的代理端口")
                        self.proxy_port.setFocus()
                        return
                
                settings.proxy_enabled = self.enable_proxy.isChecked()
                settings.proxy_host = self.proxy_host.text().strip() if self.enable_proxy.isChecked() else None
                settings.proxy_port = self.proxy_port.value() if self.enable_proxy.isChecked() else None
                
                # 保存连接设置
                defaults = session.query(Defaults).first()
                if not defaults:
                    defaults = Defaults()
                    session.add(defaults)
                
                defaults.timeout = self.timeout_spin.value()
                defaults.global_delay_factor = float(self.delay_spin.value())
                defaults.fast_cli = self.fast_cli_check.isChecked()
                defaults.num_workers = self.workers_spin.value()
                
                # 保存日志设置
                settings.log_file_level = self.file_log_combo.currentText()
                
                session.commit()
                
                # 重新应用日志配置
                from core.utils.logger import setup_logging
                setup_logging()
                
                # 发送设置变化信号
                event_bus.settings_changed.emit()
                
                QMessageBox.information(self, "成功", "设置已保存并应用")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存设置失败: {str(e)}")

    def on_proxy_enabled(self, enabled):
        """代理启用状态改变时触发"""
        self.proxy_host.setEnabled(enabled)
        self.proxy_port.setEnabled(enabled)

    def _load_databases(self):
        """加载可用数据库"""
        db_dir = os.path.join(os.getcwd(), 'databases')
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        self.db_combo.clear()
        for file in os.listdir(db_dir):
            if file.endswith('.db'):
                self.db_combo.addItem(file.replace('.db', ''))
                
    def _on_switch_db(self):
        """切换数据库"""
        db_name = self.db_combo.currentText()
        if db_name:
            success = self.db.switch_database(db_name)
            if success:
                # 更新最后使用的数据库
                self.db.update_last_used_db(db_name)
                QMessageBox.information(self, "成功", f"已切换到数据库: {db_name}")
                event_bus.settings_changed.emit()  # 通知其他组件
            else:
                QMessageBox.warning(self, "错误", "数据库切换失败")

    def _on_new_db(self):
        """新建数据库"""
        db_name, ok = QInputDialog.getText(
            self,
            "新建数据库",
            "请输入新数据库名称:",
            QLineEdit.Normal
        )
        
        if ok and db_name:
            # 检查名称是否合法
            if not db_name.replace('_', '').isalnum():
                QMessageBox.warning(self, "错误", "数据库名称只能包含字母、数字和下划线")
                return
            
            # 检查是否已存在
            db_path = os.path.join(os.getcwd(), 'databases', f'{db_name}.db')
            if os.path.exists(db_path):
                QMessageBox.warning(self, "错误", "数据库已存在")
                return
            
            # 创建新数据库
            try:
                # 创建数据库文件
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                temp_engine = create_engine(f'sqlite:///{db_path}')
                Base.metadata.create_all(temp_engine)
                temp_engine.dispose()
                
                # 刷新数据库列表
                self._load_databases()
                self.db_combo.setCurrentText(db_name)
                
                # 自动切换到新数据库
                success = self.db.switch_database(db_name)
                if success:
                    self.db.update_last_used_db(db_name)
                    QMessageBox.information(self, "成功", f"数据库 {db_name} 创建成功并已切换")
                    event_bus.settings_changed.emit()
                else:
                    QMessageBox.warning(self, "警告", f"数据库创建成功，但切换失败")
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建数据库失败: {str(e)}")

    def _on_delete_db(self):
        """删除数据库"""
        db_name = self.db_combo.currentText()
        if not db_name:
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除数据库 {db_name} 吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 不能删除当前数据库
                if db_name == self.db.get_current_db_name():
                    QMessageBox.warning(self, "错误", "不能删除当前正在使用的数据库")
                    return
                
                # 删除数据库文件
                db_path = os.path.join(os.getcwd(), 'databases', f'{db_name}.db')
                if os.path.exists(db_path):
                    os.remove(db_path)
                    # 刷新数据库列表
                    self._load_databases()
                    QMessageBox.information(self, "成功", f"数据库 {db_name} 已删除")
                else:
                    QMessageBox.warning(self, "错误", "数据库文件不存在")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除数据库失败: {str(e)}") 

    def on_database_changed(self):
        """数据库切换后的处理"""
        # 刷新数据库列表
        self._load_databases()
        
        # 设置当前选中的数据库
        self.db_combo.setCurrentText(self.db.get_current_db_name())
        
        # 重新加载所有数据
        self.load_settings()
        
        # 通知其他组件
        event_bus.settings_changed.emit()
        event_bus.device_list_changed.emit()