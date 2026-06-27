from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from main_server.api.deps.auth_dep import CurrentUser, require_admin
from main_server.services import rbac_service

router = APIRouter(prefix="/api/admin", tags=["admin-rbac"])


class PermissionTreeNode(BaseModel):
    key: str
    label: str
    children: list["PermissionTreeNode"] = Field(default_factory=list)


class PermissionTreeResponse(BaseModel):
    items: list[PermissionTreeNode]


class RolePermissionsResponse(BaseModel):
    role_code: str
    permission_codes: list[str]


class RolePermissionsUpdateRequest(BaseModel):
    permission_codes: list[str] = Field(..., min_length=1)


@router.get("/permissions/tree", response_model=PermissionTreeResponse)
def get_permission_tree(_: CurrentUser = Depends(require_admin)):
    return PermissionTreeResponse(items=rbac_service.get_permission_tree())


@router.get("/roles/{role_code}/permissions", response_model=RolePermissionsResponse)
def get_role_permissions(role_code: str, _: CurrentUser = Depends(require_admin)):
    return RolePermissionsResponse(**rbac_service.get_role_permissions(role_code))


@router.patch("/roles/{role_code}/permissions", response_model=RolePermissionsResponse)
def update_role_permissions(
    role_code: str,
    body: RolePermissionsUpdateRequest,
    current_user: CurrentUser = Depends(require_admin),
):
    result = rbac_service.update_role_permissions(
        role_code,
        body.permission_codes,
        operator_user_id=current_user.user_id,
    )
    return RolePermissionsResponse(**result)
