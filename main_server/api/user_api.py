from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from main_server.core.auth.auth_schema import LoginRequest, TokenResponse
from main_server.core.auth.auth_service import login
from main_server.api.deps.auth_dep import (
    CurrentUser,
    get_current_user,
    require_admin,
)
from main_server.core.auth.permission import (
    DEFAULT_ROLE_SEEDS,
    Role,
    load_user_with_roles,
)
from main_server.core.auth.user_schema import (
    ChangePasswordRequest,
    CreateUserRequest,
    ResetPasswordRequest,
    RoleInfo,
    UpdateUserRequest,
    UpdateUserRolesRequest,
    UserListResponse,
    UserResponse,
)
from main_server.core.auth.user_service import (
    change_password,
    create_user,
    delete_user,
    list_users,
    reset_password,
    update_user,
    update_user_roles,
    user_to_dict,
)
from main_server.core.exceptions import NotFoundError
from main_server.DB import get_db
from main_server.DB.repositories import user_repo

router = APIRouter(tags=["users"])


@router.post("/auth/login", response_model=TokenResponse)
def login_api(body: LoginRequest, db: Session = Depends(get_db)):
    return login(db, body.username, body.password)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = load_user_with_roles(db, current_user.user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    return UserResponse(**user_to_dict(user))


@router.get("/roles", response_model=list[RoleInfo])
def list_roles(db: Session = Depends(get_db)):
    return [
        RoleInfo(
            code=code,
            name=name,
            description=desc,
            user_count=user_repo.count_users_by_role_code(db, code),
        )
        for code, name, desc in DEFAULT_ROLE_SEEDS
    ]


@router.get("/users", response_model=UserListResponse)
def list_users_api(
    keyword: str | None = Query(default=None),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users, total = list_users(
        db,
        keyword=keyword,
        role=role,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return UserListResponse(
        items=[UserResponse(**user_to_dict(user)) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/users", response_model=UserResponse)
def create_user_api(
    body: CreateUserRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = create_user(
        db,
        username=body.username,
        password=body.password,
        display_name=body.display_name,
        roles=body.roles,
    )
    return UserResponse(**user_to_dict(user))


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user_api(
    user_id: int,
    body: UpdateUserRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = update_user(
        db,
        user_id,
        display_name=body.display_name,
        is_active=body.is_active,
    )
    return UserResponse(**user_to_dict(user))


@router.patch("/users/{user_id}/roles", response_model=UserResponse)
def update_user_roles_api(
    user_id: int,
    body: UpdateUserRolesRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = update_user_roles(
        db,
        user_id,
        body.roles,
        operator_user_id=current_user.user_id,
    )
    return UserResponse(**user_to_dict(user))


@router.delete("/users/{user_id}")
def delete_user_api(
    user_id: int,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    delete_user(db, user_id, operator_user_id=current_user.user_id)
    return {"message": "用户已删除"}


@router.put("/users/me/password")
def change_my_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    change_password(
        db,
        current_user.user_id,
        old_password=body.old_password,
        new_password=body.new_password,
    )
    return {"message": "密码修改成功"}


@router.patch("/users/{user_id}/password")
def reset_user_password(
    user_id: int,
    body: ResetPasswordRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    reset_password(db, user_id, body.new_password)
    return {"message": "密码重置成功"}
