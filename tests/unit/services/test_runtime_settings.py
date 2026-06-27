"""运行时配置单元测试。"""

from __future__ import annotations

from main_server.services.runtime_settings import RuntimeSettingsService


class TestRuntimeSettings:
    def test_update_email_dry_run(self) -> None:
        svc = RuntimeSettingsService()
        svc.clear_all_overrides()
        before = svc.get_email_public_config()
        assert before["dry_run"] is True

        after = svc.update_email_settings(dry_run=False, operator_user_id=1)
        assert after["dry_run"] is False
        svc.clear_all_overrides()

    def test_empty_update_returns_current(self) -> None:
        svc = RuntimeSettingsService()
        svc.clear_all_overrides()
        cfg = svc.update_email_settings()
        assert "enabled" in cfg
        assert "dry_run" in cfg

    def test_smtp_update_masks_password_in_public_config(self) -> None:
        svc = RuntimeSettingsService()
        svc.clear_all_overrides()
        cfg = svc.update_smtp_settings(
            smtp_host="smtp.example.com",
            smtp_password="top-secret",
            operator_user_id=1,
        )
        assert cfg["smtp_password_set"] is True
        assert "top-secret" not in str(cfg)
        svc.clear_all_overrides()

    def test_system_params_override(self) -> None:
        svc = RuntimeSettingsService()
        svc.clear_all_overrides()
        params = svc.update_system_params(system_name="自定义名称", operator_user_id=1)
        assert params["system_name"] == "自定义名称"
        svc.clear_all_overrides()

    def test_llm_settings_override(self) -> None:
        svc = RuntimeSettingsService()
        svc.clear_all_overrides()
        cfg = svc.update_llm_settings(temperature=0.3, max_tokens=1024, operator_user_id=1)
        assert cfg["temperature"] == 0.3
        assert cfg["max_tokens"] == 1024
        svc.clear_all_overrides()
