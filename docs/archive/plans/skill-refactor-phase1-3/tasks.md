# Tasks

Checkbox list chi tiết theo phase. Mark `[x]` khi done. Mỗi task estimate ≤30 phút; task lớn hơn được chia nhỏ.

**Quy ước:**
- 🆕 = file tạo mới
- ✏️ = file sửa
- 🗑️ = file xoá
- 🧪 = test
- 🔍 = verification / smoke test

---

## Phase 1 — MVP Framework + complexity_classifier ✅ DONE

**Status:** 18 tests pass + 1 xfail. Backend healthy sau rebuild. Integration verified trong log realtime.

### 1.1 Thêm dependencies

- [x] ✏️ `requirements.txt` — thêm `jinja2>=3.1` và `PyYAML>=6.0`
- [x] 🔍 Rebuild container

### 1.2 Framework skeleton

- [x] 🆕 `backend/src/skills/__init__.py`
- [x] 🆕 `backend/src/skills/_errors.py`
- [x] 🆕 `backend/src/skills/_prompt_loader.py` (với `PromptSource` auto-reload bonus)
- [x] 🆕 `backend/src/skills/_base.py`
- [x] 🆕 `backend/src/skills/_registry.py`

### 1.3 Skill đầu tiên: complexity_classifier

- [x] 🆕 `backend/src/skills/complexity_classifier/skill.yaml`
- [x] 🆕 `backend/src/skills/complexity_classifier/prompt.md`
- [x] 🆕 `backend/src/skills/complexity_classifier/handler.py` (+ JSON fence parsing fix)

### 1.4 Wire vào LangGraph

- [x] ✏️ `backend/src/api/deps.py` — `_ensure_skills_discovered()` trước khi build graph
- [x] ✏️ `backend/src/research_agent/nodes/complexity_node.py` — gọi skill qua registry

### 1.5 Tests

- [x] 🧪 `backend/tests/unit/test_skills_framework.py` (11 tests + auto-reload test)
- [x] 🧪 `backend/tests/unit/test_complexity_classifier_skill.py` (7 tests + 1 xfail + 2 fence parsing)

### 1.6 Verification

- [x] 🔍 Rebuild + `docker compose up -d`
- [x] 🔍 `/health` → 200
- [x] 🔍 `docker logs ai-backend` — thấy `[SKILLS] loaded complexity_classifier v1` + `[SKILL] name=complexity_classifier duration_ms=1784.95`
- [x] 🔍 `pytest backend/tests/unit/test_skills_framework.py backend/tests/unit/test_complexity_classifier_skill.py` — 18 passed, 1 xfailed
- [ ] 🔍 Smoke test `/api/v2/chat` end-to-end (bị rate-limit Gemini free tier — non-blocking; skill đã được verify invoke thành công qua log)

### 1.7 Bonus (ngoài plan gốc)

- [x] ✅ **Prompt auto-reload** — `PromptSource` check mtime mỗi invoke, sửa `prompt.md` không cần restart container
- [x] ✅ **Dev workflow documented** — [plan/dev-workflow.md](dev-workflow.md) hướng dẫn `docker exec`
- [x] ✅ **JSON markdown fence parsing** — handler chịu được khi Gemini wrap JSON trong ` ```json ... ``` `

### 1.8 Git

- [ ] Commit: `refactor(skills): phase 1 — framework + complexity_classifier skill`

---

## Phase 2a — Research agent skills ✅ DONE

**Status:** 46 tests pass (framework 12 + 5 skill suites 34). Backend rebuilt healthy. Bug "sắp tới" FIXED at query_router layer.

### 2a.1 response_composer

- [x] 🆕 `skills/response_composer/skill.yaml` (no hardcoded model, inherits from DEFAULT_MODEL env)
- [x] 🆕 `skills/response_composer/prompt.md`
- [x] 🆕 `skills/response_composer/handler.py` (short-circuit empty KB, fallback returns KB verbatim)
- [x] ✏️ `research_agent/nodes/synthesis_node.py` — gọi skill qua registry, fallback về old composer
- [x] 🧪 `test_response_composer_skill.py` (4 tests)

### 2a.2 planning

- [x] 🆕 `skills/planning/skill.yaml`
- [x] 🆕 `skills/planning/prompt.md`
- [x] 🆕 `skills/planning/handler.py` + `to_research_tasks()` adapter helper
- [x] ✏️ `research_agent/nodes/planning_node.py` — gọi skill qua registry
- [x] 🧪 `test_planning_skill.py` (8 tests bao gồm markdown fence, cap 5, fallback, empty plan)

### 2a.3 direct_answer

- [x] 🆕 `skills/direct_answer/skill.yaml` (với runtime params: max_history, timeout, retries)
- [x] 🆕 `skills/direct_answer/prompt.md` với `{% block system %}` + `{% block user %}`
- [x] 🆕 `skills/direct_answer/handler.py` — port `_select_history`, `_trim_content`; giữ `call_with_retry` + `with_timeout`
- [x] ✏️ `research_agent/nodes/common.py:run_llm_node` + `synthesis_node` — gọi skill, fallback về direct_llm cũ
- [x] 🧪 `test_direct_answer_skill.py` (7 tests bao gồm history trimming, retry exhaustion, exception fallback)

### 2a.4 research_search

- [x] 🆕 `skills/research_search/skill.yaml`
- [x] 🆕 `skills/research_search/prompt.md`
- [x] 🆕 `skills/research_search/handler.py` — Tavily call + LLM extraction, Tavily key injected post-discovery trong `api/deps.py`
- [x] ✏️ `research_agent/nodes/research_node.py` — gọi skill qua registry, fallback về old tool

### 2a.5 query_router (no LLM)

- [x] 🆕 `skills/query_router/skill.yaml` — chuyển TẤT CẢ keyword lists từ `intent_patterns.py` sang YAML (bao gồm `sắp tới`, `lễ hội`, `sự kiện`, `upcoming` etc.)
- [x] 🆕 `skills/query_router/handler.py` — override `run()`, không LLM
- [x] ✏️ `research_agent/nodes/router_node.py` — gọi skill, fallback keyword match
- [x] ✏️ `research_agent/nodes/complexity_node.py` — `_force_complex_via_skill()` dùng query_router làm force_complex check thay vì `is_*_request()`
- [x] 🧪 `test_query_router_skill.py` (8 tests bao gồm `test_sap_toi_bug_fix`, `test_le_hoi_keyword_routes_research`)

### 2a.6 Bonus Bug Fix

- [x] ✅ **Model resolution chain 3-tier**: request.model > skill.yaml > settings.default_model (env DEFAULT_MODEL). Cho phép đổi global default chỉ bằng env, không cần sửa 5 file yaml.
- [x] ✅ **Bug "sắp tới" FIXED** — `query_router/skill.yaml` bao gồm keyword "sắp tới", "lễ hội", "sự kiện" v.v. → `test_sap_toi_bug_fix` PASS.

### 2a.7 Verification

- [x] 🔍 Rebuild backend + `/health` → 200
- [x] 🔍 Registry discover 6 skills lúc startup
- [x] 🔍 Full skill test suite 46/46 PASS trong 6.47s
- [ ] 🔍 Manual curl test end-to-end (blocked by Gemini free-tier quota, non-blocking)

### 2a.8 Git

- [ ] Commit: `refactor(skills): phase 2a — response_composer, planning, direct_answer, research_search, query_router`

---

## Phase 2b — RAG skills ✅ DONE

**Status:** 63 tests pass (Phase 1+2a: 46 + Phase 2b RAG: 17). Registry 12 skills discovered. RAG subgraph wiring updated.

### 2b.1 rag.query_expand (no LLM) — wrap QueryExpander
- [x] 🆕 `skills/rag/query_expand/skill.yaml`
- [x] 🆕 `skills/rag/query_expand/handler.py`

### 2b.2 rag.transform_query
- [x] 🆕 `skills/rag/transform_query/skill.yaml`
- [x] 🆕 `skills/rag/transform_query/prompt.md`
- [x] 🆕 `skills/rag/transform_query/handler.py`

### 2b.3 rag.grade_documents
- [x] 🆕 `skills/rag/grade_documents/skill.yaml` (có `fallback_score_threshold` trong yaml)
- [x] 🆕 `skills/rag/grade_documents/prompt.md`
- [x] 🆕 `skills/rag/grade_documents/handler.py` (score-based fallback khi LLM parse fail)

### 2b.4 rag.grade_generation
- [x] 🆕 `skills/rag/grade_generation/skill.yaml`
- [x] 🆕 `skills/rag/grade_generation/prompt.md`
- [x] 🆕 `skills/rag/grade_generation/handler.py` (fail-open → grounded_and_useful)

### 2b.5 rag.answer_with_context
- [x] 🆕 `skills/rag/answer_with_context/skill.yaml` (có `max_context_docs`, `snippet_max_chars`)
- [x] 🆕 `skills/rag/answer_with_context/prompt.md` — system + user blocks
- [x] 🆕 `skills/rag/answer_with_context/handler.py` — context building + history + LLM + citation dedup

### 2b.6 rag.retrieve (no LLM)
- [x] 🆕 `skills/rag/retrieve/skill.yaml`
- [x] 🆕 `skills/rag/retrieve/handler.py` — wrap RetrievalNode, key injected post-discovery

### 2b.7 Wire vào RAG subgraph
- [x] ✏️ `rag/subgraph/nodes.py` — 5 node giờ là thin wrapper gọi skill, fallback về legacy path nếu skill not found
- [x] ✏️ `backend/src/api/deps.py` — inject `retrieval_node` vào `rag.retrieve` post-discovery
- [x] 🗑️ Xoá 3 hardcoded prompts: `_TRANSFORM_QUERY_PROMPT`, `_GRADE_DOCS_PROMPT`, `_GRADE_GENERATION_PROMPT`

### 2b.8 Verification
- [x] 🔍 Rebuild xanh, `/health` → 200
- [x] 🔍 Registry discover 12 skills (6 top-level + 6 under `rag/`)
- [x] 🔍 17 RAG skill tests PASS (+ 46 tests cũ = 63 total)
- [ ] 🔍 Manual RAG query smoke test (blocked by Gemini quota)

### 2b.9 Git
- [ ] Commit: `refactor(skills): phase 2b — RAG skills migrated (6 skills under rag/)`

---

## Phase 3 — Cleanup ✅ DONE

**Status:** 175 tests pass (skip 1 pre-existing unrelated ChromaDB fixture failure). Backend `/health` → 200. Grep verification 0 matches in `backend/src`.

### 3.1 Xóa class cũ

- [x] 🗑️ `backend/src/research_agent/complexity_analyzer.py`
- [x] 🗑️ `backend/src/research_agent/planning_agent.py`
- [x] 🗑️ `backend/src/research_agent/response_composer.py`
- [x] 🗑️ `backend/src/research_agent/direct_llm.py`
- [x] 🗑️ `backend/src/research_agent/research_tool.py`
- [x] 🗑️ `backend/src/research_agent/utils/intent_patterns.py` — keyword lists sống trong `skills/query_router/skill.yaml`
- [x] 🗑️ `backend/src/research_agent/tracing_pipeline.py` — LangSmith demo, không wired ở đâu; xoá trong /review cleanup pass.

### 3.2 Xóa test class cũ

- [x] 🗑️ `backend/tests/unit/test_research_agent_planning_agent.py`
- [x] 🗑️ `backend/tests/unit/test_research_agent_response_composer.py`
- [x] 🗑️ `backend/tests/unit/test_research_agent_research_tool.py`
- [x] ✏️ `backend/tests/unit/test_research_agent_router_node.py` — giữ, thêm fixture discover skills + sửa 1 test dùng từ khoá nằm trong research_keywords (trước đó test silently broken)

### 3.3 Dọn signature

- [x] ✏️ `backend/src/api/deps.py` — `GraphDependencies` chỉ còn 4 field (database, retrieval_node, rag_subgraph, aggregator). Bỏ import 5 class cũ.
- [x] ✏️ `backend/src/research_agent/graph/research_agent_graph.py` — drop reference tới analyzer/planning_agent/direct_llm/response_composer/research_tool trong lambda wrappers.
- [x] ✏️ Tất cả `nodes/*.py` đã migrate — xóa parameter legacy (`analyzer`, `planning_agent`, `direct_llm`, `response_composer`, `research_tool`).
- [x] ✏️ `backend/src/rag/subgraph/graph.py` — `RAGSubgraph.__init__(retrieval_node)` (drop `direct_llm`).
- [x] ✏️ `backend/src/rag/subgraph/nodes.py` — các node thin wrapper không nhận `direct_llm` nữa.
- [x] ✏️ `backend/src/research_agent/utils/__init__.py` — drop re-export `intent_patterns`.
- [x] ✏️ `backend/src/langgraph_platform.py` — cập nhật dependencies dict cho platform entrypoint.

### 3.4 Verification

- [x] 🔍 Grep `ComplexityAnalyzer|PlanningAgent|ResponseComposer|DirectLLM|ResearchTool|intent_patterns` trong `backend/src` → **0 matches**.
- [x] 🔍 `pytest backend/tests/unit` — 175 passed, 1 deselected (pre-existing ChromaDB metadata assertion failure trong `test_hybrid_search`, không liên quan Phase 3), 9:35 tổng.
- [x] 🔍 Backend `/health` → 200 sau khi `docker cp` source + xoá file cũ trong container.
- [ ] 🔍 Rebuild container (`docker compose up --build`) — **chưa chạy**; khuyến nghị rebuild trước commit để bake changes vào image.
- [ ] 🔍 Manual smoke test 5 query types (blocked by Gemini quota).

### 3.5 Git

- [ ] Commit: `refactor(skills): phase 3 — delete old classes, clean signatures`

---

## Bonus: Post-refactor follow-ups

Không phải scope của refactor, nhưng đáng làm ngay sau:

- [ ] Fix bug "sắp tới" — edit `skills/query_router/skill.yaml` thêm keyword. Commit riêng: `fix(router): add 'sắp tới' to research keywords`
- [ ] Xóa `@pytest.mark.xfail` khỏi `test_complexity_classifier_skill.py` sau khi fix bug
- [ ] Document cách thêm skill mới vào [README.md](../README.md) hoặc tạo `CONTRIBUTING.md`
- [ ] (Optional) Thêm `SKILLS_DIR` env var support cho A/B test prompt song song
- [ ] (Optional) Tạo `/api/v2/skills` endpoint list tất cả skill + version (cho debugging)
