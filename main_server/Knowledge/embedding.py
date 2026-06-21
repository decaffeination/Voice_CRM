from __future__ import annotations

from functools import lru_cache

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from main_server.Knowledge.storage_guard import guard_knowledge
from main_server.config.settings import get_settings
from main_server.core.logger import logger
from main_server.utils.hf_model_loader import load_sentence_transformer


class SentenceTransformerEmbedding(EmbeddingFunction[Documents]):
    """BGE 等 sentence-transformers 模型，缓存到 data/models/embedding。"""

    def __init__(self, model_name: str, cache_folder: str):
        def _load():
            return load_sentence_transformer(model_name, cache_folder)

        self._model = guard_knowledge("加载 Embedding 模型", _load)

    def __call__(self, input: Documents) -> Embeddings:
        def _encode() -> Embeddings:
            vectors = self._model.encode(list(input), normalize_embeddings=True)
            return [vector.tolist() for vector in vectors]

        return guard_knowledge("生成文本向量", _encode, timed=True)


@lru_cache
def get_embedding_function() -> EmbeddingFunction:
    settings = get_settings()
    cache_dir = settings.models.abs_embedding_cache
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_name = settings.models.embedding.model
    logger.info("加载 Embedding 模型: %s, cache=%s", model_name, cache_dir)
    return SentenceTransformerEmbedding(model_name, cache_folder=str(cache_dir))
