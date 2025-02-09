from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from ..importers.device_importer import DeviceImporter

class DropArea(QFrame):
    """文件拖放区域"""
    file_dropped = Signal(str)  # 文件拖放信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumSize(400, 200)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # 添加图标标签
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # 添加提示标签
        label = QLabel('拖放 Excel 文件到此处\n或点击"导入设备"按钮选择文件')
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.endswith(('.xlsx', '.xls')):
                self.file_dropped.emit(file_path)

class ImportDialog(QDialog):
    """导入设备对话框"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("导入设备")
        self.setMinimumWidth(500)
        
        # 创建主布局
        layout = QVBoxLayout(self)
        
        # 添加拖放区域
        self.drop_area = DropArea(self)
        self.drop_area.file_dropped.connect(self.import_from_file)
        layout.addWidget(self.drop_area)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)
        
        # 添加导出模板按钮
        self.template_btn = QPushButton("下载导入模板")
        self.template_btn.clicked.connect(self.export_template)
        button_layout.addWidget(self.template_btn)
        
        button_layout.addStretch()
        
        # 添加导入和取消按钮
        self.import_btn = QPushButton("导入设备")
        self.import_btn.clicked.connect(self.import_devices)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.cancel_btn)
    
    def import_devices(self):
        """通过文件对话框导入设备"""
        success, count = DeviceImporter.import_devices(self, self.db)
        if success:
            self.accept()
    
    def import_from_file(self, file_path: str):
        """从文件导入设备"""
        success, count = DeviceImporter.import_from_file(file_path, self.db)
        if success:
            self.accept()
    
    def export_template(self):
        """导出模板"""
        DeviceImporter.export_template(self) 