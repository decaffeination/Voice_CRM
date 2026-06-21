from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent.state import ConversationState, bind_customer, mark_new_customer
import main_server.CRM.repository.contract_repo as contract_repo
import main_server.CRM.repository.customer_repo as customer_repo
import main_server.CRM.repository.followup_repo as followup_repo
import main_server.CRM.repository.order_repo as order_repo
import main_server.CRM.writes.contract_write as contract_write
import main_server.CRM.writes.curstomer_write as curstomer_write
import main_server.CRM.writes.followup_write as followup_write
import main_server.CRM.writes.order_write as order_write
from main_server.CRM.storage_guard import crm_db_session
from main_server.config.constants import (
    MUTATION_CREATE,
    MUTATION_DELETE,
    MUTATION_UPDATE,
    PENDING_WRITE_AWAITING,
    PENDING_WRITE_DRAFT,
    WRITE_ACTIONS,
    WRITE_ENTITY_TYPES,
    WRITE_TYPE_CONTRACT,
    WRITE_TYPE_CUSTOMER,
    WRITE_TYPE_FOLLOWUP,
    WRITE_TYPE_ORDER,
    ENTITY_ID_KEYS,
)
from main_server.core.audit import audit_log
from main_server.core.auth.access_control import (
    assert_customer_access,
    can_view_employee_customers,
    resolve_customer_access_scope,
)
from main_server.core.exceptions import CRMError, PermissionDeniedError
from main_server.DB.models import Customer, Employee
from main_server.config.settings import get_settings
from main_server.DB.search import case_insensitive_like
from main_server.services.tool_result import AgentToolResult


class CustomerLookupResult(BaseModel):
    """客户查询结果，新客户由代码判定，不交给 LLM。"""

    found: bool = False
    is_new: bool = False
    ambiguous: bool = False
    customers: list[dict[str, Any]] = Field(default_factory=list)
    customer: dict[str, Any] | None = None


def _get_customer_or_404(session: Session, customer_id: int) -> Customer:
    customer = customer_repo.get_by_id(session, customer_id)
    if customer is None:
        raise CRMError(
            f"客户不存在: id={customer_id}",
            code="NOT_FOUND",
            status_code=404,
        )
    return customer


class CRMService:
    """CRM 业务逻辑层：增查直接可用；改删经 prepare → 人工确认后 execute。"""

    _ID_KEYS: dict[str, str] = ENTITY_ID_KEYS

    def lookup_customer(
        self,
        name: str,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> CustomerLookupResult:
        keyword = name.strip()
        if not keyword:
            raise CRMError("客户名称不能为空", code="VALIDATION_ERROR", status_code=400)

        with crm_db_session() as session:
            scope = resolve_customer_access_scope(session, user_id, roles)
            matches = customer_repo.search_by_name(
                session,
                keyword,
                **scope.owner_filter_kwargs(),
            )
            if not matches:
                audit_log(
                    "crm.lookup",
                    resource="customer",
                    detail=f"name={keyword} is_new=true",
                )
                return CustomerLookupResult(found=False, is_new=True)

            items = [customer_repo.to_dict(c) for c in matches]
            audit_log(
                "crm.lookup",
                resource="customer",
                detail=f"name={keyword} count={len(items)}",
            )
            if len(matches) == 1:
                return CustomerLookupResult(
                    found=True,
                    is_new=False,
                    customer=items[0],
                    customers=items,
                )

            return CustomerLookupResult(
                found=True,
                is_new=False,
                ambiguous=True,
                customers=items,
            )

    def get_customer_by_id(
        self,
        customer_id: int,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        with crm_db_session() as session:
            customer = _get_customer_or_404(session, customer_id)
            assert_customer_access(session, customer, user_id, roles)
            result = customer_repo.to_dict(customer)
            audit_log(
                "crm.read",
                resource=f"customer:{customer_id}",
            )
            return result

    def list_customers(
        self,
        *,
        user_id: int,
        keyword: str | None = None,
        limit: int = 50,
        roles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        with crm_db_session() as session:
            scope = resolve_customer_access_scope(session, user_id, roles)
            filter_kwargs = scope.owner_filter_kwargs()
            if keyword:
                matches = customer_repo.search_by_name(
                    session,
                    keyword,
                    limit=limit,
                    **filter_kwargs,
                )
            elif scope.mode == "all":
                matches = customer_repo.list_all(session, limit=limit)
            elif scope.mode == "team":
                matches = customer_repo.list_by_owner_ids(
                    session, filter_kwargs.get("owner_user_ids") or []
                )[:limit]
            else:
                matches = customer_repo.list_by_owner(session, user_id)[:limit]
            audit_log(
                "crm.list",
                resource="customer",
                detail=f"keyword={keyword or '-'} count={len(matches)}",
            )
            return [customer_repo.to_dict(c) for c in matches]

    def get_customer_profile(
        self,
        customer_id: int,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        """客户联系方式 + 最近订单 + 最近合同 + 最近跟进。"""
        with crm_db_session() as session:
            customer = _get_customer_or_404(session, customer_id)
            assert_customer_access(session, customer, user_id, roles)

            last_order = order_repo.get_latest_by_customer(session, customer_id)
            last_contract = contract_repo.get_latest_by_customer(session, customer_id)
            last_followup = followup_repo.get_latest_by_customer(session, customer_id)

            audit_log(
                "crm.read_profile",
                resource=f"customer:{customer_id}",
            )
            return {
                "customer": customer_repo.to_dict(customer),
                "last_order": order_repo.to_dict(last_order) if last_order else None,
                "last_contract": (
                    contract_repo.to_dict(last_contract) if last_contract else None
                ),
                "last_followup": (
                    followup_repo.to_dict(last_followup) if last_followup else None
                ),
            }

    def get_last_order(
        self,
        customer_id: int,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any] | None:
        with crm_db_session() as session:
            customer = _get_customer_or_404(session, customer_id)
            assert_customer_access(session, customer, user_id, roles)
            order = order_repo.get_latest_by_customer(session, customer_id)
            return order_repo.to_dict(order) if order else None

    def list_orders(
        self,
        customer_id: int,
        limit: int = 10,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        with crm_db_session() as session:
            customer = _get_customer_or_404(session, customer_id)
            assert_customer_access(session, customer, user_id, roles)
            orders = order_repo.list_by_customer(session, customer_id, limit=limit)
            return [order_repo.to_dict(o) for o in orders]

    def list_contracts(
        self,
        customer_id: int,
        limit: int = 10,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        with crm_db_session() as session:
            customer = _get_customer_or_404(session, customer_id)
            assert_customer_access(session, customer, user_id, roles)
            contracts = contract_repo.list_by_customer(
                session, customer_id, limit=limit
            )
            return [contract_repo.to_dict(c) for c in contracts]

    def list_followups(
        self,
        customer_id: int,
        limit: int = 20,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        with crm_db_session() as session:
            customer = _get_customer_or_404(session, customer_id)
            assert_customer_access(session, customer, user_id, roles)
            items = followup_repo.list_by_customer(session, customer_id, limit=limit)
            return [followup_repo.to_dict(f) for f in items]

    def list_employee_customers(
        self,
        employee_name: str,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        """查询某职员对接的客户名单。"""
        keyword = employee_name.strip()
        if not keyword:
            raise CRMError("员工姓名不能为空", code="VALIDATION_ERROR", status_code=400)

        with crm_db_session() as session:
            pattern = f"%{keyword}%"
            dialect = get_settings().database.dialect
            employees = (
                session.query(Employee)
                .filter(case_insensitive_like(Employee.name, pattern, dialect))
                .all()
            )
            if not employees:
                raise CRMError(
                    f"未找到员工: {employee_name}",
                    code="NOT_FOUND",
                    status_code=404,
                )
            if len(employees) > 1:
                return {
                    "ambiguous": True,
                    "employees": [
                        {
                            "id": e.id,
                            "name": e.name,
                            "department": e.department,
                        }
                        for e in employees
                    ],
                    "customers": [],
                }

            employee = employees[0]
            if user_id is not None and not can_view_employee_customers(
                session,
                viewer_user_id=user_id,
                target_employee_user_id=employee.user_id,
                roles=roles,
            ):
                raise PermissionDeniedError("无权查看该员工的客户列表")

            customers = (
                customer_repo.list_by_employee_user_id(session, employee.user_id)
                if employee.user_id
                else []
            )
            audit_log(
                "crm.list_employee_customers",
                resource=f"employee:{employee.id}",
            )
            return {
                "ambiguous": False,
                "employee": {
                    "id": employee.id,
                    "name": employee.name,
                    "department": employee.department,
                },
                "customers": [customer_repo.to_dict(c) for c in customers],
            }

    def list_recent_updates(
        self,
        days: int = 30,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """最近 N 天有更新的客户列表。"""
        with crm_db_session() as session:
            scope = resolve_customer_access_scope(session, user_id, roles)
            customers = customer_repo.list_recent_updated(
                session,
                days=days,
                **scope.owner_filter_kwargs(),
            )
            audit_log(
                "crm.list_recent",
                detail=f"days={days} count={len(customers)}",
            )
            return [customer_repo.to_dict(c) for c in customers]

    def add_customer(
        self,
        *,
        name: str,
        contact_person: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        owner_user_id: int | None = None,
    ) -> dict[str, Any]:
        with crm_db_session() as session:
            result = curstomer_write.create_customer(
                session,
                name=name,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                owner_user_id=owner_user_id,
            )
            audit_log(
                "crm.create",
                resource=f"customer:{result['id']}",
                detail=f"name={name}",
            )
            return result

    def add_followup(
        self,
        *,
        customer_id: int,
        content: str,
        followup_type: str = "note",
        created_by: int | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        with crm_db_session() as session:
            customer = _get_customer_or_404(session, customer_id)
            assert_customer_access(session, customer, created_by, roles)
            result = followup_write.create_followup(
                session,
                customer_id=customer_id,
                content=content,
                followup_type=followup_type,
                created_by=created_by,
            )
            audit_log(
                "crm.create",
                resource=f"followup:{result['id']}",
                detail=f"customer_id={customer_id}",
            )
            return result

    def add_contract(
        self,
        *,
        customer_id: int,
        title: str,
        amount: float = 0,
        status: str = "draft",
        signed_at: datetime | None = None,
        content: str | None = None,
        created_by: int | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        with crm_db_session() as session:
            customer = _get_customer_or_404(session, customer_id)
            assert_customer_access(session, customer, created_by, roles)
            result = contract_write.create_contract(
                session,
                customer_id=customer_id,
                title=title,
                amount=amount,
                status=status,
                signed_at=signed_at,
                content=content,
                created_by=created_by,
            )
            audit_log(
                "crm.create",
                resource=f"contract:{result['id']}",
                detail=f"customer_id={customer_id}",
            )
            return result

    def add_order(
        self,
        *,
        customer_id: int,
        title: str,
        amount: float = 0,
        status: str = "pending",
        contract_id: int | None = None,
        order_date: datetime | None = None,
        content: str | None = None,
        created_by: int | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        with crm_db_session() as session:
            customer = _get_customer_or_404(session, customer_id)
            assert_customer_access(session, customer, created_by, roles)
            result = order_repo.create_order(
                session,
                customer_id=customer_id,
                title=title,
                amount=amount,
                status=status,
                contract_id=contract_id,
                order_date=order_date,
                content=content,
                created_by=created_by,
            )
            audit_log(
                "crm.create",
                resource=f"order:{result['id']}",
                detail=f"customer_id={customer_id}",
            )
            return result

    def get_customer_profile_by_name(
        self,
        name: str,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        lookup = self.lookup_customer(name, user_id=user_id, roles=roles)
        if lookup.is_new:
            return {"is_new": True, "customer_name": name, "profile": None}
        if lookup.ambiguous:
            return {"ambiguous": True, "customers": lookup.customers}
        customer = lookup.customer
        assert customer is not None
        profile = self.get_customer_profile(
            customer["id"], user_id=user_id, roles=roles
        )
        return {"is_new": False, "customer": customer, "profile": profile}

    def summarize_recent_customers(
        self,
        *,
        days: int = 30,
        user_id: int | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        customers = self.list_recent_updates(
            days=days, user_id=user_id, roles=roles
        )
        return {"days": days, "count": len(customers), "customers": customers}

    def build_pending_write(
        self,
        write_type: str,
        payload: dict[str, Any],
        turn_count: int,
        *,
        action: str = MUTATION_CREATE,
        before: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        pending: dict[str, Any] = {
            "action": action,
            "type": write_type,
            "payload": payload,
            "status": PENDING_WRITE_DRAFT,
            "created_at_turn": turn_count,
        }
        if before:
            pending["before"] = before
        return pending

    def _normalize_mutation(
        self,
        action: str,
        write_type: str,
    ) -> tuple[str, str]:
        if action not in WRITE_ACTIONS:
            raise CRMError(
                f"不支持的操作: {action}",
                code="VALIDATION_ERROR",
                status_code=400,
            )
        if write_type not in WRITE_ENTITY_TYPES:
            raise CRMError(
                f"不支持的实体类型: {write_type}",
                code="VALIDATION_ERROR",
                status_code=400,
            )
        return action, write_type

    def _record_id_from_payload(
        self, write_type: str, payload: dict[str, Any]
    ) -> int:
        id_key = self._ID_KEYS[write_type]
        raw = payload.get(id_key)
        if raw is None:
            raise CRMError(
                f"操作 {write_type} 需提供 {id_key}",
                code="VALIDATION_ERROR",
                status_code=400,
            )
        return int(raw)

    def _extract_updates(
        self, write_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        id_key = self._ID_KEYS[write_type]
        reserved = {id_key, "customer_id"}
        updates = {
            key: value
            for key, value in payload.items()
            if key not in reserved and value is not None
        }
        if not updates:
            raise CRMError(
                "修改操作至少提供一个待更新字段",
                code="VALIDATION_ERROR",
                status_code=400,
            )
        return updates

    def _load_entity_snapshot(
        self,
        session: Session,
        write_type: str,
        record_id: int,
        user_id: int | None,
        roles: list[str] | None,
    ) -> dict[str, Any]:
        if write_type == WRITE_TYPE_CUSTOMER:
            customer = _get_customer_or_404(session, record_id)
            assert_customer_access(session, customer, user_id, roles)
            return customer_repo.to_dict(customer)
        if write_type == WRITE_TYPE_FOLLOWUP:
            followup = followup_repo.get_by_id(session, record_id)
            if followup is None:
                raise CRMError(
                    f"跟进不存在: id={record_id}",
                    code="NOT_FOUND",
                    status_code=404,
                )
            customer = _get_customer_or_404(session, followup.customer_id)
            assert_customer_access(session, customer, user_id, roles)
            return followup_repo.to_dict(followup)
        if write_type == WRITE_TYPE_ORDER:
            order = order_repo.get_by_id(session, record_id)
            if order is None:
                raise CRMError(
                    f"订单不存在: id={record_id}",
                    code="NOT_FOUND",
                    status_code=404,
                )
            customer = _get_customer_or_404(session, order.customer_id)
            assert_customer_access(session, customer, user_id, roles)
            return order_repo.to_dict(order)
        if write_type == WRITE_TYPE_CONTRACT:
            contract = contract_repo.get_by_id(session, record_id)
            if contract is None:
                raise CRMError(
                    f"合同不存在: id={record_id}",
                    code="NOT_FOUND",
                    status_code=404,
                )
            customer = _get_customer_or_404(session, contract.customer_id)
            assert_customer_access(session, customer, user_id, roles)
            return contract_repo.to_dict(contract)
        raise CRMError(
            f"不支持的实体类型: {write_type}",
            code="VALIDATION_ERROR",
            status_code=400,
        )

    def execute_write(
        self,
        write_type: str,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        roles: list[str] | None = None,
        action: str = MUTATION_CREATE,
    ) -> dict[str, Any]:
        action, write_type = self._normalize_mutation(action, write_type)
        if action == MUTATION_CREATE:
            return self._execute_create(
                write_type, payload, user_id=user_id, roles=roles
            )
        if action == MUTATION_UPDATE:
            return self._execute_update(
                write_type, payload, user_id=user_id, roles=roles
            )
        return self._execute_delete(
            write_type, payload, user_id=user_id, roles=roles
        )

    def _execute_create(
        self,
        write_type: str,
        payload: dict[str, Any],
        *,
        user_id: int | None,
        roles: list[str] | None,
    ) -> dict[str, Any]:
        if write_type == WRITE_TYPE_CUSTOMER:
            return self.add_customer(
                name=payload["name"],
                contact_person=payload.get("contact_person"),
                phone=payload.get("phone"),
                email=payload.get("email"),
                address=payload.get("address"),
                owner_user_id=user_id,
            )
        if write_type == WRITE_TYPE_FOLLOWUP:
            return self.add_followup(
                customer_id=int(payload["customer_id"]),
                content=payload["content"],
                followup_type=payload.get("followup_type", "note"),
                created_by=user_id,
                roles=roles,
            )
        if write_type == WRITE_TYPE_CONTRACT:
            return self.add_contract(
                customer_id=int(payload["customer_id"]),
                title=payload["title"],
                amount=float(payload.get("amount", 0)),
                status=payload.get("status", "draft"),
                content=payload.get("content"),
                created_by=user_id,
                roles=roles,
            )
        if write_type == WRITE_TYPE_ORDER:
            return self.add_order(
                customer_id=int(payload["customer_id"]),
                title=payload["title"],
                amount=float(payload.get("amount", 0)),
                status=payload.get("status", "pending"),
                content=payload.get("content"),
                created_by=user_id,
                roles=roles,
            )
        raise CRMError(
            f"不支持的写库类型: {write_type}",
            code="VALIDATION_ERROR",
            status_code=400,
        )

    def _execute_update(
        self,
        write_type: str,
        payload: dict[str, Any],
        *,
        user_id: int | None,
        roles: list[str] | None,
    ) -> dict[str, Any]:
        record_id = self._record_id_from_payload(write_type, payload)
        updates = self._extract_updates(write_type, payload)
        with crm_db_session() as session:
            before = self._load_entity_snapshot(
                session, write_type, record_id, user_id, roles
            )
            if write_type == WRITE_TYPE_CUSTOMER:
                result = curstomer_write.update_customer(
                    session, record_id, updates=updates
                )
            elif write_type == WRITE_TYPE_FOLLOWUP:
                result = followup_write.update_followup(
                    session,
                    record_id,
                    content=updates.get("content"),
                    followup_type=updates.get("followup_type"),
                )
            elif write_type == WRITE_TYPE_CONTRACT:
                result = contract_write.update_contract(
                    session, record_id, updates=updates
                )
            elif write_type == WRITE_TYPE_ORDER:
                result = order_write.update_order(
                    session, record_id, updates=updates
                )
            else:
                raise CRMError(
                    f"不支持的写库类型: {write_type}",
                    code="VALIDATION_ERROR",
                    status_code=400,
                )
            audit_log(
                "crm.update",
                resource=f"{write_type}:{record_id}",
                detail=f"before={before} after={result}",
            )
            return result

    def _execute_delete(
        self,
        write_type: str,
        payload: dict[str, Any],
        *,
        user_id: int | None,
        roles: list[str] | None,
    ) -> dict[str, Any]:
        record_id = self._record_id_from_payload(write_type, payload)
        with crm_db_session() as session:
            before = self._load_entity_snapshot(
                session, write_type, record_id, user_id, roles
            )
            if write_type == WRITE_TYPE_CUSTOMER:
                result = curstomer_write.archive_customer(session, record_id)
            elif write_type == WRITE_TYPE_FOLLOWUP:
                result = followup_write.delete_followup(session, record_id)
            elif write_type == WRITE_TYPE_CONTRACT:
                result = contract_write.delete_contract(session, record_id)
            elif write_type == WRITE_TYPE_ORDER:
                result = order_write.delete_order(session, record_id)
            else:
                raise CRMError(
                    f"不支持的写库类型: {write_type}",
                    code="VALIDATION_ERROR",
                    status_code=400,
                )
            audit_log(
                "crm.delete",
                resource=f"{write_type}:{record_id}",
                detail=f"deleted={before}",
            )
            return result

    def resolve_customer_id(
        self,
        *,
        conversation_state: ConversationState,
        turn_count: int,
        user_id: int | None,
        customer_id: int | None = None,
        customer_name: str | None = None,
        roles: list[str] | None = None,
    ) -> tuple[int | None, dict[str, Any] | None]:
        if customer_id:
            return int(customer_id), None

        customer_ctx = conversation_state.get("customer_context") or {}

        if customer_name:
            lookup = self.lookup_customer(
                customer_name, user_id=user_id, roles=roles
            )
            if lookup.is_new:
                mark_new_customer(
                    conversation_state,
                    customer_name=customer_name,
                    turn_count=turn_count,
                )
                return None, {
                    "is_new": True,
                    "customer_name": customer_name,
                    "message": f"{customer_name} 是新客户，暂无合作记录",
                }
            if lookup.ambiguous:
                return None, {
                    "ambiguous": True,
                    "customers": lookup.customers,
                }
            customer = lookup.customer
            if customer:
                bind_customer(
                    conversation_state,
                    customer_id=customer["id"],
                    customer_name=customer["name"],
                    turn_count=turn_count,
                )
                return int(customer["id"]), None

        if customer_ctx.get("customer_id"):
            return int(customer_ctx["customer_id"]), None

        return None, {"error": "customer_not_found", "message": "请先说明客户名称"}

    def get_customer_profile_for_agent(
        self,
        *,
        conversation_state: ConversationState,
        turn_count: int,
        user_id: int | None,
        customer_name: str | None = None,
        customer_id: int | None = None,
        roles: list[str] | None = None,
    ) -> AgentToolResult:
        if customer_name:
            result = self.get_customer_profile_by_name(
                customer_name, user_id=user_id, roles=roles
            )
            if result.get("is_new"):
                mark_new_customer(
                    conversation_state,
                    customer_name=customer_name,
                    turn_count=turn_count,
                )
            elif not result.get("ambiguous") and result.get("customer"):
                customer = result["customer"]
                bind_customer(
                    conversation_state,
                    customer_id=customer["id"],
                    customer_name=customer["name"],
                    turn_count=turn_count,
                )
            return AgentToolResult(payload=result)

        resolved_id, err = self.resolve_customer_id(
            conversation_state=conversation_state,
            turn_count=turn_count,
            user_id=user_id,
            customer_id=customer_id,
            customer_name=customer_name,
            roles=roles,
        )
        if err:
            return AgentToolResult(payload=err)
        assert resolved_id is not None
        profile = self.get_customer_profile(
            resolved_id, user_id=user_id, roles=roles
        )
        customer_ctx = conversation_state.get("customer_context") or {}
        return AgentToolResult(payload={"customer": customer_ctx, "profile": profile})

    def list_recent_updates_for_agent(
        self,
        *,
        days: int,
        user_id: int | None,
        roles: list[str] | None = None,
    ) -> AgentToolResult:
        customers = self.list_recent_updates(
            days=days, user_id=user_id, roles=roles
        )
        return AgentToolResult(
            payload={"days": days, "count": len(customers), "customers": customers}
        )

    def prepare_write(
        self,
        *,
        conversation_state: ConversationState,
        turn_count: int,
        user_id: int | None,
        write_type: str,
        payload: dict[str, Any],
        customer_name: str | None = None,
        customer_id: int | None = None,
        roles: list[str] | None = None,
        action: str = MUTATION_CREATE,
    ) -> AgentToolResult:
        existing = conversation_state.get("pending_write")
        if existing and existing.get("status") == PENDING_WRITE_AWAITING:
            return AgentToolResult(
                payload={"error": "pending_exists", "pending_write": existing}
            )

        try:
            action, write_type = self._normalize_mutation(action, write_type)
        except CRMError as exc:
            return AgentToolResult(
                payload={"error": "validation", "message": str(exc)}
            )

        payload = dict(payload)
        before: dict[str, Any] | None = None

        if action == MUTATION_CREATE:
            if write_type != WRITE_TYPE_CUSTOMER:
                resolved_id, err = self.resolve_customer_id(
                    conversation_state=conversation_state,
                    turn_count=turn_count,
                    user_id=user_id,
                    customer_id=customer_id,
                    customer_name=customer_name,
                    roles=roles,
                )
                if err:
                    return AgentToolResult(payload=err)
                if resolved_id is not None:
                    payload["customer_id"] = resolved_id
            elif "name" not in payload and customer_name:
                payload["name"] = customer_name

            if write_type == WRITE_TYPE_CUSTOMER and "name" not in payload:
                return AgentToolResult(
                    payload={"error": "validation", "message": "新增客户需提供 name"}
                )
            if write_type != WRITE_TYPE_CUSTOMER and "customer_id" not in payload:
                return AgentToolResult(
                    payload={"error": "validation", "message": "未找到可写入的客户"}
                )
            if write_type == WRITE_TYPE_FOLLOWUP and "content" not in payload:
                return AgentToolResult(
                    payload={"error": "validation", "message": "跟进记录需提供 content"}
                )
            if write_type in (WRITE_TYPE_CONTRACT, WRITE_TYPE_ORDER) and "title" not in payload:
                return AgentToolResult(
                    payload={"error": "validation", "message": f"{write_type} 需提供 title"}
                )
        else:
            id_key = self._ID_KEYS[write_type]
            if action in (MUTATION_UPDATE, MUTATION_DELETE):
                if write_type != WRITE_TYPE_CUSTOMER:
                    resolved_id, err = self.resolve_customer_id(
                        conversation_state=conversation_state,
                        turn_count=turn_count,
                        user_id=user_id,
                        customer_id=customer_id or payload.get("customer_id"),
                        customer_name=customer_name,
                        roles=roles,
                    )
                    if err and id_key not in payload:
                        return AgentToolResult(payload=err)
                    if resolved_id is not None and id_key not in payload:
                        payload.setdefault("customer_id", resolved_id)

                if id_key not in payload:
                    return AgentToolResult(
                        payload={
                            "error": "validation",
                            "message": f"{action} 操作需提供 {id_key}",
                        }
                    )

                try:
                    with crm_db_session() as session:
                        before = self._load_entity_snapshot(
                            session,
                            write_type,
                            int(payload[id_key]),
                            user_id,
                            roles,
                        )
                except CRMError as exc:
                    return AgentToolResult(
                        payload={"error": exc.code or "validation", "message": str(exc)}
                    )

                if action == MUTATION_UPDATE:
                    try:
                        self._extract_updates(write_type, payload)
                    except CRMError as exc:
                        return AgentToolResult(
                            payload={"error": "validation", "message": str(exc)}
                        )

        pending = self.build_pending_write(
            write_type,
            payload,
            turn_count,
            action=action,
            before=before,
        )
        conversation_state["pending_write"] = pending
        action_hint = {
            MUTATION_CREATE: "写入",
            MUTATION_UPDATE: "修改",
            MUTATION_DELETE: "删除",
        }[action]
        return AgentToolResult(
            payload={
                "prepared": True,
                "action": action,
                "write_type": write_type,
                "pending_write": pending,
                "preview": payload,
                "before": before,
                "message": (
                    f"已生成待确认{action_hint}，需用户回复「确认」后才会变更数据库"
                ),
            },
            side_effects={"needs_confirm": True},
        )


crm_service = CRMService()
