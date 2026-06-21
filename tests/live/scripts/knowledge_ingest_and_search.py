"""真实 Embedding 导入与检索验收（慢，需 sentence-transformers）。

pytest 等价: unit/knowledge/test_knowledge_rag.py（mock 向量库）

用法:
  python tests/live/scripts/knowledge_ingest_and_search.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from main_server.services.knowledge_service import knowledge_service

    print("导入前:", knowledge_service.stats())
    result = knowledge_service.ingest_directory()
    print("导入:", {k: v for k, v in result.items() if k != "details"})

    docs = knowledge_service.search("报销流程是什么")
    print(f"检索 {len(docs)} 条")
    for i, doc in enumerate(docs[:3], 1):
        print(f"  [{i}] score={doc.get('score')}")
        print(f"      {str(doc.get('content', ''))[:80]}...")

    if not docs:
        print("WARN: 无结果，请确认 main_server/data/knowledge 有文档")
    else:
        print("OK")


if __name__ == "__main__":
    main()
