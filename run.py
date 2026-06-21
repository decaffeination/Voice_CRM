"""
Voice-CRM 一键启动：同时拉起前端(Vite) + 后端(FastAPI)。

用法（在项目根目录）:
    python run.py                # 前端 + 后端
    python run.py --no-frontend  # 仅后端
    python run.py --backend-only # 仅后端（同上）
"""

from __future__ import annotations

import argparse
import atexit
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web_server"
FRONTEND_PORT = 5173
_frontend_proc: subprocess.Popen | None = None


def _find_npm() -> str | None:
    for name in ("npm.cmd", "npm"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _start_frontend() -> bool:
    global _frontend_proc

    if not WEB_DIR.exists():
        print(f"[前端] 未找到目录 {WEB_DIR}，跳过前端启动")
        return False

    npm = _find_npm()
    if npm is None:
        print("[前端] 未检测到 npm，请先安装 Node.js；本次仅启动后端")
        return False

    if not (WEB_DIR / "node_modules").exists():
        print("[前端] 正在安装依赖 npm install（首次较慢）...")
        subprocess.run([npm, "install"], cwd=str(WEB_DIR), check=True)

    print("[前端] 启动 Vite 开发服务器...")
    _frontend_proc = subprocess.Popen([npm, "run", "dev"], cwd=str(WEB_DIR))
    atexit.register(_stop_frontend)
    return True


def _stop_frontend() -> None:
    global _frontend_proc
    if _frontend_proc is not None and _frontend_proc.poll() is None:
        print("\n[前端] 正在关闭 Vite ...")
        _frontend_proc.terminate()
        try:
            _frontend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _frontend_proc.kill()
    _frontend_proc = None


def _print_banner(host: str, port: int, frontend_on: bool) -> None:
    open_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    line = "=" * 56
    print("\n" + line)
    print("  Voice-CRM 已启动")
    print(line)
    if frontend_on:
        print(f"  浏览器打开:  http://localhost:{FRONTEND_PORT}")
    print(f"  后端 API:    http://{open_host}:{port}")
    print(f"  接口文档:    http://{open_host}:{port}/docs")
    print(f"  默认账号:    admin / admin123")
    print(line + "\n")


def _warn_if_port_busy(port: int, host: str = "127.0.0.1") -> None:
  import socket

  # 尝试绑定目标端口：能绑定说明端口空闲，绑定失败说明已被占用。
  bind_host = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    try:
      sock.bind((bind_host, port))
    except OSError:
      print(
        f"[警告] 端口 {port} 已被占用，请先结束旧进程再启动：\n"
        f"  netstat -ano | findstr :{port}\n"
        f"  taskkill /F /PID <pid>"
      )
      raise SystemExit(1)


def _backend_health_url(port: int, host: str = "127.0.0.1") -> str:
    check_host = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    return f"http://{check_host}:{port}/health"


def _wait_for_backend(url: str, timeout: float = 90.0) -> bool:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    return False


def _start_backend(host: str, port: int) -> subprocess.Popen:
    bind_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    print("[后端] 启动 FastAPI ...")
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main_server.api.main:app",
            "--host",
            bind_host,
            "--port",
            str(port),
        ],
        cwd=str(ROOT),
    )


def _warn_startup_config() -> None:
    from main_server.utils.startup_checks import warn_startup_config

    warn_startup_config()


def main() -> None:
    parser = argparse.ArgumentParser(description="Voice-CRM 启动入口")
    parser.add_argument("--no-frontend", action="store_true", help="只启动后端")
    parser.add_argument("--backend-only", action="store_true", help="只启动后端")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="后端热重载（仅 --no-frontend 时推荐，前后端同启时默认关闭）",
    )
    args = parser.parse_args()

    want_frontend = not (args.no_frontend or args.backend_only)

    _warn_startup_config()

    from main_server.config.settings import get_settings

    settings = get_settings()
    _warn_if_port_busy(settings.app.port, settings.app.host)

    use_reload = args.reload and not want_frontend and settings.app.debug
    if use_reload:
        _print_banner(settings.app.host, settings.app.port, frontend_on=False)
        import uvicorn

        try:
            uvicorn.run(
                "main_server.api.main:app",
                host=settings.app.host,
                port=settings.app.port,
                reload=True,
                reload_dirs=["main_server", "agent"],
            )
        finally:
            _stop_frontend()
        return

    backend_proc = _start_backend(settings.app.host, settings.app.port)
    atexit.register(
        lambda: backend_proc.terminate() if backend_proc.poll() is None else None
    )

    health_url = _backend_health_url(settings.app.port, settings.app.host)
    if not _wait_for_backend(health_url):
        print(f"[后端] 启动超时，请检查日志（{health_url}）")
        backend_proc.kill()
        raise SystemExit(1)

    frontend_on = _start_frontend() if want_frontend else False
    _print_banner(settings.app.host, settings.app.port, frontend_on)

    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        _stop_frontend()
        if backend_proc.poll() is None:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_proc.kill()


if __name__ == "__main__":
    sys.exit(main())
