from __future__ import annotations

from pathlib import Path

from adapters.base import AdapterOutput
from skills import SkillRegistry

_SKILLS_ROOT = Path(__file__).resolve().parents[2] / "src" / "skills"


class _StubAdapter:
    provider = "stub"

    def __init__(self, output_text: str = "", raise_exc: Exception | None = None):
        self._text = output_text
        self._raise = raise_exc

    def invoke(self, *, model, messages, constraints):
        if self._raise is not None:
            raise self._raise
        return AdapterOutput(answer_text=self._text)


def _load_skill(name: str, adapter=None):
    reg = SkillRegistry()
    reg.discover(_SKILLS_ROOT)
    skill = reg.get(name)
    if adapter is not None:
        skill._adapter_factory = lambda m: adapter
        skill._adapter_cache.clear()
    return skill


# ---------- rag.transform_query ----------

def test_transform_query_returns_rewritten() -> None:
    skill = _load_skill("rag.transform_query", _StubAdapter("Câu hỏi viết lại chi tiết"))
    out = skill.invoke({"question": "X là gì", "retry_count": 0})
    assert out["transformed_query"] == "Câu hỏi viết lại chi tiết"


def test_transform_query_fallback_to_original_on_empty() -> None:
    skill = _load_skill("rag.transform_query", _StubAdapter("   "))
    out = skill.invoke({"question": "original", "retry_count": 0})
    assert out["transformed_query"] == "original"


def test_transform_query_fallback_on_adapter_error() -> None:
    skill = _load_skill("rag.transform_query", _StubAdapter(raise_exc=RuntimeError("boom")))
    out = skill.invoke({"question": "original", "retry_count": 0})
    assert out["transformed_query"] == "original"


# ---------- rag.grade_documents ----------

def test_grade_documents_filters_by_llm() -> None:
    raw = '{"grades": [{"index": 1, "relevant": true}, {"index": 2, "relevant": false}, {"index": 3, "relevant": true}]}'
    skill = _load_skill("rag.grade_documents", _StubAdapter(raw))
    docs = [
        {"content": "a", "score": 0.9},
        {"content": "b", "score": 0.8},
        {"content": "c", "score": 0.2},
    ]
    out = skill.invoke({"question": "Q", "documents": docs})
    contents = [d["content"] for d in out["relevant_documents"]]
    assert contents == ["a", "c"]


def test_grade_documents_empty_input() -> None:
    skill = _load_skill("rag.grade_documents", _StubAdapter("x"))
    out = skill.invoke({"question": "Q", "documents": []})
    assert out["relevant_documents"] == []


def test_grade_documents_fallback_score_threshold() -> None:
    skill = _load_skill("rag.grade_documents", _StubAdapter("not json"))
    docs = [
        {"content": "high", "score": 0.9},
        {"content": "low", "score": 0.1},
    ]
    out = skill.invoke({"question": "Q", "documents": docs})
    # LLM parse fails → score-based fallback (threshold 0.4)
    assert [d["content"] for d in out["relevant_documents"]] == ["high"]


# ---------- rag.grade_generation ----------

def test_grade_generation_accepts_when_no_context() -> None:
    skill = _load_skill("rag.grade_generation", _StubAdapter("x"))
    out = skill.invoke({"question": "Q", "generation": "A", "context_docs": []})
    # No context → fail open
    assert out["grade"] == "grounded_and_useful"


def test_grade_generation_parses_grade() -> None:
    raw = '{"grade": "hallucination", "reason": "made up data"}'
    skill = _load_skill("rag.grade_generation", _StubAdapter(raw))
    out = skill.invoke({
        "question": "Q",
        "generation": "A",
        "context_docs": [{"content": "doc"}],
    })
    assert out["grade"] == "hallucination"


def test_grade_generation_invalid_value_defaults_to_grounded() -> None:
    raw = '{"grade": "some_random_value"}'
    skill = _load_skill("rag.grade_generation", _StubAdapter(raw))
    out = skill.invoke({
        "question": "Q",
        "generation": "A",
        "context_docs": [{"content": "doc"}],
    })
    assert out["grade"] == "grounded_and_useful"


def test_grade_generation_returns_not_useful_on_adapter_error() -> None:
    # When the grader call fails, the skill must NOT silently accept the
    # answer. Returning "not_useful" lets the subgraph retry via
    # transform_query (or give up cleanly when retries are exhausted).
    skill = _load_skill("rag.grade_generation", _StubAdapter(raise_exc=RuntimeError("x")))
    out = skill.invoke({
        "question": "Q",
        "generation": "A",
        "context_docs": [{"content": "doc"}],
    })
    assert out["grade"] == "not_useful"


# ---------- rag.answer_with_context ----------

def test_answer_with_context_builds_context() -> None:
    adapter_calls = []

    class _RecordingAdapter:
        provider = "stub"

        def invoke(self, *, model, messages, constraints):
            adapter_calls.append(messages)
            return AdapterOutput(answer_text="Câu trả lời có context.")

    skill = _load_skill("rag.answer_with_context", _RecordingAdapter())
    docs = [{"content": "Đây là nội dung quan trọng", "metadata": {"file_path": "/doc1.md"}}]
    out = skill.invoke({"question": "X là gì", "history": [], "relevant_documents": docs})
    assert out["generation"] == "Câu trả lời có context."
    assert "/doc1.md" in out["citations"]
    # Context included in the user message
    user_msg = adapter_calls[0][-1][1]
    assert "NGỮ CẢNH NỘI BỘ" in user_msg
    assert "Đây là nội dung quan trọng" in user_msg


def test_answer_with_context_deduplicates_citations() -> None:
    skill = _load_skill("rag.answer_with_context", _StubAdapter("ok"))
    docs = [
        {"content": "a", "metadata": {"file_path": "/doc1.md"}},
        {"content": "b", "metadata": {"file_path": "/doc1.md"}},  # dup
        {"content": "c", "metadata": {"file_path": "/doc2.md"}},
    ]
    out = skill.invoke({"question": "Q", "history": [], "relevant_documents": docs})
    assert out["citations"] == ["/doc1.md", "/doc2.md"]


def test_answer_with_context_no_docs_no_context_marker() -> None:
    adapter_calls = []

    class _RecordingAdapter:
        provider = "stub"

        def invoke(self, *, model, messages, constraints):
            adapter_calls.append(messages)
            return AdapterOutput(answer_text="OK")

    skill = _load_skill("rag.answer_with_context", _RecordingAdapter())
    skill.invoke({"question": "Q", "history": [], "relevant_documents": []})
    user_msg = adapter_calls[0][-1][1]
    assert "NGỮ CẢNH NỘI BỘ" not in user_msg  # no context added when no docs


# ---------- rag.query_expand ----------

def test_query_expand_returns_list_including_original() -> None:
    skill = _load_skill("rag.query_expand")
    out = skill.invoke({"query": "tìm tài liệu về FastAPI"})
    assert isinstance(out["expansions"], list)
    assert len(out["expansions"]) >= 1
    assert "tìm tài liệu về FastAPI" in out["expansions"]


def test_query_expand_empty_input() -> None:
    skill = _load_skill("rag.query_expand")
    out = skill.invoke({"query": ""})
    assert out["expansions"] == []


# ---------- rag.retrieve ----------

def test_retrieve_returns_empty_when_not_wired() -> None:
    skill = _load_skill("rag.retrieve")
    # retrieval service not injected → returns empty safely
    out = skill.invoke({"query": "X"})
    assert out["documents"] == []


def test_retrieve_uses_injected_service() -> None:
    class _FakeDoc:
        id = "doc1"
        content = "hello"
        score = 0.95
        source_type = "document"
        metadata = {"file_path": "/a.md"}

    class _FakeRetrievalService:
        def retrieve(self, **kwargs):
            return [_FakeDoc()]

    skill = _load_skill("rag.retrieve")
    skill.service = _FakeRetrievalService()
    out = skill.invoke({"query": "X"})
    assert len(out["documents"]) == 1
    assert out["documents"][0]["id"] == "doc1"
    assert out["documents"][0]["score"] == 0.95
