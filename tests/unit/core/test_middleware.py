"""HTTP 请求上下文中间件测试。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from main_server.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware


class TestRequestContextMiddleware:
    def test_generates_request_id(self) -> None:
        # 场景：无 X-Request-ID；输入：普通请求；预期：响应头含 request_id
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.get("/ping")
        def ping():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert REQUEST_ID_HEADER in resp.headers
        assert resp.headers[REQUEST_ID_HEADER]

    def test_reuses_client_request_id(self) -> None:
        # 场景：客户端传入 request_id；输入：X-Request-ID；预期：原样返回
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.get("/ping")
        def ping():
            return {"ok": True}

        client = TestClient(app)
        custom_id = "client-req-abc"
        resp = client.get("/ping", headers={REQUEST_ID_HEADER: custom_id})
        assert resp.headers[REQUEST_ID_HEADER] == custom_id
