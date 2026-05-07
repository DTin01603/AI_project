# Design

## 1. Kiến trúc target

### 1.1 Folder structure

```
backend/src/skills/
├── __init__.py
├── _base.py                     # BaseSkill ABC
├── _registry.py                 # SkillRegistry + get_registry()
├── _prompt_loader.py            # Jinja2 env + load_prompt()
├── _errors.py                   # SkillError, SkillValidationError, SkillInvocationError
│
├── complexity_classifier/       # Phase 1
│   ├── skill.yaml
│   ├── prompt.md
│   └── handler.py
│
├── query_router/                # Phase 2a — keyword-based, no LLM
│   ├── skill.yaml               # chứa YAML arrays của keyword lists
│   └── handler.py               # (no prompt.md)
│
├── planning/                    # Phase 2a
├── response_composer/           # Phase 2a
├── direct_answer/               # Phase 2a
├── research_search/             # Phase 2a — tool + LLM extraction
│
└── rag/                         # Phase 2b
    ├── query_expand/            # wrap QueryExpander (no LLM)
    ├── transform_query/         # LLM query rewrite
    ├── grade_documents/         # LLM grade
    ├── grade_generation/        # LLM grade
    ├── answer_with_context/     # LLM answer với context
    └── retrieve/                # hybrid + rerank, no LLM
```

### 1.2 Data flow trong LangGraph node (ví dụ)

**Trước:**
```python
@node_timing_wrapper("complexity")
def complexity_node(state, analyzer):
    message = extract_last_message_content(state)
    result = analyzer.analyze(message)  # <-- prompt hardcode inside
    # ... override logic
    return {"query_type": ..., "complexity_result": ...}
```

**Sau:**
```python
@node_timing_wrapper("complexity")
def complexity_node(state):
    message = extract_last_message_content(state)
    skill = get_registry().get("complexity_classifier")
    result = skill.invoke({"message": message})
    # ... override logic (unchanged)
    return {"query_type": "complex" if result["is_complex"] else "simple", ...}
```

### 1.3 Skill anatomy (ví dụ `complexity_classifier/`)

**`skill.yaml`:**
```yaml
name: complexity_classifier
version: 1
description: Classify user query as simple or complex for routing
model: gemini-2.5-flash
temperature: 0.0
max_output_tokens: 150
llm: true
```

**`prompt.md`:**
```markdown
{% block user %}
Classify user request complexity for routing.
Return strict JSON with keys: is_complex (boolean), confidence (0..1), reason (string).
Mark is_complex=true only if request needs multi-step research or external web evidence.

Examples of complex requests:
- Questions about current or upcoming events (sự kiện sắp tới, lễ hội sắp diễn ra)
- Questions requiring real-time data (prices, weather, news)
- Comparison or analysis requests

User request: {{ message }}
{% endblock %}
```

**`handler.py`:**
```python
from pydantic import BaseModel
from skills._base import BaseSkill

class Inputs(BaseModel):
    message: str

class Outputs(BaseModel):
    is_complex: bool
    confidence: float
    reason: str

class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def parse_output(self, raw: str) -> dict:
        import json
        payload = json.loads(raw)
        return {
            "is_complex": bool(payload.get("is_complex", False)),
            "confidence": float(payload.get("confidence", 0.5)),
            "reason": str(payload.get("reason", "model_classification")),
        }

    def fallback(self, inputs: Inputs, error: Exception) -> dict:
        # Port _heuristic from old ComplexityAnalyzer
        lowered = inputs.message.lower()
        complex_keywords = ["nghiên cứu", "research", "so sánh", ...]
        is_complex = len(inputs.message) > 220 or any(k in lowered for k in complex_keywords)
        return {
            "is_complex": is_complex,
            "confidence": 0.7 if is_complex else 0.8,
            "reason": "heuristic_complex" if is_complex else "heuristic_simple",
        }
```

---

## 2. Quyết định kiến trúc

### D1. Prompt file format → **Markdown + Jinja2**
- `.md` để IDE render đẹp, GitHub preview tốt
- Jinja2 `{{ var }}` cho biến động
- `{% block system %}` / `{% block user %}` cho multi-segment prompt
- `StrictUndefined` mode — fail loud khi thiếu biến
- Autoescape off (đây là plain text cho LLM, không phải HTML)

### D2. Schema → **Pydantic v2**
- Đã có trong requirements.txt, không thêm dep
- `class Inputs(BaseModel)` / `class Outputs(BaseModel)` là source of truth
- `skill.yaml` metadata fields chỉ là documentation cho human
- Validation tự động 2 chiều (inputs trước invoke, outputs sau parse)

### D3. Adapter access → **Qua registry, không import trực tiếp**
- Skill khai `model: gemini-2.5-flash` trong `skill.yaml`
- `BaseSkill.invoke()` resolve adapter tại runtime qua `get_adapter_for_model(self.model)`
- Adapter cached per-model trong registry
- Per-request override: `invoke(inputs, model_override=...)` — resolve adapter mới cho call đó

### D4. Skill không cần LLM → **Cùng interface, prompt optional**
- `skill.yaml` có `llm: false`
- `prompt.md` có thể thiếu
- `handler.py` override `invoke()` trực tiếp, không gọi `self.llm.invoke()`
- Ví dụ: `query_router` wrap keyword matching, `rag.retrieve` wrap hybrid search

### D5. Streaming → **Out of scope Phase 1–3**
- Hiện tại: `adapter.invoke()` blocking, LangGraph stream updates level node
- Token-level streaming có thể thêm `BaseSkill.ainvoke_stream()` trong future phase
- Refactor hiện tại không cản trở thêm sau

### D6. Discovery → **Eager at startup**
- `api/deps.py` gọi `SkillRegistry.discover(Path(__file__).parent.parent / "skills")` trong startup event
- Walk directory, skip `_*` prefix
- Skill folder hợp lệ: có `skill.yaml` + `handler.py`
- Import lỗi → log + skip, không crash app

### D7. Error handling → **Try/except + fallback**
```python
def invoke(self, inputs_dict):
    inputs = self.Inputs(**inputs_dict)
    try:
        raw = self._call_llm(inputs)
        outputs_dict = self.parse_output(raw)
    except Exception as e:
        outputs_dict = self.fallback(inputs, e)
    return self.Outputs(**outputs_dict).model_dump()
```

### D8. Observability → **LangSmith traceable + node timing**
- Wrap `_call_llm` với `@traceable(name=f"skill.{name}", run_type="llm")`
- Node timing decorator `@node_timing_wrapper` giữ ở node level
- Log format: `[SKILL] name=<name> duration_ms=<ms> fallback=<bool>`

---

## 3. Class hierarchy

```
BaseSkill (ABC)
├── attrs: name, version, model, temperature, max_tokens, prompt_template
├── Inputs: type[BaseModel]       # overridden
├── Outputs: type[BaseModel]      # overridden
├── invoke(inputs: dict) -> dict
├── ainvoke(inputs: dict) -> dict
├── _call_llm(inputs: Inputs) -> str   # internal
├── parse_output(raw: str) -> dict      # override point
└── fallback(inputs, error) -> dict     # override point
```

```
SkillRegistry
├── _skills: dict[str, BaseSkill]
├── discover(root: Path)
├── get(name: str) -> BaseSkill
├── _load_skill(folder: Path) -> BaseSkill
└── _resolve_adapter(model: str) -> BaseAdapter  # cached
```

---

## 4. Integration points với LangGraph

### 4.1 Node wiring
Node function signature đơn giản hóa — bỏ dependency parameters:

**Trước:**
```python
graph.add_node("complexity", lambda state: complexity_node(state, deps["analyzer"]))
graph.add_node("planning", lambda state: planning_node(state, deps["planning_agent"]))
```

**Sau (Phase 3):**
```python
graph.add_node("complexity", complexity_node)
graph.add_node("planning", planning_node)
```

(Phase 1 và 2 giữ nguyên signature cũ để không break, chỉ không dùng parameter đó — cleanup ở Phase 3.)

### 4.2 State shape
**Không đổi.** `AgentState` TypedDict giữ nguyên fields. Skill input/output phải map vào đúng các field đó.

### 4.3 Checkpointer
**Không đụng.** `get_checkpointer()` trong `research_agent/config.py` không thay đổi. Thread_id, conversation persistence không ảnh hưởng.

---

## 5. Non-goals (tuyệt đối không đụng)

| Thành phần | Lý do giữ nguyên |
|---|---|
| `research_agent/graph/research_agent_graph.py` edges | Topology = contract của graph |
| `research_agent/edges/*.py` | Edge logic chỉ đọc `state["query_type"]`, không liên quan prompt |
| `api/routers/chat_v2.py` | API contract bất biến |
| `AgentState` TypedDict | Thay đổi = break checkpoints cũ |
| `adapters/*.py` | Orthogonal concern |
| `research_agent/config.py` checkpointer | Persistence layer |
| `rag/fts_engine.py`, `vector_store.py`, `hybrid_search.py`, `reranker.py`, `chunking.py`, `embedding.py` | RAG retrieval primitives, không chứa prompt |
| Bug "sắp tới" | Fix sau, không bundle chung refactor |

---

## 6. Rủi ro kiến trúc + giảm thiểu

| Rủi ro | Mức độ | Giảm thiểu |
|---|---|---|
| Jinja2 `StrictUndefined` break prompt cũ có biến rỗng silent | Trung bình | Phase 1 test kỹ complexity_classifier (chỉ 1 biến `{{message}}`). Phase 2+ thêm validator `meta.find_undeclared_variables` so với `Inputs.model_fields` tại discovery |
| Per-request model override không tác dụng vì adapter cached sai scope | Cao | Resolve adapter trong `invoke()` không phải `__init__()`. Adapter cache ở registry level, key = model string |
| Skill import lỗi làm crash app | Cao | Wrap `importlib.import_module` trong try/except. Log error, skip skill. Nếu node yêu cầu skill không có → raise rõ ràng khi `registry.get()` |
| History trimming của `direct_answer` divergent với `DirectLLM._select_history` | Trung bình | Copy method verbatim. Unit test so sánh output trên 20 fixture histories |
| `research_search` swallow exception khác với `ResearchTool.execute_task` | Trung bình | Port y hệt try/except structure. Giữ `success=False` + error string format |
| State shape subtle change | Cao | Skill Outputs schema declare chính xác keys mà graph state expect. Validation catch mismatch tại invoke time |
| Docker image lớn thêm | Thấp | Deps nhỏ (~1MB total). Negligible |
| RAG subgraph internal state break | Cao | Phase 2b cuối cùng, có Phase 2a làm proof-of-concept trước |
