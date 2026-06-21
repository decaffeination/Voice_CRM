# 常见问题（FAQ）

## 安装与环境

### Python 版本？

**3.11+**。CI 与 Docker 镜像基于 3.11。

### `pip install` 很慢？

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

Windows 编译失败时安装 [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)。

### 没有 Node.js 能跑吗？

可以：`python run.py --no-frontend`，用 http://127.0.0.1:8000/docs 调试 API。完整 UI 需要 Node.js 18+（`run.py` 会自动 `npm install` 并启动 Vite）。

---

## 配置与密钥

### 对话无响应？

1. `.env` 中设置 `LLM_API_KEY`
2. 访问 `GET /health`，查看 `components.llm`
3. 确认 DeepSeek 账户余额

### `config.yaml` 和 `.env` 区别？

| 文件 | 用途 | 提交 Git |
|------|------|:--------:|
| `config.example.yaml` | 非敏感配置模板 | 是 |
| `config.yaml` | 本地配置 | 否 |
| `.env.example` | 环境变量模板 | 是 |
| `.env` | 密钥 | 否 |

### 打开网页没有登录页？

多为浏览器仍保存 JWT（`localStorage` 键 `voice_crm_token`）。侧边栏点「退出」，或 F12 清除站点数据。无痕窗口可验证。

---

## CORS

本地 Vite（:5173）通过代理访问 API，通常无需改 CORS。

跨域部署时在 `config.yaml` 或 `.env` 中设置具体域名，见 [deployment.md](deployment.md#cors)。

---

## 语音

### ASR 失败？

```bash
python -m main_server.utils.download_asr_model
python -m main_server.utils.download_vad_model
```

### TTS 无声音？

默认 **edge-tts** 需外网。离线可改 `models.tts.provider: chattts` 并下载本地模型。

### WebSocket 断开？

检查 JWT 是否过期、Nginx WebSocket 配置（`deploy/nginx.conf`）、`ws_idle_timeout_seconds`（默认 300s）。

---

## 知识库

### 问答总是「未找到相关内容」？

```bash
python scripts/ingest_knowledge.py
```

示例文档目录：`main_server/data/knowledge/`。首次检索会下载 BGE Embedding，需等待。

---

## 数据库

### 切换 PostgreSQL？

```bash
docker compose -f docker-compose.postgres.yml up -d
```

```env
DATABASE_URL=postgresql+psycopg://voice_crm:voice_crm@localhost:5432/voice_crm
```

详见 [database.md](database.md)。

### 重置 SQLite？

删除 `main_server/data/sqlite/voice_crm.db` 后重启，会自动迁移并重建 admin。

---

## Docker

### compose 后无法对话？

```bash
docker compose exec api printenv LLM_API_KEY
```

确认项目根目录 `.env` 存在且 compose 中 `api` 配置了 `env_file: .env`。

### 两个 compose 文件区别？

- `docker-compose.yml` — 全栈（PG + API + 前端）
- `docker-compose.postgres.yml` — **仅** PostgreSQL，配合本地 `run.py`

---

## Git 与开源

### 首次 push 体积大吗？

`.gitignore` 已排除模型（~4GB）、`node_modules` 等。实际提交约 **15–25 MB**（源码 + 文档 + 截图）。`git add` 前用 `git status` 确认无 `.env`、`models/`、`node_modules/`。

### 需要从 Git 历史清 Key 吗？

若**从未** `git commit` 过，无历史问题。Key 只放 `.env` 即可。

---

## 安全

生产环境务必修改默认密码、设置 `JWT_SECRET_KEY`。详见 [SECURITY.md](../SECURITY.md)。

---

## 测试

```bash
pytest tests/unit tests/api tests/integration
```

无需真实 LLM。Live 验收见 [tests/live/README.md](../tests/live/README.md)。
