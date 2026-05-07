# Requirements — improve-architecture-v2

## 1. Overview

Sau refactor Model-Repository-Service (`refactor-architecture/`, 9 bước, đã merge vào master), backend đã có phân tầng dữ liệu sạch (`db/` → `models/` → `repositories/` → `services/` → `api/`). Tuy nhiên cấu trúc tầng **runtime** (LangGraph + RAG) vẫn lai feature-first cũ: `rag/` chứa hỗn hợp 4 loại code khác nhau (LangGraph node, business orchestration, pure tooling, shim), `agent/` thiếu một node retrieval và đang chứa file lạc tầng (`aggregator.py`, `resilience.py`). Inconsistency giữa "tầng dữ liệu layer-first vs tầng runtime feature-first" là nguồn lú lẫn chính cho reader. Plan này dọn dẹp để mọi tầng đều layer-first nhất quán, xóa 5 shim còn sót, làm rõ ranh giới Skill/Service, và bổ sung integration test thực sự verify được.

## 2. Goals

- **Dọn `rag/` và `agent/` về đúng nguyên tắc layer-first**: `agent/` = toàn bộ LangGraph runtime (nodes/edges/graph/subgraph/state); `services/` = toàn bộ business orchestration; `rag/` = chỉ pure tooling (chunking, embedding, vector_store, reranker, ...).
- **Xóa hoàn toàn 5 shim** (`Database`, `FTSEngine`, `CitationTracker`, `DocumentIndexer`, `ConversationIndexer`). Sau plan này `grep "class Database" backend/src/` zero hit.
- **Đặt ranh giới Skill/Service rõ ràng** trong `CLAUDE.md`: Skill = wrapper LLM call duy nhất, không flow control; Service = orchestrate nhiều skill/repo, có business logic.
- **Cosmetic consistency**: rename `ResearchAgentGraph` → `AgentGraph` + `research_agent_graph.py` → `agent_graph.py` để khớp package `agent/`.
- **Integration test thực sự chạy được**: lazy-import LLM SDK ở `adapters/`, thêm 3-5 integration test mới qua FastAPI TestClient.
- **Mọi test cũ phải xanh sau từng bước** (cùng nguyên tắc với plan trước).

## 3. Non-goals

- **Không** đổi schema DB.
- **Không** đổi behavior public API (response payload, route path, status code giữ nguyên byte-equal).
- **Không** đổi LLM provider, không đổi vector store, không đổi RAG retrieval logic.
- **Không** tạo abstract base class hoặc Protocol vội — YAGNI tiếp tục.
- **Không** thay đổi DI pattern (`@lru_cache` + `cached_property` giữ nguyên).
- **Không** big-bang — mỗi việc 1 PR độc lập.

## 4. User stories

- Là **engineer mới onboard**, tôi muốn nhìn `agent/` là biết ở đó có toàn bộ LangGraph runtime, không phải thắc mắc "tại sao retrieval_node lại ở rag/?".
- Là **engineer thêm node mới**, tôi muốn `agent/nodes/` có pattern rõ ràng để bắt chước, không cần bypass package boundary.
- Là **engineer đọc business logic**, tôi muốn `services/` chứa **mọi** orchestration (gồm hybrid_search, multi_query, research_aggregation), không phải lùng từng góc `rag/` và `agent/`.
- Là **engineer sửa data flow**, tôi muốn không gặp 2 đường để làm cùng 1 việc (`Database.save_message` vs `ConversationService.persist_turn`).
- Là **engineer thêm provider LLM mới**, tôi muốn drop file vào `adapters/` và đăng ký qua registry, không phải sửa `adapters/__init__.py`.
- Là **engineer review PR**, tôi muốn mỗi PR chỉ chạm 1 layer, diff <500 LOC, có integration test smoke gác cổng.

## 5. Functional requirements

- **FR-1**: Toàn bộ LangGraph node/edge/graph/subgraph nằm trong `agent/`. Sau plan: `find backend/src/rag -name "*node*.py"` zero hit; `find backend/src/rag -type d -name subgraph` zero hit.
- **FR-2**: Toàn bộ business orchestration nằm trong `services/`. `rag/hybrid_search.py`, `rag/multi_query_retriever.py`, `agent/aggregator.py` được dời thành 3 service tương ứng.
- **FR-3**: `rag/` chỉ còn pure tooling: `chunking`, `embedding`, `vector_store`, `reranker`, `query_expander`, `contextual_compressor`, `document_loader`, `metrics`, `config`. Mỗi file có thể test isolated, không depend `agent/` hay `services/` core logic.
- **FR-4**: 5 shim file bị xóa. Mọi caller (production + test) chuyển sang dùng repos/services trực tiếp.
- **FR-5**: `agent/nodes/common.py` + `llm_node.py` không nhận `Database`, nhận `ConversationService` + `MessageRepository`.
- **FR-6**: `RetrievalNode.__init__` nhận `MessageRepository` thay `FTSEngine`.
- **FR-7**: Class `AgentGraph` thay `ResearchAgentGraph`, file `agent_graph.py` thay `research_agent_graph.py`. Function `get_research_agent_graph` đổi thành `get_agent_graph` (giữ alias deprecated 1 release để caller external có thời gian migrate, hoặc đổi thẳng nếu không có external caller — verify bằng grep repo).
- **FR-8**: `CLAUDE.md` (hoặc `docs/architecture/conventions.md`) có section "Skill vs Service boundary" với ví dụ + anti-pattern.
- **FR-9**: Audit `skills/rag/` — skill nào chứa flow control (multi-step, retry, conditional logic) phải chuyển thành service.
- **FR-10**: `adapters/__init__.py` lazy-import LLM SDK. Import top-level `adapters` không yêu cầu `groq`/`google-genai` đã cài.
- **FR-11**: Thêm ≥3 integration test qua FastAPI TestClient: `POST /api/v2/chat` happy path, `POST /api/search` happy path, `AppContainer` smoke test full graph compile.
- **FR-12**: `agent/resilience.py` move → `agent/utils/resilience.py`.
- **FR-13**: `agent/models.py` audit — xóa nếu mồ côi, đổi tên `agent/types.py` nếu còn dùng.
- **FR-14**: `models/__init__.py` re-export entities chính cho consistency với `repositories/__init__.py`, `services/__init__.py`.

## 6. Non-functional requirements

- **Performance**: Không regression. Số connection mở per request không tăng. Move file không thay đổi runtime cost.
- **Security**: Không thay đổi attack surface. Tất cả parameterized SQL giữ nguyên.
- **Compatibility — internal API**: Public route path + payload shape không đổi. External caller (mobile app, web client) không thấy khác biệt.
- **Compatibility — Python imports**: Class name đổi (`ResearchAgentGraph` → `AgentGraph`) là breaking — cần grep verify zero external caller trước khi đổi.
- **Reviewability**: Mỗi việc trong roadmap = 1 PR ≤500 LOC diff (trừ việc xóa shim có thể cần ≤1000 LOC vì đụng nhiều test).
- **Test coverage**: Sau mỗi việc, toàn bộ test cũ + test mới xanh. Không skip test.
- **Documentation**: Mỗi thay đổi structural (move file, rename class) phải update `CLAUDE.md` hoặc README liên quan trong cùng PR.

## 7. Acceptance criteria

- [ ] **Cấu trúc đích đạt được:**
  - `find backend/src/rag -name "*node*.py" -o -name "subgraph"` zero hit.
  - `find backend/src/rag -name "hybrid_search.py" -o -name "multi_query_retriever.py"` zero hit.
  - `find backend/src/agent -name "aggregator.py"` zero hit.
  - `ls backend/src/services/` chứa: `conversation_service.py`, `citation_service.py`, `document_indexing_service.py`, `conversation_indexing_service.py`, `hybrid_search_service.py`, `multi_query_service.py`, `research_aggregation_service.py`.
- [ ] **Shim đã xóa:**
  - `find backend/src -name "database.py" -path "*/agent/*"` zero hit (file `agent/database.py` không còn).
  - `grep -rn "class FTSEngine\|class CitationTracker\|class DocumentIndexer\|class ConversationIndexer" backend/src/` zero hit.
- [ ] **Rename áp dụng đầy đủ:**
  - `grep -rn "ResearchAgentGraph\|research_agent_graph" backend/src/` zero hit.
  - `grep -rn "ResearchAgentGraph\|research_agent_graph" backend/tests/` zero hit (hoặc hợp lệ trong test_agent_rename.py kiểm tra absence).
- [ ] **Lazy-import áp dụng:**
  - `python -c "import sys; sys.path.insert(0, 'backend/src'); import adapters"` thành công trong env không có `groq`.
- [ ] **Integration test thực sự chạy:**
  - `pytest backend/tests/integration/` xanh ≥3 test mới được thêm.
- [ ] **Skill/Service boundary documented:**
  - `CLAUDE.md` (hoặc `docs/architecture/conventions.md`) có section ≥30 dòng giải thích boundary + ví dụ.
- [ ] **Test cũ + mới đều xanh sau mỗi PR.**
- [ ] **API smoke test:** chạy `main.py`, gọi 1 chat request + 1 search request → cả 2 trả 200 với payload giống branch trước plan.

## 8. Open questions

- **Có nên giữ alias `ResearchAgentGraph = AgentGraph`** ở `agent/__init__.py` cho backwards-compat 1 release không? — Đề xuất: **không**, project nội bộ, alias là technical debt thừa (theo §8.3 plan trước).
- **`skills/rag/retrieve/`** có thực sự là skill hay là service? — Audit ở Task 9. Nếu nó chỉ wrap 1 LLM call thì giữ. Nếu nó orchestrate retrieve + grade + rerank thì chuyển service.
- **Lazy-import có ảnh hưởng startup time không?** — Negligible (import lần đầu khi gọi method, sau đó cached). Verify bằng smoke test thời gian boot trước/sau.
- **Có nên gộp `agent/utils/parsing.py` + `text.py` + `node_helpers.py`** thành 1 file không? — Defer. Chỉ làm khi có pattern emerge rõ.
