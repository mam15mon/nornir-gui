#!/usr/bin/env python3
"""
测试运行脚本
"""
import subprocess
import sys
import os
from pathlib import Path

def run_tests(test_type="all"):
    """运行测试"""
    project_root = Path(__file__).parent
    
    # 设置环境变量
    os.environ['PYTHONPATH'] = str(project_root)
    os.environ['TESTING'] = 'true'
    
    # 构建pytest命令
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "--tb=short",
        "--html=reports/test_report.html",
        "--self-contained-html"
    ]
    
    # 根据测试类型添加参数
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "ui":
        cmd.extend(["-m", "ui"])
    elif test_type == "coverage":
        cmd.extend([
            "--cov=core",
            "--cov=ui",
            "--cov-report=html:reports/coverage",
            "--cov-report=term-missing",
            "--cov-fail-under=70"
        ])
    
    # 创建报告目录
    reports_dir = project_root / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    # 运行测试
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode

if __name__ == "__main__":
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    exit_code = run_tests(test_type)
    sys.exit(exit_code)