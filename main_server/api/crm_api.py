from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from main_server.api.deps.auth_dep import CurrentUser, require_crm_read
from main_server.services.crm_service import crm_service

router = APIRouter(prefix="/api/crm", tags=["crm"])


class CustomerListResponse(BaseModel):
    customers: list[dict[str, Any]]
    total: int


class CustomerLookupResponse(BaseModel):
    found: bool
    is_new: bool
    ambiguous: bool
    customers: list[dict[str, Any]] = Field(default_factory=list)
    customer: dict[str, Any] | None = None


@router.get("/customers", response_model=CustomerListResponse)
def list_customers(
    keyword: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_crm_read),
):
    customers = crm_service.list_customers(
        user_id=current_user.user_id,
        keyword=keyword,
        limit=limit,
        roles=current_user.roles,
    )
    return CustomerListResponse(customers=customers, total=len(customers))


@router.get("/customers/lookup", response_model=CustomerLookupResponse)
def lookup_customer(
    name: str = Query(..., min_length=1),
    current_user: CurrentUser = Depends(require_crm_read),
):
    result = crm_service.lookup_customer(
        name,
        user_id=current_user.user_id,
        roles=current_user.roles,
    )
    return CustomerLookupResponse(**result.model_dump())


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    current_user: CurrentUser = Depends(require_crm_read),
):
    return crm_service.get_customer_by_id(
        customer_id,
        user_id=current_user.user_id,
        roles=current_user.roles,
    )


@router.get("/customers/{customer_id}/profile")
def get_customer_profile(
    customer_id: int,
    current_user: CurrentUser = Depends(require_crm_read),
):
    return crm_service.get_customer_profile(
        customer_id,
        user_id=current_user.user_id,
        roles=current_user.roles,
    )


@router.get("/customers/{customer_id}/followups")
def list_followups(
    customer_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_crm_read),
):
    return crm_service.list_followups(
        customer_id,
        limit=limit,
        user_id=current_user.user_id,
        roles=current_user.roles,
    )


@router.get("/customers/{customer_id}/orders")
def list_orders(
    customer_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    current_user: CurrentUser = Depends(require_crm_read),
):
    return crm_service.list_orders(
        customer_id,
        limit=limit,
        user_id=current_user.user_id,
        roles=current_user.roles,
    )


@router.get("/customers/{customer_id}/contracts")
def list_contracts(
    customer_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    current_user: CurrentUser = Depends(require_crm_read),
):
    return crm_service.list_contracts(
        customer_id,
        limit=limit,
        user_id=current_user.user_id,
        roles=current_user.roles,
    )


@router.get("/recent-updates")
def list_recent_updates(
    days: int = Query(default=30, ge=1, le=365),
    current_user: CurrentUser = Depends(require_crm_read),
):
    customers = crm_service.list_recent_updates(
        days=days,
        user_id=current_user.user_id,
        roles=current_user.roles,
    )
    return {"days": days, "count": len(customers), "customers": customers}
