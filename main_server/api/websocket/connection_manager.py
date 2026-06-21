from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    """WebSocket 连接池。"""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}

    async def connect(
        self,
        session_id: str,
        websocket: WebSocket,
        *,
        accept: bool = True,
    ) -> None:
        if accept:
            await websocket.accept()
        old = self._connections.get(session_id)
        if old is not None:
            try:
                await old.close(code=1000)
            except Exception:
                pass
        self._connections[session_id] = websocket

    def disconnect(self, session_id: str) -> None:
        self._connections.pop(session_id, None)

    def get(self, session_id: str) -> WebSocket | None:
        return self._connections.get(session_id)

    async def send_json(self, session_id: str, data: dict) -> None:
        ws = self._connections.get(session_id)
        if ws is not None:
            await ws.send_json(data)


connection_manager = ConnectionManager()
