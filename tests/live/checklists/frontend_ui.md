# 前端 UI 联调清单

浏览器手工验收。API 自动化见 `tests/api/`。

## 一、准备知识库（可选）

1. 将 `.pdf` / `.docx` / `.txt` 放入 `main_server/data/knowledge/`
2. 执行：
   ```bash
   python scripts/ingest_knowledge.py
   ```
3. 确认输出中 `files`、`chunks` 大于 0

清空向量库：删除 `main_server/data/chroma/` 后重新 ingest。

## 二、启动

```bash
python run.py
```

浏览器：http://localhost:5173 ，账号 `admin` / `admin123`

> `run.py` 会同时启动后端与 Vite 前端，无需再开第二个终端跑 `npm run dev`。

## 三、功能检查

| 模块 | 操作 | 预期 |
|------|------|------|
| 登录 | admin / admin123 | 进入主界面 |
| 会话 | 新建 / 切换 / 删除 | 侧边栏与对话区正确 |
| 知识库 | 问文档相关问题 | 回答与文档一致 |
| CRM | 查客户、写库确认/取消 | 对话内完成 |
| 文本+TTS | 开启语音回复 | 有文字与可播放音频 |
| 上传音频 | 选 wav/mp3 | 识别 + 回复 |
| 实时语音 | WS + 麦克风 | ASR + 回复 |
| 概览 | Dashboard | 数据与图表展示 |
| 管理 | 系统管理（Admin） | 用户/审计等页面可访问 |

## 四、与 live 脚本对照

| 能力 | 前端 | live 脚本 |
|------|------|-----------|
| 文本 / Memory | ChatView | `http_memory_multiturn.py` |
| CRM 确认 | 对话确认 | `http_crm_write_confirm.py` |
| 上传音频 | 上传按钮 | `http_audio_upload.py` |
| 实时语音 | WS + 麦克风 | `websocket_realtime_voice.py` |

## 五、常见问题

| 现象 | 处理 |
|------|------|
| 连不上后端 | 确认 `run.py` 已启动，8000 端口可用 |
| 无登录页 | 清除 `localStorage` 或点「退出」 |
| 知识库无答案 | 是否 ingest；问题是否与文档相关 |
| TTS 无声音 | edge-tts 需外网 |
| 实时语音无反应 | 允许麦克风；检查 WS 连接 |
