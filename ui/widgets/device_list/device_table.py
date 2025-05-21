from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                               QCheckBox, QWidget, QHBoxLayout, QStyle, QStyleOptionButton,
                               QLabel, QFrame, QVBoxLayout)
from PySide6.QtCore import Qt, Signal, QRect
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

    def set_checked_state(self, state: bool, emit_signal: bool = True):
        """设置复选框状态

        Args:
            state: 复选框状态
            emit_signal: 是否发送信号
        """
        if self.isChecked != state:
            self.isChecked = state
            self.updateSection(0)
            if emit_signal:
                self.checkStateChanged.emit(state)

class DraggableCheckBox(QCheckBox):
    """可拖动的复选框"""
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 将事件传递给父窗口
            event.ignore()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        # 将事件传递给父窗口
        event.ignore()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            # 将事件传递给父窗口
            event.ignore()
            return
        super().mouseReleaseEvent(event)

class CheckBoxWidget(QWidget):
    """复选框部件，用于居中显示复选框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # 减小间距
        layout.setAlignment(Qt.AlignCenter)

        self.checkbox = DraggableCheckBox()
        self.checkbox.setFixedSize(16, 16)  # 设置固定大小
        layout.addWidget(self.checkbox)

        # 存储行号
        self.row = -1

    def setRow(self, row):
        """设置当前行号"""
        self.row = row

    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 将事件传递给父窗口（表格）
            event.ignore()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        # 将事件传递给父窗口（表格）
        event.ignore()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            # 将事件传递给父窗口（表格）
            event.ignore()
            return
        super().mouseReleaseEvent(event)

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
        self.device_status_map = {}  # 改名为device_status_map
        self.filtered_devices = []  # 添加已过滤设备列表
        self.sort_column_logical_index = -1  # 排序列逻辑索引
        self.current_sort_order = Qt.AscendingOrder  # 排序顺序

        # 鼠标拖动选择相关变量
        self.mouse_pressed_on_checkbox_column = False  # 是否在复选框列按下鼠标
        self.drag_last_row = -1  # 拖动时上一次处理的行
        self.drag_target_check_state = False  # 拖动时要设置的目标状态

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

        # 设置列宽
        if self.columnCount() > 0:
            self.setColumnWidth(0, 40)  # 复选框列稍宽一点

        # 让最后一列拉伸
        if self.columnCount() > 1:
            self.horizontalHeader().setSectionResizeMode(self.columnCount() - 1, QHeaderView.Stretch)

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

    def update_device_statuses(self, status_dict: dict):
        """更新设备状态（增强版，仅更新状态列）"""
        self.device_status_map.clear()  # 确保使用 self.device_status_map
        self.device_status_map.update(status_dict)

        status_col_idx = self.get_status_column_index()
        if status_col_idx != -1 and self.rowCount() > 0:
            for row in range(self.rowCount()):
                # 假设设备名称在第1列 (索引1)
                name_item = self.item(row, 1)
                if name_item:
                    device_name = name_item.text()
                    status_text = self.device_status_map.get(device_name, '')

                    # 更新或创建状态单元格
                    item_to_update = self.item(row, status_col_idx)
                    if not item_to_update:
                        item_to_update = QTableWidgetItem()
                        item_to_update.setTextAlignment(Qt.AlignCenter)
                        self.setItem(row, status_col_idx, item_to_update)

                    item_to_update.setText(status_text)

                    # 根据状态设置颜色
                    if '成功' in status_text:
                        item_to_update.setForeground(Qt.green)
                    elif '失败' in status_text or '不可达' in status_text:
                        item_to_update.setForeground(Qt.red)
                    elif '正在测试' in status_text:
                        item_to_update.setForeground(Qt.blue)
                    else:
                        item_to_update.setForeground(Qt.black)  # 默认颜色

    def _ip_to_int(self, ip_str):
        """将IP地址转换为整数以便正确排序 (增强版)"""
        try:
            # 匹配IP地址格式
            ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', str(ip_str))  # 确保是字符串
            if ip_match:
                ip_addr = ip_match.group(1)
                parts = list(map(int, ip_addr.split('.')))
                if all(0 <= p <= 255 for p in parts):  # 验证IP各部分范围
                    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
            return float('inf')  # 无效IP或非IP字符串排在最后
        except ValueError:  # 处理非整数部分
            return float('inf')
        except Exception:  # 其他意外
            return float('inf')

    def _sort_devices(self):
        """根据当前排序设置对设备进行排序 (使用 self.sort_column_logical_index)"""
        # 使用 self.sort_column_logical_index 和 self.current_sort_order
        if self.sort_column_logical_index <= 0 or self.sort_column_logical_index >= len(self.columns):
            # 如果表头有指示器，可以尝试读取，否则不排序
            header_sort_col = self.custom_header.sortIndicatorSection()
            if header_sort_col > 0:
                self.sort_column_logical_index = header_sort_col
                self.current_sort_order = self.custom_header.sortIndicatorOrder()
            else:
                return  # 没有有效的排序列

        col_attr_name = self.columns[self.sort_column_logical_index][0]
        reverse = (self.current_sort_order == Qt.DescendingOrder)

        def get_sort_key(device_obj):  # device_obj 应该是你的 Device 类的实例
            val = getattr(device_obj, col_attr_name, "")
            if col_attr_name == 'hostname':  # 假设 hostname 是IP地址的属性名
                return self._ip_to_int(val)
            if isinstance(val, (int, float)):
                return val
            return str(val).lower()

        try:
            self.filtered_devices.sort(key=get_sort_key, reverse=reverse)
        except Exception as e:
            print(f"Error during sorting: {e}")

    def refresh_table(self):
        """刷新表格数据 (增加保持选中状态的逻辑)"""
        # 1. 保存当前选中的设备名称
        previously_checked_names = self.get_checked_devices()

        self.setRowCount(0)  # 清空

        # 应用搜索和筛选
        current_display_devices = []
        for device in self.all_devices:
            # 检查搜索条件
            search_match = True
            if self.search_text:
                name = getattr(device, 'name', '').lower()
                hostname = getattr(device, 'hostname', '').lower()
                site = getattr(device, 'site', '').lower() if getattr(device, 'site', None) else ''

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
            if not filter_match:
                continue

            current_display_devices.append(device)

        self.filtered_devices = current_display_devices
        self._sort_devices()  # 排序

        self.setRowCount(len(self.filtered_devices))  # 一次性设置行数

        for i, device in enumerate(self.filtered_devices):
            self.setVerticalHeaderItem(i, QTableWidgetItem(str(i + 1)))

            checkbox_widget = CheckBoxWidget()
            # 2. 恢复选中状态
            if device.name in previously_checked_names:
                checkbox_widget.checkbox.setChecked(True)
            # 连接到新的处理函数
            checkbox_widget.checkbox.stateChanged.connect(self._on_individual_checkbox_changed)
            checkbox_widget.setRow(i)  # 设置行号
            self.setCellWidget(i, 0, checkbox_widget)

            # 添加数据
            for col, (attr, _) in enumerate(self.columns):
                if col > 0:  # 跳过第一列（复选框）
                    value = getattr(device, attr, '')
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.setItem(i, col, item)

            # 如果有状态列，添加状态
            status_col_idx = self.get_status_column_index()
            if status_col_idx != -1:
                status_text = self.device_status_map.get(device.name, '')  # 使用 map
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignCenter)

                # 根据状态设置颜色
                if '成功' in status_text:
                    status_item.setForeground(Qt.green)
                elif '失败' in status_text or '不可达' in status_text:
                    status_item.setForeground(Qt.red)
                elif '正在测试' in status_text:
                    status_item.setForeground(Qt.blue)
                else:
                    status_item.setForeground(Qt.black)

                self.setItem(i, status_col_idx, status_item)

        # 3. 更新表头和状态栏
        self._update_header_checkbox_state_from_rows()  # 新的辅助函数
        self.update_status_bar()

    def _on_sort_changed(self, logicalIndex, order):
        """处理排序变化"""
        self.sort_column_logical_index = logicalIndex  # 保存逻辑索引
        self.current_sort_order = order
        # 表头控件的 setSortIndicator 应该在 CheckBoxHeader._on_section_clicked 中调用
        self.refresh_table()

    def _on_select_all_changed(self, state):
        """全选框状态改变时触发"""
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget and isinstance(checkbox_widget, CheckBoxWidget):  # 安全检查
                checkbox_widget.checkbox.blockSignals(True)
                checkbox_widget.checkbox.setChecked(state)
                checkbox_widget.checkbox.blockSignals(False)
        self._finalize_checkbox_changes()  # 调用统一处理函数

    def _update_header_checkbox_state_from_rows(self):
        """根据当前所有行的勾选状态，更新表头复选框（不发送信号）"""
        if self.rowCount() == 0:
            self.custom_header.set_checked_state(False, emit_signal=False)
            return

        all_checked_flag = True
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget and isinstance(checkbox_widget, CheckBoxWidget):
                if not checkbox_widget.checkbox.isChecked():
                    all_checked_flag = False
                    break

        # 仅当状态不同时更新，且不触发 CheckBoxHeader 的 checkStateChanged 信号
        if self.custom_header.isChecked != all_checked_flag:
            self.custom_header.set_checked_state(all_checked_flag, emit_signal=False)

    def _on_individual_checkbox_changed(self):
        """单个行内复选框状态改变时触发"""
        self._finalize_checkbox_changes()  # 调用统一处理函数

    def _finalize_checkbox_changes(self):
        """任何复选框状态改变后的统一处理（单个、全选、拖动结束）"""
        self._update_header_checkbox_state_from_rows()  # 更新表头
        checked_devices_list = self.get_checked_devices()  # 获取选中的设备
        self.devices_checked.emit(checked_devices_list)  # 发送信号
        self.update_status_bar()  # 更新状态栏

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

    def mousePressEvent(self, event):
        """鼠标按下事件 - 核心修改"""
        if event.button() == Qt.LeftButton:
            # 使用 event.position().toPoint() (PySide6) 或 event.pos() (PyQt5)
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            row = self.rowAt(pos.y())
            col = self.columnAt(pos.x())

            if row >= 0 and col == 0:  # 确保点击在复选框列的有效行上
                checkbox_widget = self.cellWidget(row, 0)
                if checkbox_widget and isinstance(checkbox_widget, CheckBoxWidget):
                    self.mouse_pressed_on_checkbox_column = True
                    self.drag_last_row = row  # 记录初始拖动行

                    initial_state = checkbox_widget.checkbox.isChecked()
                    self.drag_target_check_state = not initial_state  # 目标状态是反转

                    # 立即应用到被点击的行，并阻塞信号
                    checkbox_widget.checkbox.blockSignals(True)
                    checkbox_widget.checkbox.setChecked(self.drag_target_check_state)
                    checkbox_widget.checkbox.blockSignals(False)

                    self.setMouseTracking(True)  # 开始追踪鼠标
                    event.accept()  # 声明事件已被处理
                    return

        super().mousePressEvent(event)  # 如果不是我们处理的情况，则调用父类

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 核心修改"""
        if self.mouse_pressed_on_checkbox_column:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            current_row = self.rowAt(pos.y())

            if current_row >= 0 and current_row != self.drag_last_row:
                # 处理从 self.drag_last_row 到 current_row 之间的所有行 (包含两端)
                # 这样可以处理鼠标快速移动跳过某些行的情况
                row_start_iter = min(self.drag_last_row, current_row)
                row_end_iter = max(self.drag_last_row, current_row)

                for r_iter in range(row_start_iter, row_end_iter + 1):
                    checkbox_widget_iter = self.cellWidget(r_iter, 0)
                    if checkbox_widget_iter and isinstance(checkbox_widget_iter, CheckBoxWidget):
                        # 仅当状态不同时才更改，并阻塞信号
                        if checkbox_widget_iter.checkbox.isChecked() != self.drag_target_check_state:
                            checkbox_widget_iter.checkbox.blockSignals(True)
                            checkbox_widget_iter.checkbox.setChecked(self.drag_target_check_state)
                            checkbox_widget_iter.checkbox.blockSignals(False)

                self.drag_last_row = current_row  # 更新上一行记录

            event.accept()  # **关键：声明事件已被处理**
            return          # **关键：阻止事件进一步传播**

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 核心修改"""
        if event.button() == Qt.LeftButton and self.mouse_pressed_on_checkbox_column:
            self.mouse_pressed_on_checkbox_column = False  # 重置状态
            self.drag_last_row = -1
            self.setMouseTracking(False)  # 关闭追踪

            self._finalize_checkbox_changes()  # **关键：拖动结束后，统一处理状态更新和信号发射**

            event.accept()  # **关键：声明事件已被处理**
            return          # **关键：阻止事件进一步传播**

        super().mouseReleaseEvent(event)