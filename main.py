# 标准库导入
import locale
import logging
import sys
from pathlib import Path

# 第三方库导入
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
except ImportError as e:
    logging.error("无法导入 PySide6: %s", str(e))
    sys.exit(1)

# 本地导入
from ui.main_window import MainWindow
from core.utils.logger import setup_logging
from core.db.database import Database

# 设置日志记录器
logger = logging.getLogger(__name__)
setup_logging()

def init_locale() -> None:
    """初始化本地化设置"""
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error as e:
        logger.error("设置本地化失败: %s", str(e))

def init_database() -> None:
    """初始化数据库"""
    try:
        Database()
    except (ImportError, RuntimeError) as e:
        logger.error("数据库初始化失败: %s", str(e))

def get_app_icon_path() -> Path:
    """获取应用图标路径"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径
        base_path = Path(sys._MEIPASS)  # pylint: disable=protected-access
    else:
        # 开发环境路径
        base_path = Path(__file__).parent

    return base_path / 'assets' / 'icon.ico'

def init_app() -> QApplication:
    """初始化应用程序"""
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    logger.info("正在启动应用程序...")
    logger.info("Python 版本: %s", sys.version)

    # 设置应用程序图标
    try:
        icon_path = get_app_icon_path()
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        else:
            logger.warning("应用图标文件不存在: %s", icon_path)
    except OSError as e:
        logger.error("设置应用图标失败: %s", str(e))

    return app

def main() -> None:
    """主函数"""
    # 初始化
    init_locale()
    init_database()
    app = init_app()

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 
