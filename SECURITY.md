# 安全策略

## 支持版本

| 版本 | 支持 |
|------|------|
| 0.1.x | 是 |

## 漏洞报告

**请勿在公开 Issue 中披露安全漏洞。**

请通过 GitHub **Security → Report a vulnerability** 私下报告。我们会在 72 小时内确认收到并评估修复。

## 部署检查清单

### 密钥与认证

- [ ] `LLM_API_KEY` 仅写在 `.env`，不提交 Git
- [ ] 生产环境设置强随机 `JWT_SECRET_KEY`（≥ 32 字符）
- [ ] 修改默认账号 `admin` / `admin123`
- [ ] 已泄露的 API Key 在服务商控制台吊销并轮换

### 网络与 CORS

- [ ] 生产环境 `cors.allow_origins` 使用具体域名，避免 `*`
- [ ] `allow_credentials: true` 时禁止 `origins: ["*"]`
- [ ] 反向代理启用 HTTPS
- [ ] 限制 `/docs`、`/openapi.json` 的内网访问

### 应用与数据

- [ ] `app.env: production`，`app.debug: false`
- [ ] 生产使用 PostgreSQL 并定期备份
- [ ] 监控 `GET /health` 与各 Provider 状态
- [ ] 不将 SQLite、日志、模型权重提交到公开仓库

## 已知限制

- 默认 JWT 占位符与 CORS `*` 仅适用于**本地开发**
- 联网搜索使用 DuckDuckGo HTML 抓取，会访问外网
- 邮件工具默认 `dry_run: true`；启用真实 SMTP 前请确认权限

## 披露

安全修复完成后，会在 [CHANGELOG.md](CHANGELOG.md) 中记录（不含 exploit 细节）。
