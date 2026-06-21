"""用户管理相关请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    user_id: int
    username: str
    display_name: str | None = None
    roles: list[str] = Field(default_factory=list)
    is_active: bool = True


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)
    roles: list[str] = Field(..., min_length=1)


class UpdateUserRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    is_active: bool | None = None


class UpdateUserRolesRequest(BaseModel):
    roles: list[str] = Field(..., min_length=1)


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


class RoleInfo(BaseModel):
    code: str
    name: str
    description: str | None = None
