# 数据库部署

Voice-CRM 支持 **SQLite**（默认）与 **PostgreSQL**（生产推荐）二选一。

## 配置优先级

1. 环境变量 `DATABASE_URL`
2. `config.yaml` → `database.url`
3. 回退 `database.sqlite_path`（SQLite 文件）

## SQLite（默认）

适用：本地开发、单机演示。

```yaml
database:
  url: ""
  sqlite_path: main_server/data/sqlite/voice_crm.db
```

**首次启动**时，`main_server.api.main` 的 lifespan 会自动执行 Alembic 迁移并创建默认管理员，一般无需手动初始化。

手动初始化（可选）：

```bash
python -m main_server.utils.init_db
```

## PostgreSQL（生产）

### 1. 启动数据库

```bash
docker compose -f docker-compose.postgres.yml up -d
```

### 2. 配置连接

Windows：

```cmd
set DATABASE_URL=postgresql+psycopg://voice_crm:voice_crm@localhost:5432/voice_crm
```

Linux / macOS：

```bash
export DATABASE_URL=postgresql+psycopg://voice_crm:voice_crm@localhost:5432/voice_crm
```

### 3. 初始化

```bash
python -m main_server.utils.init_db
# 或
alembic upgrade head
```

Docker 全栈（`docker-compose.yml`）中 API 服务已注入 `DATABASE_URL`，启动时同样自动迁移。

## SQLite → PostgreSQL 迁移

```bash
python scripts/migrate_sqlite_to_postgres.py ^
  --sqlite main_server/data/sqlite/voice_crm.db ^
  --postgres postgresql+psycopg://voice_crm:voice_crm@localhost:5432/voice_crm
```

脚本会先对目标库 `alembic upgrade head`，再按外键顺序复制数据。

## 测试

默认 pytest 使用内存 / 临时 SQLite。PostgreSQL 集成测试：

```bash
set DATABASE_URL=postgresql+psycopg://voice_crm:voice_crm@localhost:5432/voice_crm_test
pytest tests/integration/test_postgres_db.py -m postgres
```

`postgres` 标记在 [pytest.ini](../pytest.ini) 中注册。

## 健康检查

`GET /health` → `components.database`：

- `dialect`：`sqlite` / `postgresql`
- `display_name`：SQLite / PostgreSQL
- `status`：连接状态

## 数据访问层

| 目录 | 职责 |
|------|------|
| `main_server/DB/repositories/` | 用户、会话、Memory、审计、知识库元数据 |
| `main_server/CRM/repository/` | CRM 领域读写 |

## LangGraph Checkpointer（可选）

默认关闭。启用后按 dialect 选择 SQLite 或 PostgreSQL checkpoint，入口：`agent/checkpoint_factory.py`。

## CI

[`.github/workflows/database-tests.yml`](../.github/workflows/database-tests.yml) 包含 SQLite 与 PostgreSQL 两个 job。

## 相关文档

- [deployment.md](deployment.md) — Docker 与生产
- [faq.md](faq.md) — 重置数据库等
