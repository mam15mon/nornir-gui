from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextEdit, QRadioButton,
                             QButtonGroup, QGroupBox, QCheckBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QWidget, QMessageBox)
from PySide6.QtCore import Qt

class CommandDialog(QDialog):
    """命令发送对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.command = None
        self.command_mode = "netmiko_send_command"  # 默认模式
        self.use_timing = False  # 默认不使用timing模式
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("发送命令")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 命令输入区域
        command_group = QGroupBox("命令")
        command_layout = QVBoxLayout(command_group)
        
        # 普通命令输入框
        self.command_edit = QTextEdit()
        self.command_edit.setPlaceholderText("请输入要执行的命令...")
        
        # 交互式命令表格
        self.command_table = QTableWidget()
        self.command_table.setColumnCount(2)
        self.command_table.setHorizontalHeaderLabels(["命令", "期望响应"])
        header = self.command_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.command_table.hide()  # 默认隐藏
        
        # 交互式命令按钮组
        self.button_widget = QWidget()  # 创建一个容器widget
        button_layout = QHBoxLayout(self.button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        add_row_btn = QPushButton("添加行")
        add_row_btn.clicked.connect(self.add_command_row)
        delete_row_btn = QPushButton("删除行")
        delete_row_btn.clicked.connect(self.delete_command_row)
        button_layout.addWidget(add_row_btn)
        button_layout.addWidget(delete_row_btn)
        button_layout.addStretch()
        
        self.button_widget.hide()  # 默认隐藏按钮组
        
        command_layout.addWidget(self.command_edit)
        command_layout.addWidget(self.command_table)
        command_layout.addWidget(self.button_widget)  # 添加按钮组容器
        
        layout.addWidget(command_group)
        
        # 命令模式选择
        mode_group = QGroupBox("命令模式")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_group = QButtonGroup(self)
        
        # 普通命令模式
        self.normal_mode = QRadioButton("视图命令模式")
        self.normal_mode.setChecked(True)
        self.normal_mode.setToolTip("执行display等查看命令")
        self.mode_group.addButton(self.normal_mode)
        mode_layout.addWidget(self.normal_mode)
        
        # 配置命令模式
        self.config_mode = QRadioButton("配置命令模式")
        self.config_mode.setToolTip("执行配置命令，自动进入配置模式")
        self.mode_group.addButton(self.config_mode)
        mode_layout.addWidget(self.config_mode)
        
        # 多行命令模式
        self.multiline_mode = QRadioButton("交互式命令模式")
        self.multiline_mode.setToolTip("执行需要交互的命令，如删除文件确认等")
        self.mode_group.addButton(self.multiline_mode)
        mode_layout.addWidget(self.multiline_mode)
        
        # 添加timing模式选项
        self.use_timing_check = QCheckBox("使用timing模式")
        self.use_timing_check.setToolTip("使用基于时间的方式执行命令，适用于有交互提示或长时间运行的命令")
        mode_layout.addWidget(self.use_timing_check)
        
        layout.addWidget(mode_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept_command)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
        
        # 连接信号
        self.mode_group.buttonClicked.connect(self.on_mode_changed)
        
        # 添加timing模式复选框的状态变化监听
        self.use_timing_check.stateChanged.connect(self._update_column_visibility)
        
    def on_mode_changed(self, button):
        """当模式改变时切换输入界面"""
        is_multiline = button == self.multiline_mode
        is_config = button == self.config_mode
        
        self.command_edit.setVisible(not is_multiline)
        self.command_table.setVisible(is_multiline)
        self.button_widget.setVisible(is_multiline)
        
        # 配置模式下禁用 timing 选项
        if is_config:
            self.use_timing_check.setEnabled(False)
            self.use_timing_check.setChecked(False)  # 配置模式强制不使用 timing
        else:
            self.use_timing_check.setEnabled(True)
        
        self._update_column_visibility()
        
        # 如果切换到交互式模式且表格为空，自动添加一行
        if is_multiline and self.command_table.rowCount() == 0:
            self.add_command_row()
        
    def _update_column_visibility(self):
        """更新表格列可见性"""
        if self.multiline_mode.isChecked():
            timing_mode = self.use_timing_check.isChecked()
            # 第二列（期望响应）在非timing模式时显示
            self.command_table.setColumnHidden(1, timing_mode)
            # 调整列宽
            if timing_mode:
                self.command_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            else:
                self.command_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
                self.command_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
    def add_command_row(self):
        """添加新的命令行"""
        row = self.command_table.rowCount()
        self.command_table.insertRow(row)
        self.command_table.setItem(row, 0, QTableWidgetItem(""))
        self.command_table.setItem(row, 1, QTableWidgetItem(""))
        
    def delete_command_row(self):
        """删除选中的命令行"""
        current_row = self.command_table.currentRow()
        if current_row >= 0:
            self.command_table.removeRow(current_row)
            
    def accept_command(self):
        """接受命令输入"""
        if self.multiline_mode.isChecked():
            # 收集交互式命令
            commands = []
            for row in range(self.command_table.rowCount()):
                cmd_item = self.command_table.item(row, 0)
                expect_item = self.command_table.item(row, 1)
                
                # 非timing模式下检查命令和期望值是否都已填写
                if not self.use_timing_check.isChecked():
                    cmd_text = cmd_item.text().strip() if cmd_item else ""
                    expect_text = expect_item.text().strip() if expect_item else ""
                    
                    if not cmd_text or not expect_text:
                        QMessageBox.warning(
                            self,
                            "输入错误", 
                            f"第 {row+1} 行的命令和期望响应都不能为空！",
                            QMessageBox.Ok
                        )
                        return
                
                if cmd_item and cmd_item.text().strip():
                    cmd = cmd_item.text().strip()
                    if self.use_timing_check.isChecked():
                        # timing模式下直接使用命令
                        commands.append(cmd)
                    else:
                        # 非timing模式使用命令|期望值格式
                        expect = expect_item.text().strip() if expect_item and expect_item.text().strip() else r"[#>]"
                        commands.append(f"{cmd}|{expect}")
            self.command = "\n".join(commands)
            self.command_mode = "multiline"
        else:
            self.command = self.command_edit.toPlainText().strip()
            if not self.command:
                return
                
            if self.config_mode.isChecked():
                self.command_mode = "configuration"
            else:
                self.command_mode = "netmiko_send_command"
                
        self.use_timing = self.use_timing_check.isChecked()
        self.accept()
        
    def get_command(self) -> tuple:
        """获取命令和模式
        
        Returns:
            tuple: (command, mode, use_timing) 命令内容、模式和是否使用timing
        """
        return self.command, self.command_mode, self.use_timing 