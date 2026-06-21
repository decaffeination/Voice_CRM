"""一键将 knowledge.docs_path 目录下的文档导入向量库。

用法（项目根目录）:
    python scripts/ingest_knowledge.py
    python scripts/ingest_knowledge.py --path main_server/data/knowledge

等价于:
    python -m main_server.Knowledge.ingest
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main_server.Knowledge.ingest import main

if __name__ == "__main__":
    main()
