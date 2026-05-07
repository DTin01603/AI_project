# Requirements

## 1. Yêu cầu chức năng (Functional)

### FR-1. Skill là đơn vị tự chứa
Mỗi skill nằm trong một folder riêng `backend/src/skills/<skill_name>/` chứa:
- `skill.yaml` — metadata (name, version, model, temperature, max_tokens, description)
- `prompt.md` — template Jinja2 (optional với skill không gọi LLM)
- `handler.py` — class `Handler(BaseSkill)` với pydantic `Inputs` / `Outputs`

### FR-2. Registry tự động discover
- Khi FastAPI startup, `SkillRegistry.discover()` walk folder `skills/`, đọc metadata, import `Handler`.
- Skill lấy qua `registry.get("<name>")`.
- Skill lỗi import không được làm crash app — log error, skip skill đó.

### FR-3. Prompt dùng Jinja2 template
- Biến động interpolate qua `{{ variable }}`.
- Prompt đa phần tách bằng Jinja2 blocks: `{% block system %}...{% endblock %}` và `{% block user %}...{% endblock %}`.
- `StrictUndefined` — tham chiếu biến không khai báo → lỗi rõ ràng khi load, không silent render "".

### FR-4. Input/Output có schema
- Mỗi skill khai `class Inputs(BaseModel)` và `class Outputs(BaseModel)` trong `handler.py`.
- `invoke(inputs_dict)` validate trước khi chạy, validate output trước khi return.
- Validation fail → `SkillValidationError`.

### FR-5. Fallback khi LLM lỗi
- `BaseSkill.invoke()` bọc LLM call trong try/except.
- Lỗi → gọi `self.fallback(inputs, error)`.
- Fallback mặc định raise; mỗi skill override với logic fallback của code cũ (ví dụ `_heuristic` của ComplexityAnalyzer).

### FR-6. LangGraph node trở thành wrapper mỏng
Node chỉ làm việc:
1. Extract input từ state
2. Gọi `registry.get("<skill>").invoke(inputs)`
3. Map output vào state update

### FR-7. Skill không cần LLM vẫn dùng chung interface
Ví dụ `rag.retrieve`, `query_router` — gọi pure-Python logic (hybrid search, keyword match) thay vì LLM. `prompt.md` optional; `skill.yaml` set `llm: false`.

### FR-8. Per-request model override
Giữ behavior hiện có của `resolve_and_apply_model()` — user có thể override model trong request body, skill phải tôn trọng.

### FR-9. Keyword lists di chuyển vào YAML
`intent_patterns.py` keyword constants (research_keywords, temporal_keywords, market_keywords, date patterns) → di chuyển vào `skills/query_router/skill.yaml` dưới dạng YAML arrays, có thể edit không cần code.

---

## 2. Yêu cầu phi chức năng (Non-functional)

### NFR-1. Tương thích ngược 100%
- `/api/v2/chat` request/response shape không đổi
- SSE event names không đổi
- Error codes (BAD_REQUEST, INTERNAL_ERROR, MODEL_ERROR, EXECUTION_ERROR) không đổi
- Header `x-api-version: 2` giữ nguyên

### NFR-2. Graph topology không thay đổi
- Không thêm/xoá node trong `research_agent_graph.py`
- Không đổi edges, không đổi state shape (`AgentState`)
- Checkpointer (SQLite/Postgres) tiếp tục hoạt động với thread_id hiện có

### NFR-3. Test pass 100%
- Toàn bộ `backend/tests/integration/` chạy xanh
- Toàn bộ `backend/tests/unit/` chạy xanh (trừ file test của class bị xóa ở Phase 3 — sẽ thay bằng test skill tương ứng)

### NFR-4. Performance không suy giảm đáng kể
- Skill dispatch overhead < 5ms/call
- Adapter cached per-model (không tạo client mới mỗi invoke)
- Prompt render (Jinja2) < 1ms cho template <10KB

### NFR-5. Observability giữ nguyên
- LangSmith tracing spans tiếp tục xuất hiện
- Node timing logs (`[node_timing_wrapper]`) tiếp tục hoạt động
- Log routing `[ROUTER] message=... | route=... | reason=...` giữ nguyên format

### NFR-6. Docker image không phình to đáng kể
- Chỉ thêm 2 dep: `jinja2` (~300KB, đã transitively có qua LangChain), `PyYAML` (~750KB)
- Không thêm native binary

---

## 3. Ràng buộc (Constraints)

### C-1. Stack hiện tại
- Python 3.12
- FastAPI + Uvicorn
- LangGraph 1.0.x
- Pydantic v2 (đã có — dùng ngay, không thêm lib validation mới)
- Adapters: Gemini (Google), Groq
- Run qua Docker Compose

### C-2. Không đụng vào
- `adapters/` — giữ nguyên, skill chỉ dùng qua interface
- `api/routers/chat_v2.py` — không đổi handler logic
- `research_agent/config.py` checkpointer logic
- `rag/fts_engine.py`, `vector_store.py`, `hybrid_search.py`, `reranker.py` — RAG retrieval primitives, skill chỉ wrap

### C-3. Dev loop
- Sửa `prompt.md` hoặc `skill.yaml` → restart container (`docker compose restart backend`)
- Hot-reload KHÔNG phải requirement; document "restart container" là dev loop chính thức

### C-4. Solo dev
- Không có CI pipeline tự động
- Review qua self-diff + manual curl test
- Không có staging env riêng

---

## 4. Non-goals (ngoài scope)

| Không làm | Lý do |
|---|---|
| Sửa bug "sắp tới" trong cùng PR refactor | Tách để diff sạch, verify story rõ. Fix sau = 1 dòng edit YAML |
| Token streaming per-skill | LangGraph stream ở level node, không cần thiết cho refactor này |
| Hot-reload prompt không restart container | Complexity cao, lợi ích nhỏ với solo dev |
| Skill composition / skill chaining | Không có nhu cầu hiện tại |
| Refactor adapters | Orthogonal, không liên quan prompt organization |
| A/B test multi-prompt simultaneous | Có thể thêm sau qua `SKILLS_DIR` env var (chưa làm Phase 1) |
| Migrate [tracing_pipeline.py](../backend/src/research_agent/tracing_pipeline.py) | File demo LangSmith, không wired vào graph thật — xóa/migrate riêng |
| Đổi graph topology | Non-goal tuyệt đối — toàn bộ refactor là transparent với LangGraph |

---

## 5. Success criteria

### SC-1. Functional
- [ ] Gọi `/api/v2/chat` với body giống hệt trước refactor → response shape identical
- [ ] Câu "hôm nay ngày mấy" → route `current_date` (không đổi)
- [ ] Câu "giá vàng hôm nay" → route `research_intent` (không đổi)
- [ ] Câu "đà nẵng sắp tới có lễ hội gì" → sau refactor + 1-line edit `query_router/skill.yaml` → route `research_intent`

### SC-2. Code quality
- [ ] Không còn prompt hardcode trong `.py` file (trừ `_base.py` helper text, không phải LLM prompt)
- [ ] Grep `ComplexityAnalyzer|PlanningAgent|ResponseComposer|DirectLLM|ResearchTool` sau Phase 3 → 0 kết quả
- [ ] `backend/src/skills/` có ≥10 skill folder

### SC-3. Developer experience
- [ ] Sửa một prompt = edit 1 file `.md`, không cần mở Python
- [ ] Thêm skill mới = tạo folder với 3 file, không cần sửa graph hay node
- [ ] Test skill độc lập không cần stub LangGraph state

### SC-4. Observability
- [ ] LangSmith traces hiển thị span `skill.<name>` cho mỗi LLM call
- [ ] Log level DEBUG có thể trace: "skill=<name> inputs=<...> duration_ms=<...>"

### SC-5. Regression
- [ ] `pytest backend/tests/` — 100% xanh
- [ ] Manual smoke test 5 query types (simple, research, current_date, RAG, streaming) — PASS
