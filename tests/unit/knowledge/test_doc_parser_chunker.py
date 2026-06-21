"""文档解析与切块单元测试（对应 manual P2 parse）。"""

from __future__ import annotations

import pytest

from main_server.Knowledge.chunker import chunk_documents
from main_server.Knowledge.doc_parser import parse_file
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
