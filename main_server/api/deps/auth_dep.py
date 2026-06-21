"""FastAPI 认证与 RBAC 依赖统一出口。

API 层应从此模块导入 Depends，避免直接引用 jwt_auth / permission。
"""

from main_server.core.auth.auth_schema import CurrentUser
from main_server.core.auth.jwt_auth import get_current_user, get_current_user_from_token
from main_server.core.auth.permission import (
    Role,
    require_admin,
    require_business_user,
    require_crm_read,
    require_roles,
    user_has_any_role,
    user_is_admin,
)

__all__ = [
    "CurrentUser",
    "Role",
    "get_current_user",
    "get_current_user_from_token",
    "require_admin",
    "require_business_user",
    "require_crm_read",
    "require_roles",
    "user_has_any_role",
    "user_is_admin",
]
