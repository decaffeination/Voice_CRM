"""RBAC 权限目录与默认角色权限（与前端 constants/rbac.ts 对齐）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from main_server.core.auth.permission import Role


@dataclass(frozen=True)
class PermissionNode:
    key: str
    label: str
    children: tuple["PermissionNode", ...] = field(default_factory=tuple)


PERMISSION_TREE: tuple[PermissionNode, ...] = (
    PermissionNode(
        "ai",
        "AI 助手",
        (
            PermissionNode("ai.chat", "对话访问"),
            PermissionNode("ai.voice", "语音交互"),
            PermissionNode("ai.history", "历史记录"),
        ),
    ),
    PermissionNode(
        "knowledge",
        "知识库",
        (
            PermissionNode("knowledge.read", "文档查看"),
            PermissionNode("knowledge.upload", "文档上传"),
            PermissionNode("knowledge.delete", "文档删除"),
            PermissionNode("knowledge.search", "检索测试"),
        ),
    ),
    PermissionNode(
        "crm",
        "CRM",
        (
            PermissionNode("crm.read", "客户查看"),
            PermissionNode("crm.write", "客户编辑"),
            PermissionNode("crm.followup", "跟进记录"),
        ),
    ),
    PermissionNode(
        "admin",
        "系统管理",
        (
            PermissionNode("admin.users", "用户管理"),
            PermissionNode("admin.roles", "角色权限"),
            PermissionNode("admin.audit", "操作审计"),
            PermissionNode("admin.settings", "系统配置"),
        ),
    ),
)


def flatten_permission_tree(
    nodes: tuple[PermissionNode, ...] = PERMISSION_TREE,
) -> list[tuple[str, str, str | None, int]]:
    """返回 (code, label, parent_code, sort_order) 列表。"""
    rows: list[tuple[str, str, str | None, int]] = []
    order = 0
    for module in nodes:
        rows.append((module.key, module.label, None, order))
        order += 1
        for child in module.children:
            rows.append((child.key, child.label, module.key, order))
            order += 1
    return rows


def all_permission_codes() -> frozenset[str]:
    return frozenset(code for code, _, _, _ in flatten_permission_tree())


ALL_PERMISSION_CODES = all_permission_codes()

_DEFAULT_ALL = sorted(ALL_PERMISSION_CODES)

DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.ADMIN: _DEFAULT_ALL,
    Role.SALES_MANAGER: [
        "ai",
        "ai.chat",
        "ai.voice",
        "ai.history",
        "knowledge",
        "knowledge.read",
        "knowledge.upload",
        "knowledge.search",
        "crm",
        "crm.read",
        "crm.write",
        "crm.followup",
    ],
    Role.SALES: [
        "ai",
        "ai.chat",
        "ai.voice",
        "ai.history",
        "knowledge",
        "knowledge.read",
        "crm",
        "crm.read",
        "crm.write",
        "crm.followup",
    ],
    Role.CUSTOMER_SERVICE: [
        "ai",
        "ai.chat",
        "ai.voice",
        "knowledge",
        "knowledge.read",
        "knowledge.search",
        "crm",
        "crm.read",
        "crm.followup",
    ],
}

ADMIN_REQUIRED_PERMISSIONS = frozenset({"admin.users", "admin.settings"})
