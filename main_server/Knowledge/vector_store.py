from __future__ import annotations

from functools import lru_cache
from typing import Any

import chromadb

from main_server.Knowledge.embedding import get_embedding_function
from main_server.Knowledge.storage_guard import guard_knowledge
from main_server.config.settings import get_settings
from main_server.core.logger import logger


class KnowledgeVectorStore:
    def __init__(self) -> None:
        def _init() -> None:
            settings = get_settings()
            settings.knowledge.abs_chroma_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(settings.knowledge.abs_chroma_path)
            )
            self._collection = self._client.get_or_create_collection(
                name=settings.knowledge.collection_name,
                embedding_function=get_embedding_function(),
                metadata={"hnsw:space": "cosine"},
            )

        guard_knowledge("初始化向量库", _init)

    def add_chunks(self, chunks: list[dict]) -> int:
        if not chunks:
            return 0

        def _add() -> int:
            ids: list[str] = []
            documents: list[str] = []
            metadatas: list[dict[str, Any]] = []

            for index, chunk in enumerate(chunks):
                metadata = dict(chunk.get("metadata") or {})
                source = str(metadata.get("source", "unknown"))
                doc_id = str(metadata.get("doc_id", source))
                doc_index = metadata.get("doc_index", 0)
                chunk_index = metadata.get("chunk_index", index)
                chunk_id = f"{doc_id}:{doc_index}:{chunk_index}:{index}"
                ids.append(chunk_id)
                documents.append(chunk["content"])
                metadatas.append(
                    {
                        "doc_id": doc_id,
                        "source": source,
                        "file_path": str(metadata.get("file_path", "")),
                        "page": int(metadata.get("page", 0) or 0),
                        "doc_index": int(doc_index),
                        "chunk_index": int(chunk_index),
                    }
                )

            self._collection.upsert(
                ids=ids, documents=documents, metadatas=metadatas
            )
            logger.info("向量库写入 %s 条 chunk", len(chunks))
            return len(chunks)

        return guard_knowledge("写入向量库", _add, timed=True)

    def query(self, query_text: str, top_k: int) -> list[dict[str, Any]]:
        if not query_text.strip():
            return []

        def _query() -> list[dict[str, Any]]:
            result = self._collection.query(
                query_texts=[query_text],
                n_results=top_k,
            )
            return _format_query_result(result)

        return guard_knowledge("检索向量库", _query, timed=True)

    def count(self) -> int:
        return guard_knowledge("统计向量库", self._collection.count, timed=True)

    def delete_by_doc_id(self, doc_id: str) -> int:
        keyword = doc_id.strip()
        if not keyword:
            return 0

        def _delete() -> int:
            existing = self._collection.get(
                where={"doc_id": keyword},
                include=[],
            )
            ids = existing.get("ids") or []
            if not ids:
                return 0
            self._collection.delete(ids=ids)
            logger.info("向量库删除 doc_id=%s chunks=%s", keyword, len(ids))
            return len(ids)

        return guard_knowledge("删除向量库文档", _delete, timed=True)

    def get_chunks_by_doc_id(self, doc_id: str, limit: int = 5) -> list[dict[str, Any]]:
        keyword = doc_id.strip()
        if not keyword:
            return []

        def _get() -> list[dict[str, Any]]:
            result = self._collection.get(
                where={"doc_id": keyword},
                include=["documents", "metadatas"],
                limit=limit,
            )
            items: list[dict[str, Any]] = []
            ids = result.get("ids") or []
            documents = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            for index, chunk_id in enumerate(ids):
                items.append(
                    {
                        "id": chunk_id,
                        "content": documents[index] if index < len(documents) else "",
                        "metadata": metadatas[index] if index < len(metadatas) else {},
                    }
                )
            return items

        return guard_knowledge("读取文档 Chunk", _get, timed=True)

    def fetch_all(self) -> list[dict[str, Any]]:
        """读取全部 chunk（供 BM25 索引构建）。"""

        def _fetch() -> list[dict[str, Any]]:
            total = self._collection.count()
            if total == 0:
                return []
            result = self._collection.get(limit=total, include=["documents", "metadatas"])
            items: list[dict[str, Any]] = []
            ids = result.get("ids") or []
            documents = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            for index, doc_id in enumerate(ids):
                items.append(
                    {
                        "id": doc_id,
                        "content": documents[index] if index < len(documents) else "",
                        "metadata": metadatas[index] if index < len(metadatas) else {},
                    }
                )
            return items

        return guard_knowledge("读取向量库语料", _fetch, timed=True)


@lru_cache
def get_vector_store() -> KnowledgeVectorStore:
    return KnowledgeVectorStore()


def _format_query_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    for index, doc_id in enumerate(ids):
        distance = distances[index] if index < len(distances) else None
        score = None if distance is None else round(1 - float(distance), 4)
        items.append(
            {
                "id": doc_id,
                "content": documents[index] if index < len(documents) else "",
                "metadata": metadatas[index] if index < len(metadatas) else {},
                "score": score,
            }
        )
    return items
