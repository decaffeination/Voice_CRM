"""邮件与搜索服务单元测试（mock 外部 Provider）。"""

from __future__ import annotations

from agent.state import default_conversation_state
from main_server.services.email_service import email_service
from main_server.services.search_service import search_service


class TestSearchService:
    def test_web_search(self, mock_web_search) -> None:
        # 场景：联网搜索；输入：query；预期：results 非空
        result = search_service.web_search("测试查询")
        assert "results" in result
        assert len(result["results"]) > 0

    def test_search_company_contact(self, mock_web_search) -> None:
        # 场景：公司联系人搜索；输入：公司名；预期：emails_found
        result = search_service.search_company_contact("测试公司")
        assert "test@example.com" in result["emails_found"]


class TestEmailService:
    def test_send_dry_run(self, mock_email_provider) -> None:
        # 场景：发送邮件；输入：to/subject/body；预期：sent=True
        result = email_service.send(
            to="user@example.com",
            subject="测试",
            body="内容",
        )
        assert result["sent"]
        assert result["to"] == "user@example.com"

    def test_lookup_manual_email(self) -> None:
        # 场景：手动邮箱；输入：source=manual + email；预期：resolved_email
        state = default_conversation_state()
        result = email_service.lookup_recipient(
            source="manual",
            conversation_state=state,
            user_id=1,
            turn_count=1,
            manual_email="manual@test.com",
        )
        assert result.side_effects.get("resolved_email") == "manual@test.com"

    def test_lookup_manual_needs_input(self) -> None:
        # 场景：手动无邮箱；输入：source=manual；预期：needs_input
        state = default_conversation_state()
        result = email_service.lookup_recipient(
            source="manual",
            conversation_state=state,
            user_id=1,
            turn_count=1,
        )
        assert result.payload.get("needs_input")

    def test_lookup_web_search(self, mock_web_search) -> None:
        # 场景：web 来源查邮箱；输入：公司名；预期：resolved_email
        state = default_conversation_state()
        result = email_service.lookup_recipient(
            source="web",
            conversation_state=state,
            user_id=1,
            turn_count=1,
            customer_name="测试公司",
        )
        assert result.side_effects.get("resolved_email") == "test@example.com"

    def test_send_for_agent_no_recipient(self) -> None:
        # 场景：无收件人发送；输入：to=None；预期：needs_input
        result = email_service.send_for_agent(
            to=None,
            subject="hi",
            body="body",
            resolved_email=None,
        )
        assert result.payload.get("needs_input")

    def test_send_for_agent_success(self, mock_email_provider) -> None:
        # 场景：有收件人发送；输入：resolved_email；预期：sent
        result = email_service.send_for_agent(
            to=None,
            subject="hi",
            body="body",
            resolved_email="a@b.com",
        )
        assert result.payload.get("sent")
