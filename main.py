import sys
import os
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
import locale
from core.utils.logger import setup_logging
from core.db.database import Database

# 添加这一行
logger = logging.getLogger(__name__)

# 设置默认编码
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception as e:
        logger.warning(f"编码重配置失败: {str(e)}")
else:
    try:
        # 处理NoneType情况和旧版本Python
        if sys.stdout and sys.stdout.encoding != 'utf-8':
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except (AttributeError, Exception) as e:
        logger.error(f"编码设置失败: {str(e)}", exc_info=True)

# 设置区域
try:
    locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

def main():
    """程序入口"""
    try:
        # 检查日志目录
        log_dir = os.path.abspath('logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, mode=0o777)
        
        # 初始化日志系统
        setup_logging()
        logger = logging.getLogger(__name__)
        
        # 记录基本系统信息
        logger.info(f"操作系统: {os.name}")
        logger.info(f"当前工作目录: {os.getcwd()}")
        
        # 确保数据库初始化
        db = Database()
        db.ensure_initialized()
        
        app = QApplication(sys.argv)
        
        # 设置应用图标
        icon_path = os.path.join('assets', 'icon.ico')
        if hasattr(sys, '_MEIPASS'):  # 如果是打包后的exe
            icon_path = os.path.join(sys._MEIPASS, 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"程序初始化失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 