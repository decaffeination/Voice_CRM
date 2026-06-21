"""日志验收：先跑 pytest 离线用例，可选对已启动服务做 HTTP 抽检。

pytest 等价: unit/core/test_logger.py

用法:
  python tests/live/scripts/logger_check.py
  python tests/live/scripts/logger_check.py --http
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

RUN_TAG = uuid.uuid4().hex[:8]


def run_http_smoke() -> None:
    from _http_common import chat, create_session, login

    token = login()
    sid = create_session(token, f"logger-http-{RUN_TAG}")
    result = chat(token, sid, f"你好 logger-{RUN_TAG}")
    print("chat reply:", result.get("reply"))
    print("[OK] 请查看 main_server/data/logs/app.log 中的 http.request / api.chat")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true")
    args = parser.parse_args()

    print("运行 pytest tests/unit/core/test_logger.py ...")
    code = subprocess.call(
        [sys.executable, "-m", "pytest", "tests/unit/core/test_logger.py", "-v"],
        cwd=str(PROJECT_ROOT),
    )
    if code != 0:
        raise SystemExit(code)

    if args.http:
        run_http_smoke()


if __name__ == "__main__":
    main()
