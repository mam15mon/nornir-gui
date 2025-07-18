from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QGroupBox, QButtonGroup, QRadioButton, QMessageBox,
                             QInputDialog, QLineEdit)
from PySide6.QtCore import Qt
from datetime import datetime
from typing import List, Optional, Type, Dict, Any, Callable
import logging

from core.nornir_manager.threads import (
    TestThread,
    BackupThread,
    DiffThread,
    SaveThread,
    CommandThread,
    BaseOperationThread,
    DnatThread,
    InterfaceThread,
    MacIpNewThread,
    DeviceInspectionThread,
    FirewallAddressGroupThread
)
from .command_dialog import CommandDialog
from .firewall_address_group_dialog import FirewallAddressGroupDialog
from core.nornir_manager.operations.dnat_query import DnatQuery

logger = logging.getLogger(__name__)

class OperationDialog(QDialog):
    """设备操作对话框"""

    def __init__(self, device_manager: Any, device_names: List[str], parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.device_names = device_names

        # 初始化线程为 None
        self.current_thread: Optional[BaseOperationThread] = None

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("设备操作")
        layout = QVBoxLayout(self)

        # 设备信息
        info_label = QLabel(f"选中设备：{len(self.device_names)} 个")
        layout.addWidget(info_label)

        # 创建分组框 - 功能杂项
        function_group = QGroupBox("功能杂项")
        function_layout = QHBoxLayout()
        function_group.setLayout(function_layout)

        # 连接测试按钮
        self.test_btn = QPushButton("连接测试")
        self.test_btn.clicked.connect(lambda: self._start_operation(TestThread, "连接测试"))
        function_layout.addWidget(self.test_btn)

        # 查询DNAT按钮
        self.dnat_btn = QPushButton("查询DNAT")
        self.dnat_btn.clicked.connect(self._on_dnat_clicked)
        function_layout.addWidget(self.dnat_btn)

        # 查询接口按钮
        self.interface_btn = QPushButton("查询接口")
        self.interface_btn.clicked.connect(self._on_interface_clicked)
        function_layout.addWidget(self.interface_btn)

        # MAC-IP查询按钮
        self.mac_ip_btn = QPushButton("查询MAC-IP")
        self.mac_ip_btn.clicked.connect(self._on_mac_ip_clicked)
        function_layout.addWidget(self.mac_ip_btn)

        # 设备巡检按钮
        self.inspection_btn = QPushButton("设备巡检")
        self.inspection_btn.clicked.connect(lambda: self._start_operation(DeviceInspectionThread, "设备巡检"))
        function_layout.addWidget(self.inspection_btn)

        function_layout.addStretch()

        # 创建分组框 - 配置操作
        config_group = QGroupBox("配置操作")
        config_layout = QHBoxLayout()
        config_group.setLayout(config_layout)

        # 配置备份按钮
        self.backup_btn = QPushButton("配置备份")
        self.backup_btn.clicked.connect(lambda: self._start_operation(BackupThread, "配置备份"))
        config_layout.addWidget(self.backup_btn)

        # 配置对比按钮
        self.diff_btn = QPushButton("配置对比")
        self.diff_btn.clicked.connect(lambda: self._start_operation(DiffThread, "配置对比"))
        config_layout.addWidget(self.diff_btn)

        # 保存配置按钮
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(lambda: self._start_operation(SaveThread, "保存配置"))
        config_layout.addWidget(self.save_btn)

        # 防火墙地址组管理按钮
        self.firewall_address_btn = QPushButton("地址组管理")
        self.firewall_address_btn.clicked.connect(self._on_firewall_address_group_clicked)
        config_layout.addWidget(self.firewall_address_btn)


        # 创建分组框 - 命令执行
        command_group = QGroupBox("命令执行")
        command_layout = QHBoxLayout()
        command_group.setLayout(command_layout)

        # 命令执行按钮
        self.command_btn = QPushButton("命令执行")
        self.command_btn.clicked.connect(self.on_send_command)
        command_layout.addWidget(self.command_btn)
        command_layout.addStretch()

        # 添加所有分组到主布局
        layout.addWidget(function_group)
        layout.addWidget(config_group)
        layout.addWidget(command_group)

        # 添加按钮布局
        button_layout = QHBoxLayout()

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _on_dnat_clicked(self):
        """DNAT查询按钮点击事件"""
        # 获取所有选中的设备
        devices = self._get_selected_devices()
        if not devices:
            return

        # 检查是否有非防火墙设备
        non_firewall_devices = [d.name for d in devices if '防火墙' not in d.device_type.lower() and 'firewall' not in d.device_type.lower()]
        if non_firewall_devices:
            QMessageBox.warning(
                self,
                "警告",
                f"以下设备不是防火墙，无法执行 DNAT 查询：\n{', '.join(non_firewall_devices)}"
            )
            return

        # 如果全是防火墙设备，就启动操作
        self._start_operation(DnatThread, "查询DNAT")

    def _on_interface_clicked(self):
        """接口查询按钮点击事件"""
        # 获取所有选中的设备
        devices = self._get_selected_devices()
        if not devices:
            return

        # 检查是否有非交换机设备
        non_switch_devices = [d.name for d in devices if '交换机' not in d.device_type.lower() and 'switch' not in d.device_type.lower()]
        if non_switch_devices:
            QMessageBox.warning(
                self,
                "警告",
                f"以下设备不是交换机，无法执行接口查询：\n{', '.join(non_switch_devices)}"
            )
            return

        # 如果全是交换机设备，就启动操作
        self._start_operation(InterfaceThread, "查询接口")

    def _on_mac_ip_clicked(self):
        """MAC-IP查询按钮点击事件"""
        # 获取所有选中的设备
        devices = self._get_selected_devices()
        if not devices:
            return

        # 检查是否有非交换机设备
        non_switch_devices = [d.name for d in devices if '交换机' not in d.device_type.lower() and 'switch' not in d.device_type.lower()]
        if non_switch_devices:
            QMessageBox.warning(
                self,
                "警告",
                f"以下设备不是交换机，无法执行MAC-IP查询：\n{', '.join(non_switch_devices)}"
            )
            return

        # 弹出输入对话框
        mac_or_ip, ok = QInputDialog.getText(
            self,
            "输入MAC或IP",
            "请输入要查询的MAC地址或IP地址：",
            QLineEdit.Normal
        )

        if ok and mac_or_ip:
            # 启动MAC-IP查询操作
            self._start_operation(MacIpNewThread, "查询MAC-IP", mac_or_ip=mac_or_ip)

    def _start_operation(self, thread_class: Type[BaseOperationThread], operation_name: str, **kwargs) -> None:
        """启动操作的通用方法"""
        logging.info(f"开始执行操作: {operation_name}")

        # +++ 新增：清空所有设备状态 +++
        self.parent().clear_all_status()  # 调用父窗口的清空方法

        devices = self._get_selected_devices()
        if devices:
            logging.info(f"获取到设备: {len(devices)}个")
            # 创建并设置线程
            self.current_thread = thread_class()

            # 根据是否有额外参数调用setup
            if operation_name == "查询MAC-IP" and 'mac_or_ip' in kwargs:
                self.current_thread.setup(devices, self.parent().update_device_status, mac_or_ip=kwargs['mac_or_ip'])
            else:
                self.current_thread.setup(devices, self.parent().update_device_status)

            # 添加到线程管理器
            thread_type = thread_class.__name__.replace('Thread', '').lower()
            # 特殊处理DeviceInspectionThread
            if thread_type == "deviceinspection":
                thread_type = "deviceinspection"
            logging.info(f"线程类型: {thread_type}")

            try:
                thread_manager = self.parent().thread_manager
                # 使用统一的add_thread方法
                thread_manager.add_thread(
                    thread_type,
                    self.current_thread,
                    lambda results, start_time: self.parent().show_result_dialog(operation_name, results, start_time)
                )
                logging.info("线程已添加到管理器")

                self.current_thread.start()
                logging.info("线程已启动")
                self.accept()
            except Exception as e:
                logging.error(f"执行操作时出错: {str(e)}")
                raise

    def on_send_command(self) -> None:
        """发送命令按钮点击事件"""
        devices = self._get_selected_devices()
        if not devices:
            return

        # 显示命令输入对话框
        command_dialog = CommandDialog(self)
        if command_dialog.exec() == QDialog.Accepted:
            command, mode, use_timing = command_dialog.get_command()
            if command:
                # 创建并设置命令线程
                self.current_thread = CommandThread()
                self.current_thread.setup(devices, command, mode, use_timing, self.parent().update_device_status)
                # 添加到线程管理器，使用统一的add_thread方法
                self.parent().thread_manager.add_thread(
                    'command',
                    self.current_thread,
                    lambda results, start_time: self.parent().show_result_dialog("命令执行", results, start_time)
                )
                self.current_thread.start()
                # 关闭操作对话框
                self.accept()

    def _on_firewall_address_group_clicked(self) -> None:
        """处理防火墙地址组管理按钮点击"""
        devices = self._get_selected_devices()
        if not devices:
            return

        # 检查设备类型是否支持防火墙功能
        supported_platforms = ["huawei", "hp_comware"]
        unsupported_devices = []

        for device in devices:
            if device.platform not in supported_platforms:
                unsupported_devices.append(f"{device.name} ({device.platform})")

        if unsupported_devices:
            QMessageBox.warning(
                self,
                "设备类型不支持",
                f"以下设备不支持防火墙地址组管理功能：\n\n" +
                "\n".join(unsupported_devices) +
                f"\n\n支持的设备类型：{', '.join(supported_platforms)}"
            )
            return

        # 显示防火墙地址组管理对话框
        address_group_dialog = FirewallAddressGroupDialog(self)
        address_group_dialog.operation_requested.connect(
            lambda op_type, ip_list, group_name: self._start_firewall_address_group_operation(
                devices, op_type, ip_list, group_name
            )
        )
        address_group_dialog.exec()

    def _start_firewall_address_group_operation(self, devices: List[Any], operation_type: str,
                                              ip_addresses: List[str], group_name: str) -> None:
        """启动防火墙地址组操作"""
        try:
            # 创建防火墙地址组线程
            self.current_thread = FirewallAddressGroupThread()
            self.current_thread.setup(
                devices,
                operation_type,
                ip_addresses,
                group_name,
                self.parent().update_device_status
            )

            # 添加到线程管理器
            operation_name = f"防火墙地址组{'添加' if operation_type == 'add' else '删除'}"
            self.parent().thread_manager.add_thread(
                'firewall_address_group',
                self.current_thread,
                lambda results, start_time: self.parent().show_result_dialog(operation_name, results, start_time)
            )

            self.current_thread.start()

            # 关闭操作对话框
            self.accept()

        except Exception as e:
            logger.error(f"启动防火墙地址组操作失败: {str(e)}")
            QMessageBox.critical(self, "操作失败", f"启动防火墙地址组操作失败：\n{str(e)}")

    def _get_selected_devices(self) -> List[Any]:
        """获取选中的设备数据"""
        devices = []
        for name in self.device_names:
            device = self.device_manager.get_device_by_name(name)
            if device:
                devices.append(device)
        return devices

    def closeEvent(self, event: Any) -> None:
        """对话框关闭事件"""
        try:
            # 停止当前运行的线程
            if hasattr(self, 'current_thread') and self.current_thread:
                logger.info("检测到运行中的线程")
                try:
                    if self.current_thread.isRunning():
                        logger.info("正在停止运行中的线程...")
                        self.current_thread.stop()
                        if not self.current_thread.wait(5000):  # 等待最多5秒
                            logger.warning("线程未能在5秒内停止")
                    self.current_thread.deleteLater()  # 安全删除线程对象
                except RuntimeError as e:
                    logger.error(f"线程操作失败: {str(e)}")
                except Exception as e:
                    logger.error(f"处理线程时出错: {str(e)}")
                finally:
                    self.current_thread = None
        except Exception as e:
            logger.error(f"关闭对话框时出错: {str(e)}")
        finally:
            event.accept()