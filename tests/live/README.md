# Live 验收

`tests/live/` 用于 **pytest 无法替代** 的端到端验证：真实 LLM、本地语音模型、向量库与服务重启。

**不属于日常 CI。** 日常请运行：

```bash
pytest tests/unit tests/api tests/integration
```

## 前置条件

- `.env` 中配置 `LLM_API_KEY`
- 多数 HTTP/WS 脚本需先启动服务：`python run.py --no-frontend` 或 `python run.py`

## 目录

```
live/
├── README.md
├── checklists/frontend_ui.md
└── scripts/
    ├── agent_real_llm.py
    ├── http_memory_multiturn.py
    ├── http_crm_write_confirm.py
    ├── http_audio_upload.py
    ├── websocket_realtime_voice.py
    ├── knowledge_ingest_and_search.py
    ├── smoke_real_db_init.py
    └── logger_check.py
```

## 脚本一览

| 脚本 | 验收内容 | 依赖 |
|------|----------|------|
| `agent_real_llm.py` | LangGraph + 真实 LLM | `LLM_API_KEY` |
| `http_memory_multiturn.py` | 多轮 Memory | 服务 + Key |
| `http_crm_write_confirm.py` | CRM 写确认流 | 服务 + Key |
| `http_audio_upload.py` | 上传音频全链路 | Key；ASR 可自动下载 |
| `websocket_realtime_voice.py` | WS 实时语音 | VAD + Key |
| `knowledge_ingest_and_search.py` | 真实向量检索 | Embedding 模型 |
| `smoke_real_db_init.py` | 真实 DB 初始化 | 写入 `data/` |
| `logger_check.py` | 日志检查 | 可选 `--http` |

## 常用命令

```bash
# 无需 HTTP 服务
python tests/live/scripts/agent_real_llm.py

# 需服务在 8000 端口
python tests/live/scripts/http_memory_multiturn.py
python tests/live/scripts/http_crm_write_confirm.py
python tests/live/scripts/http_audio_upload.py
python tests/live/scripts/websocket_realtime_voice.py

# 知识库（较慢）
python tests/live/scripts/knowledge_ingest_and_search.py
```

语音预下载（可选）：

```bash
python -m main_server.utils.download_asr_model
python -m main_server.utils.download_vad_model
```

## 发版前最小集

1. `agent_real_llm.py` 或 `http_memory_multiturn.py`
2. `http_crm_write_confirm.py`
3. [checklists/frontend_ui.md](checklists/frontend_ui.md)

有语音环境时增加 `http_audio_upload.py`。

## 与 pytest 对照

| 能力 | pytest | live |
|------|--------|------|
| JWT / 登录 | ✓ | — |
| 多轮 Memory | integration | `http_memory_multiturn.py` |
| CRM 确认 | integration | `http_crm_write_confirm.py` |
| 语音 HTTP/WS | api + unit | `http_audio_upload.py` / `websocket_*` |
| 浏览器 UI | — | `frontend_ui.md` |
