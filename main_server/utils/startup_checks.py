"""启动前配置与安全检查（run.py / FastAPI lifespan 共用）。"""

from __future__ import annotations

_DEFAULT_JWT_SECRET = "change-me-in-production-use-long-random-string"
_MIN_JWT_SECRET_LEN = 32


def warn_startup_config() -> None:
    from main_server.config.settings import get_settings, using_example_config

    if using_example_config():
        print(
            "[配置] 未找到 config.yaml，已使用 config.example.yaml。\n"
            "       建议执行: copy config.example.yaml config.yaml"
        )

    settings = get_settings()

    if not settings.llm.api_key:
        print(
            "[配置] 未设置 LLM_API_KEY，文本对话 / Agent 不可用。\n"
            "       请复制 .env.example 为 .env 并填写 DeepSeek API Key。"
        )

    secret = settings.jwt.secret_key
    if secret == _DEFAULT_JWT_SECRET or len(secret) < _MIN_JWT_SECRET_LEN:
        print(
            "[安全] JWT 使用弱密钥或默认占位符。\n"
            "       生产环境请设置环境变量 JWT_SECRET_KEY（建议 >= 32 位随机字符串）。"
        )

    if settings.app.env == "production" and settings.app.debug:
        print("[安全] app.env=production 时建议将 app.debug 设为 false。")

    cors = settings.cors
    if settings.app.env == "production" and cors.uses_wildcard:
        print(
            "[安全] 生产环境 CORS allow_origins 含 *，建议改为具体前端域名。\n"
            "       可在 config.yaml 的 cors.allow_origins 或环境变量 CORS_ORIGINS 中配置。"
        )
    if cors.allow_credentials and cors.uses_wildcard:
        print(
            "[安全] allow_credentials=true 与 origins=* 在浏览器中不兼容；\n"
            "       生产环境请配置具体来源（如 http://localhost:5173）。"
        )
