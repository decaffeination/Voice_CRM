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

### Changed

- README 重写：快速启动、Docker、环境变量说明
- LLM API Key 改为环境变量 `LLM_API_KEY` 注入
- 启动时检测弱 JWT / 弱 CORS 配置并警告

### Security

- 移除配置文件中的硬编码 DeepSeek API Key；密钥仅通过 `.env` 注入

## [0.1.0] - 2025-06-21

### Added

- FastAPI 后端 + Vue3 前端
- 文本 / 语音对话、WebSocket 实时语音
- RAG 知识库（ChromaDB + BGE + BM25）
- CRM 与 LangGraph Function Calling Agent
- Alembic 迁移，SQLite / PostgreSQL 双模式
- pytest 自动化测试与 live 验收脚本
