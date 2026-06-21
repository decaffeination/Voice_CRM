"""多轮 Memory HTTP 验收（需服务 + llm.api_key）。

pytest 等价: integration/test_memory_multiturn.py

用法:
  python -m main_server.api.main
  python tests/live/scripts/http_memory_multiturn.py
  python tests/live/scripts/http_memory_multiturn.py --session-id <id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _http_common import chat, create_session, login


def main() -> None:
    parser = argparse.ArgumentParser(description="多轮 Memory HTTP 验收")
    parser.add_argument("--session-id", help="重启后继续同一会话")
    parser.add_argument("--only", help="只发一条消息")
    args = parser.parse_args()

    print("登录...")
    token = login()
    session_id = args.session_id or create_session(token, "Memory验收")
    if args.session_id:
        print(f"使用已有 session_id: {session_id}")
    else:
        print(f"新建 session_id: {session_id}")

    if args.only:
        messages = [args.only]
    elif args.session_id and not args.only:
        messages = ["合同金额呢"]
        print("\n（重启验证：仅发送「合同金额呢」）")
    else:
        messages = ["查一下测试科技联系方式", "合同金额呢"]

    for message in messages:
        result = chat(token, session_id, message)
        print(f"\n用户: {message}")
        print(f"intent: {result.get('intent')}")
        print(f"助手: {result.get('reply')}")

    print("\n重启后继续:")
    print(f"  python tests/live/scripts/http_memory_multiturn.py --session-id {session_id}")


if __name__ == "__main__":
    main()
