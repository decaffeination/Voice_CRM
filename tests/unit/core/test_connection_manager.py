"""WebSocket 连接管理单元测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from main_server.api.websocket.connection_manager import ConnectionManager


@pytest.mark.asyncio
async def test_connect_send_disconnect() -> None:
    # 场景：连接池收发；输入：session_id + mock ws；预期：send_json 被调用
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect("session-1", ws, accept=False)
    assert manager.get("session-1") is ws

    await manager.send_json("session-1", {"type": "ping"})
    ws.send_json.assert_called_once_with({"type": "ping"})

    manager.disconnect("session-1")
    assert manager.get("session-1") is None


@pytest.mark.asyncio
async def test_connect_replaces_old_websocket() -> None:
    # 场景：同 session 重连；输入：两个 ws；预期：旧连接 close
    manager = ConnectionManager()
    old_ws = AsyncMock()
    new_ws = AsyncMock()
    await manager.connect("s1", old_ws, accept=False)
    await manager.connect("s1", new_ws, accept=False)
    old_ws.close.assert_called_once()
    assert manager.get("s1") is new_ws
