"""Vector store abstractions and implementations for RAG.

`ChromaVectorStore` uses ChromaDB when available and falls back to a
lightweight JSON-backed store for local execution and tests.
"""

from __future__ import annotations

import hashlib
import json
import math
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


def build_conversation_collection_name(db_path: str) -> str:
    """Return a stable per-database collection name for conversation vectors."""
    normalized = str(Path(db_path).resolve()).lower()
    suffix = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"conversation_messages_{suffix}"


class VectorStore(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add vectors and their payloads."""

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search by vector similarity, returning highest scores first."""

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """Delete records by IDs."""

    @abstractmethod
    def persist(self) -> None:
        """Persist store state to durable storage."""

    @abstractmethod
    def load(self) -> None:
        """Load store state from durable storage."""


class ChromaVectorStore(VectorStore):
    """Chroma-backed vector store with a dependency-free fallback."""

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "rag_documents",
    ) -> None:
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._fallback_path = self.persist_directory / f"{collection_name}.json"

        self._records: dict[str, dict[str, Any]] = {}
        self._use_chroma = False
        self._chroma_collection = None
        self._chroma_client = None

        try:
            import chromadb

            self._chroma_client = chromadb.PersistentClient(path=str(self.persist_directory))
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self.load()

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        if not (len(ids) == len(embeddings) == len(texts)):
            raise ValueError("ids, embeddings, and texts must have equal length")

        metadatas = metadatas or [{} for _ in ids]
        if len(metadatas) != len(ids):
            raise ValueError("metadatas length must match ids length")

        sanitized_metadatas = [self._sanitize_metadata(meta) for meta in metadatas]

        if self._use_chroma and self._chroma_collection is not None:
            self._chroma_collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=sanitized_metadatas,
            )
            return

        for idx, doc_id in enumerate(ids):
            self._records[doc_id] = {
                "id": doc_id,
                "embedding": embeddings[idx],
                "text": texts[idx],
                "metadata": sanitized_metadatas[idx],
            }

    @classmethod
    def _sanitize_metadata(cls, metadata: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in metadata.items():
            sanitized[str(key)] = cls._sanitize_metadata_value(value)
        return sanitized

    @classmethod
    def _sanitize_metadata_value(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            # Chroma metadata does not accept nested dict values.
            return json.dumps(value, ensure_ascii=True)
        if isinstance(value, list):
            return [cls._sanitize_metadata_value(item) for item in value]
        return str(value)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        top_k = max(1, top_k)
        filters = filters or {}

        if self._use_chroma and self._chroma_collection is not None:
            where = self._build_chroma_where(filters)
            result = self._chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            ids = result.get("ids", [[]])[0]
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]

            rows: list[dict[str, Any]] = []
            for i, doc_id in enumerate(ids):
                distance = float(distances[i]) if i < len(distances) else 1.0
                score = max(0.0, min(1.0, 1.0 - distance))
                rows.append(
                    {
                        "id": str(doc_id),
                        "text": str(docs[i]) if i < len(docs) else "",
                        "metadata": metas[i] if i < len(metas) and metas[i] else {},
                        "score": score,
                    }
                )
            return rows

        scored: list[dict[str, Any]] = []
        for record in self._records.values():
            if not self._matches_filters(record.get("metadata", {}), filters):
                continue
            score = self._cosine_similarity(query_embedding, record["embedding"])
            scored.append(
                {
                    "id": record["id"],
                    "text": record["text"],
                    "metadata": record.get("metadata", {}),
                    "score": score,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _build_chroma_where(filters: dict[str, Any] | None) -> dict[str, Any] | None:
        if not filters:
            return None

        normalized = dict(filters)

        # Translate custom multi-source filter used by RetrievalNode.
        source_types = normalized.pop("source_types", None)
        if isinstance(source_types, list) and source_types:
            mapped = [{"source_type": str(item)} for item in source_types if isinstance(item, str)]
            if mapped:
                if len(mapped) == 1:
                    normalized["source_type"] = mapped[0]["source_type"]
                else:
                    if normalized:
                        return {"$and": [{"$or": mapped}, normalized]}
                    return {"$or": mapped}

        # date_range is handled in fallback mode only; avoid passing unsupported shape to Chroma.
        normalized.pop("date_range", None)

        return normalized or None

    def delete(self, ids: list[str]) -> None:
        if self._use_chroma and self._chroma_collection is not None:
            self._chroma_collection.delete(ids=ids)
            return

        for doc_id in ids:
            self._records.pop(doc_id, None)

    def persist(self) -> None:
        if self._use_chroma and self._chroma_client is not None:
            return

        payload = {
            "collection_name": self.collection_name,
            "records": list(self._records.values()),
        }
        self._fallback_path.write_text(json.dumps(payload), encoding="utf-8")

    def load(self) -> None:
        if self._use_chroma and self._chroma_client is not None:
            return

        if not self._fallback_path.exists():
            self._records = {}
            return

        raw = self._fallback_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        rows = parsed.get("records", [])
        self._records = {str(row["id"]): row for row in rows}

    @staticmethod
    def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        for key, expected in filters.items():
            if key == "source_types":
                if not isinstance(expected, list):
                    return False
                if metadata.get("source_type") not in expected:
                    return False
                continue

            if key == "date_range":
                if not isinstance(expected, (list, tuple)) or len(expected) != 2:
                    return False
                value = metadata.get("created_at")
                if value is None:
                    return False
                start, end = expected
                if not (start <= value <= end):
                    return False
                continue

            if metadata.get(key) != expected:
                return False
        return True

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            size = min(len(a), len(b))
            a = a[:size]
            b = b[:size]

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        score = dot / (norm_a * norm_b)
        return max(0.0, min(1.0, (score + 1.0) / 2.0))
