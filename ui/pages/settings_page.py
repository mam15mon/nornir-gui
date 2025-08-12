from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QGroupBox,
                             QFormLayout, QMessageBox, QGridLayout, QFileDialog, QComboBox, QInputDialog)
from sqlalchemy.orm import Session, sessionmaker
import os
import time
import shutil
from sqlalchemy import create_engine

from core.db.database import Database
from core.db.models import Defaults, Base, Host
from core.proxy_manager import ProxyManager
from core.event_bus import event_bus

class SettingsPage(QWidget):
    """设置页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.db.register_callback(self.on_database_changed)  # 注册回调
        # 使用父窗口的ProxyManager实例
        if parent and hasattr(parent, 'proxy_manager'):
            self.proxy_manager = parent.proxy_manager
        else:
            self.proxy_manager = ProxyManager(self.db)

        # 标记是否正在加载设置
        self.is_loading = True

        self.init_ui()
        self.load_settings()

        # 设置加载完成
        self.is_loading = False
        
        # 在初始化完成后才连接信号
        self.enable_proxy.stateChanged.connect(self.on_proxy_enabled)

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

        # 读取超时时间
        self.read_timeout_spin = QSpinBox()
        self.read_timeout_spin.setRange(10, 600)
        self.read_timeout_spin.setValue(30)
        layout.addRow("读取超时(秒):", self.read_timeout_spin)

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

        # 按钮组 - 第一行
        btn_layout1 = QHBoxLayout()
        self.new_db_btn = QPushButton("新建")
        self.delete_db_btn = QPushButton("删除")

        for btn in [self.new_db_btn, self.delete_db_btn]:
            btn.setFixedWidth(80)
            btn_layout1.addWidget(btn)

        btn_layout1.addStretch()
        layout.addLayout(btn_layout1)

        # 按钮组 - 第二行
        btn_layout2 = QHBoxLayout()
        self.backup_db_btn = QPushButton("备份")
        self.restore_db_btn = QPushButton("恢复")

        for btn in [self.backup_db_btn, self.restore_db_btn]:
            btn.setFixedWidth(80)
            btn_layout2.addWidget(btn)

        btn_layout2.addStretch()
        layout.addLayout(btn_layout2)

        # 连接信号
        self.new_db_btn.clicked.connect(self._on_new_db)
        self.delete_db_btn.clicked.connect(self._on_delete_db)
        self.backup_db_btn.clicked.connect(self._on_backup_db)
        self.restore_db_btn.clicked.connect(self._on_restore_db)

        # 数据库选择变化时自动切换
        self.db_combo.currentTextChanged.connect(self._on_db_selection_changed)

        group.setLayout(layout)
        return group

    def _create_config_group(self):
        """创建存档设置组"""
        group = QGroupBox("存档设置")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 用户配置文件信息
        config_info_layout = QVBoxLayout()
        config_info_label = QLabel("用户配置文件:")
        config_info_label.setStyleSheet("font-weight: bold;")
        config_info_layout.addWidget(config_info_label)

        self.config_file_path_label = QLabel()
        self.config_file_path_label.setStyleSheet("color: #666; font-size: 11px;")
        self.config_file_path_label.setWordWrap(True)
        config_info_layout.addWidget(self.config_file_path_label)

        layout.addLayout(config_info_layout)

        # 存档路径设置
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

        # 数据库路径设置
        db_path_layout = QHBoxLayout()
        db_path_layout.addWidget(QLabel("数据库路径:"))
        self.db_base_path = QLineEdit()
        self.db_base_path.setPlaceholderText("选择数据库存储路径")
        db_path_layout.addWidget(self.db_base_path)
        
        self.select_db_path_btn = QPushButton("浏览...")
        self.select_db_path_btn.setFixedWidth(80)
        self.select_db_path_btn.clicked.connect(self.select_db_path)
        db_path_layout.addWidget(self.select_db_path_btn)
        
        layout.addLayout(db_path_layout)

        # 配置管理按钮
        config_btn_layout = QHBoxLayout()

        self.reset_config_btn = QPushButton("重置为默认")
        self.reset_config_btn.setFixedWidth(100)
        self.reset_config_btn.clicked.connect(self.reset_config_to_defaults)
        config_btn_layout.addWidget(self.reset_config_btn)

        self.backup_config_btn = QPushButton("备份配置")
        self.backup_config_btn.setFixedWidth(100)
        self.backup_config_btn.clicked.connect(self.backup_user_config)
        config_btn_layout.addWidget(self.backup_config_btn)

        self.restore_config_btn = QPushButton("恢复配置")
        self.restore_config_btn.setFixedWidth(100)
        self.restore_config_btn.clicked.connect(self.restore_user_config)
        config_btn_layout.addWidget(self.restore_config_btn)

        config_btn_layout.addStretch()
        layout.addLayout(config_btn_layout)

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
            
    def select_db_path(self):
        """选择数据库路径"""
        path = QFileDialog.getExistingDirectory(
            self,
            "选择数据库存储路径",
            self.db_base_path.text() or os.getcwd(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if path:
            self.db_base_path.setText(path)

    def reset_config_to_defaults(self):
        """重置配置为默认值"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有配置为默认值吗？\n这将清除所有自定义设置。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                config_manager = self.db.get_config_manager()
                if config_manager:
                    config_manager.reset_to_defaults()
                    QMessageBox.information(self, "成功", "配置已重置为默认值，请重新加载设置。")
                    self.load_settings()  # 重新加载设置
                else:
                    QMessageBox.warning(self, "错误", "无法获取配置管理器")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重置配置失败: {str(e)}")

    def backup_user_config(self):
        """备份用户配置文件"""
        try:
            config_manager = self.db.get_config_manager()
            if not config_manager:
                QMessageBox.warning(self, "错误", "无法获取配置管理器")
                return

            # 选择备份文件路径
            backup_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存配置备份",
                f"nornir-gui-config-backup.ini",
                "配置文件 (*.ini);;所有文件 (*)"
            )

            if backup_path:
                config_manager.backup_config(backup_path)
                QMessageBox.information(self, "成功", f"配置已备份到: {backup_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"备份配置失败: {str(e)}")

    def restore_user_config(self):
        """恢复用户配置文件"""
        try:
            # 选择备份文件
            backup_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择配置备份文件",
                "",
                "配置文件 (*.ini);;所有文件 (*)"
            )

            if backup_path:
                reply = QMessageBox.question(
                    self,
                    "确认恢复",
                    "确定要从备份文件恢复配置吗？\n这将覆盖当前的所有设置。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    config_manager = self.db.get_config_manager()
                    if config_manager:
                        config_manager.restore_config(backup_path)
                        QMessageBox.information(self, "成功", "配置已从备份恢复，请重新加载设置。")
                        self.load_settings()  # 重新加载设置
                    else:
                        QMessageBox.warning(self, "错误", "无法获取配置管理器")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"恢复配置失败: {str(e)}")

    def load_settings(self):
        """加载设置"""
        try:
            # 显示用户配置文件路径
            config_manager = self.db.get_config_manager()
            if config_manager:
                config_file_path = config_manager.get_config_file_path()
                self.config_file_path_label.setText(f"配置文件位置: {config_file_path}")
                
                # 从用户配置文件加载设置
                proxy_settings = config_manager.get_proxy_settings()
                self.enable_proxy.setChecked(proxy_settings['enabled'])
                self.proxy_host.setText(proxy_settings['host'])
                self.proxy_port.setValue(proxy_settings['port'])
                
                # 加载存档路径
                archive_path = config_manager.get_archive_base_path()
                self.config_base_path.setText(archive_path)
                
                # 加载数据库路径
                db_path = config_manager.get_database_path()
                self.db_base_path.setText(db_path)
                
                # 加载日志级别
                log_level = config_manager.get_log_level()
                self.file_log_combo.setCurrentText(log_level)
            else:
                self.config_file_path_label.setText("用户配置文件不可用")
            
            # 设置当前数据库显示
            current_db = self.db.get_current_db_name()
            self.db_combo.setCurrentText(current_db)
            
            # 加载连接设置（仍从数据库加载）
            with Session(self.db.engine) as session:
            
                # 加载连接设置
                defaults = session.query(Defaults).first()
                if defaults:
                    self.timeout_spin.setValue(defaults.timeout)
                    self.delay_spin.setValue(defaults.global_delay_factor)
                    self.fast_cli_check.setChecked(defaults.fast_cli)
                    if hasattr(defaults, 'read_timeout'):
                        self.read_timeout_spin.setValue(defaults.read_timeout)
                    if hasattr(defaults, 'num_workers'):
                        self.workers_spin.setValue(defaults.num_workers)
                
                # 更新代理控件状态
                self.on_proxy_enabled(self.enable_proxy.isChecked(), save_settings=False)
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载设置失败: {str(e)}")

    def save_settings(self):
        """保存设置"""
        try:
            # 验证代理设置
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

            # 获取并规范化基础路径
            base_path = os.path.normpath(self.config_base_path.text().strip())

            # 创建基础目录
            os.makedirs(base_path, exist_ok=True)

            # 创建必要的子目录
            from core.config.path_utils import ensure_archive_subdirs
            ensure_archive_subdirs(self.db)

            # 使用配置管理器保存设置
            config_manager = self.db.get_config_manager()
            if config_manager:
                # 保存代理设置
                config_manager.set_proxy_settings(
                    enabled=self.enable_proxy.isChecked(),
                    host=self.proxy_host.text().strip() if self.enable_proxy.isChecked() else '',
                    port=self.proxy_port.value() if self.enable_proxy.isChecked() else 8080
                )

                # 保存存档路径
                config_manager.set_archive_base_path(base_path)

                # 保存数据库路径
                db_path = os.path.normpath(self.db_base_path.text().strip())
                config_manager.set_database_path(db_path)

                # 保存日志级别
                config_manager.set_log_level(self.file_log_combo.currentText())
            else:
                QMessageBox.warning(self, "警告", "配置管理器不可用，设置可能无法正确保存")

            # 保存连接设置（仍保存到数据库）
            with Session(self.db.engine) as session:
                defaults = session.query(Defaults).first()
                if not defaults:
                    defaults = Defaults()
                    session.add(defaults)

                defaults.timeout = self.timeout_spin.value()
                defaults.global_delay_factor = float(self.delay_spin.value())
                defaults.fast_cli = self.fast_cli_check.isChecked()
                defaults.read_timeout = self.read_timeout_spin.value()
                defaults.num_workers = self.workers_spin.value()

                session.commit()

                # 重新应用日志配置
                from core.utils.logger import setup_logging
                setup_logging()

                # 发送设置变化信号
                event_bus.settings_changed.emit()

                QMessageBox.information(self, "成功", "设置已保存并应用")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存设置失败: {str(e)}")

    def on_proxy_enabled(self, enabled, save_settings=True):
        """代理启用状态改变时触发"""
        self.proxy_host.setEnabled(enabled)
        self.proxy_port.setEnabled(enabled)
        
        # 自动保存代理设置
        if save_settings:
            self._save_proxy_settings()
    
    def _save_proxy_settings(self):
        """保存代理设置"""
        try:
            # 使用配置管理器保存代理设置
            config_manager = self.db.get_config_manager()
            if config_manager:
                config_manager.set_proxy_settings(
                    enabled=self.enable_proxy.isChecked(),
                    host=self.proxy_host.text().strip() if self.enable_proxy.isChecked() else '',
                    port=self.proxy_port.value() if self.enable_proxy.isChecked() else 8080
                )
                # 重新应用代理配置
                self.proxy_manager.apply_proxy()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存代理设置失败: {str(e)}")

    def _load_databases(self):
        """加载可用数据库"""
        # 从配置管理器获取数据库路径
        config_manager = self.db.get_config_manager()
        if config_manager:
            db_dir = config_manager.get_database_path()
        else:
            db_dir = os.path.join(os.getcwd(), 'databases')

        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self.db_combo.clear()
        for file in os.listdir(db_dir):
            if file.endswith('.db'):
                self.db_combo.addItem(file.replace('.db', ''))

    def _on_db_selection_changed(self, db_name):
        """数据库选择变化时自动切换"""
        # 如果正在加载设置，不执行切换
        if hasattr(self, 'is_loading') and self.is_loading:
            return

        # 如果选择的是当前数据库，不需要切换
        if db_name == self.db.get_current_db_name():
            return

        # 如果数据库名为空，不处理
        if not db_name:
            return

        # 切换到选中的数据库
        success = self.db.switch_database(db_name)
        if success:
            # 通知其他组件
            event_bus.settings_changed.emit()
        else:
            QMessageBox.warning(self, "错误", f"切换到数据库 {db_name} 失败")
            # 恢复下拉框选择
            self.db_combo.setCurrentText(self.db.get_current_db_name())

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
                    QMessageBox.information(self, "成功", f"数据库 {db_name} 创建成功并已切换")
                    event_bus.settings_changed.emit()
                else:
                    QMessageBox.warning(self, "警告", f"数据库创建成功，但切换失败")

            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建数据库失败: {str(e)}")

    def _create_default_db(self):
        """创建默认数据库"""
        db_path = os.path.join(os.getcwd(), 'databases', 'default.db')
        if not os.path.exists(db_path):
            try:
                # 创建数据库文件
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                temp_engine = create_engine(f'sqlite:///{db_path}')
                Base.metadata.create_all(temp_engine)
                temp_engine.dispose()

                # 刷新数据库列表
                self._load_databases()
                self.db_combo.setCurrentText('default')

                # 自动切换到新数据库
                success = self.db.switch_database('default')
                if success:
                    event_bus.settings_changed.emit()
                
                return True
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建默认数据库失败: {str(e)}")
                return False
        return True

    def _on_backup_db(self):
        """备份数据库"""
        db_name = self.db_combo.currentText()
        if not db_name:
            return

        # 创建备份目录
        backup_dir = os.path.join(os.getcwd(), "database_backups")
        os.makedirs(backup_dir, exist_ok=True)

        # 选择备份位置
        backup_path = QFileDialog.getExistingDirectory(
            self,
            "选择备份目录",
            backup_dir,
            QFileDialog.ShowDirsOnly
        )

        if not backup_path:
            return

        try:
            # 创建备份目录
            os.makedirs(backup_path, exist_ok=True)

            # 源数据库路径
            source_path = os.path.join(os.getcwd(), 'databases', f'{db_name}.db')

            # 目标备份路径（添加时间戳）
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            target_path = os.path.join(backup_path, f'{db_name}_{timestamp}.db')

            # 复制文件
            shutil.copy2(source_path, target_path)

            QMessageBox.information(
                self,
                "备份成功",
                f"数据库 {db_name} 已备份到:\n{target_path}"
            )
        except Exception as e:
            QMessageBox.warning(self, "备份失败", f"备份数据库时出错: {str(e)}")

    def _on_restore_db(self):
        """恢复数据库"""
        # 创建备份目录
        backup_dir = os.path.join(os.getcwd(), "database_backups")
        os.makedirs(backup_dir, exist_ok=True)

        # 选择备份文件
        backup_file, _ = QFileDialog.getOpenFileName(
            self,
            "选择备份文件",
            backup_dir,
            "数据库文件 (*.db)"
        )

        if not backup_file:
            return

        # 获取文件名（不带路径和扩展名）
        db_name = os.path.basename(backup_file).split('.')[0]

        # 如果文件名包含时间戳，去掉时间戳
        if '_' in db_name:
            parts = db_name.split('_')
            if len(parts) > 1 and parts[-2].isdigit() and parts[-1].isdigit():
                db_name = '_'.join(parts[:-2])

        # 询问用户是否要修改数据库名称
        new_name, ok = QInputDialog.getText(
            self,
            "恢复数据库",
            "请输入恢复后的数据库名称:",
            QLineEdit.Normal,
            db_name
        )

        if not ok or not new_name:
            return

        # 检查名称是否已存在
        target_path = os.path.join(os.getcwd(), 'databases', f'{new_name}.db')
        if os.path.exists(target_path):
            reply = QMessageBox.question(
                self,
                "确认覆盖",
                f"数据库 {new_name} 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

        try:
            # 复制文件
            shutil.copy2(backup_file, target_path)

            # 刷新数据库列表
            self._load_databases()
            self.db_combo.setCurrentText(new_name)

            QMessageBox.information(
                self,
                "恢复成功",
                f"数据库已恢复为 {new_name}"
            )
        except Exception as e:
            QMessageBox.warning(self, "恢复失败", f"恢复数据库时出错: {str(e)}")

    def _on_delete_db(self):
        """删除数据库"""
        db_name = self.db_combo.currentText()
        if not db_name:
            return

        # 检查是否为当前数据库
        is_current = db_name == self.db.get_current_db_name()

        # 获取数据库中的设备数量
        device_count = 0
        db_path = os.path.join(os.getcwd(), 'databases', f'{db_name}.db')
        if os.path.exists(db_path):
            try:
                temp_engine = create_engine(f'sqlite:///{db_path}')
                Session = sessionmaker(bind=temp_engine)
                with Session() as session:
                    device_count = session.query(Host).count()
                temp_engine.dispose()
            except Exception:
                pass

        # 获取其他可用数据库
        other_dbs = [self.db_combo.itemText(i) for i in range(self.db_combo.count())
                    if self.db_combo.itemText(i) != db_name]

        # 如果是唯一的数据库，不允许删除
        if len(other_dbs) == 0:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("无法删除数据库")
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText("无法删除唯一的数据库")

            detail_text = f"数据库: {db_name}\n"
            detail_text += f"包含设备数量: {device_count}\n"
            detail_text += "\n这是唯一的数据库，无法删除。"
            detail_text += "\n请先创建一个新数据库，然后再尝试删除此数据库。"

            msg_box.setDetailedText(detail_text)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
            return

        # 创建确认对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认删除数据库")
        msg_box.setIcon(QMessageBox.Warning)

        # 设置详细信息
        detail_text = f"数据库: {db_name}\n"
        detail_text += f"包含设备数量: {device_count}\n"
        detail_text += "此操作将永久删除该数据库，且无法恢复！"

        if is_current:
            # 如果是当前数据库，提示将自动切换到其他数据库
            switch_to = other_dbs[0]  # 默认切换到列表中的第一个数据库
            detail_text += f"\n\n当前正在使用此数据库，删除后将自动切换到 {switch_to} 数据库。"

            msg_box.setText(f"确定要删除当前使用的数据库 {db_name} 吗？")
        else:
            msg_box.setText(f"确定要删除数据库 {db_name} 吗？")

        msg_box.setDetailedText(detail_text)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # 显示对话框
        reply = msg_box.exec()

        # 处理删除操作
        if reply == QMessageBox.Yes:
            try:
                # 如果是当前数据库，先切换到其他数据库
                if is_current:
                    switch_to = other_dbs[0]
                    success = self.db.switch_database(switch_to)
                    if not success:
                        QMessageBox.warning(self, "错误", f"切换到数据库 {switch_to} 失败，无法删除当前数据库")
                        return

                # 删除数据库文件
                if os.path.exists(db_path):
                    os.remove(db_path)

                    # 刷新数据库列表
                    self._load_databases()

                    # 如果删除后列表为空，自动创建一个默认数据库
                    if self.db_combo.count() == 0:
                        self._create_default_db()

                    # 更新当前选中的数据库
                    if is_current:
                        self.db_combo.setCurrentText(switch_to)
                        QMessageBox.information(self, "成功", f"数据库 {db_name} 已删除，已切换到 {switch_to}")
                        # 通知其他组件
                        event_bus.settings_changed.emit()
                    else:
                        QMessageBox.information(self, "成功", f"数据库 {db_name} 已删除")
                else:
                    QMessageBox.warning(self, "错误", "数据库文件不存在")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除数据库失败: {str(e)}")

    def on_database_changed(self):
        """数据库切换后的处理"""
        # 设置正在加载标记，防止触发额外的切换操作
        self.is_loading = True

        # 刷新数据库列表
        self._load_databases()

        # 设置当前选中的数据库
        self.db_combo.setCurrentText(self.db.get_current_db_name())

        # 重新加载所有数据
        self.load_settings()

        # 完成加载
        self.is_loading = False

        # 通知其他组件
        event_bus.device_list_changed.emit()