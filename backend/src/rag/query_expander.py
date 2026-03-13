"""Query expansion utilities for advanced retrieval."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError


class QueryExpander:
    """Generate alternative query formulations with caching and timeout control."""

    def __init__(
        self,
        max_expansions: int = 3,
        timeout_ms: int = 200,
        cache_size: int = 512,
    ) -> None:
        self.max_expansions = max(1, min(5, max_expansions))
        self.timeout_ms = max(50, timeout_ms)
        self.cache_size = max(0, cache_size)
        self._cache: dict[str, list[str]] = {}

    def expand(self, query: str, max_alternatives: int | None = None) -> list[str]:
        """Return original query followed by 2-5 alternative formulations when possible."""
        normalized = query.strip()
        if not normalized:
            return []

        cached = self._cache.get(normalized)
        if cached is not None:
            return list(cached)

        target_alternatives = self.max_expansions if max_alternatives is None else max(1, min(5, max_alternatives))

        start = time.time()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self._expand_impl, normalized, target_alternatives)
                expanded = future.result(timeout=self.timeout_ms / 1000.0)
        except TimeoutError:
            expanded = [normalized]
        except Exception:
            expanded = [normalized]

        # Fallback guarantees at least two alternatives for non-trivial queries.
        if len(expanded) < 3 and len(normalized.split()) >= 2:
            expanded = self._ensure_minimum(expanded, target_alternatives)

        if self.cache_size > 0:
            if len(self._cache) >= self.cache_size:
                oldest = next(iter(self._cache))
                self._cache.pop(oldest, None)
            self._cache[normalized] = list(expanded)

        _ = start  # keeps code explicit for future timing metrics without warnings
        return expanded

    def _expand_impl(self, query: str, target_alternatives: int) -> list[str]:
        candidates: list[str] = [query]

        for expanded in self._rule_based_expansion(query):
            candidates.append(expanded)

        for expanded in self._wordnet_expansion(query):
            candidates.append(expanded)

        unique = self._dedupe_case_insensitive(candidates)
        if len(unique) < 2:
            return unique

        return unique[: target_alternatives + 1]

    def _ensure_minimum(self, existing: list[str], target_alternatives: int) -> list[str]:
        query = existing[0]
        templates = [
            f"explain {query}",
            f"{query} examples",
            f"how to {query}",
            f"best practices for {query}",
        ]
        merged = existing + templates
        deduped = self._dedupe_case_insensitive(merged)
        return deduped[: target_alternatives + 1]

    @staticmethod
    def _dedupe_case_insensitive(items: list[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for item in items:
            normalized = item.strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            output.append(normalized)
        return output

    @staticmethod
    def _rule_based_expansion(query: str) -> list[str]:
        synonym_map = {
            "auth": "authentication",
            "login": "authentication",
            "signin": "authentication",
            "deploy": "deployment",
            "bug": "issue",
            "error": "failure",
            "perf": "performance",
            "api": "application programming interface",
            "db": "database",
        }

        tokens = query.split()
        if not tokens:
            return []

        outputs: list[str] = []

        replaced = [synonym_map.get(token.lower(), token) for token in tokens]
        if replaced != tokens:
            outputs.append(" ".join(replaced))

        outputs.append(f"detailed {query}")
        outputs.append(f"{query} troubleshooting")

        return outputs

    @staticmethod
    def _wordnet_expansion(query: str) -> list[str]:
        try:
            from nltk.corpus import wordnet as wn  # type: ignore
        except Exception:
            return []

        tokens = query.split()
        if not tokens:
            return []

        outputs: list[str] = []
        for idx, token in enumerate(tokens):
            synsets = wn.synsets(token)
            if not synsets:
                continue
            lemmas: list[str] = []
            for synset in synsets[:2]:
                for lemma in synset.lemma_names()[:2]:
                    lemmas.append(lemma.replace("_", " "))
            for lemma in lemmas[:2]:
                replaced = list(tokens)
                replaced[idx] = lemma
                outputs.append(" ".join(replaced))

        return outputs
