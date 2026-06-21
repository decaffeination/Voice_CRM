"""文本分句工具单元测试。"""

from __future__ import annotations

from main_server.utils.text_split import split_sentences


class TestSplitSentences:
    def test_simple_sentences(self) -> None:
        # 场景：中文句号分句；输入：两句；预期：2 段
        parts = split_sentences("你好。世界。")
        assert len(parts) == 2
        assert parts[0] == "你好。"
        assert parts[1] == "世界。"

    def test_empty_string(self) -> None:
        # 场景：空字符串；输入：""；预期：空列表
        assert split_sentences("") == []

    def test_no_punctuation(self) -> None:
        # 场景：无标点；输入：单句；预期：1 段
        parts = split_sentences("没有标点")
        assert len(parts) == 1
        assert parts[0] == "没有标点"

    def test_mixed_punctuation(self) -> None:
        # 场景：混合标点；输入：!?；预期：正确分句
        parts = split_sentences("什么？真的！")
        assert len(parts) >= 2

    def test_long_text(self) -> None:
        # 场景：长文本；输入：重复句；预期：多段
        text = "测试。" * 50
        parts = split_sentences(text)
        assert len(parts) == 50
