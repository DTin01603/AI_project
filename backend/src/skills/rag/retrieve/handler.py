from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from skills._base import BaseSkill

logger = logging.getLogger("skills")


class Inputs(BaseModel):
    query: str
    top_k: int | None = None
    min_score: float | None = None
    source_types: list[str] | None = None
    method: str | None = None


class Outputs(BaseModel):
    documents: list[dict[str, Any]] = []


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    # Injected post-discovery from api/deps.py
    retrieval_node: Any = None

    def __init__(self, *, retrieval_node: Any = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.retrieval_node = retrieval_node

    def run(self, inputs: Inputs) -> dict[str, Any]:
        if self.retrieval_node is None:
            logger.warning("rag.retrieve called without retrieval_node injected")
            return {"documents": []}

        try:
            docs = self.retrieval_node.retrieve(
                query=inputs.query,
                method=inputs.method or self.config.get("method", "hybrid"),
                top_k=inputs.top_k or int(self.config.get("top_k", 8)),
                min_score=inputs.min_score if inputs.min_score is not None else float(self.config.get("min_score", 0.0)),
                filters={"source_types": inputs.source_types or self.config.get("source_types", ["document", "code_file"])},
            )
        except Exception:
            logger.exception("rag.retrieve failed")
            return {"documents": []}

        serialized = [
            {
                "id": d.id,
                "content": d.content,
                "score": d.score,
                "source_type": d.source_type,
                "metadata": d.metadata,
            }
            for d in docs
        ]
        if serialized:
            top_sources = [
                f"{d.get('metadata', {}).get('file_path') or d.get('id', '?')} (score={d['score']:.3f})"
                for d in serialized[:3]
            ]
            logger.info("[RAG] query=%r | retrieved=%d | top3=%s", inputs.query, len(serialized), top_sources)
        else:
            logger.info("[RAG] query=%r | retrieved=0", inputs.query)
        return {"documents": serialized}
