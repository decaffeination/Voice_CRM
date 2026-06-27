# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 格式。

## [Unreleased]

### Added

- 开源文档：`LICENSE`、`CONTRIBUTING`、`SECURITY`、`CHANGELOG`
- 部署：`deploy/Dockerfile`、`docker-compose.yml`、`docs/deployment.md`
- 文档：`docs/faq.md`、`docs/api.md`、架构图与界面截图
- 脚本：`scripts/ingest_knowledge.py` 知识库一键导入
- 配置：`config.example.yaml`、`.env.example`、根目录 `.gitignore`
- CORS 可通过 `config.yaml` 与 `CORS_ORIGINS` 配置
- **管理后台 REST**：邮件 SMTP（`GET/PATCH /api/settings/email`、测试发送）、系统参数（`GET/PATCH /api/settings/system`）、模型配置（`GET/PATCH /api/settings/models`）；前端 `EmailView` / `ParamsView` / `ModelsView` 对接真实 API
- **RBAC 持久化**：权限目录 `rbac_catalog`、数据库表 `permissions` / `role_permissions`（Alembic `004`）、`GET /api/permissions/tree`、`GET/PATCH /api/roles/{role_code}/permissions`；启动时 `seed_permissions` / `seed_role_permissions`；管理端 `RolesView` 可编辑权限树并保存
- **Tavily 联网搜索**：`TavilySearchProvider`，通过 `search.provider: tavily` 与 `TAVILY_API_KEY` 启用；保留 DuckDuckGo 作为备选
- **RAG 增强（P3）**：
  - 分片：按 Markdown 标题与段落边界预切分，再按字符窗口 + overlap 切块
  - 检索：`knowledge.rerank_top_k` 独立控制 rerank 候选数
  - 引用：Agent 检索结果经 API / WebSocket 返回 `citations`（含 `doc_id`）；聊天界面展示「参考来源」卡片
- **测试**：`test_dashboard_api`、`test_websocket_integration`、`test_rbac_api`、`test_tavily_search`；知识库分片 / rerank / 引用强制相关用例

### Changed

- README 重写：快速启动、Docker、环境变量说明
- LLM API Key 改为环境变量 `LLM_API_KEY` 注入
- 启动时检测弱 JWT / 弱 CORS 配置并警告
- **Knowledge 模块路径统一**：`main_server/Knowledge/` → `main_server/knowledge/`，全项目 import 改为小写包名
- **CRM 写入模块**：`curstomer_write.py` 重命名为 `customer_write.py`
- **角色数据**：`RolesView` 接 `GET /api/roles`（含 `user_count`）；前端 RBAC 常量迁至 `constants/rbac.ts`；精简 `mock/admin.ts`
- **流式输出**：`on_text_final` 增加 `citations` 参数，贯穿 `chat_pipeline` / `voice_pipeline` / `stream_emitter`

### Removed

- 废弃的 `main_server/CRM/sql_connection.py`（已由统一 DB 层替代）

### Security

- 移除配置文件中的硬编码 DeepSeek API Key；密钥仅通过 `.env` 注入
- Tavily / SMTP 等第三方密钥仅通过环境变量或运行时配置注入，不写入仓库

## [0.1.0] - 2025-06-21

### Added

- FastAPI 后端 + Vue3 前端
- 文本 / 语音对话、WebSocket 实时语音
- RAG 知识库（ChromaDB + BGE + BM25）
- CRM 与 LangGraph Function Calling Agent
- Alembic 迁移，SQLite / PostgreSQL 双模式
- pytest 自动化测试与 live 验收脚本
