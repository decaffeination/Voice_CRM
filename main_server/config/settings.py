from __future__ import annotations

import copy
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from sqlalchemy.engine import make_url

from main_server.config.cors import CORSSettings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
CONFIG_EXAMPLE_PATH = PROJECT_ROOT / "config.example.yaml"


def _load_dotenv() -> None:
    env_file = PROJECT_ROOT / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_file, override=False)


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


class AppSettings(BaseModel):
    name: str = "Voice-CRM"
    env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000


class DatabaseSettings(BaseModel):
    """数据库配置：优先 ``DATABASE_URL`` 环境变量，其次 ``url``，最后回退 SQLite 文件。"""

    url: str = ""
    sqlite_path: str = "main_server/data/sqlite/voice_crm.db"

    @property
    def abs_path(self) -> Path:
        return _resolve_path(self.sqlite_path)

    @property
    def effective_url(self) -> str:
        env_url = os.environ.get("DATABASE_URL", "").strip()
        if env_url:
            return env_url
        configured = self.url.strip()
        if configured:
            return configured
        return f"sqlite:///{self.abs_path.as_posix()}"

    @property
    def dialect(self) -> str:
        return make_url(self.effective_url).get_backend_name()


class JWTSettings(BaseModel):
    secret_key: str
    algorithm: str = "HS256"
    expire_minutes: int = 1440


class LLMSettings(BaseModel):
    provider: str = "deepseek"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"


class ProviderSettings(BaseModel):
    timeout_seconds: float = 60.0
    llm_timeout_seconds: float = 60.0
    asr_timeout_seconds: float = 90.0
    tts_timeout_seconds: float = 45.0
    pipeline_timeout_seconds: float = 180.0
    ws_idle_timeout_seconds: float = 300.0
    max_retries: int = 2
    retry_delay_seconds: float = 0.5


class MemorySettings(BaseModel):
    history_active_rounds: int = 20
    summary_trigger_count: int = 50


class LoggingSettings(BaseModel):
    level: str = "INFO"
    file: str = "main_server/data/logs/app.log"

    @property
    def abs_file(self) -> Path:
        return _resolve_path(self.file)


class KnowledgeSettings(BaseModel):
    docs_path: str = "main_server/data/knowledge"
    chroma_path: str = "main_server/data/chroma"
    collection_name: str = "voice_crm_kb"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    fetch_k: int = 20
    rerank_enabled: bool = True
    hybrid_enabled: bool = True
    rrf_k: int = 60
    min_vector_score: float = 0.35
    min_rerank_score: float = 0.0
    reject_empty: bool = True
    timeout_seconds: float = 30.0

    @property
    def abs_docs_path(self) -> Path:
        return _resolve_path(self.docs_path)

    @property
    def abs_chroma_path(self) -> Path:
        return _resolve_path(self.chroma_path)


class ASRModelSettings(BaseModel):
    provider: str = "funasr"
    model_dir: str = "SenseVoiceSmall"
    device: str = "cpu"


class VADModelSettings(BaseModel):
    provider: str = "silero-vad"
    model_dir: str = "silero_vad"
    sample_rate: int = 16000
    threshold: float = 0.5
    min_silence_duration_ms: int = 500


class TTSModelSettings(BaseModel):
    provider: str = "edge-tts"
    voice: str = "zh-CN-XiaoxiaoNeural"
    device: str = "cpu"
    compile: bool = False
    model_dir: str = "chattts"


class EmbeddingModelSettings(BaseModel):
    model: str = "BAAI/bge-small-zh-v1.5"
    cache_dir: str = "embedding"


class RerankModelSettings(BaseModel):
    model: str = "BAAI/bge-reranker-base"
    cache_dir: str = "rerank"


class EmailToolSettings(BaseModel):
    enabled: bool = True
    dry_run: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = "voice-crm@localhost"
    use_tls: bool = True


class WebSearchSettings(BaseModel):
    enabled: bool = True
    max_results: int = 5
    timeout_seconds: float = 15.0


class AgentToolSettings(BaseModel):
    max_steps: int = 6


class ToolsSettings(BaseModel):
    email: EmailToolSettings = Field(default_factory=EmailToolSettings)
    web_search: WebSearchSettings = Field(default_factory=WebSearchSettings)
    agent: AgentToolSettings = Field(default_factory=AgentToolSettings)


class ModelsSettings(BaseModel):
    base_path: str = "main_server/data/models"
    asr: ASRModelSettings = Field(default_factory=ASRModelSettings)
    vad: VADModelSettings = Field(default_factory=VADModelSettings)
    tts: TTSModelSettings = Field(default_factory=TTSModelSettings)
    embedding: EmbeddingModelSettings = Field(default_factory=EmbeddingModelSettings)
    rerank: RerankModelSettings = Field(default_factory=RerankModelSettings)

    @property
    def abs_base_path(self) -> Path:
        return _resolve_path(self.base_path)

    @property
    def abs_asr_path(self) -> Path:
        return self.abs_base_path / self.asr.model_dir

    @property
    def abs_vad_path(self) -> Path:
        return self.abs_base_path / self.vad.model_dir

    @property
    def abs_tts_path(self) -> Path:
        return self.abs_base_path / self.tts.model_dir

    @property
    def abs_embedding_cache(self) -> Path:
        return self.abs_base_path / self.embedding.cache_dir

    @property
    def abs_rerank_cache(self) -> Path:
        return self.abs_base_path / self.rerank.cache_dir


class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    jwt: JWTSettings
    cors: CORSSettings = Field(default_factory=CORSSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    knowledge: KnowledgeSettings = Field(default_factory=KnowledgeSettings)
    models: ModelsSettings = Field(default_factory=ModelsSettings)
    providers: ProviderSettings = Field(default_factory=ProviderSettings)
    tools: ToolsSettings = Field(default_factory=ToolsSettings)

    model_config = {"extra": "ignore"}


def _resolve_config_path() -> Path:
    if CONFIG_PATH.is_file():
        return CONFIG_PATH
    if CONFIG_EXAMPLE_PATH.is_file():
        return CONFIG_EXAMPLE_PATH
    return CONFIG_PATH


def _load_yaml_config() -> dict[str, Any]:
    config_path = _resolve_config_path()
    if not config_path.is_file():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def _env_first(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _apply_env_overrides(raw: dict[str, Any]) -> dict[str, Any]:
    """环境变量优先于 YAML，避免密钥写入配置文件。"""
    data = copy.deepcopy(raw) if raw else {}

    llm_api_key = _env_first("LLM_API_KEY", "DEEPSEEK_API_KEY")
    if llm_api_key:
        data.setdefault("llm", {})["api_key"] = llm_api_key

    jwt_secret = _env_first("JWT_SECRET_KEY", "JWT_SECRET")
    if jwt_secret:
        data.setdefault("jwt", {})["secret_key"] = jwt_secret

    smtp_password = _env_first("SMTP_PASSWORD")
    if smtp_password:
        data.setdefault("tools", {}).setdefault("email", {})["smtp_password"] = smtp_password

    cors_origins = _env_first("CORS_ORIGINS")
    if cors_origins:
        data.setdefault("cors", {})["allow_origins"] = [
            origin.strip() for origin in cors_origins.split(",") if origin.strip()
        ]

    return data


def using_example_config() -> bool:
    return not CONFIG_PATH.is_file() and CONFIG_EXAMPLE_PATH.is_file()


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    raw = _apply_env_overrides(_load_yaml_config())
    return Settings(**raw)
