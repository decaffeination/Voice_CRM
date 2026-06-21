"""CORS 配置解析（config.yaml + 环境变量）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CORSSettings(BaseModel):
    allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])

    @property
    def resolved_origins(self) -> list[str]:
        cleaned = [origin.strip() for origin in self.allow_origins if origin.strip()]
        return cleaned or ["*"]

    @property
    def uses_wildcard(self) -> bool:
        return "*" in self.resolved_origins
