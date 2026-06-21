"""真实 LLM + Agent Graph 联调（需 llm.api_key，无需启动 HTTP 服务）。

pytest 等价: integration/test_chat_pipeline.py（mock Graph）

用法:
  python tests/live/scripts/agent_real_llm.py
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from main_server.memory.memory_schema import ActorContext
    from main_server.services.pipeline.chat_pipeline import chat_pipeline
    from main_server.utils.warmup_models import warmup_knowledge_models

    print("预热知识库模型（首次可能需下载 Rerank，请稍候）...")
    warmup_knowledge_models()

    session_id = str(uuid.uuid4())
    actor = ActorContext(
        user_id=1,
        username="admin",
        roles=["Admin"],
        session_id=session_id,
        channel="text",
    )
    for text in ["报销流程是什么", "查一下测试科技联系方式"]:
        print("\n" + "=" * 50)
        print("用户:", text)
        result = chat_pipeline.run(actor=actor, user_input=text)
        state = result.conversation_state
        print("助手:", result.text)
        print("intent:", state.get("current_intent"))
        print("customer_context:", state.get("customer_context"))


if __name__ == "__main__":
    main()
