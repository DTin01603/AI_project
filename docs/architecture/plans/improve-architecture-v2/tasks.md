# Tasks — improve-architecture-v2

> Convention: mỗi task có 1 block test đi kèm (pytest, AAA), tối thiểu 1 happy
> + 1 edge case. Mỗi task = 1 PR độc lập, test cũ phải xanh trước và sau.
> Không đổi schema DB, không đổi public API behavior.

---

## Task 1 — Move `rag/retrieval_node.py` → `agent/nodes/retrieval_node.py`

**What:** `git mv` file. Update import ở 4 caller production (`api/deps.py`, `agent/graph/research_agent_graph.py`, `rag/subgraph/nodes.py`, `skills/rag/retrieve/handler.py`) và ~5 caller test. Giữ class signature, behavior không đổi.

**Where:**
- `backend/src/agent/nodes/retrieval_node.py` (move target)
- `backend/src/api/deps.py`, `backend/src/agent/graph/research_agent_graph.py`
- `backend/src/rag/subgraph/nodes.py`, `backend/src/skills/rag/retrieve/handler.py`
- `backend/tests/integration/test_*retrieval*.py`, `backend/tests/unit/test_retrieval_node.py`

**Done when:**
- `find backend/src/rag -name "retrieval_node.py"` zero hit.
- `grep -rn "from rag.retrieval_node\|from rag\\.retrieval_node" backend/` zero hit.
- Test cũ `test_retrieval_node.py` xanh sau khi đổi import.

### Unit test 1.1 — `should_import_retrieval_node_from_agent_when_renamed`
- Framework: pytest
- Arrange: nothing.
- Act: `from agent.nodes.retrieval_node import RetrievalNode`.
- Assert: import thành công, class có method `retrieve`.

### Unit test 1.2 — `should_have_no_retrieval_node_under_rag`
- Framework: pytest (smoke grep)
- Arrange: helper `subprocess.run(["grep", "-rn", "from rag.retrieval_node", "backend/"], capture_output=True)`.
- Act: chạy.
- Assert: `result.stdout == b""`.

---

## Task 2 — Move `rag/subgraph/` → `agent/subgraph/`

**What:** `git mv` thư mục. Update import ở 2 caller (`api/deps.py`, `agent/graph/research_agent_graph.py`) + import nội bộ trong `subgraph/` files.

**Where:**
- `backend/src/agent/subgraph/{__init__,graph,nodes,edges,state}.py` (move target)
- `backend/src/api/deps.py`
- `backend/src/agent/graph/research_agent_graph.py`

**Done when:**
- `find backend/src/rag -type d -name subgraph` zero hit.
- `grep -rn "from rag.subgraph" backend/` zero hit.
- Test cũ liên quan subgraph (nếu có) xanh.

### Unit test 2.1 — `should_import_subgraph_from_agent`
- Framework: pytest
- Arrange: nothing.
- Act: `from agent.subgraph import RAGSubgraph`.
- Assert: import thành công.

### Unit test 2.2 — `should_have_no_subgraph_under_rag`
- Framework: pytest (smoke grep) — như 1.2 nhưng cho `rag.subgraph`.
- Assert: zero hit.

---

## Task 3 — Move `rag/hybrid_search.py` → `services/hybrid_search_service.py` + rename class

**What:** Move file + đổi tên `HybridSearchEngine` → `HybridSearchService`. Update import ở `RetrievalNode`, `api/deps.py`, test files. Giữ public method signature.

**Where:**
- `backend/src/services/hybrid_search_service.py` (new)
- `backend/src/agent/nodes/retrieval_node.py` (đổi import + dùng tên class mới)
- `backend/src/api/deps.py`
- Test files dùng `HybridSearchEngine`

**Done when:**
- `find backend/src/rag -name "hybrid_search.py"` zero hit.
- `grep -rn "HybridSearchEngine" backend/` zero hit.

### Unit test 3.1 — `should_merge_fts_and_vector_results_when_search`
- Framework: pytest
- Arrange: stub `MessageRepository.search_fts` trả 2 result, stub `VectorStore.search` trả 2 result khác.
- Act: `service.search(query, top_k=4)`.
- Assert: 4 result merge đúng, score weighted đúng.

### Unit test 3.2 — `should_fallback_to_fts_only_when_vector_store_fails`
- Framework: pytest
- Arrange: stub `VectorStore.search` raise `RuntimeError`. FTS trả 2 result.
- Act: `service.search(query, top_k=4)`.
- Assert: trả 2 FTS result, không raise.

---

## Task 4 — Move `rag/multi_query_retriever.py` → `services/multi_query_service.py`

**What:** Move + giữ tên class hoặc đổi `MultiQueryRetriever` → `MultiQueryService`. Update caller ở `RetrievalNode`, test.

**Where:**
- `backend/src/services/multi_query_service.py` (new)
- `backend/src/agent/nodes/retrieval_node.py`
- Test files

**Done when:**
- `find backend/src/rag -name "multi_query*.py"` zero hit.

### Unit test 4.1 — `should_call_search_fn_for_each_subquery`
- Framework: pytest
- Arrange: mock `search_fn` ghi nhận từng call. Service config `max_sub_queries=3`.
- Act: `service.retrieve("query")`.
- Assert: `search_fn` được gọi đúng 3 lần với 3 query khác nhau.

### Unit test 4.2 — `should_dedupe_results_across_subqueries`
- Framework: pytest
- Arrange: mock `search_fn` trả result trùng (cùng `id`) cho mỗi subquery.
- Act: retrieve.
- Assert: kết quả unique theo `id`, không lặp.

---

## Task 5 — Move `agent/aggregator.py` → `services/research_aggregation_service.py`

**What:** Move + đổi tên `Aggregator` → `ResearchAggregationService`. Update caller `api/deps.py`, `agent/nodes/synthesis_node.py`, test.

**Where:**
- `backend/src/services/research_aggregation_service.py` (new)
- `backend/src/api/deps.py`, `backend/src/agent/nodes/synthesis_node.py`
- `backend/tests/unit/test_research_agent_aggregator.py` → `test_research_aggregation_service.py`

**Done when:**
- `find backend/src/agent -name "aggregator.py"` zero hit.

### Unit test 5.1 — `should_merge_research_branches_when_aggregate`
- Framework: pytest
- Arrange: 2 research branch result dict.
- Act: `service.aggregate(branches)`.
- Assert: output có citations + answer combined đúng.

### Unit test 5.2 — `should_handle_empty_branches_gracefully`
- Framework: pytest
- Arrange: `branches = []`.
- Act: `service.aggregate([])`.
- Assert: trả default empty result, không raise.

---

## Task 6 — Move `agent/resilience.py` → `agent/utils/resilience.py`

**What:** Move file + update import nội bộ trong `agent/`.

**Where:**
- `backend/src/agent/utils/resilience.py` (move)
- Caller trong `agent/nodes/`, `agent/graph/`

**Done when:**
- `find backend/src/agent -maxdepth 1 -name "resilience.py"` zero hit.

### Unit test 6.1 — `should_import_resilience_from_utils`
- Framework: pytest
- Arrange: nothing.
- Act: `from agent.utils.resilience import retry_with_backoff` (hoặc symbol thật).
- Assert: import OK.

### Unit test 6.2 — Test cũ `test_research_agent_resilience.py` xanh sau đổi import.
- Framework: pytest
- Arrange: existing fixtures.
- Act: chạy test suite cũ.
- Assert: zero failure.

---

## Task 7 — Rename `ResearchAgentGraph` → `AgentGraph` + `research_agent_graph.py` → `agent_graph.py`

**What:** Đổi tên class + file. Update mọi caller (`api/deps.py`, `chat_v2.py`, `langgraph_platform.py`, `agent/__init__.py`). Đổi `get_research_agent_graph` → `get_agent_graph` ở `api/deps.py`.

**Where:**
- `backend/src/agent/graph/agent_graph.py` (rename)
- `backend/src/agent/graph/__init__.py`
- `backend/src/api/deps.py`, `backend/src/api/__init__.py`
- `backend/src/api/routers/chat_v2.py`
- `backend/src/langgraph_platform.py`

**Done when:**
- `grep -rn "ResearchAgentGraph\|research_agent_graph" backend/src/` zero hit.
- `grep -rn "get_research_agent_graph" backend/src/` zero hit (đổi sang `get_agent_graph`).

### Unit test 7.1 — `should_import_agent_graph_class_when_renamed`
- Framework: pytest
- Arrange: nothing.
- Act: `from agent.graph import AgentGraph`.
- Assert: class có method `ainvoke`, `astream`.

### Unit test 7.2 — `should_have_no_legacy_class_name_in_src`
- Framework: pytest (smoke grep)
- Arrange: subprocess grep `"ResearchAgentGraph"` trong `backend/src/`.
- Assert: zero hit.

---

## Task 8 — Lazy-import LLM SDK trong `adapters/__init__.py` (registry pattern)

**What:** Refactor `adapters/__init__.py` thành registry với loader function. SDK chỉ import lúc adapter được resolve.

**Where:**
- `backend/src/adapters/__init__.py`
- `backend/src/adapters/google_adapter.py`, `groq_adapter.py` (giữ nguyên content)

**Done when:**
- `python -c "import adapters"` không raise trong env không có `groq` package.
- Test mới verify lazy behavior.

### Unit test 8.1 — `should_import_adapters_module_without_optional_sdk`
- Framework: pytest
- Arrange: `monkeypatch.setitem(sys.modules, "groq", None)` (giả lập groq missing).
- Act: `import adapters` + `adapters.list_providers()` (chỉ list keys, không import SDK).
- Assert: import + list không raise.

### Unit test 8.2 — `should_raise_clear_error_when_resolving_adapter_for_uninstalled_provider`
- Framework: pytest
- Arrange: monkeypatch để `groq` import raise `ImportError`.
- Act: `get_adapter_for_model("groq/llama-3.3-70b-versatile")`.
- Assert: raise `ImportError` hoặc custom error có message rõ "groq SDK not installed".

---

## Task 9 — Audit `skills/rag/`, refactor skill vi phạm boundary thành service

**What:** Đọc 6 skill trong `skills/rag/` (`retrieve`, `grade_documents`, `grade_generation`, `query_expand`, `transform_query`, `answer_with_context`). Áp dụng checklist (xem design §2): >1 LLM call hoặc DB I/O hoặc conditional logic phức tạp → chuyển service.

**Where:**
- `backend/src/skills/rag/<offending>/handler.py` (audit)
- `backend/src/services/` (target nếu cần move)
- Caller (typically `agent/nodes/`, `subgraph/nodes.py`)

**Done when:**
- `docs/architecture/conventions.md` (hoặc section trong `CLAUDE.md`) ghi rõ skill nào đã chuyển service và lý do.
- Mỗi skill còn lại trong `skills/rag/` thật sự là single LLM call wrapper.

### Unit test 9.1 — `should_be_single_llm_call_when_skill_invoked` (cho mỗi skill còn lại)
- Framework: pytest
- Arrange: mock LLM adapter, count `invoke` calls.
- Act: gọi `skill.invoke(payload)`.
- Assert: adapter `invoke` đúng 1 lần.

### Unit test 9.2 — `should_have_no_db_imports_in_skill_handlers`
- Framework: pytest (static check)
- Arrange: list file `skills/rag/*/handler.py`. Read text mỗi file.
- Act: grep `import sqlite3\|from db\|from repositories\|from services`.
- Assert: zero hit (skill không dùng DB hay service).

---

## Task 10 — Document Skill/Service boundary

**What:** Thêm section "Skill vs Service boundary" vào `CLAUDE.md` (hoặc tạo `docs/architecture/conventions.md`). Nội dung theo design §2 component "conventions.md" — định nghĩa, ví dụ đúng, anti-pattern, audit checklist.

**Where:**
- `CLAUDE.md` hoặc `docs/architecture/conventions.md`

**Done when:**
- Section tồn tại, ≥30 dòng.
- Ví dụ ≥1 skill đúng + ≥1 service đúng + ≥2 anti-pattern.
- (Note: pure documentation task — không có unit test cho việc này. Smoke test thay thế: file tồn tại + chứa keyword "Skill", "Service", "boundary".)

### Smoke test 10.1 — `should_have_conventions_doc_with_required_sections`
- Framework: pytest
- Arrange: `Path("docs/architecture/conventions.md")` hoặc check `CLAUDE.md`.
- Act: read text.
- Assert: contains "Skill", "Service", "boundary", có ≥30 dòng non-empty.

(Justification: thuần documentation; không có code logic để unit test.)

---

## Task 11 — Refactor caller test cũ dùng shim → dùng AppContainer fixture

**What:** Tạo conftest fixture `app_container(tmp_path)` build `AppContainer` với DB tạm. Refactor 30+ test (unit + integration + property + manual) dùng `Database(db_path)`, `FTSEngine(db_path)`, `CitationTracker(db_path)`, `DocumentIndexer(db_path)`, `ConversationIndexer(database=db, ...)` → dùng `app_container.message_repo`, `app_container.conversation_service`, etc.

**Where:**
- `backend/tests/conftest.py` (new) — định nghĩa fixture
- 30+ test files (xem grep ở bước 7b survey)

**Done when:**
- `grep -rn "Database(\|FTSEngine(\|CitationTracker(\|DocumentIndexer(\|ConversationIndexer(" backend/tests/` zero hit (trừ trong fixture định nghĩa).

### Unit test 11.1 — `should_provide_app_container_fixture_with_temp_db`
- Framework: pytest (test cho fixture mới)
- Arrange: pytest tự inject `app_container` fixture.
- Act: `app_container.conversation_service.persist_turn("c", "u", "a")`.
- Assert: `app_container.message_repo.list_by_conversation("c")` trả 2 messages.

### Unit test 11.2 — `should_isolate_db_across_test_runs`
- Framework: pytest
- Arrange: 2 test riêng dùng cùng fixture.
- Act: test 1 ghi data. Test 2 query.
- Assert: test 2 thấy DB rỗng (tmp_path khác nhau).

---

## Task 12 — Update `RetrievalNode` nhận `MessageRepository` thay `FTSEngine`

**What:** Đổi `RetrievalNode.__init__` từ `fts_engine: FTSEngine` sang `message_repo: MessageRepository`. Internal dùng `message_repo.search_fts()` thay vì `fts_engine.search()`. Update wiring ở `AppContainer`.

**Where:**
- `backend/src/agent/nodes/retrieval_node.py` (đã ở vị trí mới sau Task 1)
- `backend/src/api/deps.py`
- Test files khởi tạo `RetrievalNode`

**Done when:**
- `RetrievalNode.__init__` không còn param `fts_engine`.
- `grep -rn "FTSEngine" backend/src/agent/" zero hit.

### Unit test 12.1 — `should_call_message_repo_search_fts_when_retrieve`
- Framework: pytest
- Arrange: mock `MessageRepository.search_fts`. Stub các thành phần khác.
- Act: `node.retrieve(query="hi", method="fts")`.
- Assert: `message_repo.search_fts` được gọi đúng 1 lần.

### Unit test 12.2 — `should_propagate_error_when_repo_raises`
- Framework: pytest
- Arrange: mock `message_repo.search_fts` raise `sqlite3.OperationalError`.
- Act: `node.retrieve(...)`.
- Assert: error propagate hoặc handle theo design.

---

## Task 13 — Update `agent/nodes/common.py` + `llm_node.py` nhận `ConversationService`

**What:** Đổi signature `run_llm_node(state, database: Database, ...)` → `run_llm_node(state, conversation_service: ConversationService, ...)`. Tương tự `llm_node`. Update wiring ở graph builder. Test cũ `test_research_agent_llm_node.py` (nếu có) cập nhật fake.

**Where:**
- `backend/src/agent/nodes/common.py`
- `backend/src/agent/nodes/llm_node.py`
- `backend/src/agent/graph/agent_graph.py` (đã rename ở Task 7)
- Test files

**Done when:**
- `grep -n "from agent.database" backend/src/agent/nodes/" zero hit.

### Unit test 13.1 — `should_call_conversation_service_get_history_when_run_llm`
- Framework: pytest
- Arrange: fake `ConversationService` ghi nhận call. State với `conversation_id` set.
- Act: `run_llm_node(state, fake_service, ...)`.
- Assert: `fake_service.get_history(conv_id)` được gọi.

### Unit test 13.2 — `should_create_conversation_when_id_missing`
- Framework: pytest
- Arrange: state không có `conversation_id`. Fake service.
- Act: `run_llm_node(state, fake_service, ...)`.
- Assert: `fake_service.get_or_create_conversation(None)` được gọi, state metadata có conv_id mới.

---

## Task 14 — Xóa 5 shim file

**What:** Sau khi Task 11, 12, 13 đã chuyển hết caller, xóa: `agent/database.py`, `rag/fts_engine.py`, `rag/citation_tracker.py`, `rag/document_indexer.py`, `rag/conversation_indexer.py`. Update `agent/__init__.py`, `rag/__init__.py` để bỏ re-export.

**Where:**
- DELETE 5 file
- `backend/src/agent/__init__.py`, `backend/src/rag/__init__.py`

**Done when:**
- 5 file không còn trong tree.
- `grep -rn "class Database\|class FTSEngine\|class CitationTracker\|class DocumentIndexer\|class ConversationIndexer" backend/src/` zero hit.
- Toàn bộ test xanh.

### Unit test 14.1 — `should_have_no_shim_files_remaining`
- Framework: pytest
- Arrange: list expected paths.
- Act: check `Path(...).exists()` cho 5 path shim.
- Assert: tất cả `False`.

### Unit test 14.2 — Toàn bộ test cũ + mới xanh.
- Framework: pytest (full regression).
- Arrange: empty.
- Act: `pytest backend/tests/` (smoke).
- Assert: exit code 0.

---

## Task 15 — Thêm 3 integration test qua FastAPI TestClient

**What:** Tạo 3 test mới ở `backend/tests/integration/`:
- `test_chat_endpoint_e2e.py` — `POST /api/v2/chat` happy path.
- `test_search_endpoint_e2e.py` — `POST /api/search` happy path.
- `test_app_container_full_graph_compile.py` — smoke `AgentGraph` compile thành công với container thật.

**Where:**
- `backend/tests/integration/test_chat_endpoint_e2e.py` (new)
- `backend/tests/integration/test_search_endpoint_e2e.py` (new)
- `backend/tests/integration/test_app_container_full_graph_compile.py` (new)

**Done when:**
- 3 file test mới tồn tại.
- Cả 3 xanh trong env có đủ SDK (Gemini/Groq mocked nếu env không cài).

### Integration test 15.1 — `should_return_200_when_post_chat_with_valid_payload`
- Framework: pytest + `fastapi.testclient.TestClient`
- Arrange: `monkeypatch.setenv("GEMINI_API_KEY", "fake")`. Mock LLM adapter ở edge.
- Act: `client.post("/api/v2/chat", json={"message": "hi"})`.
- Assert: status 200, response shape match `ChatResponse`.

### Integration test 15.2 — `should_return_400_when_post_chat_with_empty_message`
- Framework: pytest + TestClient
- Arrange: TestClient.
- Act: `client.post("/api/v2/chat", json={"message": ""})`.
- Assert: status 400, error code `BAD_REQUEST`.

### Integration test 15.3 — `should_compile_full_agent_graph_via_container`
- Framework: pytest
- Arrange: `AppContainer(db_path=tmp_path/"x.db")`.
- Act: `await container.research_agent_graph._ensure_compiled()` (rename theo Task 7).
- Assert: trả compiled graph object, không raise.

---

## Definition of done

- [ ] Toàn bộ 15 task hoàn thành, mỗi task = 1 PR đã merge.
- [ ] Acceptance criteria trong `requirements.md §7` được verify (gồm 8 grep zero-hit checks).
- [ ] Test cũ + test mới xanh sau **mỗi** PR (gác cổng regression).
- [ ] `python -c "import adapters"` không raise trong env không có optional SDK.
- [ ] `pytest backend/tests/integration/` có ≥3 test mới xanh.
- [ ] `CLAUDE.md` (hoặc `conventions.md`) có section Skill/Service boundary với ≥30 dòng + ≥3 ví dụ.
- [ ] Không file nào trong `agent/nodes/` import từ `repositories/` trực tiếp (phải qua service).
- [ ] Không file nào trong `services/` import từ `api/` (đảo chiều dependency).
- [ ] Smoke test thủ công: chạy `main.py`, gọi 1 chat + 1 search → response giống branch trước plan (semantic equal).
