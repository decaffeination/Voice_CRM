# 部署指南

本地开发、Docker 全栈与生产环境说明。

## 部署模式

| 模式 | 命令 | 适用 |
|------|------|------|
| 本地开发 | `python run.py` | 日常开发，热更新方便 |
| Docker 全栈 | `docker compose up -d --build` | 演示 / 单机部署 |
| 仅 PostgreSQL | `docker compose -f docker-compose.postgres.yml up -d` | 本地连 PG，代码仍用 `run.py` |

| 模式 | 前端 | 后端 |
|------|------|------|
| `run.py` | :5173 | :8000 |
| Docker 全栈 | :8080（Nginx） | :8000 |

## Docker 全栈

### 1. 环境变量

```bash
copy .env.example .env
```

`.env` 至少包含：

```env
LLM_API_KEY=sk-your-key
JWT_SECRET_KEY=your-long-random-secret-at-least-32-chars
```

### 2. 构建启动

```bash
docker compose up -d --build
```

服务组成：

- **postgres** — PostgreSQL 16（`voice_crm` / `voice_crm`）
- **api** — FastAPI；卷 `voice_crm_data` 持久化 `main_server/data`
- **web** — Nginx 静态前端 + 反代 `/api`、`/ws`

### 3. 首次初始化

```bash
docker compose exec api python scripts/ingest_knowledge.py
docker compose exec api python -m main_server.utils.download_asr_model   # 按需
docker compose exec api python -m main_server.utils.download_vad_model   # 按需
```

### 4. 健康检查

```bash
curl http://localhost:8000/health
curl http://localhost:8080/health
```

默认管理员：`admin` / `admin123`（API 首次启动时创建）。

## 仅 PostgreSQL（本地开发）

```bash
docker compose -f docker-compose.postgres.yml up -d
set DATABASE_URL=postgresql+psycopg://voice_crm:voice_crm@localhost:5432/voice_crm
python run.py
```

详见 [database.md](database.md)。

## 生产清单

- [ ] 强随机 `JWT_SECRET_KEY`（≥ 32 字符）
- [ ] 修改默认管理员密码
- [ ] `app.env: production`，`app.debug: false`
- [ ] 使用 PostgreSQL，备份 `voice_crm_pg_data` 卷
- [ ] HTTPS + 具体 CORS 域名（见下文）
- [ ] 监控 `/health`
- [ ] 模型与 `main_server/data` 使用持久卷

## CORS

生产勿使用 `origins: ["*"]`：

```yaml
cors:
  allow_origins:
    - "https://your-domain.example.com"
  allow_credentials: true
```

或环境变量：

```env
CORS_ORIGINS=https://your-domain.example.com
```

`allow_credentials: true` 时浏览器不允许 `*`。详见 [faq.md](faq.md)。

## 资源建议

| 组件 | 最低 | 推荐 |
|------|------|------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB+ |
| 磁盘 | 20 GB | 50 GB+（含模型缓存） |

## 网络依赖

- DeepSeek API（LLM）
- edge-tts（默认 TTS）
- HuggingFace / ModelScope（Embedding、ASR 首次下载）

## 故障排查

| 现象 | 处理 |
|------|------|
| API 启动慢 | 首次迁移 DB；Embedding 冷启动 1–2 分钟 |
| 无法对话 | 检查 `LLM_API_KEY`；`curl /health` |
| 知识库无结果 | `scripts/ingest_knowledge.py` |
| WebSocket 断开 | Nginx `proxy_read_timeout`；JWT 是否过期 |
| 镜像构建慢 | PyTorch 体积大，首次 10–20 分钟属正常 |

## 相关文档

- [architecture.md](architecture.md)
- [database.md](database.md)
- [faq.md](faq.md)
