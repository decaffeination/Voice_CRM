"""认证相关请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from main_server.config.constants import TOKEN_TYPE


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = TOKEN_TYPE


class TokenPayload(BaseModel):
    sub: str
    user_id: int
    username: str
    roles: list[str] = Field(default_factory=list)
    display_name: str | None = None
    exp: int


class CurrentUser(BaseModel):
    user_id: int
    username: str
    display_name: str | None = None
    roles: list[str] = Field(default_factory=list)
