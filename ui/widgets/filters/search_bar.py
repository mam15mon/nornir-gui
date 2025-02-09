from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel
from PySide6.QtCore import Signal

class SearchBar(QWidget):
    """搜索栏组件"""
    textChanged = Signal(str)  # 搜索文本改变信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 搜索标签
        search_label = QLabel("搜索：")
        layout.addWidget(search_label)

        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入设备名称、IP或站点进行搜索...")
        self.search_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.search_input)

    def _on_text_changed(self, text):
        """搜索文本改变时触发"""
        self.textChanged.emit(text)

    def text(self):
        """获取搜索文本"""
        return self.search_input.text()

    def clear(self):
        """清空搜索框"""
        self.search_input.clear() 