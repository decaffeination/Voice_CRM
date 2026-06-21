"""RAG 生产化：hybrid 检索、rerank、空结果拒答、citation。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from main_server.Knowledge.bm25_index import BM25Index, tokenize
from main_server.Knowledge.hybrid import reciprocal_rank_fusion
from main_server.services.knowledge_service import KnowledgeService


class TestTokenize:
    def test_chinese_and_english(self) -> None:
        tokens = tokenize("报销流程 ABC test")
        assert "报" in tokens
        assert "报销" in tokens
        assert "abc" in tokens
        assert "test" in tokens


class TestBM25Index:
    def test_search_ranks_by_relevance(self) -> None:
        docs = [
            {"id": "a", "content": "员工报销需要填写报销单并提交审批", "metadata": {}},
            {"id": "b", "content": "请假流程需提前三天申请", "metadata": {}},
        ]
        index = BM25Index(docs)
        results = index.search("报销流程", top_k=2)
        assert results[0]["id"] == "a"
        assert results[0]["bm25_score"] > 0


class TestRRF:
    def test_merges_two_lists(self) -> None:
        vector = [
            {"id": "1", "content": "v1", "score": 0.9},
            {"id": "2", "content": "v2", "score": 0.8},
        ]
        keyword = [
            {"id": "2", "content": "v2", "bm25_score": 5.0},
            {"id": "3", "content": "v3", "bm25_score": 4.0},
        ]
        merged = reciprocal_rank_fusion(vector, keyword, top_k=3)
        ids = [doc["id"] for doc in merged]
        assert "2" in ids
        assert merged[0].get("hybrid_score") is not None


class TestKnowledgeServiceAgent:
    @patch("main_server.services.knowledge_service.retriever_module.search")
    def test_search_for_agent_builds_citations(self, mock_search: MagicMock) -> None:
        mock_search.return_value = [
            {
                "id": "doc:0:0:0",
                "content": "报销需提交发票原件",
                "metadata": {"source": "test.txt", "page": 1},
                "score": 0.88,
            }
        ]
        service = KnowledgeService()
        result = service.search_for_agent("报销流程")

        assert result["rejected"] is False
        assert len(result["citations"]) == 1
        assert result["citations"][0]["ref"] == "[1]"
        assert "[1]" in result["context"]
        assert "必须标注引用编号" in result["context"]

    @patch("main_server.services.knowledge_service.retriever_module.search")
    def test_search_for_agent_empty_rejection(self, mock_search: MagicMock) -> None:
        mock_search.return_value = []
        service = KnowledgeService()
        result = service.search_for_agent("不存在的内容")

        assert result["rejected"] is True
        assert result["error"] == "no_results"
        assert result["docs"] == []
        assert "未找到" in result["message"]

    @patch("main_server.services.knowledge_service.retriever_module.search")
    def test_build_context_raises_on_empty(self, mock_search: MagicMock) -> None:
        from main_server.core.exceptions import KnowledgeError

        mock_search.return_value = []
        service = KnowledgeService()
        with pytest.raises(KnowledgeError) as exc_info:
            service.build_context("不存在")
        assert exc_info.value.code == "NOT_FOUND"


class TestRetrieverFilter:
    @patch("main_server.Knowledge.retriever._rerank")
    @patch("main_server.Knowledge.retriever._hybrid_search")
    @patch("main_server.Knowledge.retriever.get_settings")
    def test_filters_low_vector_score(
        self,
        mock_settings: MagicMock,
        mock_hybrid: MagicMock,
        mock_rerank: MagicMock,
    ) -> None:
        from main_server.Knowledge import retriever

        settings = MagicMock()
        settings.knowledge.top_k = 5
        settings.knowledge.fetch_k = 20
        settings.knowledge.rerank_enabled = False
        settings.knowledge.hybrid_enabled = True
        settings.knowledge.min_vector_score = 0.5
        settings.knowledge.min_rerank_score = 0.0
        mock_settings.return_value = settings

        mock_hybrid.return_value = [
            {"id": "1", "content": "a", "score": 0.9},
            {"id": "2", "content": "b", "score": 0.2},
        ]

        with patch("main_server.Knowledge.retriever.guard_knowledge", side_effect=lambda _op, fn: fn()):
            docs = retriever.search("测试")

        assert len(docs) == 1
        assert docs[0]["id"] == "1"
