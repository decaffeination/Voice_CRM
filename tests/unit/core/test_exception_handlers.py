"""FastAPI HTTP 异常处理器集成测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main_server.core.exception_handlers import build_error_body


class TestBuildErrorBody:
    def test_standard_shape(self, request_id: str) -> None:
        # 场景：标准错误体；输入：code+message；预期：含 success/request_id
        body = build_error_body(code="TEST", message="测试消息")
        assert body == {
            "success": False,
            "code": "TEST",
            "message": "测试消息",
            "request_id": request_id,
        }

    def test_extra_fields(self, request_id: str) -> None:
        # 场景：附加字段；输入：extra dict；预期：合并到 body
        body = build_error_body(code="TEST", message="测试", extra={"stage": "decode"})
        assert body["stage"] == "decode"
        assert body["success"] is False


class TestHttpExceptionHandlers:
    def test_not_found(self, client: TestClient) -> None:
        # 场景：404；输入：GET /not-found；预期：NOT_FOUND
        resp = client.get("/not-found")
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert data["code"] == "NOT_FOUND"
        assert "request_id" in data

    def test_auth_error(self, client: TestClient) -> None:
        # 场景：401；输入：GET /auth；预期：AUTH_ERROR
        resp = client.get("/auth")
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTH_ERROR"

    def test_permission_denied(self, client: TestClient) -> None:
        # 场景：403；输入：GET /forbidden；预期：PERMISSION_DENIED
        resp = client.get("/forbidden")
        assert resp.status_code == 403
        assert resp.json()["code"] == "PERMISSION_DENIED"

    def test_validation_error(self, client: TestClient) -> None:
        # 场景：400 校验；输入：GET /validation；预期：VALIDATION_ERROR
        resp = client.get("/validation")
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_crm_error_custom_status(self, client: TestClient) -> None:
        # 场景：CRM 404；输入：GET /crm；预期：status=404
        resp = client.get("/crm")
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"

    def test_knowledge_error(self, client: TestClient) -> None:
        # 场景：知识库 500；输入：GET /knowledge；预期：STORAGE_ERROR
        resp = client.get("/knowledge")
        assert resp.status_code == 500
        assert resp.json()["code"] == "STORAGE_ERROR"

    @pytest.mark.parametrize(
        "path,expected_code",
        [
            ("/llm", "LLM_ERROR"),
            ("/asr", "ASR_ERROR"),
            ("/tts", "TTS_ERROR"),
        ],
    )
    def test_provider_errors_return_502(
        self, client: TestClient, path: str, expected_code: str
    ) -> None:
        # 场景：Provider 502；输入：各 Provider 路由；预期：对应 code
        resp = client.get(path)
        assert resp.status_code == 502
        assert resp.json()["code"] == expected_code

    def test_pipeline_error(self, client: TestClient) -> None:
        # 场景：Pipeline 500；输入：GET /pipeline；预期：PIPELINE_ERROR
        resp = client.get("/pipeline")
        assert resp.status_code == 500
        assert resp.json()["code"] == "PIPELINE_ERROR"

    def test_unexpected_error(self, client: TestClient) -> None:
        # 场景：未捕获异常；输入：GET /unexpected；预期：INTERNAL_ERROR
        resp = client.get("/unexpected")
        assert resp.status_code == 500
        data = resp.json()
        assert data["code"] == "INTERNAL_ERROR"
        assert data["message"] == "服务内部错误"

    def test_http_exception_dict_detail(self, client: TestClient) -> None:
        # 场景：HTTPException dict detail；输入：418；预期：TEAPOT
        resp = client.get("/http-detail-dict")
        assert resp.status_code == 418
        data = resp.json()
        assert data["code"] == "TEAPOT"
        assert data["message"] == "我是茶壶"

    def test_http_exception_str_detail(self, client: TestClient) -> None:
        # 场景：HTTPException str detail；输入：400；预期：HTTP_ERROR
        resp = client.get("/http-detail-str")
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "HTTP_ERROR"
        assert data["message"] == "请求无效"
