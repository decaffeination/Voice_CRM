from __future__ import annotations

from pathlib import Path

from main_server.Knowledge.chunker import chunk_documents
from main_server.Knowledge.doc_parser import SUPPORTED_SUFFIXES, parse_file
from main_server.Knowledge.doc_registry import (
    build_doc_id,
    compute_file_hash,
    get_document,
    upsert_active_document,
)
from main_server.Knowledge.retriever import invalidate_index_cache
from main_server.Knowledge.vector_store import get_vector_store
from main_server.config.settings import get_settings
from main_server.core.exceptions import KnowledgeError
from main_server.core.logger import logger


def ingest_file(
    file_path: str | Path,
    *,
    operator_user_id: int | None = None,
    logical_name: str | None = None,
) -> dict:
    path = Path(file_path)
    filename = logical_name or path.name
    doc_id = build_doc_id(filename)
    file_hash = compute_file_hash(path)
    existing = get_document(doc_id)

    if (
        existing
        and existing.status == "active"
        and existing.file_hash == file_hash
    ):
        return {
            "doc_id": doc_id,
            "file": str(path),
            "filename": filename,
            "documents": 0,
            "chunks": existing.chunk_count,
            "version": existing.version,
            "unchanged": True,
        }

    if existing and existing.status == "active":
        removed = get_vector_store().delete_by_doc_id(doc_id)
        logger.info(
            "知识库覆盖 doc_id=%s filename=%s removed_chunks=%s",
            doc_id,
            filename,
            removed,
        )
        next_version = existing.version + 1
    elif existing and existing.status == "deleted":
        next_version = 1
    else:
        next_version = 1

    documents = parse_file(path)
    for doc in documents:
        metadata = dict(doc.get("metadata") or {})
        metadata["doc_id"] = doc_id
        doc["metadata"] = metadata

    chunks = chunk_documents(documents)
    count = get_vector_store().add_chunks(chunks)
    invalidate_index_cache()

    record = upsert_active_document(
        doc_id=doc_id,
        filename=filename,
        file_hash=file_hash,
        chunk_count=count,
        file_path=str(path),
        operator_user_id=operator_user_id,
        version=next_version,
    )

    return {
        "doc_id": doc_id,
        "file": str(path),
        "filename": filename,
        "documents": len(documents),
        "chunks": count,
        "version": record.version,
        "unchanged": False,
        "replaced": existing is not None and existing.status == "active",
    }


def ingest_directory(
    directory: str | Path | None = None,
    *,
    operator_user_id: int | None = None,
) -> dict:
    settings = get_settings()
    root = Path(directory) if directory else settings.knowledge.abs_docs_path
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        logger.warning("知识库目录为空，已创建: %s", root)
        return {"directory": str(root), "files": 0, "chunks": 0, "details": []}

    details: list[dict] = []
    total_chunks = 0
    file_count = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        try:
            relative = path.relative_to(root)
            logical_name = str(relative).replace("\\", "/")
        except ValueError:
            logical_name = path.name
        file_count += 1
        result = ingest_file(
            path,
            operator_user_id=operator_user_id,
            logical_name=logical_name,
        )
        total_chunks += result["chunks"]
        details.append(result)

    return {
        "directory": str(root),
        "files": file_count,
        "chunks": total_chunks,
        "details": details,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="导入知识库文档")
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="文件或目录路径，默认读取 config.yaml 中 knowledge.docs_path",
    )
    args = parser.parse_args()

    if args.path is None:
        result = ingest_directory()
    else:
        target = Path(args.path)
        if target.is_dir():
            result = ingest_directory(target)
        elif target.is_file():
            result = ingest_file(target)
        else:
            raise KnowledgeError(
                f"路径不存在: {target}", code="VALIDATION_ERROR", status_code=400
            )

    print(result)


if __name__ == "__main__":
    main()
