from __future__ import annotations

from pathlib import Path

from main_server.core.exceptions import AppError, KnowledgeError

SUPPORTED_SUFFIXES = {".txt", ".pdf", ".docx"}


def parse_file(file_path: str | Path) -> list[dict]:
    """解析文档，返回 [{content, metadata}, ...]。"""
    path = Path(file_path)
    if not path.exists():
        raise KnowledgeError(
            f"文件不存在: {path}", code="VALIDATION_ERROR", status_code=400
        )
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise KnowledgeError(
            f"不支持的文件类型: {path.suffix}",
            code="VALIDATION_ERROR",
            status_code=400,
        )

    suffix = path.suffix.lower()
    try:
        if suffix == ".txt":
            return _parse_txt(path)
        if suffix == ".pdf":
            return _parse_pdf(path)
        if suffix == ".docx":
            return _parse_docx(path)
    except AppError:
        raise
    except Exception as exc:
        raise KnowledgeError(f"文档解析失败: {path.name}") from exc
    raise KnowledgeError(
        f"不支持的文件类型: {suffix}", code="VALIDATION_ERROR", status_code=400
    )


def _parse_txt(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return [
        {
            "content": text,
            "metadata": {
                "source": path.name,
                "file_path": str(path),
                "page": 1,
            },
        }
    ]


def _parse_pdf(path: Path) -> list[dict]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    docs: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        docs.append(
            {
                "content": text,
                "metadata": {
                    "source": path.name,
                    "file_path": str(path),
                    "page": index,
                },
            }
        )
    return docs


def _parse_docx(path: Path) -> list[dict]:
    from docx import Document

    document = Document(str(path))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs).strip()
    if not text:
        return []
    return [
        {
            "content": text,
            "metadata": {
                "source": path.name,
                "file_path": str(path),
                "page": 1,
            },
        }
    ]
