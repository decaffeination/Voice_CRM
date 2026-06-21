from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func

from main_server.core.auth.access_control import resolve_customer_access_scope
from main_server.DB import db_session
from main_server.DB.models import (
    ChatMessageORM,
    ChatSessionORM,
    Customer,
    Followup,
    User,
)
from main_server.config.settings import get_settings
from main_server.DB.database_info import database_display_name
from main_server.Knowledge.doc_registry import list_documents as list_knowledge_docs
from main_server.Knowledge.vector_store import get_vector_store
from main_server.services.audit_service import list_audit_logs
from main_server.services.health_service import get_health_status
from main_server.services.knowledge_service import knowledge_service
from main_server.services.runtime_settings import runtime_settings

_ACTION_LABELS: dict[str, str] = {
    "knowledge.ingest": "上传知识库",
    "knowledge.ingest_directory": "批量导入知识库",
    "knowledge.delete": "删除知识库文档",
    "knowledge.rebuild": "重建知识库索引",
    "knowledge.search": "知识库检索",
    "crm.create": "新增业务记录",
    "crm.update": "更新业务记录",
    "crm.delete": "删除业务记录",
    "crm.lookup": "客户查询",
    "settings.email_update": "系统配置修改",
    "auth.login": "用户登录",
}


def _today_start() -> datetime:
    now = datetime.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _week_start() -> datetime:
    now = datetime.now()
    return (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _apply_customer_scope(query, scope):
    kwargs = scope.owner_filter_kwargs()
    if "owner_user_id" in kwargs:
        return query.filter(Customer.owner_user_id == kwargs["owner_user_id"])
    if "owner_user_ids" in kwargs:
        ids = kwargs["owner_user_ids"]
        if not ids:
            return query.filter(Customer.id < 0)
        return query.filter(Customer.owner_user_id.in_(ids))
    return query


def _resolve_user_name(session, user_id: int | None) -> str:
    if user_id is None:
        return "-"
    user = session.query(User).filter(User.id == user_id).first()
    if user:
        return user.display_name or user.username
    return str(user_id)


def _format_activity(action: str, detail: str, resource: str) -> str:
    if action.startswith("knowledge."):
        return detail or resource or "知识库操作"
    if action == "crm.create" and "customer:" in resource:
        return detail or "新增客户"
    if action == "settings.email_update":
        return "邮件配置已更新"
    if action == "crm.create" and "followup:" in resource:
        return detail or "新增跟进记录"
    return detail or resource or _ACTION_LABELS.get(action, action)


class DashboardService:
    def get_overview(self, *, user_id: int, roles: list[str]) -> dict[str, Any]:
        today = _today_start()
        week = _week_start()

        with db_session() as session:
            today_sessions = (
                session.query(ChatSessionORM)
                .filter(ChatSessionORM.user_id == user_id)
                .filter(ChatSessionORM.created_at >= today)
                .count()
            )
            total_sessions = (
                session.query(ChatSessionORM)
                .filter(ChatSessionORM.user_id == user_id).count()
            )
            today_answers = (
                session.query(ChatMessageORM)
                .join(
                    ChatSessionORM,
                    ChatMessageORM.session_id == ChatSessionORM.session_id,
                )
                .filter(ChatSessionORM.user_id == user_id)
                .filter(ChatMessageORM.role == "assistant")
                .filter(ChatMessageORM.created_at >= today)
                .count()
            )
            total_answers = (
                session.query(ChatMessageORM)
                .join(
                    ChatSessionORM,
                    ChatMessageORM.session_id == ChatSessionORM.session_id,
                )
                .filter(ChatSessionORM.user_id == user_id)
                .filter(ChatMessageORM.role == "assistant")
                .count()
            )
            online_users = (
                session.query(func.count(func.distinct(ChatSessionORM.user_id)))
                .filter(ChatSessionORM.last_active >= datetime.now() - timedelta(hours=1))
                .scalar()
                or 0
            )

            scope = resolve_customer_access_scope(session, user_id, roles)
            customer_query = _apply_customer_scope(session.query(Customer), scope)
            customer_count = customer_query.count()
            new_customers_week = customer_query.filter(
                Customer.created_at >= week
            ).count()

            pending_followups = self._count_pending_followups(session, scope)

            recent_followups = self._list_recent_followups(session, scope, limit=5)

        kb_stats = knowledge_service.stats()
        knowledge_docs = list_knowledge_docs()
        recent_docs = sorted(
            knowledge_docs,
            key=lambda d: d.updated_at or d.ingested_at or datetime.min,
            reverse=True,
        )[:5]
        popular_docs = sorted(
            knowledge_docs, key=lambda d: d.chunk_count, reverse=True
        )[:5]

        ai_metrics = self._ai_metrics(today_answers, total_answers)
        activities = self._recent_activities(limit=10)
        system_status = self._system_status()

        return {
            "overview": {
                "today_sessions": today_sessions,
                "total_sessions": total_sessions,
                "knowledge_documents": kb_stats["document_count"],
                "customer_count": customer_count,
                "ai_answer_count": total_answers,
                "today_ai_answers": today_answers,
                "online_users": online_users,
                "system_status": system_status["overall"],
            },
            "ai_runtime": ai_metrics,
            "knowledge": {
                "document_count": kb_stats["document_count"],
                "chunk_count": kb_stats["chunk_count"],
                "last_updated": kb_stats.get("last_updated"),
                "kb_status": kb_stats.get("kb_status", "-"),
                "recent_documents": [
                    {
                        "doc_id": d.doc_id,
                        "filename": d.filename,
                        "chunk_count": d.chunk_count,
                        "updated_at": d.updated_at.isoformat()
                        if d.updated_at
                        else None,
                    }
                    for d in recent_docs
                ],
                "popular_documents": [
                    {
                        "doc_id": d.doc_id,
                        "filename": d.filename,
                        "chunk_count": d.chunk_count,
                    }
                    for d in popular_docs
                ],
            },
            "crm": {
                "customer_count": customer_count,
                "new_customers_week": new_customers_week,
                "pending_followups": pending_followups,
                "recent_followups": recent_followups,
            },
            "recent_activities": activities,
            "system_status": system_status["services"],
        }

    def _count_pending_followups(self, session, scope) -> int:
        threshold = datetime.now() - timedelta(days=14)
        customers = _apply_customer_scope(session.query(Customer), scope).all()
        pending = 0
        for customer in customers:
            latest = (
                session.query(Followup)
                .filter(Followup.customer_id == customer.id)
                .order_by(Followup.created_at.desc())
                .first()
            )
            if latest is None or (latest.created_at and latest.created_at < threshold):
                pending += 1
        return pending

    def _list_recent_followups(
        self, session, scope, *, limit: int
    ) -> list[dict[str, Any]]:
        customer_ids = [
            c.id for c in _apply_customer_scope(session.query(Customer), scope).all()
        ]
        if not customer_ids:
            return []
        rows = (
            session.query(Followup, Customer.name)
            .join(Customer, Followup.customer_id == Customer.id)
            .filter(Followup.customer_id.in_(customer_ids))
            .order_by(Followup.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": f.id,
                "customer_id": f.customer_id,
                "customer_name": name,
                "content": (f.content or "")[:120],
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f, name in rows
        ]

    def _ai_metrics(
        self, today_answers: int, total_answers: int
    ) -> dict[str, Any]:
        items, _ = list_audit_logs(action="knowledge.search", limit=200, offset=0)
        searches = len(items)
        misses = sum(1 for item in items if "hits=0" in (item.get("detail") or ""))
        hit_rate = (
            round((searches - misses) / searches * 100, 1) if searches else None
        )
        return {
            "today_qa_count": today_answers,
            "total_qa_count": total_answers,
            "knowledge_hit_rate": hit_rate,
            "knowledge_miss_count": misses,
            "avg_response_time_ms": None,
            "token_consumption": None,
        }

    def _recent_activities(self, *, limit: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        audit_items, _ = list_audit_logs(limit=30, offset=0)
        with db_session() as session:
            for item in audit_items:
                events.append(
                    {
                        "type": item["action"],
                        "label": _ACTION_LABELS.get(
                            item["action"], item["action"]
                        ),
                        "description": _format_activity(
                            item["action"],
                            item.get("detail") or "",
                            item.get("resource") or "",
                        ),
                        "user_name": _resolve_user_name(session, item.get("user_id")),
                        "created_at": item.get("created_at"),
                    }
                )

            messages = (
                session.query(ChatMessageORM, ChatSessionORM.user_id)
                .join(
                    ChatSessionORM,
                    ChatMessageORM.session_id == ChatSessionORM.session_id,
                )
                .filter(ChatMessageORM.role == "assistant")
                .order_by(ChatMessageORM.id.desc())
                .limit(8)
                .all()
            )
            for msg, uid in messages:
                events.append(
                    {
                        "type": "ai.qa",
                        "label": "AI 问答",
                        "description": (msg.content or "")[:100],
                        "user_name": _resolve_user_name(session, uid),
                        "created_at": msg.created_at.isoformat()
                        if msg.created_at
                        else None,
                    }
                )

        events.sort(key=lambda e: e.get("created_at") or "", reverse=True)
        return events[:limit]

    def _system_status(self) -> dict[str, Any]:
        health = get_health_status()
        email = runtime_settings.get_email_public_config()

        db_status = "正常"
        try:
            with db_session() as session:
                session.query(User).limit(1).first()
        except Exception:
            db_status = "异常"

        vector_status = "正常"
        try:
            get_vector_store().count()
        except Exception:
            vector_status = "异常"

        llm = health.get("components", {}).get("llm", {})
        llm_status = "正常" if llm.get("status") == "ok" else "异常"

        smtp_status = "正常" if email.get("smtp_configured") else "未配置"

        db_dialect = get_settings().database.dialect
        db_label = database_display_name(db_dialect)

        services = [
            {"name": "LLM 服务", "key": "llm", "status": llm_status},
            {"name": "向量数据库", "key": "vector_db", "status": vector_status},
            {"name": db_label, "key": "database", "status": db_status},
            {"name": "Redis", "key": "redis", "status": "未启用"},
            {"name": "WebSocket", "key": "websocket", "status": "正常"},
            {"name": "SMTP", "key": "smtp", "status": smtp_status},
        ]

        overall = "正常"
        if any(s["status"] == "异常" for s in services):
            overall = "异常"
        elif health.get("status") == "degraded":
            overall = "降级"

        return {"overall": overall, "services": services}


dashboard_service = DashboardService()
