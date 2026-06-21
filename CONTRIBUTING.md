# 贡献指南

感谢关注 Voice-CRM。欢迎通过 Issue 与 Pull Request 参与改进。

## 开始之前

1. Fork 并克隆仓库
2. 阅读 [README.md](README.md) 完成本地配置
3. 浏览 [docs/architecture.md](docs/architecture.md) 了解分层约定

## 开发环境

- Python 3.11+
- Node.js 18+（前端开发）
- DeepSeek API Key（对话相关功能）

```bash
pip install -r requirements.txt
cd web_server && npm install
copy config.example.yaml config.yaml
copy .env.example .env
# 编辑 .env 填入 LLM_API_KEY
python run.py
```

## 分支与提交

- 分支命名：`feat/xxx`、`fix/xxx`、`docs/xxx`
- 提交信息：`类型: 简短说明`（例：`fix: 修复会话删除级联`）
- 一个 PR 只做一类改动，避免无关重构

## 代码约定

- 业务逻辑放在 `main_server/services/`
- `agent/tools/` 保持薄封装，不堆业务
- 新增 API 需考虑鉴权与角色（`main_server/api/deps/`）
- **禁止**在可提交文件中硬编码密钥；使用 `.env` 与环境变量

## 测试

提交前运行：

```bash
pytest tests/unit tests/api tests/integration
```

- 日常测试使用 mock 与内存数据库，**不需要**真实 LLM
- 语音 / 真实 LLM 端到端验收见 [tests/live/README.md](tests/live/README.md)

## Pull Request 清单

- [ ] 说明变更动机与影响范围
- [ ] 相关测试已通过
- [ ] 文档已更新（如适用）
- [ ] 未包含 `.env`、`config.yaml`、模型权重、`node_modules`、数据库文件

## 首次提交到 Git 请注意

`.gitignore` 已排除敏感与大体积目录。`git add` 前请确认 **未** 纳入：

- `.env`、`config.yaml`
- `main_server/data/models/`（约数 GB）
- `web_server/node_modules/`、`web_server/dist/`
- SQLite、日志、Chroma 运行时数据

## 报告问题

Issue 请包含：操作系统、Python 版本、复现步骤、期望与实际行为、相关日志。

## 行为准则

请保持友善、尊重与建设性沟通。
