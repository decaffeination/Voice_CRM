"""审计日志持久化单元测试。"""

from __future__ import annotations

from main_server.core.audit import audit_log
from main_server.core.context import request_id_var, session_id_var, user_id_var
from main_server.services.audit_service import list_audit_logs


class TestAuditLog:
    def test_persisted_to_db(self, memory_db) -> None:
        # 场景：写入审计；输入：action + detail；预期：DB 可查询
        rid = request_id_var.set("audit-req-001")
        uid = user_id_var.set(1)
        sid = session_id_var.set("sess-audit")
        try:
            audit_log("crm.lookup", resource="customer", detail="name=测试")
        finally:
            request_id_var.reset(rid)
            user_id_var.reset(uid)
            session_id_var.reset(sid)

        items, total = list_audit_logs(action="crm.lookup", limit=10)
        assert total == 1
        assert items[0]["action"] == "crm.lookup"
        assert "name=测试" in items[0]["detail"]
