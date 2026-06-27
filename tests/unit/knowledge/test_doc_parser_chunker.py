"""文档解析与切块单元测试（对应 manual P2 parse）。"""

from __future__ import annotations

import pytest

from main_server.knowledge.chunker import chunk_documents
from main_server.knowledge.doc_parser import parse_file
from main_server.core.exceptions import KnowledgeError


class TestDocParser:
    def test_parse_txt(self, tmp_path) -> None:
        # 场景：解析 txt；输入：两行文本；预期：至少 1 个 doc
        sample = tmp_path / "policy.txt"
        sample.write_text(
            "报销流程：先提交申请，再部门审批。\n请假需要提交请假单。",
            encoding="utf-8",
        )
        docs = parse_file(sample)
        assert len(docs) >= 1
        assert "报销" in docs[0]["content"]

    def test_file_not_found(self) -> None:
        # 场景：文件不存在；输入：无效路径；预期：KnowledgeError
        with pytest.raises(KnowledgeError, match="不存在"):
            parse_file("/nonexistent/file.txt")

    def test_unsupported_suffix(self, tmp_path) -> None:
        # 场景：不支持后缀；输入：.doc；预期：KnowledgeError
        bad = tmp_path / "file.doc"
        bad.write_text("x", encoding="utf-8")
        with pytest.raises(KnowledgeError, match="不支持"):
            parse_file(bad)


class TestChunker:
    def test_chunk_documents(self, tmp_path) -> None:
        # 场景：切块；输入：长文本 doc；预期：chunks >= 1
        sample = tmp_path / "long.txt"
        sample.write_text("第一句内容。" * 20, encoding="utf-8")
        docs = parse_file(sample)
        chunks = chunk_documents(docs)
        assert len(chunks) >= 1
        assert chunks[0].get("content")

    def test_chunk_respects_paragraph_boundary(self) -> None:
        from main_server.knowledge.chunker import chunk_text

        text = ("段落A内容。" * 15) + "\n\n" + ("段落B内容。" * 15)
        chunks = chunk_text(text, chunk_size=80, chunk_overlap=10)
        assert len(chunks) >= 2
        assert any("段落A" in c for c in chunks)
        assert any("段落B" in c for c in chunks)

    def test_chunk_respects_heading_boundary(self) -> None:
        from main_server.knowledge.chunker import chunk_text

        text = (
            "## 报销制度\n"
            + ("报销需提交发票。" * 15)
            + "\n\n## 请假制度\n"
            + ("请假需提前申请。" * 15)
        )
        chunks = chunk_text(text, chunk_size=120, chunk_overlap=10)
        assert len(chunks) >= 2
        assert any("报销" in c for c in chunks)
        assert any("请假" in c for c in chunks)
