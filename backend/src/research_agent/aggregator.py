from __future__ import annotations

from research_agent.models import ResearchResult


class Aggregator:
    def __init__(self, timeout_seconds: float = 3.0) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _deduplicate(lines: list[str]) -> list[str]:
        # Remove empty/duplicate lines while preserving order.
        seen: set[str] = set()
        output: list[str] = []
        for line in lines:
            normalized = line.strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            output.append(normalized)
        return output

    def aggregate(self, results: list[ResearchResult]) -> tuple[str, list[str]]:
        # Merge task outputs into one knowledge base text and unique source list.
        information_lines: list[str] = []
        all_sources: list[str] = []

        for result in sorted(results, key=lambda item: item.task_order):
            if result.extracted_information:
                information_lines.extend(result.extracted_information.splitlines())
            all_sources.extend(result.sources)

        dedup_info = self._deduplicate(information_lines)
        dedup_sources = self._deduplicate(all_sources)
        return "\n".join(dedup_info).strip(), dedup_sources
