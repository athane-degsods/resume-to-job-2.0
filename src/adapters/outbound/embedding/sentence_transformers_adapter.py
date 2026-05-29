from __future__ import annotations

from typing import Sequence
import logging

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None  # type: ignore

from src.ports.output.embedding_service import EmbeddingServicePort


class SentenceTransformersEmbeddingAdapter(EmbeddingServicePort):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None
        if SentenceTransformer is not None:
            try:
                self._model = SentenceTransformer(model_name)
            except Exception as exc:  # pragma: no cover
                logging.exception("Failed to load sentence-transformers model: %s", exc)
                self._model = None

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is None:
            # graceful fallback: return small zero vectors matching typical dimensionality
            dim = 384
            return [[0.0] * dim for _ in texts]

        # model.encode returns numpy arrays; convert to lists
        embeddings = self._model.encode(list(texts), show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]
