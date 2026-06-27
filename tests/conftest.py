"""pytest 全局配置与公共夹具。

提供内存数据库、认证头、子应用客户端、外部依赖 mock 等，
供 unit / api / integration 测试复用。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main_server.core.context import request_id_var
from main_server.core.exception_handlers import register_exception_handlers
from main_server.core.exceptions import (
    ASRError,
    AuthError,
    CRMError,
    KnowledgeError,
    LLMError,
    NotFoundError,
    PermissionDeniedError,
    PipelineError,
    TTSError,
    ValidationError,
)
from main_server.core.auth.jwt_auth import create_access_token
from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user
from main_server.CRM.writes.customer_write import create_customer
from main_server.DB import db_session
from main_server.DB.models import Employee
from main_server.utils.init_db import seed_default_user, seed_roles
from tests.db_helpers import (
    is_postgresql_url,
    setup_test_engine,
    teardown_test_engine,
)


# ---------------------------------------------------------------------------
# 基础上下文
# ---------------------------------------------------------------------------


@pytest.fixture
def request_id() -> str:
    """场景：测试需要固定 request_id；输入：无；预期：上下文变量被设置。"""
    token = request_id_var.set("test-req-001")
    yield "test-req-001"
    request_id_var.reset(token)


# ---------------------------------------------------------------------------
# 内存数据库
# ---------------------------------------------------------------------------


def _setup_memory_engine(
    monkeypatch: pytest.MonkeyPatch, db_path: Path
) -> tuple[Any, Any]:
    env_url = os.environ.get("DATABASE_URL", "").strip()
    if env_url:
        url = env_url
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path.as_posix()}"
    return setup_test_engine(monkeypatch, url)


def _teardown_memory_engine(conn: Any, engine: Any) -> None:
    teardown_test_engine(conn, engine)


@pytest.fixture
def memory_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """场景：标准测试 DB（默认 SQLite 文件；设 DATABASE_URL 可切 PostgreSQL）。"""
    engine, conn = _setup_memory_engine(monkeypatch, tmp_path / "test.db")
    seed_roles()
    seed_default_user()
    yield engine
    _teardown_memory_engine(conn, engine)


@pytest.fixture
def postgres_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """场景：PostgreSQL 集成测试；未设置 DATABASE_URL 时跳过。"""
    env_url = os.environ.get("DATABASE_URL", "").strip()
    if not env_url or not is_postgresql_url(env_url):
        pytest.skip("需要 DATABASE_URL=postgresql+psycopg://...")
    engine, conn = setup_test_engine(monkeypatch, env_url)
    seed_roles()
    seed_default_user()
    yield engine
    teardown_test_engine(conn, engine)


@pytest.fixture
def memory_db_sales(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """场景：含销售用户与客户；输入：无；预期：sales1 用户及测试客户就绪。"""
    engine, conn = _setup_memory_engine(monkeypatch, tmp_path / "test.db")
    seed_roles()
    seed_default_user()

    fixture: dict[str, Any] = {}
    with db_session() as session:
        user = create_user(
            session,
            username="sales1",
            password="sales123",
            display_name="销售一号",
            roles=[Role.SALES],
        )
        customer = create_customer(
            session,
            name="测试客户",
            phone="13800000001",
            owner_user_id=user.id,
        )
        fixture.update({"user_id": user.id, "customer": customer, "sales": user})

    yield {"engine": engine, **fixture}
    _teardown_memory_engine(conn, engine)


@pytest.fixture
def memory_db_team(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """场景：含销售经理团队 CRM 夹具；输入：无；预期：多角色用户与客户种子数据。"""
    engine, conn = _setup_memory_engine(monkeypatch, tmp_path / "test.db")
    seed_roles()
    seed_default_user()
    users = _seed_team_fixture()
    yield {"engine": engine, "users": users}
    _teardown_memory_engine(conn, engine)


def _seed_team_fixture() -> dict[str, Any]:
    with db_session() as session:
        manager = create_user(
            session,
            username="mgr1",
            password="mgr12345",
            display_name="销售经理",
            roles=[Role.SALES_MANAGER],
        )
        sales_a = create_user(
            session,
            username="sales_a",
            password="sales123",
            display_name="销售A",
            roles=[Role.SALES],
        )
        sales_b = create_user(
            session,
            username="sales_b",
            password="sales123",
            display_name="销售B",
            roles=[Role.SALES],
        )
        other_sales = create_user(
            session,
            username="sales_other",
            password="sales123",
            display_name="外区销售",
            roles=[Role.SALES],
        )

        session.add(
            Employee(name="销售经理", department="华东销售部", user_id=manager.id)
        )
        session.add(
            Employee(name="销售A", department="华东销售部", user_id=sales_a.id)
        )
        session.add(
            Employee(name="销售B", department="华东销售部", user_id=sales_b.id)
        )
        session.add(
            Employee(
                name="外区销售", department="华南销售部", user_id=other_sales.id
            )
        )
        session.flush()

        create_customer(session, name="团队客户甲", owner_user_id=sales_a.id)
        create_customer(session, name="团队客户乙", owner_user_id=sales_b.id)
        create_customer(session, name="外区客户", owner_user_id=other_sales.id)

        return {
            "manager": manager,
            "sales_a": sales_a,
            "sales_b": sales_b,
            "other_sales": other_sales,
        }


# ---------------------------------------------------------------------------
# 认证辅助
# ---------------------------------------------------------------------------


def login_token(
    client: TestClient,
    username: str = "admin",
    password: str = "admin123",
) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def token_for_user(user_id: int, username: str, roles: list[str]) -> str:
    return create_access_token(
        user_id=user_id,
        username=username,
        roles=roles,
    )


@pytest.fixture
def admin_headers(memory_db) -> dict[str, str]:
    """场景：admin JWT；输入：内存 DB；预期：Bearer 头可用。"""
    token = create_access_token(1, "admin", [Role.ADMIN], display_name="管理员")
    return auth_headers(token)


# ---------------------------------------------------------------------------
# FastAPI 子应用工厂
# ---------------------------------------------------------------------------


def make_test_app(*routers: Any, prefix: str = "") -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    for router in routers:
        if prefix:
            app.include_router(router, prefix=prefix)
        else:
            app.include_router(router)
    return app


@pytest.fixture
def exception_app() -> FastAPI:
    """场景：异常处理器 HTTP 层测试；输入：无；预期：最小 App 含各异常路由。"""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    def _not_found() -> None:
        raise NotFoundError("资源不存在")

    @app.get("/auth")
    def _auth() -> None:
        raise AuthError("认证失败")

    @app.get("/forbidden")
    def _forbidden() -> None:
        raise PermissionDeniedError("无权访问")

    @app.get("/validation")
    def _validation() -> None:
        raise ValidationError("参数错误")

    @app.get("/crm")
    def _crm() -> None:
        raise CRMError("客户不存在", code="NOT_FOUND", status_code=404)

    @app.get("/knowledge")
    def _knowledge() -> None:
        raise KnowledgeError("检索失败", code="STORAGE_ERROR", status_code=500)

    @app.get("/llm")
    def _llm() -> None:
        raise LLMError("LLM 调用失败", provider="deepseek")

    @app.get("/asr")
    def _asr() -> None:
        raise ASRError("ASR 识别失败", provider="funasr")

    @app.get("/tts")
    def _tts() -> None:
        raise TTSError("TTS 合成失败", provider="edge-tts")

    @app.get("/pipeline")
    def _pipeline() -> None:
        raise PipelineError("处理失败", stage="agent_invoke")

    @app.get("/unexpected")
    def _unexpected() -> None:
        raise RuntimeError("boom")

    @app.get("/http-detail-dict")
    def _http_detail_dict() -> None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=418,
            detail={"code": "TEAPOT", "message": "我是茶壶"},
        )

    @app.get("/http-detail-str")
    def _http_detail_str() -> None:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="请求无效")

    return app


@pytest.fixture
def client(exception_app: FastAPI) -> TestClient:
    return TestClient(exception_app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 外部依赖 mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_agent_invoke(monkeypatch: pytest.MonkeyPatch):
    """场景：mock Agent 调用；输入：自定义回复文本；预期：pipeline 不调用真实 Graph。"""
    from main_server.services.agent_service import AgentInvokeResult

    def _factory(text: str = "测试回复", intent: str | None = "chat"):
        def _invoke(*, turn):
            return AgentInvokeResult(
                text=text,
                conversation_state={"current_intent": intent},
            )

        monkeypatch.setattr(
            "main_server.services.pipeline.chat_pipeline.agent_service.invoke",
            _invoke,
        )
        monkeypatch.setattr(
            "main_server.services.agent_service.agent_service.invoke",
            _invoke,
        )

    return _factory


@pytest.fixture
def mock_tts(monkeypatch: pytest.MonkeyPatch):
    """场景：mock TTS；输入：无；预期：返回固定音频字节。"""
    async def _synthesize(text: str) -> bytes:
        return b"fake-audio-bytes"

    monkeypatch.setattr(
        "main_server.services.pipeline.chat_pipeline.synthesize_async",
        _synthesize,
    )
    monkeypatch.setattr(
        "main_server.services.voice_services.tts_service.synthesize_async",
        _synthesize,
    )


@pytest.fixture
def mock_asr(monkeypatch: pytest.MonkeyPatch):
    """场景：mock ASR；输入：无；预期：返回固定转写文本。"""

    def _transcribe(path: str) -> str:
        return "你好，这是测试语音"

    monkeypatch.setattr(
        "main_server.services.voice_services.asr_service.transcribe",
        _transcribe,
    )
    monkeypatch.setattr(
        "main_server.services.pipeline.voice_pipeline.transcribe",
        _transcribe,
    )


@pytest.fixture
def mock_llm_provider(monkeypatch: pytest.MonkeyPatch):
    """场景：mock LLM Provider；输入：无；预期：chat 返回固定内容。"""
    class _StubLLM:
        def chat(self, messages, **kwargs):
            return {"content": "LLM stub 回复", "tool_calls": None}

        def health_check(self):
            return {"status": "ok", "provider": "stub"}

    monkeypatch.setattr(
        "main_server.providers.registry.get_llm_provider",
        lambda: _StubLLM(),
    )


@pytest.fixture
def mock_email_provider(monkeypatch: pytest.MonkeyPatch):
    """场景：mock 邮件发送；输入：无；预期：dry_run 成功。"""
    class _StubEmail:
        def send(self, to, subject, body, html_body=None):
            return {"sent": True, "dry_run": True, "to": to}

    monkeypatch.setattr(
        "main_server.providers.Tools.email_tool.get_email_provider",
        lambda: _StubEmail(),
    )


@pytest.fixture
def mock_web_search(monkeypatch: pytest.MonkeyPatch):
    """场景：mock 联网搜索；输入：无；预期：返回固定搜索结果。"""
    class _StubSearch:
        def search(self, query, max_results=None):
            return {"results": [{"title": "测试", "url": "http://test.com"}]}

        def search_company_contact(self, company_name):
            return {
                "company": company_name,
                "emails_found": ["test@example.com"],
            }

    stub = _StubSearch()
    monkeypatch.setattr(
        "main_server.services.search_service.get_web_search_provider",
        lambda: stub,
    )


@pytest.fixture
def tmp_knowledge_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """场景：隔离知识库目录；输入：tmp_path；预期：Chroma/docs 指向临时目录。"""
    chroma = tmp_path / "chroma"
    docs = tmp_path / "docs"
    chroma.mkdir()
    docs.mkdir()

    monkeypatch.setenv("KNOWLEDGE_CHROMA_PATH", str(chroma))
    monkeypatch.setenv("KNOWLEDGE_DOCS_PATH", str(docs))

    return {"chroma": chroma, "docs": docs}
