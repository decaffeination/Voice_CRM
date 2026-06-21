"""角色与权限校验单元测试。"""

from __future__ import annotations

import pytest

from main_server.core.auth.permission import (
    Role,
    normalize_roles,
    user_has_any_role,
    user_is_admin,
)
from main_server.core.auth.auth_schema import CurrentUser


class TestNormalizeRoles:
    def test_valid_roles(self) -> None:
        # 场景：合法角色去重；输入：Sales+Admin；预期：去重后列表
        result = normalize_roles([Role.SALES, Role.ADMIN, Role.SALES])
        assert result == [Role.SALES, Role.ADMIN]

    def test_empty_raises(self) -> None:
        # 场景：空角色列表；输入：[]；预期：ValueError
        with pytest.raises(ValueError, match="至少"):
            normalize_roles([])

    def test_invalid_role_raises(self) -> None:
        # 场景：非法角色；输入：UnknownRole；预期：ValueError
        with pytest.raises(ValueError, match="无效"):
            normalize_roles(["UnknownRole"])


class TestRoleChecks:
    def test_user_is_admin(self) -> None:
        # 场景：Admin 判断；输入：Admin 用户；预期：True
        admin = CurrentUser(user_id=1, username="a", roles=[Role.ADMIN])
        sales = CurrentUser(user_id=2, username="s", roles=[Role.SALES])
        assert user_is_admin(admin)
        assert not user_is_admin(sales)

    def test_user_has_any_role(self) -> None:
        # 场景：多角色匹配；输入：Sales；预期：匹配 Sales/CS
        user = CurrentUser(user_id=1, username="s", roles=[Role.SALES])
        assert user_has_any_role(user, Role.SALES, Role.CUSTOMER_SERVICE)
        assert not user_has_any_role(user, Role.ADMIN)

    def test_all_roles_defined(self) -> None:
        # 场景：角色全集；输入：Role.ALL；预期：4 个角色
        assert len(Role.ALL) == 4
        assert Role.ADMIN in Role.ALL
