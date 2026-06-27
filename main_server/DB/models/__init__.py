"""ORM 表定义统一导出，供 Alembic / metadata 注册。"""

from main_server.DB.models.audit_log import AuditLogORM
from main_server.DB.models.chat_message import ChatMessageORM
from main_server.DB.models.chat_session import ChatSessionORM
from main_server.DB.models.chat_state import ChatStateORM
from main_server.DB.models.chat_summary import ChatSummaryORM
from main_server.DB.models.contract import Contract
from main_server.DB.models.customer import Customer
from main_server.DB.models.employee import Employee
from main_server.DB.models.followup import Followup
from main_server.DB.models.knowledge_document import KnowledgeDocumentORM
from main_server.DB.models.order import Order
from main_server.DB.models.permission import PermissionORM, role_permissions
from main_server.DB.models.role import Role, user_roles
from main_server.DB.models.user import User

__all__ = [
    "AuditLogORM",
    "User",
    "Role",
    "user_roles",
    "PermissionORM",
    "role_permissions",
    "Customer",
    "Employee",
    "Contract",
    "Order",
    "Followup",
    "KnowledgeDocumentORM",
    "ChatSessionORM",
    "ChatMessageORM",
    "ChatStateORM",
    "ChatSummaryORM",
]
