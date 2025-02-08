import os
import shutil
import sys
import glob
import subprocess

def clean_build_files():
    """清理构建文件"""
    print("\n🧹 清理构建文件...")
    
    # 清理目录
    for dir_name in ['dist', 'build', '__pycache__']:
        if os.path.exists(dir_name):
            print(f"   删除目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理spec文件
    for spec_file in glob.glob('*.spec'):
        print(f"   删除文件: {spec_file}")
        os.remove(spec_file)
    
    # 清理所有 __pycache__ 目录
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            cache_dir = os.path.join(root, '__pycache__')
            print(f"   删除缓存: {cache_dir}")
            shutil.rmtree(cache_dir)

def install_requirements():
    """安装必要的依赖"""
    print("检查依赖...")
    
    # 获取已安装的包列表
    installed_packages = subprocess.check_output([
        sys.executable, 
        "-m", 
        "pip", 
        "list"
    ]).decode().split('\n')
    
    installed_packages = {
        line.split()[0].lower(): line.split()[1] 
        for line in installed_packages[2:] 
        if len(line.split()) >= 2
    }
    
    # 从requirements.txt读取依赖
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip()]
    
    # 添加构建所需的额外依赖
    requirements.append("pyinstaller")
    
    # 只安装缺失的包
    for req in requirements:
        req_lower = req.lower()
        if req_lower not in installed_packages:
            print(f"正在安装 {req}...")
            subprocess.check_call([
                sys.executable, 
                "-m", 
                "pip", 
                "install",
                "-i", 
                "https://pypi.tuna.tsinghua.edu.cn/simple",
                req
            ])
        else:
            print(f"{req} 已安装 (版本: {installed_packages[req_lower]})")

def verify_and_convert_icon():
    """验证图标文件"""
    # 确保assets目录存在
    assets_dir = 'assets'
    os.makedirs(assets_dir, exist_ok=True)
    
    # 只检查ico文件
    ico_path = os.path.join(assets_dir, 'icon.ico')
    
    if not os.path.exists(ico_path):
        print(f"错误: 图标文件不存在: {ico_path}")
        sys.exit(1)
        
    return ico_path

def build_exe():
    # 确保安装了依赖
    install_requirements()
    
    # 导入 PyInstaller
    import PyInstaller.__main__
    
    # 清理旧的release目录
    if os.path.exists('release'):
        shutil.rmtree('release')
    
    # PyInstaller 配置
    PyInstaller.__main__.run([
        'main.py',  # 主程序文件
        '--name=nornir_gui',  # 英文名称
        '--windowed',  # 无控制台窗口
        '--noconfirm',  # 覆盖现有文件
        '--clean',  # 清理临时文件
        '--onefile',  # 生成单个exe文件
        f'--icon={verify_and_convert_icon()}',  # 添加图标
        '--exclude-module=PyQt5',
        '--exclude-module=PySide2',
        # 添加资源文件
        '--add-data=assets;assets',  # 添加assets目录
        # 添加核心模板文件
        '--add-data=core/nornir_manager/templates;core/nornir_manager/templates',  # 添加模板文件
        # 添加依赖包
        '--collect-all=nornir',
        '--collect-all=nornir_netmiko',
        '--collect-all=nornir_utils',
        '--collect-all=netmiko',
        '--collect-all=ntc_templates',
        # 显式导入关键模块
        '--hidden-import=nornir.plugins.runners.threaded',
        '--hidden-import=nornir.plugins.inventory.simple',
        '--hidden-import=nornir_netmiko.tasks',
        # PySide6相关
        '--hidden-import=PySide6',
        '--hidden-import=PySide6.QtWidgets',
        '--hidden-import=PySide6.QtCore',
        '--hidden-import=PySide6.QtGui',
        # 其他依赖
        '--hidden-import=openpyxl',
        '--hidden-import=pandas',
        '--hidden-import=jinja2',
        '--hidden-import=textfsm',
        '--hidden-import=netmiko',
        '--hidden-import=paramiko',
        '--hidden-import=socks',
        '--hidden-import=yaml',
        '--hidden-import=sqlalchemy',
        '--hidden-import=natsort',
        # 添加 nornir 相关目录
        '--add-data={};{}'.format(
            os.path.join(sys.prefix, 'Lib', 'site-packages', 'nornir', 'plugins'),
            'nornir/plugins'
        ),
        '--add-data={};{}'.format(
            os.path.join(sys.prefix, 'Lib', 'site-packages', 'nornir_netmiko'),
            'nornir_netmiko'
        ),
        '--add-data={};{}'.format(
            os.path.join(sys.prefix, 'Lib', 'site-packages', 'nornir_utils', 'plugins'),
            'nornir_utils/plugins'
        ),
        '--hidden-import=logging',
        '--hidden-import=logging.handlers',
        '--hidden-import=codecs',
        '--hidden-import=logging.config',
        '--hidden-import=core.utils.logger',
        '--hidden-import=sqlalchemy.ext',
    ])
    
    # 创建发布目录
    release_dir = 'release'
    os.makedirs(release_dir, exist_ok=True)
    
    exe_name = 'nornir_gui.exe'
    src_path = os.path.join('dist', exe_name)
    
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"生成文件 {src_path} 不存在，请检查构建日志")
    
    shutil.copy2(src_path, release_dir)
    
    # 清理构建文件
    clean_build_files()
    
    print("\n🎉 构建完成！发布包在 release 目录中")

if __name__ == '__main__':
    build_exe()