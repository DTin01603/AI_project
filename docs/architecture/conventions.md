# Backend conventions

This document captures the rules every contributor should follow when adding
or moving code in `backend/src/`. It complements `CLAUDE.md` (which holds
project-level operating instructions for AI assistants).

## Layered architecture

Code is organised **layer-first**, not feature-first:

```
backend/src/
├── db/             SQLite connection + schema (one place)
├── models/         Domain entity dataclasses (no I/O, no Pydantic, no LLM)
├── repositories/   One table = one repo. Raw SQL only. Returns Domain entities.
├── services/       Business logic + transactions. Composes repos + tools.
├── api/            HTTP boundary
│   ├── schemas/    Pydantic DTOs (request/response only)
│   ├── routers/    FastAPI endpoints — call services
│   └── deps.py     AppContainer (the single composition root)
├── agent/          LangGraph runtime — nodes, edges, graph, subgraph, state
├── rag/            Pure RAG tooling — chunking, embedding, vector_store, reranker
├── skills/         Single LLM-call wrappers (see "Skill vs Service" below)
└── adapters/       LLM SDK adapters (lazy registry)
```

Two non-negotiable rules:

1. **Lower layers must not import from higher layers.** Repositories never
   import services. Services never import routers. Models never import
   Pydantic. The dependency arrow always points downward.

2. **One table = one repository.** Adding a new table means adding one
   `repositories/<table>_repo.py`. Don't pile multiple-table queries into a
   single repo — that belongs in a service.

---

## Skill vs Service boundary

This is the most easily confused boundary in the codebase. Read it carefully.

### Skill

A **Skill** is a thin wrapper around **one LLM call**. It exists to:

1. Load a prompt template (`skills/<name>/prompt.md`) and render it with inputs.
2. Call the LLM adapter once.
3. Parse + validate the response (Pydantic).

A skill **must not**:

- Make more than one LLM call.
- Read or write the database (SQLite, vector store).
- Contain `if/else` flow control beyond input validation.
- Implement retry loops, timeouts, or fan-out logic.
- Orchestrate other skills.

Examples that are correctly skills:

- `skills/direct_answer/` — render prompt + one LLM call → string.
- `skills/intent_classifier/` — render prompt + one LLM call → enum.
- `skills/rag/grade_documents/` — render prompt + one LLM call → grade.
- `skills/rag/grade_generation/` — render prompt + one LLM call → grade.
- `skills/rag/answer_with_context/` — render prompt + one LLM call → answer.
- `skills/rag/transform_query/` — render prompt + one LLM call → query.
- `skills/planning/` — render prompt + one LLM call → plan.
- `skills/response_composer/` — render prompt + one LLM call → response.
- `skills/research_search/` — Tavily API call (one external tool call,
  treated like an LLM call for skill purposes).

### Service

A **Service** lives in `backend/src/services/` and **orchestrates** repos,
skills, and pure tools. It owns:

- Transaction boundaries (open/commit/rollback).
- Multi-step business logic (e.g. chunk → embed → persist).
- Cross-entity invariants (`persist_turn` writes both messages atomically).
- Calling multiple skills/tools in sequence or parallel.

A service **may**:

- Call repositories.
- Call skills (for an LLM step).
- Call pure tools in `rag/` (chunking, embedding, vector_store, reranker).
- Open `factory.transaction()` blocks.

A service **must not**:

- Open SQLite connections directly (always go through the factory).
- Receive `sqlite3.Row` objects (repos translate to Domain entities first).
- Be imported from `api/routers/` without going through `AppContainer`.

Examples:

- `ConversationService.persist_turn()` writes user + assistant messages in
  one transaction. Multi-step + transaction → service.
- `DocumentIndexingService.index_document()` chunks → embeds → persists →
  pushes to vector store. Multi-step → service.
- `CitationService.attach_to_documents()` upserts citations + usage rows in
  one transaction.
- `HybridSearchService.search()` runs FTS and vector search in parallel,
  merges + reranks. Multi-source orchestration → service.

### The grey zone: thin wrappers

Two skills wrap a single non-LLM tool because the agent's skill registry
gives them a uniform invocation API:

- `skills/rag/retrieve/` — wraps `RetrievalNode.retrieve()`. Not an LLM call,
  but follows the skill registry contract (Inputs → run() → Outputs).
- `skills/rag/query_expand/` — wraps `QueryExpander.expand()`. Same pattern.

These are **acceptable** because:

1. They are still single-step wrappers (no flow control, no orchestration).
2. The agent invokes everything through the skill registry; forcing a
   different invocation path for two endpoints would be more complexity than
   it solves.

Do **not** add new non-LLM skills. New non-LLM operations belong in
`services/` or `rag/` and are called directly by the agent node.

### Anti-patterns (do NOT write skills like this)

```python
# ANTI-PATTERN: skill that reads the database
class Handler(BaseSkill):
    def run(self, inputs: Inputs) -> dict[str, Any]:
        history = self.database.get_conversation_history(...)  # ❌
        # ...
```
→ This is a service. Move to `services/`.

```python
# ANTI-PATTERN: skill with retry loop
class Handler(BaseSkill):
    def run(self, inputs: Inputs) -> dict[str, Any]:
        for attempt in range(3):  # ❌
            try:
                return self._call_llm(inputs)
            except RateLimitError:
                time.sleep(2 ** attempt)
```
→ Retry/backoff is orchestration. Move to a service or use
`agent/utils/resilience.py`.

```python
# ANTI-PATTERN: skill with conditional branching
class Handler(BaseSkill):
    def run(self, inputs: Inputs) -> dict[str, Any]:
        if inputs.complexity == "simple":  # ❌
            return self._direct_answer(...)
        elif inputs.complexity == "complex":
            return self._multi_step_answer(...)
```
→ This is a router/service. Move to a service or split into multiple skills
plus a service that picks the right one.

### Audit checklist when adding a new module

Ask these questions in order:

1. Does it open a SQLite connection? → repository.
2. Does it own a transaction? → service.
3. Does it call >1 LLM? → service.
4. Does it have `if/else` over inputs to pick a strategy? → service.
5. Is it a single LLM call wrapping a prompt? → skill.
6. Is it CPU-only deterministic computation (chunk, embed, rerank)? → `rag/`
   tool.
7. Is it a LangGraph node, edge, or graph? → `agent/`.
8. Is it Pydantic input/output for HTTP? → `api/schemas/`.

If the answer to (1)-(4) is "yes" and you ended up calling it a skill,
that's an anti-pattern — refactor before merging.

---

## Imports and circular dependencies

- `from api.deps import get_container` is the canonical way for routers to
  pull dependencies. Routers should not call `AppContainer(...)` directly.
- `agent/nodes/__init__.py` is intentionally empty; import each node module
  by its full path (`from agent.nodes.retrieval_node import RetrievalNode`).
  This avoids triggering the whole skills + LLM SDK chain when a unit test
  exercises only one node.
- `adapters/__init__.py` lazy-loads vendor SDKs (`groq`, `google-genai`).
  Listing providers (`adapters.list_providers()`) does not import any SDK.

---

## Tests

- Unit tests for repositories use `SQLiteConnectionFactory(tmp_path / "x.db")`
  + `run_migrations(factory)` directly — no `AppContainer`.
- Unit tests for services build a real factory + repos + service stack
  (no mocks for SQLite). Mock only external IO (LLM, vector store, embedding).
- Integration tests use `AppContainer(db_path=tmp_path / "x.db")` to
  exercise the full wiring.
- Cosmetic tests (grep "no legacy import remaining") are valuable
  immediately after a refactor PR but are rarely worth keeping long-term —
  prune them once the refactor has stabilised.
