"""运行时邮件配置单元测试。"""

from __future__ import annotations

from main_server.services.runtime_settings import RuntimeSettingsService


class TestRuntimeSettings:
    def test_update_email_dry_run(self) -> None:
        # 场景：更新 dry_run；输入：patch dry_run=False；预期：配置反映
        svc = RuntimeSettingsService()
        svc._email_overrides.clear()
        before = svc.get_email_public_config()
        assert before["dry_run"] is True

        after = svc.update_email_settings(dry_run=False, operator_user_id=1)
        assert after["dry_run"] is False
        svc._email_overrides.clear()

    def test_empty_update_returns_current(self) -> None:
        # 场景：无更新字段；输入：空 update；预期：返回当前配置
        svc = RuntimeSettingsService()
        svc._email_overrides.clear()
        cfg = svc.update_email_settings()
        assert "enabled" in cfg
        assert "dry_run" in cfg
