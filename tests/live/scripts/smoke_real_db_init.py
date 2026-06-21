"""真实 SQLite 初始化冒烟（会写入 config.yaml 指向的 DB 文件）。

JWT/CRM 等逻辑已由 pytest 覆盖，本脚本仅验证本地环境与真实 DB。

用法:
  python tests/live/scripts/smoke_real_db_init.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from main_server.config.settings import get_settings
    from main_server.utils.init_db import init_database

    s = get_settings()
    print("app.name:", s.app.name)
    print("database.dialect:", s.database.dialect)
    print("database.url:", s.database.effective_url)
    print("jwt.algorithm:", s.jwt.algorithm)

    init_database()
    print("OK - 数据库已初始化，默认账号 admin / admin123")


if __name__ == "__main__":
    main()
