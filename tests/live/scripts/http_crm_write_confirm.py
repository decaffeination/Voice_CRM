"""CRM 写库确认流 HTTP 验收（需服务 + llm.api_key）。

pytest 等价: integration/test_crm_mutation.py

用法:
  python tests/live/scripts/http_crm_write_confirm.py
  python tests/live/scripts/http_crm_write_confirm.py --cancel
  python tests/live/scripts/http_crm_write_confirm.py --restart-check --session-id <id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _http_common import chat, create_session, login

WRITE_MESSAGE = (
    "给客户编号1录入：今天签了合同，金额50万，跟进记录：已签约"
)


def run_confirm(token: str, session_id: str) -> None:
    r1 = chat(token, session_id, WRITE_MESSAGE)
    print(f"\n步骤1 助手: {r1.get('reply')}")
    r2 = chat(token, session_id, "确认")
    print(f"步骤2 助手: {r2.get('reply')}")


def run_cancel(token: str, session_id: str) -> None:
    chat(token, session_id, WRITE_MESSAGE)
    r = chat(token, session_id, "取消")
    print(f"取消后助手: {r.get('reply')}")


def run_restart_check(token: str, session_id: str) -> None:
    r = chat(token, session_id, "确认")
    print(f"重启后「确认」: {r.get('reply')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CRM 写库确认 HTTP 验收")
    parser.add_argument("--session-id")
    parser.add_argument("--restart-check", action="store_true")
    parser.add_argument("--cancel", action="store_true")
    args = parser.parse_args()

    token = login()
    if args.restart_check:
        if not args.session_id:
            raise SystemExit("需要 --session-id")
        run_restart_check(token, args.session_id)
        return
    if args.cancel:
        sid = create_session(token, "CRM取消验收")
        run_cancel(token, sid)
        return

    sid = args.session_id or create_session(token, "CRM确认验收")
    run_confirm(token, sid)
    print(
        f"\n重启验证: python tests/live/scripts/http_crm_write_confirm.py "
        f"--restart-check --session-id {sid}"
    )


if __name__ == "__main__":
    main()
