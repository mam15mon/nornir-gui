from typing import List, Dict
import logging
import os
from PySide6.QtCore import QObject, Signal
from nornir_netmiko.tasks import netmiko_send_command, netmiko_send_config, netmiko_multiline
from ..base.nornir_manager import NornirManager
from core.db.database import Database
from core.db.models import Settings
from nornir.core.task import Result
from PySide6.QtCore import QUrl

logger = logging.getLogger(__name__)

class CommandSender(QObject):
    """命令发送操作类"""
    
    # 定义信号
    status_changed = Signal(str, str)  # (device_name, status)
    progress_updated = Signal(int, int)  # (current, total)
    operation_finished = Signal(bool)  # success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.nornir_mgr = NornirManager()
        self.results = {}  # 存储执行结果
        self.db = Database()
        
        try:
            # 获取基础路径
            with Database().get_session() as session:
                settings = session.query(Settings).first()
                if settings and settings.config_base_path:
                    self.base_path = settings.config_base_path
                else:
                    # 如果没有设置或数据库未初始化，使用默认路径
                    self.base_path = os.path.join(os.getcwd(), "配置文件")
                    # 创建默认设置
                    if not settings:
                        new_settings = Settings(config_base_path=self.base_path)
                        session.add(new_settings)
                        session.commit()
        except Exception as e:
            logger.warning(f"数据库初始化失败，使用默认配置: {str(e)}")
            self.base_path = os.path.join(os.getcwd(), "配置文件")
            
        # 创建命令回显目录
        self.output_path = os.path.join(self.base_path, "命令回显")
        os.makedirs(self.output_path, exist_ok=True)
        
    def send_command(self, task, command: str, mode: str, use_timing: bool = False) -> Result:
        """发送命令到设备"""
        if not self.is_running:
            return Result(
                host=task.host,
                result="任务已停止",
                failed=True
            )
        
        try:
            device = task.host
            device_name = device.name
            site = device.data.get('site', "未分类")
            
            logger.info(f"开始执行命令 - 设备: {device_name}, 站点: {site}")
            logger.info(f"命令模式: {mode}")
            logger.info(f"使用timing模式: {use_timing}")
            logger.info(f"执行命令: \n{command}")

            # 更新状态为正在执行
            self.status_changed.emit(device_name, "正在执行命令...")

            # 创建站点输出目录
            site_path = os.path.join(self.output_path, site)
            os.makedirs(site_path, exist_ok=True)
            
            # 根据命令模式创建子目录
            mode_display = {
                "configuration": "配置命令",
                "multiline": "交互命令",
                "netmiko_send_command": "视图命令"
            }
            mode_path = os.path.join(site_path, mode_display.get(mode, "其他命令"))
            os.makedirs(mode_path, exist_ok=True)
            
            output_file = os.path.join(mode_path, f'{device_name}-commands.txt')
            combined_output = []

            # 根据模式选择发送方法
            if mode == "configuration":
                logger.info(f"{device_name} - 使用配置命令模式")
                # 分割命令并过滤空行
                config_commands = [cmd.strip() for cmd in command.split('\n') if cmd.strip()]
                output = task.run(
                    task=netmiko_send_config,
                    config_commands=config_commands,
                    name=f"send_config_to_{device_name}"
                )
                # 写入命令和输出
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"配置命令执行:\n")
                    f.write(f"命令列表:\n")
                    for cmd in config_commands:
                        f.write(f"  {cmd}\n")
                    f.write("\n执行输出:\n")
                    f.write(str(output.result))
                
                combined_output = [
                    "配置命令执行结果:",
                    "执行的命令:",
                    *[f"  {cmd}" for cmd in config_commands],
                    "",
                    "命令输出:",
                    str(output.result)
                ]
                
            elif mode == "multiline":
                logger.info(f"{device_name} - 使用交互命令模式")
                command_list = []
                
                # 改进命令解析
                for line in command.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    if use_timing:
                        # timing模式下直接使用命令
                        command_list.append(line)
                    else:
                        # 非timing模式需要处理期望响应
                        parts = line.split('|', 1)
                        cmd = parts[0].strip()
                        expect = parts[1].strip() if len(parts) > 1 else r"[#>]"
                        command_list.append([cmd, expect])
                
                logger.debug(f"处理后的命令列表: {command_list}")
                
                try:
                    # 根据timing模式决定如何传递命令
                    output = task.run(
                        task=netmiko_multiline,
                        commands=command_list,
                        use_timing=use_timing,
                        last_read=8,
                        read_timeout=0,
                        name=f"send_multiline_to_{device_name}",
                    )
                    
                    # 改进输出文件格式
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write("=== 交互命令执行 ===\n\n")
                        f.write("执行的命令序列:\n")
                        for i, cmd in enumerate(command_list, 1):
                            f.write(f"{i}. 命令: {cmd}\n")
                        f.write("\n=== 执行输出 ===\n")
                        f.write(str(output.result))
                    
                    # 优化结果显示
                    combined_output = [
                        "交互命令执行结果:",
                        f"输出文件: <a href='{QUrl.fromLocalFile(output_file).toString()}'>{os.path.basename(output_file)}</a>",
                        "\n执行的命令序列:"
                    ]
                    for i, cmd in enumerate(command_list, 1):
                        combined_output.append(f"{i}. {cmd}")
                    combined_output.extend(["\n命令输出:", str(output.result)])
                    
                    return Result(
                        host=task.host,
                        result=(True, "\n".join(combined_output), output_file)
                    )
                    
                except Exception as e:
                    error_msg = f"交互命令执行失败: {str(e)}"
                    logger.error(f"{device_name} - {error_msg}")
                    raise Exception(error_msg)
                
            else:  # netmiko_send_command
                logger.info(f"{device_name} - 使用视图命令模式")
                # 分割多行命令
                commands = [cmd.strip() for cmd in command.split('\n') if cmd.strip()]
                all_outputs = []
                
                # 逐条执行命令
                for cmd in commands:
                    output = task.run(
                        task=netmiko_send_command,
                        command_string=cmd,
                        use_timing=use_timing,
                        name=f"send_command_to_{device_name}"
                    )
                    all_outputs.append((cmd, str(output.result)))
                
                # 写入命令和输出
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"视图命令执行:\n")
                    for cmd, out in all_outputs:
                        f.write(f"\n命令:\n{cmd}\n")
                        f.write(f"输出:\n{out}\n")
                        f.write("-" * 50 + "\n")
                
                combined_output = [
                    "视图命令执行结果:",
                    f"输出文件: <a href='{QUrl.fromLocalFile(output_file).toString()}'>{os.path.basename(output_file)}</a>",
                    "",
                    "执行的命令:",
                    *[f"  {cmd}" for cmd, _ in all_outputs],
                    "",
                    "命令输出:"
                ]
                
                for cmd, out in all_outputs:
                    combined_output.extend([
                        f"命令: {cmd}",
                        out.rstrip()  # 移除尾部空白字符
                    ])

            return Result(
                host=task.host,
                result=(True, "\n".join(combined_output), output_file)
            )
            
        except Exception as e:
            error_msg = f"命令执行失败: {str(e)}"
            logger.error(f"{device_name} - {error_msg}")
            self.status_changed.emit(device_name, f"失败: {str(e)}")
            return Result(
                host=task.host,
                result=(False, error_msg, None)
            )
            
    def _validate_device(self, device) -> bool:
        """验证设备数据是否完整"""
        required_fields = ['name', 'hostname', 'username', 'password']
        return all(hasattr(device, field) and getattr(device, field) for field in required_fields)
    
    def stop_command(self):
        """停止命令执行"""
        if self.is_running:
            self.is_running = False
            if self.nornir_mgr:
                self.nornir_mgr.close()
            
    def start_command(self, devices: List, command: str, mode: str, use_timing: bool = False):
        """开始执行命令"""
        if self.is_running:
            logger.warning("命令执行器已在运行中")
            return
            
        if not devices:
            logger.error("没有设备需要执行命令")
            self.operation_finished.emit(False)
            return
            
        self.is_running = True
        self.results = {}  # 重置结果
        total = len(devices)
        completed = 0
        logger.info(f"开始在 {total} 个设备上执行命令")
        logger.info(f"命令: {command}")
        logger.info(f"模式: {mode}")
        logger.info(f"使用timing模式: {use_timing}")
        
        try:
            # 验证设备数据
            for device in devices:
                if not self._validate_device(device):
                    name = getattr(device, 'name', 'Unknown')
                    raise ValueError(f"设备 {name} 数据不完整")
            
            # 使用 NornirManager 初始化
            self.nornir_mgr.init_nornir(devices)
            nr = self.nornir_mgr.get_nornir()
            
            # 执行并行命令
            results = nr.run(
                task=self.send_command,
                command=command,
                mode=mode,
                use_timing=use_timing
            )
            
            # 处理结果
            all_completed = True
            for device_name, result in results.items():
                if not self.is_running:
                    logger.info("命令执行被中止")
                    all_completed = False
                    break
                
                completed += 1
                self.progress_updated.emit(completed, total)
                
                # 统一在这里发送状态更新
                if result.failed:
                    error_msg = f"失败: {str(result.exception)}"
                    self.results[device_name] = {
                        'status': error_msg,
                        'result': str(result.exception),
                        'output_file': None
                    }
                    self.status_changed.emit(device_name, error_msg)
                else:
                    success, output, output_file = result[0].result
                    final_status = "成功: 命令已执行" if success else "失败: 命令执行出错"
                    mode_display = {
                        "configuration": "配置命令",
                        "multiline": "交互命令",
                        "netmiko_send_command": "视图命令"
                    }.get(mode, "命令")
                    status_msg = f"成功: {mode_display}已执行" if success else final_status
                    
                    self.results[device_name] = {
                        'status': status_msg,
                        'result': output,
                        'output_file': output_file
                    }
                    self.status_changed.emit(device_name, status_msg)
                
                # 移除原来的状态更新信号发送
                # self.status_changed.emit(device_name, self.results[device_name]['status'])  # 注释掉这行
            
            # 如果所有设备都执行完成，立即发送结果
            if all_completed and completed == total:
                logger.info("所有设备命令执行完成")
                self.operation_finished.emit(True)
                return
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"执行命令时发生错误: {error_msg}")
            logger.exception("详细错误信息:")
            self.operation_finished.emit(False)
            
        finally:
            self.is_running = False
            self.nornir_mgr.close()  # 确保关闭连接
            logger.info("命令执行操作结束")
    
    def get_results(self) -> dict:
        """获取执行结果
        
        Returns:
            dict: {device_name: {'status': str, 'result': str}} 格式的结果字典
        """
        return self.results 

    def format_overview_content(self, device_name, result):
        """格式化概览内容"""
        status = result.get('status', 'Unknown')
        output_file = result.get('output_file')
        
        content = []
        content.append(f"设备: {device_name}")
        
        # 添加状态，带颜色
        if '成功' in status:
            content.append(f"状态: <span style='color: green;'>{status}</span>")
        else:
            content.append(f"状态: <span style='color: red;'>{status}</span>")
            
        # 如果有输出文件，添加文件链接
        if output_file:
            file_url = QUrl.fromLocalFile(output_file).toString()
            content.append(f"文件: <a href='{file_url}'>{os.path.basename(output_file)}</a>")
            
        content.append("<hr>")
        return "<br>".join(content) 