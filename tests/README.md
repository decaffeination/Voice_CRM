# 测试体系

Voice-CRM 采用 **pytest 自动化** + **live 真实环境验收** 两层测试。

## 目录

```
tests/
├── conftest.py       # 公共 fixtures（内存 DB、mock Provider）
├── unit/             # 单模块逻辑
├── api/              # HTTP 路由
├── integration/      # 跨模块流程
└── live/             # 真实 LLM / 模型 / 浏览器（见 live/README.md）
```

## 快速运行

```bash
pip install -r requirements.txt
pytest tests/unit tests/api tests/integration
```

PostgreSQL 专项（需运行中的 PG 与 `DATABASE_URL`）：

```bash
pytest tests/integration/test_postgres_db.py -m postgres
```

## 设计原则

| 层级 | 外部依赖 | 数据库 |
|------|----------|--------|
| unit / api / integration | mock | 内存 / 临时 SQLite |
| live | 真实 LLM、模型 | 真实 `data/` |

## 模块覆盖

| 模块 | unit | api | integration | live |
|------|:----:|:---:|:-----------:|:----:|
| core / auth / session | ✓ | ✓ | — | 部分 |
| memory / CRM | ✓ | ✓ | ✓ | ✓ |
| knowledge / pipeline | ✓ | ✓ | ✓ | ✓ |
| agent / providers | ✓ | ✓ | ✓ | ✓ |
| WebSocket / audio | ✓ | ✓ | ✓ | ✓ |

完整矩阵见下方表格（与历史文档保持一致）。

| 模块 | unit | api | integration | live |
|------|:----:|:---:|:-----------:|:----:|
| **core** | `unit/core/*` | — | — | `logger_check.py` |
| **auth** | `unit/auth/*` | `test_user_api.py` | — | — |
| **session** | `unit/session/` | `test_session_api.py` | — | — |
| **memory** | `unit/memory/*`, `unit/agent/test_memory_graph.py` | — | `test_memory_multiturn.py` | `http_memory_multiturn.py` |
| **CRM** | `unit/auth/test_access_control.py` | `test_crm_api.py` | `test_crm_crud.py`, `test_crm_mutation.py` | `http_crm_write_confirm.py` |
| **knowledge** | `unit/knowledge/*` | `test_knowledge_api.py` | — | `knowledge_ingest_and_search.py` |
| **pipeline** | — | — | `test_chat_pipeline.py`, `test_voice_pipeline.py` | — |
| **agent** | `unit/agent/*` | — | `test_citation_enforcement.py` | `agent_real_llm.py` |
| **providers** | `unit/providers/*` | `test_health.py`, `test_main_app.py` | — | — |
| **WebSocket** | `unit/core/test_ws_errors.py` | — | — | `websocket_realtime_voice.py` |
| **chat / audio** | — | `test_chat_api.py`, `test_audio_api.py` | — | `http_audio_upload.py` |

## 约定

- 用例注释：**场景 / 输入 / 预期**
- live 脚本不替代 pytest，仅覆盖 mock 无法验证的路径

## 相关文档

- [live/README.md](live/README.md) — 发版前 live 验收
- [../docs/faq.md](../docs/faq.md) — 测试常见问题
