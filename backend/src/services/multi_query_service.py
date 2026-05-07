"""Multi-query retrieval for complex question decomposition."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

from rag.fts_engine import SearchResult


@dataclass
class MultiQueryResult:
    """Merged retrieval output with sub-query attribution."""

    result: SearchResult
    sub_queries: list[str]


class MultiQueryRetriever:
    """Decompose queries, retrieve per sub-query, then aggregate and boost overlaps."""

    def __init__(
        self,
        search_fn: Callable[[str, int, float, dict[str, Any] | None], list[SearchResult]],
        max_sub_queries: int = 4,
    ) -> None:
        self.search_fn = search_fn
        self.max_sub_queries = max(2, min(4, max_sub_queries))

    def decompose(self, query: str) -> list[str]:
        text = query.strip()
        if not text:
            return []

        raw_parts = re.split(r"\?|\.|\,|\;|\band\b|\bthen\b", text, flags=re.IGNORECASE)
        parts = [part.strip() for part in raw_parts if part and part.strip()]

        if len(parts) <= 1:
            return [text]

        deduped: list[str] = []
        seen: set[str] = set()
        for part in parts:
            key = part.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(part)

        return deduped[: self.max_sub_queries]

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[MultiQueryResult]:
        sub_queries = self.decompose(query)
        if not sub_queries:
            return []

        with ThreadPoolExecutor(max_workers=len(sub_queries)) as pool:
            futures = {
                sub_query: pool.submit(self.search_fn, sub_query, top_k, min_score, filters)
                for sub_query in sub_queries
            }

            per_query_results: dict[str, list[SearchResult]] = {}
            for sub_query, future in futures.items():
                try:
                    per_query_results[sub_query] = future.result()
                except Exception:
                    per_query_results[sub_query] = []

        merged: dict[str, dict[str, Any]] = {}
        for sub_query, items in per_query_results.items():
            for item in items:
                bucket = merged.get(item.id)
                if bucket is None:
                    merged[item.id] = {
                        "result": item,
                        "sub_queries": [sub_query],
                    }
                else:
                    if sub_query not in bucket["sub_queries"]:
                        bucket["sub_queries"].append(sub_query)
                    # Keep highest base score among matches.
                    if item.score > bucket["result"].score:
                        bucket["result"] = item

        scored: list[MultiQueryResult] = []
        for payload in merged.values():
            base: SearchResult = payload["result"]
            matched_sub_queries: list[str] = payload["sub_queries"]
            boost = min(0.2, 0.05 * (len(matched_sub_queries) - 1))
            boosted_score = max(0.0, min(1.0, base.score + boost))
            enriched = SearchResult(
                id=base.id,
                content=base.content,
                score=boosted_score,
                metadata={
                    **base.metadata,
                    "matched_sub_queries": matched_sub_queries,
                    "sub_query_count": len(matched_sub_queries),
                },
                source_type=base.source_type,
            )
            scored.append(MultiQueryResult(result=enriched, sub_queries=matched_sub_queries))

        scored.sort(key=lambda row: row.result.score, reverse=True)
        return scored[:top_k]
