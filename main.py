#!/usr/bin/env python3
"""统一启动脚本：先启动后端，再启动前端"""

import subprocess
import sys
import time
import signal
import os
import webbrowser
from pathlib import Path
from typing import Optional


# 颜色输出
class Colors:
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def print_colored(message: str, color: str = Colors.NC):
    """打印带颜色的消息"""
    print(f"{color}{message}{Colors.NC}")


def check_port(port: int, timeout: int = 30) -> bool:
    """检查端口是否可用（服务是否启动）"""
    import socket

    for _ in range(timeout):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_backend(project_root: Path) -> Optional[subprocess.Popen]:
    """启动后端服务"""
    print_colored("正在启动后端 API 服务...", Colors.GREEN)

    # 后端在 backend 目录下
    backend_dir = project_root / "backend"
    if not backend_dir.exists():
        print_colored(f"错误：后端目录不存在: {backend_dir}", Colors.RED)
        return None

    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)

    try:
        # 使用 uv 运行后端（让输出直接显示在终端）
        process = subprocess.Popen(
            ["uv", "run", "python", "-m", "src.api.main"],
            cwd=str(backend_dir),
            env=env,
        )

        # 等待后端服务启动
        print_colored("等待后端服务启动...", Colors.YELLOW)
        if check_port(8000, timeout=30):
            print_colored(f"后端服务已启动 (PID: {process.pid})", Colors.GREEN)
            return process
        else:
            print_colored("后端服务启动超时，请检查上面的错误信息", Colors.RED)
            process.terminate()
            process.wait(timeout=5)
            return None
    except FileNotFoundError:
        print_colored("错误：未找到 uv 命令，请确保已安装 uv", Colors.RED)
        return None
    except Exception as e:
        print_colored(f"启动后端时发生错误: {e}", Colors.RED)
        return None


def start_frontend(project_root: Path) -> Optional[subprocess.Popen]:
    """启动前端服务"""
    print_colored("正在启动前端开发服务器...", Colors.GREEN)

    frontend_dir = project_root / "frontend"
    if not frontend_dir.exists():
        print_colored(f"错误：前端目录不存在: {frontend_dir}", Colors.RED)
        return None

    # 检查 package.json 是否存在
    if not (frontend_dir / "package.json").exists():
        print_colored("错误：前端 package.json 不存在", Colors.RED)
        return None

    try:
        # 检查是否有 node_modules
        if not (frontend_dir / "node_modules").exists():
            print_colored(
                "警告：未检测到 node_modules，需要先运行 'cd frontend && npm install'",
                Colors.YELLOW,
            )
            print_colored("正在自动安装依赖...", Colors.YELLOW)
            npm_install = subprocess.run(
                ["npm", "install"], cwd=str(frontend_dir), capture_output=False
            )
            if npm_install.returncode != 0:
                print_colored("npm install 失败", Colors.RED)
                return None

        # 使用 npm 启动前端（让输出直接显示在终端）
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
        )

        # 等待前端服务启动
        print_colored("等待前端服务启动...", Colors.YELLOW)
        time.sleep(5)  # 给前端更多启动时间

        if check_port(5173, timeout=15):
            print_colored(f"前端服务已启动 (PID: {process.pid})", Colors.GREEN)
            return process
        else:
            print_colored("前端服务可能未正常启动，请检查上面的输出信息", Colors.YELLOW)
            return process
    except FileNotFoundError:
        print_colored("错误：未找到 npm 命令，请确保已安装 Node.js", Colors.RED)
        return None
    except Exception as e:
        print_colored(f"启动前端时发生错误: {e}", Colors.RED)
        return None


def cleanup_processes(
    backend_process: Optional[subprocess.Popen],
    frontend_process: Optional[subprocess.Popen],
):
    """清理所有进程"""
    print_colored("\n正在关闭服务...", Colors.YELLOW)

    if frontend_process:
        try:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
            print_colored("前端服务已关闭", Colors.GREEN)
        except subprocess.TimeoutExpired:
            frontend_process.kill()
            print_colored("前端服务已强制关闭", Colors.YELLOW)
        except Exception as e:
            print_colored(f"关闭前端服务时出错: {e}", Colors.RED)

    if backend_process:
        try:
            backend_process.terminate()
            backend_process.wait(timeout=5)
            print_colored("后端服务已关闭", Colors.GREEN)
        except subprocess.TimeoutExpired:
            backend_process.kill()
            print_colored("后端服务已强制关闭", Colors.YELLOW)
        except Exception as e:
            print_colored(f"关闭后端服务时出错: {e}", Colors.RED)


def main():
    """主函数"""
    # 获取项目根目录
    project_root = Path(__file__).parent.absolute()

    # 切换到项目根目录
    os.chdir(project_root)

    backend_process = None
    frontend_process = None

    # 注册信号处理函数
    def signal_handler(sig, frame):
        cleanup_processes(backend_process, frontend_process)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 启动后端
        backend_process = start_backend(project_root)
        if not backend_process:
            print_colored("后端启动失败，退出", Colors.RED)
            return 1

        # 启动前端
        frontend_process = start_frontend(project_root)
        if not frontend_process:
            print_colored("前端启动失败，清理后端进程", Colors.RED)
            cleanup_processes(backend_process, None)
            return 1

        # 显示成功信息
        print_colored("\n" + "=" * 40, Colors.GREEN)
        print_colored("服务启动成功！", Colors.GREEN)
        print_colored("=" * 40, Colors.GREEN)
        print_colored("后端 API: http://localhost:8000", Colors.BLUE)
        print_colored("前端应用: http://localhost:5173", Colors.BLUE)
        print_colored("\n按 Ctrl+C 停止所有服务\n", Colors.YELLOW)

        webbrowser.open("http://localhost:5173")

        # 等待进程结束（实际上会一直运行，直到收到信号）
        try:
            # 等待任一进程结束
            while True:
                if backend_process.poll() is not None:
                    print_colored("后端进程意外退出", Colors.RED)
                    break
                if frontend_process.poll() is not None:
                    print_colored("前端进程意外退出", Colors.RED)
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        return 0

    except Exception as e:
        print_colored(f"发生未预期的错误: {e}", Colors.RED)
        cleanup_processes(backend_process, frontend_process)
        return 1
    finally:
        cleanup_processes(backend_process, frontend_process)


if __name__ == "__main__":
    sys.exit(main())
