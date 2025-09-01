import os
import subprocess
import sys
import logging

logger = logging.getLogger(__name__)

class FileHandler:
    """文件处理工具类"""
    
    @staticmethod
    def open_file(file_path):
        """打开文件"""
        try:
            if os.path.exists(file_path):
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                else:  # macOS/Linux
                    subprocess.run(['open', file_path] if sys.platform == 'darwin' else ['xdg-open', file_path])
                return True
        except Exception as e:
            logger.error(f"打开文件失败: {str(e)}")
            return False
        return False
