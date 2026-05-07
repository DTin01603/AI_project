# Design — improve-architecture-v2

## 1. Architecture summary

Plan này cải tổ tầng runtime (LangGraph + RAG) để khớp nguyên tắc layer-first đã áp dụng cho tầng dữ liệu ở plan trước. Sau plan: `agent/` = toàn bộ LangGraph runtime (gồm retrieval node, subgraph); `services/` = toàn bộ business orchestration (gồm hybrid search, multi-query, research aggregation); `rag/` = chỉ pure tooling không có flow control. 5 shim còn sót bị xóa, mỗi caller chuyển sang dùng repos/services trực tiếp. Class chính rename `ResearchAgentGraph` → `AgentGraph` để khớp package. LLM SDK adapter chuyển sang lazy-import. `CLAUDE.md` được bổ sung quy ước Skill/Service boundary với ví dụ. Mọi thay đổi qua nhiều PR nhỏ, không big-bang.

**Các thành phần chính sau plan:**

- `agent/` — đầy đủ LangGraph runtime (10 nodes gồm retrieval, edges, graph, subgraph, state, utils, checkpointer, streaming).
- `services/` — 7 service: conversation, citation, document_indexing, conversation_indexing, hybrid_search, multi_query, research_aggregation.
- `rag/` — pure tooling: chunking, embedding, vector_store, reranker, query_expander, contextual_compressor, document_loader, metrics, config.
- `adapters/` — lazy-load registry cho LLM SDK.
- `docs/architecture/conventions.md` (hoặc section trong `CLAUDE.md`) — quy ước Skill/Service.
- `tests/integration/` — ≥3 integration test mới qua TestClient.

## 2. Component breakdown

### `agent/nodes/retrieval_node.py` (move từ `rag/retrieval_node.py`)

- **Responsibility**: LangGraph node thực thi retrieval (FTS + vector + rerank). Inject service thay vì gọi engine trực tiếp.
- **Inputs**: `MessageRepository` (FTS), `VectorStore`, `EmbeddingModel`, `RAGConfig`, `HybridSearchService`, `ReRanker`.
- **Outputs**: `state["retrieved_documents"]`, `state["retrieval_metadata"]`.
- **Dependencies**: `services.hybrid_search_service`, `rag.reranker`, `rag.embedding`, `rag.vector_store`, `repositories.message_repo`.
- **Cấm**: gọi LLM trực tiếp (qua skill nếu cần), tự mở DB.

### `agent/subgraph/` (move từ `rag/subgraph/`)

- **Responsibility**: Sub-LangGraph cho self-correcting RAG (retrieve → grade → generate → grade_generation → loop). Đây thuần LangGraph.
- **Files**: `graph.py`, `nodes.py`, `edges.py`, `state.py`.
- **Cấm**: business logic ngoài flow control LangGraph.

### `services/hybrid_search_service.py` (move từ `rag/hybrid_search.py`)

- **Responsibility**: Orchestrate FTS + vector search song song, merge ranked results.
- **Inputs**: `MessageRepository`, `VectorStore`, `EmbeddingModel`, `QueryExpander | None`, weights (fts/vector).
- **Outputs**: `list[SearchResult]` (Domain entity).
- **Cấm**: mở DB trực tiếp, gọi LLM trực tiếp.

### `services/multi_query_service.py` (move từ `rag/multi_query_retriever.py`)

- **Responsibility**: Generate nhiều query variant + retrieve từng cái + merge.
- **Inputs**: `search_fn` callable (typically `HybridSearchService.search`), `max_sub_queries`.
- **Cấm**: mở DB.

### `services/research_aggregation_service.py` (move từ `agent/aggregator.py`)

- **Responsibility**: Merge research results từ nhiều branch (planning, research, synthesis).
- **Inputs**: research output dicts từ research nodes.
- **Outputs**: aggregated answer + citations + metadata.
- **Cấm**: gọi LLM trực tiếp (skill xử), gọi DB.

### `agent/graph/agent_graph.py` (rename từ `research_agent_graph.py`)

- **Responsibility**: Compile LangGraph + ainvoke/astream.
- **Class**: `AgentGraph` (rename từ `ResearchAgentGraph`).
- **Wire**: cập nhật `agent/__init__.py`, `api/deps.py`, `api/routers/chat_v2.py`, `langgraph_platform.py`.

### `agent/utils/resilience.py` (move từ `agent/resilience.py`)

- **Responsibility**: retry/timeout helper. Đúng tầng utility.

### `adapters/__init__.py` — lazy registry

- **Responsibility**: Load adapter theo `model_id` (e.g. `"gemini/gemini-2.5-flash"` → `GoogleAdapter`). Lazy-import SDK chỉ khi adapter được resolve.
- **Pattern**: registry dict mapping prefix → loader function. Loader gọi `importlib.import_module` ở thời điểm cần.

### `docs/architecture/conventions.md` (mới, hoặc section ở `CLAUDE.md`)

- **Nội dung**: Quy ước Skill/Service boundary với:
  - Định nghĩa: Skill = wrapper LLM call duy nhất (load prompt + call adapter + parse response), KHÔNG flow control. Service = orchestrate nhiều skill/repo.
  - Ví dụ đúng: `direct_answer` skill (1 LLM call). `ConversationIndexingService` service (multi-step chunk + embed + persist).
  - Anti-pattern: skill có `if/else` chọn flow → đó là service. Skill có retry loop → đó là service.
  - Audit checklist: skill có gọi >1 LLM, có DB read/write, có conditional logic → cần refactor sang service.

### Integration test mới

- **`test_chat_endpoint_e2e.py`**: TestClient gọi `POST /api/v2/chat` với payload mẫu, verify status 200, response shape đúng `ChatResponse`. Mock LLM adapter ở edge (không gọi API thật).
- **`test_search_endpoint_e2e.py`**: TestClient gọi `POST /api/search` với query mẫu, verify response shape `SearchResponse`.
- **`test_app_container_full_graph_compile.py`**: Khởi tạo `AppContainer` thật + compile `AgentGraph`, verify graph build không raise (full wiring smoke test).

## 3. Data model

**Không thay đổi data model.** Plan này thuần restructuring code. Schema SQLite, Domain entity, DTO Pydantic giữ nguyên byte-equal.

## 4. API / interface

### Class signatures sau khi rename

```python
# Trước:
class ResearchAgentGraph:
    async def ainvoke(self, payload: ChatRequest, request_id: str | None = None) -> AgentState: ...
    async def astream(self, payload: ChatRequest, request_id: str | None = None): ...

# Sau:
class AgentGraph:
    async def ainvoke(self, payload: ChatRequest, request_id: str | None = None) -> AgentState: ...
    async def astream(self, payload: ChatRequest, request_id: str | None = None): ...
```

### `RetrievalNode` signature đổi (Task 4)

```python
# Trước (qua FTSEngine shim):
class RetrievalNode:
    def __init__(self, fts_engine: FTSEngine, config: RAGConfig | None = None, ...): ...

# Sau (nhận service trực tiếp):
class RetrievalNode:
    def __init__(
        self,
        message_repo: MessageRepository,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        hybrid_search_service: HybridSearchService,
        config: RAGConfig | None = None,
        ...
    ): ...
```

### `agent/nodes/common.py` + `llm_node.py` signature đổi (Task 5)

```python
# Trước:
def run_llm_node(state, database: Database, ...): ...
def llm_node(state, database: Database, ...): ...

# Sau:
def run_llm_node(state, conversation_service: ConversationService, ...): ...
def llm_node(state, conversation_service: ConversationService, ...): ...
```

### `adapters/__init__.py` registry pattern

```python
_REGISTRY: dict[str, Callable[[], type]] = {
    "gemini": lambda: _import_module("adapters.google_adapter").GoogleAdapter,
    "google": lambda: _import_module("adapters.google_adapter").GoogleAdapter,
    "groq": lambda: _import_module("adapters.groq_adapter").GroqAdapter,
}

def get_adapter_for_model(model: str) -> BaseAdapter:
    provider = model.split("/", 1)[0].strip().lower()
    loader = _REGISTRY.get(provider)
    if loader is None:
        raise ValueError(f"No adapter for provider {provider!r}")
    cls = loader()  # lazy import
    return cls(...)
```

## 5. Data flow

### Flow A — Chat (sau plan)

1. `POST /api/v2/chat` → `chat_v2` router.
2. `AgentGraph.ainvoke(payload)`.
3. Graph nodes: entry → intent → [direct_answer | local_rag | planning→research→synthesis→citation | current_date].
4. `local_rag` node gọi `RetrievalNode` (giờ ở `agent/nodes/retrieval_node.py`) → service `HybridSearchService.search()`.
5. `persist_conversation_node` → `ConversationService.persist_turn()` (đã có ở plan trước).

### Flow B — Search (sau plan)

1. `POST /api/search` → `search` router.
2. `AppContainer.retrieval_node.retrieve()`.
3. `HybridSearchService.search()` (ở `services/`) — parallel FTS + vector.
4. FTS qua `MessageRepository.search_fts()`.
5. Vector qua `ChromaVectorStore.search()`.
6. Merge + rerank → trả `list[SearchResult]`.

### Flow C — Indexing (không đổi)

Giữ nguyên flow ở plan trước (`DocumentIndexingService.index_document` + `ConversationIndexingService.save_message`).

## 6. Error handling & edge cases

- **Move file đụng nhiều import**: từng PR có script grep verify zero remaining import từ path cũ trước khi merge.
- **Rename `ResearchAgentGraph` → `AgentGraph`**: nếu có external caller (LangGraph Platform deployment hook, IDE config), cần verify trước. Plan: grep + smoke test deploy.
- **Xóa shim đụng test cũ**: refactor 30+ test thành dùng `AppContainer` fixture chung. PR test refactor làm trước, PR xóa shim làm sau.
- **Lazy-import LLM SDK fail tại runtime**: nếu user gọi endpoint cần Gemini nhưng `google-genai` chưa cài → adapter raise `ImportError` lúc invoke (không phải lúc startup). Test: smoke test lazy registry với mock import error.
- **Skill audit phát hiện vi phạm boundary**: refactor sang service trong PR riêng, không gộp với move file.
- **Integration test mới fail do thiếu env var**: dùng pytest fixture `monkeypatch.setenv()` set fake API keys. Mock adapter ở edge.

## 7. Security considerations

- **Không thay đổi attack surface**: refactor là thuần move code, không thêm endpoint mới.
- **Không log sensitive payload**: giữ nguyên hành vi log hiện tại.
- **Lazy-import không bypass auth check**: chỉ import module, không skip validation.
- **Test mới với fake API keys**: `monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")` — không leak key thật vào CI log.

## 8. Alternatives considered

- **Để nguyên `rag/retrieval_node.py`**: rejected — gây confusion mental model "agent vs rag", phá nguyên tắc layer-first.
- **Move toàn bộ `rag/` vào `services/`**: rejected — pure tooling (chunking, embedding) không phải business orchestration. Tách ra mới đúng tầng.
- **Giữ shim, chỉ reorganize folder**: rejected — shim là technical debt rõ ràng, có 2 đường làm cùng 1 việc gây confusion lâu dài.
- **Đổi tên `ResearchAgentGraph` qua deprecation alias 1 release**: rejected — project nội bộ, alias là noise (theo §8.3 plan trước).
- **Refactor toàn bộ trong 1 PR**: rejected — diff khổng lồ, review impossible. Chia ≥7 PR theo roadmap.
- **Bỏ Skill/Service convention, để code "ai thấy hợp thì viết"**: rejected — chính lằn ranh mờ là vấn đề skill/service hiện tại. Có quy ước rõ giúp reviewer reject sớm.
- **Eager-import LLM SDK ở `adapters/`**: rejected — block test environment thiếu SDK; refactor 7a đã chứng minh lazy-import đáng làm.
