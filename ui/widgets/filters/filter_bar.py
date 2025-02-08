from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLabel
from PySide6.QtCore import Signal

class FilterBar(QWidget):
    """筛选栏组件"""
    filterChanged = Signal(str, str)  # 信号：筛选类型, 筛选值

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = {}
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 站点筛选
        site_label = QLabel("站点：")
        self.site_filter = QComboBox()
        self.site_filter.setMinimumWidth(120)
        self.site_filter.addItem("全部")
        self.site_filter.currentTextChanged.connect(
            lambda text: self.filterChanged.emit("site", text)
        )
        layout.addWidget(site_label)
        layout.addWidget(self.site_filter)

        # 设备类型筛选
        type_label = QLabel("设备类型：")
        self.type_filter = QComboBox()
        self.type_filter.setMinimumWidth(120)
        self.type_filter.addItem("全部")
        self.type_filter.currentTextChanged.connect(
            lambda text: self.filterChanged.emit("device_type", text)
        )
        layout.addWidget(type_label)
        layout.addWidget(self.type_filter)

        # 平台筛选
        platform_label = QLabel("平台：")
        self.platform_filter = QComboBox()
        self.platform_filter.setMinimumWidth(120)
        self.platform_filter.addItem("全部")
        self.platform_filter.currentTextChanged.connect(
            lambda text: self.filterChanged.emit("platform", text)
        )
        layout.addWidget(platform_label)
        layout.addWidget(self.platform_filter)

        # 添加弹性空间
        layout.addStretch()

        # 保存筛选器引用
        self.filters = {
            "site": self.site_filter,
            "device_type": self.type_filter,
            "platform": self.platform_filter
        }

    def update_filter_items(self, filter_type, items):
        """更新筛选选项"""
        if filter_type in self.filters:
            combo = self.filters[filter_type]
            current = combo.currentText()
            combo.clear()
            combo.addItem("全部")
            combo.addItems(sorted(set(items)))
            # 恢复之前的选择
            index = combo.findText(current)
            if index >= 0:
                combo.setCurrentIndex(index)

    def get_filter_values(self):
        """获取当前筛选值"""
        return {
            filter_type: combo.currentText()
            for filter_type, combo in self.filters.items()
        }

    def reset_filters(self):
        """重置所有筛选"""
        for combo in self.filters.values():
            combo.setCurrentText("全部") 