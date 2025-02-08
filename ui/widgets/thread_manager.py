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
    MacIpThread
)
from core.nornir_manager.operations.dnat_query import DnatQuery

ThreadType = Union[TestThread, BackupThread, DiffThread, CommandThread, SaveThread, DnatThread, InterfaceThread, MacIpThread]

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
            'macip': []
        }
        
    def add_thread(self, thread_type: str, thread: ThreadType, result_callback: Callable):
        """统一的添加线程方法"""
        self.threads[thread_type].append(thread)
        thread.finished.connect(result_callback)
        thread.finished.connect(lambda *args: self._on_thread_finished(thread_type, thread))
        
    def add_test_thread(self, thread: TestThread, result_callback: Callable):
        """添加测试线程"""
        self.add_thread('test', thread, result_callback)
        
    def add_backup_thread(self, thread: BackupThread, result_callback: Callable):
        """添加备份线程"""
        self.add_thread('backup', thread, result_callback)
        
    def add_diff_thread(self, thread: DiffThread, result_callback: Callable):
        """添加对比线程"""
        self.add_thread('diff', thread, result_callback)
        
    def add_command_thread(self, thread: CommandThread, result_callback: Callable):
        """添加命令线程"""
        self.add_thread('command', thread, result_callback)
        
    def add_save_thread(self, thread: SaveThread, result_callback: Callable):
        """添加保存线程"""
        self.add_thread('save', thread, result_callback)
        
    def add_dnat_thread(self, thread: DnatQuery, result_callback: Callable):
        """添加 DNAT 查询线程"""
        self.add_thread('dnat', thread, result_callback)
        
    def add_interface_thread(self, thread: InterfaceThread, result_callback: Callable):
        """添加接口查询线程"""
        self.add_thread('interface', thread, result_callback)

    def add_macip_thread(self, thread: MacIpThread, result_callback: Callable):
        """添加MAC-IP查询线程"""
        self.add_thread('macip', thread, result_callback)
        
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
        self.threads['dnat'].clear()
        self.threads['interface'].clear()
        self.threads['macip'].clear() 