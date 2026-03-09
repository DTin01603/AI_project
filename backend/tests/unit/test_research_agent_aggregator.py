from research_agent.aggregator import Aggregator
from research_agent.models import ResearchResult


def test_aggregator_preserves_and_deduplicates_sources() -> None:
    aggregator = Aggregator()
    results = [
        ResearchResult(task_order=2, extracted_information="A\nB", sources=["https://x", "https://y"]),
        ResearchResult(task_order=1, extracted_information="A\nC", sources=["https://x"]),
    ]

    info, sources = aggregator.aggregate(results)

    assert "A" in info
    assert "B" in info
    assert "C" in info
    assert sources == ["https://x", "https://y"]
