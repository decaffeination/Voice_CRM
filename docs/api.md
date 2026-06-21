# API 概览

后端基于 FastAPI。运行服务后访问交互式文档：

| 资源 | 地址 |
|------|------|
| Swagger UI | http://127.0.0.1:8000/docs |
| OpenAPI JSON | http://127.0.0.1:8000/openapi.json |
| 健康检查 | http://127.0.0.1:8000/health |

除 `/health`、`/docs`、`/openapi.json`、`POST /api/auth/login` 外，多数接口需 **JWT Bearer Token**。

## 认证

```http
POST /api/auth/login
Content-Type: application/json

{"username": "admin", "password": "admin123"}
```

后续请求：

```http
Authorization: Bearer <access_token>
```

## 会话与对话

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sessions` | 会话列表 |
| POST | `/api/session` | 创建会话 |
| GET | `/api/session/{session_id}` | 会话详情 |
| DELETE | `/api/session/{session_id}` | 删除会话 |
| GET | `/api/session/{session_id}/messages` | 会话消息 |
| POST | `/api/chat` | 文本对话（可选 TTS） |
| POST | `/api/audio` | 上传音频 → ASR → 对话 → TTS |

## WebSocket 实时语音

```
WS /ws/audio/{session_id}?token=<jwt>
```

流程：VAD → ASR → Agent → TTS（流式事件见 Swagger 或 `main_server/api/websocket/audio_ws.py`）。

## CRM

CRM **读接口**由 REST 提供；**写操作**经 Agent 工具与确认流完成（非直接 REST CRUD）。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/crm/customers` | 客户列表 |
| GET | `/api/crm/customers/lookup` | 客户检索 |
| GET | `/api/crm/customers/{id}` | 客户详情 |
| GET | `/api/crm/customers/{id}/profile` | 客户画像 |
| GET | `/api/crm/recent-updates` | 近期变更 |

## 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge/docs` | 文档列表 |
| GET | `/api/knowledge/docs/{doc_id}` | 文档详情 |
| GET | `/api/knowledge/stats` | 统计信息 |
| POST | `/api/knowledge/search` | 检索测试 |
| POST | `/api/knowledge/ingest/directory` | 批量导入（Admin） |
| POST | `/api/knowledge/ingest/file` | 上传并导入单文件（Admin） |
| DELETE | `/api/knowledge/docs/{doc_id}` | 删除文档（Admin） |
| POST | `/api/knowledge/rebuild` | 重建索引（Admin） |

## Dashboard 与管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/overview` | 概览（含 system_status） |
| GET | `/api/users` | 用户列表（Admin） |
| GET | `/api/admin/audit` | 审计日志（Admin） |
| GET | `/api/admin/settings/email` | 邮件配置（Admin） |

## 角色

| 角色 | 典型能力 |
|------|----------|
| Admin | 用户/角色、知识库导入、审计、系统配置 |
| SalesManager / Sales / CustomerService | 对话、CRM 查询、知识库检索 |
| 具体接口 | 以路由 Depends 为准 |

## 错误响应

```json
{
  "detail": "错误描述",
  "code": "ERROR_CODE",
  "request_id": "..."
}
```

常见状态码：401 未认证、403 权限不足、404 不存在、422 参数错误。

## 集成建议

- 生产环境在网关后终止 TLS
- 对 `/api/chat`、`/ws/audio` 配置超时与限流
- 限制 Swagger 内网访问

详见 [architecture.md](architecture.md)。
