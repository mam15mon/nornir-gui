from PySide6.QtCore import QObject, Signal
from typing import List, Callable, Dict, Union
from datetime import datetime

from core.nornir_manager.threads import (
    TestThread,
    BackupThread,
    DiffThread,
    CommandThread,
    SaveThread,
    DnatThread,
    InterfaceThread,
    MacIpNewThread,
    DeviceInspectionThread,
    FirewallAddressGroupThread
)
from core.nornir_manager.operations.dnat_query import DnatQuery

ThreadType = Union[TestThread, BackupThread, DiffThread, CommandThread, SaveThread, DnatThread, InterfaceThread, MacIpNewThread, DeviceInspectionThread, FirewallAddressGroupThread]

class ThreadManager(QObject):
    """线程管理器，用于管理所有操作线程"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用字典统一管理所有类型的线程
        self.threads: Dict[str, List[ThreadType]] = {
            'test': [],
            'backup': [],
            'diff': [],
            'command': [],
            'save': [],
            'dnat': [],
            'interface': [],
            'macip': [],
            'macipnew': [],
            'deviceinspection': [],
            'firewall_address_group': []
        }

    def add_thread(self, thread_type: str, thread: ThreadType, result_callback: Callable):
        """
        统一的添加线程方法

        Args:
            thread_type: 线程类型，必须是 self.threads 中的一个键
            thread: 要添加的线程实例
            result_callback: 线程完成时的回调函数
        """
        if thread_type not in self.threads:
            raise ValueError(f"不支持的线程类型: {thread_type}")

        self.threads[thread_type].append(thread)
        thread.finished.connect(result_callback)
        thread.finished.connect(lambda *args: self._on_thread_finished(thread_type, thread))

    def stop_all_threads(self):
        """停止所有线程"""
        for threads in self.threads.values():
            for thread in threads:
                if thread.isRunning():
                    thread.stop()

    def has_running_threads(self) -> bool:
        """检查是否有正在运行的线程"""
        return any(thread.isRunning()
                  for threads in self.threads.values()
                  for thread in threads)

    def _on_thread_finished(self, thread_type: str, thread: ThreadType):
        """统一的线程完成处理"""
        self.threads[thread_type].remove(thread)
        thread.deleteLater()

    def cleanup(self):
        """清理所有线程"""
        self.stop_all_threads()
        for threads in self.threads.values():
            for thread in threads:
                if thread.isRunning():
                    thread.wait()
            threads.clear()  # 清理所有类型的线程列表