"""CRM 增删查集成测试。"""

from __future__ import annotations

from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user
from main_server.DB import db_session
from main_server.services.crm_service import crm_service


class TestCRMCRUD:
    def test_lookup_new_customer(self, memory_db) -> None:
        # 场景：新客户判定；输入：不存在公司名；预期：is_new=True
        result = crm_service.lookup_customer("不存在的公司ABC")
        assert result.is_new is True
        assert not result.found

    def test_add_and_lookup_customer(self, memory_db) -> None:
        # 场景：新增后查询；输入：客户信息；预期：found=True, is_new=False
        with db_session() as session:
            user = create_user(
                session,
                username="crm_writer",
                password="crm12345",
                roles=[Role.SALES],
            )
            user_id = user.id

        created = crm_service.add_customer(
            name="测试科技有限公司",
            contact_person="张三",
            phone="13800000000",
            email="test@example.com",
            owner_user_id=user_id,
        )
        assert created["name"] == "测试科技有限公司"

        lookup = crm_service.lookup_customer(
            "测试科技",
            user_id=user_id,
            roles=[Role.SALES],
        )
        assert lookup.found is True
        assert lookup.is_new is False

        profile = crm_service.get_customer_profile(
            created["id"],
            user_id=user_id,
            roles=[Role.SALES],
        )
        assert profile.get("customer") or profile.get("profile")

    def test_add_followup(self, memory_db) -> None:
        # 场景：新增跟进；输入：customer_id + content；预期：跟进记录存在
        with db_session() as session:
            user = create_user(
                session,
                username="crm_fu",
                password="crm12345",
                roles=[Role.SALES],
            )
            user_id = user.id

        customer = crm_service.add_customer(
            name="跟进测试公司",
            owner_user_id=user_id,
        )
        followup = crm_service.add_followup(
            customer_id=customer["id"],
            content="今日电话沟通，意向良好",
            created_by=user_id,
            roles=[Role.SALES],
        )
        assert followup.get("content") == "今日电话沟通，意向良好"

        followups = crm_service.list_followups(
            customer["id"],
            user_id=user_id,
            roles=[Role.SALES],
        )
        assert len(followups) >= 1
