"""数据库迁移与种子数据初始化。"""

from __future__ import annotations

from alembic import command
from alembic.config import Config

from main_server.core.auth.auth_service import hash_password
from main_server.core.auth.permission import DEFAULT_ROLE_SEEDS, Role
from main_server.core.logger import logger
from main_server.services.rbac_service import seed_permissions, seed_role_permissions
from main_server.config.settings import PROJECT_ROOT, get_settings
from main_server.DB import db_session
from main_server.DB.models import Role as RoleModel
from main_server.DB.models import User


def run_migrations() -> None:
    settings = get_settings()
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database.effective_url)
    command.upgrade(alembic_cfg, "head")
    logger.info(
        "数据库迁移完成 dialect=%s url=%s",
        settings.database.dialect,
        settings.database.effective_url,
    )


def seed_roles() -> None:
    with db_session() as session:
        for code, name, description in DEFAULT_ROLE_SEEDS:
            exists = session.query(RoleModel).filter(RoleModel.code == code).first()
            if exists:
                continue
            session.add(
                RoleModel(code=code, name=name, description=description)
            )
        logger.info("默认角色种子数据已就绪")


def seed_default_user() -> None:
    with db_session() as session:
        admin_role = (
            session.query(RoleModel).filter(RoleModel.code == Role.ADMIN).first()
        )
        if admin_role is None:
            logger.warning("Admin 角色不存在，跳过默认用户创建")
            return

        exists = session.query(User).filter(User.username == "admin").first()
        if exists:
            if not exists.roles:
                exists.roles = [admin_role]
            logger.info("默认用户已存在，跳过种子数据")
            return

        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            display_name="管理员",
            is_active=True,
        )
        admin.roles = [admin_role]
        session.add(admin)
        logger.info("已创建默认用户 admin / admin123（角色: Admin）")


def init_database() -> None:
    run_migrations()
    seed_roles()
    seed_permissions()
    seed_role_permissions()
    seed_default_user()


if __name__ == "__main__":
    init_database()
    print("数据库初始化完成")
