# 标准库导入
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

def clean_build_files() -> None:
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
    for root, _, _ in os.walk('.'):
        cache_dir = Path(root) / '__pycache__'
        if cache_dir.exists():
            print(f"   删除缓存: {cache_dir}")
            shutil.rmtree(cache_dir)

def parse_requirement(req_str):
    """解析需求字符串，分离包名和版本信息"""
    parts = req_str.split('==')
    if len(parts) > 1:
        return parts[0].lower(), parts[1]
    return req_str.lower(), None

def get_installed_packages() -> Dict[str, str]:
    """获取已安装的包列表"""
    output = subprocess.check_output([
        sys.executable, 
        "-m", 
        "pip", 
        "list"
    ]).decode().split('\n')
    
    return {
        line.split()[0].lower(): line.split()[1] 
        for line in output[2:] 
        if len(line.split()) >= 2
    }

def install_package(package: str) -> None:
    """安装指定的包"""
    print(f"正在安装 {package}...")
    subprocess.check_call([
        sys.executable, 
        "-m", 
        "pip", 
        "install",
        "-i", 
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        package
    ])

def install_requirements() -> None:
    """安装必要的依赖"""
    print("检查依赖...")
    
    # 获取已安装的包列表
    installed_packages = get_installed_packages()
    
    # 从requirements.txt读取依赖
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip()]
    
    # 添加构建所需的额外依赖
    requirements.append("pyinstaller")
    
    # 检查并安装/更新每个依赖
    for req in requirements:
        pkg_name, pkg_version = parse_requirement(req)
        
        if pkg_name not in installed_packages:
            # 包不存在，安装它
            install_package(req)
        elif pkg_version and installed_packages[pkg_name] != pkg_version:
            # 版本不匹配，更新到指定版本
            print(f"{pkg_name} 版本不匹配 (当前: {installed_packages[pkg_name]}, 需要: {pkg_version})")
            install_package(req)
        else:
            print(f"{pkg_name} 已安装 (版本: {installed_packages[pkg_name]})")

def verify_and_convert_icon() -> str:
    """验证图标文件并返回路径"""
    # 确保assets目录存在
    assets_dir = Path('assets')
    assets_dir.mkdir(exist_ok=True)
    
    # 只检查ico文件
    ico_path = assets_dir / 'icon.ico'
    
    if not ico_path.exists():
        print(f"错误: 图标文件不存在: {ico_path}")
        sys.exit(1)
        
    return str(ico_path)

def get_pyinstaller_args() -> List[str]:
    """获取 PyInstaller 参数列表"""
    site_packages = Path(sys.prefix) / 'Lib' / 'site-packages'
    
    return [
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
        '--add-data=core/nornir_manager/templates;core/nornir_manager/templates',
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
        f'--add-data={site_packages}/nornir/plugins;nornir/plugins',
        f'--add-data={site_packages}/nornir_netmiko;nornir_netmiko',
        f'--add-data={site_packages}/nornir_utils/plugins;nornir_utils/plugins',
        # 其他导入
        '--hidden-import=logging',
        '--hidden-import=logging.handlers',
        '--hidden-import=codecs',
        '--hidden-import=logging.config',
        '--hidden-import=core.utils.logger',
        '--hidden-import=sqlalchemy.ext',
    ]

def copy_to_release(exe_name: str) -> None:
    """复制文件到发布目录"""
    release_dir = Path('release')
    release_dir.mkdir(exist_ok=True)
    
    src_path = Path('dist') / exe_name
    
    if not src_path.exists():
        raise FileNotFoundError(f"生成文件 {src_path} 不存在，请检查构建日志")
    
    shutil.copy2(src_path, release_dir)

def publish_to_github(version):
    """将构建好的文件发布到GitHub"""
    print("\n🚀 发布到GitHub...")
    
    # 确保release目录中有可执行文件
    exe_path = Path('release') / 'nornir_gui.exe'
    if not exe_path.exists():
        print("错误: 找不到要发布的可执行文件")
        return False
    
    try:
        # 创建版本标签
        subprocess.run(["git", "tag", version])
        subprocess.run(["git", "push", "origin", version])
        
        # 使用gh cli创建release
        subprocess.run([
            "gh", "release", "create", version,
            "--title", f"Nornir GUI {version}",
            "--notes", f"Nornir GUI {version} 发布版本",
            str(exe_path)
        ])
        
        print(f"✅ 成功发布 {version} 到GitHub")
        return True
    except Exception as e:
        print(f"❌ 发布失败: {str(e)}")
        return False

def build_exe() -> None:
    """构建可执行文件"""
    # 确保安装了依赖
    install_requirements()
    
    # 清理旧的release目录
    if os.path.exists('release'):
        shutil.rmtree('release')
    
    # 运行 PyInstaller
    try:
        # pylint: disable=import-outside-toplevel
        import PyInstaller.__main__
        PyInstaller.__main__.run(get_pyinstaller_args())
    except ImportError:
        print("错误: 未能导入 PyInstaller，请确保已正确安装")
        sys.exit(1)
    
    # 复制到发布目录
    copy_to_release('nornir_gui.exe')
    
    # 清理构建文件
    clean_build_files()
    
    print("\n🎉 构建完成！发布包在 release 目录中")
    
    # 询问是否发布
    response = input("\n是否发布到GitHub? (y/n): ")
    if response.lower() == 'y':
        version = input("输入版本号 (例如 v1.0.0): ")
        publish_to_github(version)

if __name__ == '__main__':
    build_exe()
