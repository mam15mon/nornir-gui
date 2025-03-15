from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                               QCheckBox, QWidget, QHBoxLayout, QStyle, QStyleOptionButton,
                               QLabel, QFrame, QVBoxLayout)
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QEvent
from PySide6.QtGui import QPainter
import re

class CheckBoxHeader(QHeaderView):
    """带复选框的表头"""
    checkStateChanged = Signal(bool)
    sortChanged = Signal(int, Qt.SortOrder)  # 添加排序信号

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.isChecked = False
        self.setSectionsClickable(True)
        self.sectionClicked.connect(self._on_section_clicked)
        self.sortIndicatorColumn = -1
        self.sortIndicatorOrder = Qt.AscendingOrder
        self.setSortIndicatorShown(True)
        self.setSectionsClickable(True)

    def paintSection(self, painter, rect, logicalIndex):
        """重写绘制表头单元格的方法"""
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()
        
        if logicalIndex == 0:  # 只在第一列绘制复选框
            option = QStyleOptionButton()
            # 调整复选框的位置和大小
            checkbox_size = 16  # 复选框大小
            x_pos = rect.x() + (rect.width() - checkbox_size) // 2 - 1  # 向左移动1像素
            y_pos = rect.y() + (rect.height() - checkbox_size) // 2
            option.rect = QRect(x_pos, y_pos, checkbox_size, checkbox_size)
            
            option.state = QStyle.State_Enabled
            if self.isChecked:
                option.state |= QStyle.State_On
            else:
                option.state |= QStyle.State_Off
            
            self.style().drawControl(QStyle.CE_CheckBox, option, painter)

    def _on_section_clicked(self, logicalIndex):
        """处理表头点击事件"""
        if logicalIndex == 0:  # 处理第一列的点击
            self.isChecked = not self.isChecked
            self.checkStateChanged.emit(self.isChecked)
            self.updateSection(0)  # 重绘第一列表头
        elif logicalIndex > 0:  # 其他列处理排序
            if self.sortIndicatorColumn == logicalIndex:
                # 切换排序顺序
                self.sortIndicatorOrder = Qt.DescendingOrder if self.sortIndicatorOrder == Qt.AscendingOrder else Qt.AscendingOrder
            else:
                # 设置新的排序列
                self.sortIndicatorColumn = logicalIndex
                self.sortIndicatorOrder = Qt.AscendingOrder
            
            # 发送排序信号
            self.sortChanged.emit(logicalIndex, self.sortIndicatorOrder)
            self.setSortIndicator(logicalIndex, self.sortIndicatorOrder)

    def set_checked_state(self, state: bool):
        """设置复选框状态"""
        if self.isChecked != state:
            self.isChecked = state
            self.updateSection(0)
            self.checkStateChanged.emit(state)

class CheckBoxWidget(QWidget):
    """复选框部件，用于居中显示复选框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # 减小间距
        layout.setAlignment(Qt.AlignCenter)
        
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(16, 16)  # 设置固定大小
        layout.addWidget(self.checkbox)

class DeviceTable(QTableWidget):
    """设备表格组件"""
    device_double_clicked = Signal(str)  # 设备双击信号，用于编辑
    devices_checked = Signal(list)  # 设备勾选信号，主要使用这个
    stats_changed = Signal(int, int)  # 状态栏信息变化信号：总设备数、已选择设备数

    def __init__(self, columns=None, show_status=False, parent=None):
        """
        Args:
            columns: 自定义列配置
            show_status: 是否显示状态列
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 基础列配置
        base_columns = [
            ('checkbox', '选择'),  # 复选框列
            ('name', '设备名称'),
            ('hostname', '主机名/IP'),
            ('platform', '平台类型'),
            ('username', '用户名'),
            ('password', '密码'),
            ('port', '端口'),
            ('site', '站点'),
            ('device_type', '设备类型'),
            ('device_model', '设备型号')
        ]
        
        # 如果需要显示状态列，添加状态列
        if show_status:
            base_columns.append(('status', '状态'))
            
        self.columns = columns or base_columns
        self.all_devices = []
        self.search_text = ""
        self.current_filters = {}
        self.device_status = {}
        self.filtered_devices = []  # 添加已过滤设备列表
        self.sort_column = -1  # 排序列
        self.sort_order = Qt.AscendingOrder  # 排序顺序
        self.init_ui()
        self.status_bar = None  # 状态栏引用

    def init_ui(self):
        """初始化UI"""
        # 设置列数和表头
        self.setColumnCount(len(self.columns))
        headers = [col[1] for col in self.columns]
        headers[0] = ""  # 清空复选框列的标题
        
        # 创建自定义表头
        self.custom_header = CheckBoxHeader(Qt.Horizontal, self)
        self.setHorizontalHeader(self.custom_header)
        self.custom_header.checkStateChanged.connect(self._on_select_all_changed)
        self.custom_header.sortChanged.connect(self._on_sort_changed)  # 连接排序信号
        
        # 设置表头标签
        self.setHorizontalHeaderLabels(headers)
        
        # 设置表格属性
        self.setAlternatingRowColors(True)  # 交替行颜色
        self.setSelectionBehavior(QTableWidget.SelectRows)  # 保留这个以防后续需要
        self.setSelectionMode(QTableWidget.NoSelection)  # 禁用行选择
        self.setEditTriggers(QTableWidget.NoEditTriggers)  # 不可编辑
        self.verticalHeader().setVisible(True)  # 显示行号
        
        # 设置表头样式
        self.custom_header.setSectionResizeMode(QHeaderView.Interactive)
        self.custom_header.setStretchLastSection(True)
        self.setColumnWidth(0, 30)  # 减小复选框列的宽度

        # 连接信号
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # 创建状态栏
        self.setup_status_bar()

    def setup_status_bar(self):
        """设置状态栏信号"""
        # 注：实际状态栏已移至页面级别，这里只保留状态栏更新函数和信号
        pass

    def update_status_bar(self):
        """更新状态栏信息"""
        total_devices = len(self.filtered_devices)
        checked_devices = len(self.get_checked_devices())
        # 发送状态栏信息变化信号
        self.stats_changed.emit(total_devices, checked_devices)

    def update_data(self, devices):
        """更新表格数据"""
        self.all_devices = devices
        self.refresh_table()

    def set_search_text(self, text):
        """设置搜索文本"""
        self.search_text = text.strip().lower()
        self.refresh_table()

    def apply_filters(self, filters):
        """应用筛选条件"""
        self.current_filters = filters or {}
        self.refresh_table()

    def update_status(self, status_dict: dict):
        """更新设备状态（增强版）"""
        # 清空旧状态数据
        self.device_status.clear()
        # 更新为新状态数据
        self.device_status.update(status_dict)
        
        status_col = self.get_status_column_index()
        for row in range(self.rowCount()):
            device_name = self.item(row, 1).text()
            status = self.device_status.get(device_name, '')  # 现在只会获取当前传入的状态
            
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            
            if '成功' in status:
                status_item.setForeground(Qt.green)
            elif '失败' in status or '不可达' in status:
                status_item.setForeground(Qt.red)
            
            self.setItem(row, status_col, status_item)

    def _ip_to_int(self, ip_str):
        """将IP地址转换为整数以便正确排序"""
        try:
            # 匹配IP地址格式
            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', ip_str)
            if ip_match:
                ip_addr = ip_match.group(1)
                # 将IP地址转换为整数
                parts = list(map(int, ip_addr.split('.')))
                return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
            return 0
        except:
            return 0

    def _sort_devices(self):
        """根据当前排序设置对设备进行排序"""
        if self.sort_column <= 0:  # 不对复选框列排序
            return
        
        col_name = self.columns[self.sort_column][0]
        reverse = (self.sort_order == Qt.DescendingOrder)
        
        # 主机名/IP特殊处理
        if col_name == 'hostname':
            # 使用IP地址转整数函数进行排序
            self.filtered_devices.sort(
                key=lambda dev: self._ip_to_int(getattr(dev, col_name, "")),
                reverse=reverse
            )
        else:
            # 其他列正常排序
            self.filtered_devices.sort(
                key=lambda dev: str(getattr(dev, col_name, "")),
                reverse=reverse
            )

    def refresh_table(self):
        """刷新表格数据"""
        # 使用新方法重置表头全选状态
        self.custom_header.set_checked_state(False)
        
        self.setRowCount(0)
        
        # 应用搜索和筛选
        self.filtered_devices = []
        for device in self.all_devices:
            # 检查搜索条件
            if self.search_text:
                name = device.name.lower()
                hostname = device.hostname.lower()
                site = device.site.lower() if device.site else ''

                search_match = (
                    self.search_text in name or
                    self.search_text in hostname or
                    self.search_text in site
                )
                if not search_match:
                    continue

            # 检查筛选条件
            filter_match = True
            for filter_type, filter_value in self.current_filters.items():
                if filter_value != "全部":
                    device_value = str(getattr(device, filter_type, ''))
                    if device_value != filter_value:
                        filter_match = False
                        break

            if filter_match:
                self.filtered_devices.append(device)
        
        # 排序设备列表
        self._sort_devices()

        # 显示过滤后的设备
        for i, device in enumerate(self.filtered_devices):
            row = self.rowCount()
            self.insertRow(row)
            
            # 设置行号（从1开始）
            self.setVerticalHeaderItem(row, QTableWidgetItem(str(i+1)))
            
            # 添加复选框（居中显示）
            checkbox_widget = CheckBoxWidget()
            checkbox_widget.checkbox.stateChanged.connect(self._on_checkbox_changed)
            self.setCellWidget(row, 0, checkbox_widget)
            
            # 添加数据
            for col, (attr, _) in enumerate(self.columns):
                if col > 0:  # 跳过第一列（复选框）
                    value = getattr(device, attr, '')
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.setItem(row, col, item)

            # 如果有状态列，添加状态
            if ('status', '状态') in self.columns:
                status = self.device_status.get(device.name, '')
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                
                # 根据状态设置颜色
                if '成功' in status:
                    status_item.setForeground(Qt.green)
                elif '失败' in status or '不可达' in status:
                    status_item.setForeground(Qt.red)
                elif '正在测试' in status:
                    status_item.setForeground(Qt.blue)
                else:
                    status_item.setForeground(Qt.black)
                
                self.setItem(row, len(self.columns) - 1, status_item)
        
        # 更新状态栏
        self.update_status_bar()

    def _on_sort_changed(self, column, order):
        """处理排序变化"""
        self.sort_column = column
        self.sort_order = order
        self.refresh_table()

    def _on_select_all_changed(self, state):
        """全选框状态改变时触发"""
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox_widget.checkbox.setChecked(state)
        # 更新状态栏
        self.update_status_bar()

    def _on_checkbox_changed(self):
        """复选框状态改变时触发"""
        checked_devices = self.get_checked_devices()
        self.devices_checked.emit(checked_devices)
        
        # 更新全选框状态
        all_checked = len(checked_devices) == self.rowCount() and self.rowCount() > 0
        if all_checked != self.custom_header.isChecked:
            self.custom_header.isChecked = all_checked
            self.custom_header.updateSection(0)
        
        # 更新状态栏
        self.update_status_bar()

    def get_checked_devices(self):
        """获取所有勾选的设备名称"""
        checked_devices = []
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                device_name = self.item(row, 1).text()
                checked_devices.append(device_name)
        return checked_devices

    def _on_item_double_clicked(self, item):
        """双击项目时触发"""
        row = item.row()
        device_name = self.item(row, 1).text()
        self.device_double_clicked.emit(device_name)

    def get_status_column_index(self):
        """获取状态列的索引"""
        for i, (attr, _) in enumerate(self.columns):
            if attr == 'status':
                return i
        return -1 