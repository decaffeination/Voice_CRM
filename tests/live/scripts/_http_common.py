"""live HTTP 验收脚本公共模块。"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "admin"
PASSWORD = "admin123"


def json_request(
    method: str,
    path: str,
    token: str | None = None,
    body: dict | None = None,
    timeout: float = 120,
) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {detail}") from exc


def login() -> str:
    return json_request(
        "POST",
        "/api/auth/login",
        body={"username": USERNAME, "password": PASSWORD},
    )["access_token"]


def create_session(token: str, title: str) -> str:
    return json_request(
        "POST",
        "/api/session",
        token=token,
        body={"title": title},
    )["session"]["session_id"]


def chat(token: str, session_id: str, message: str) -> dict:
    return json_request(
        "POST",
        "/api/chat",
        token=token,
        body={"message": message, "session_id": session_id, "with_audio": False},
    )
