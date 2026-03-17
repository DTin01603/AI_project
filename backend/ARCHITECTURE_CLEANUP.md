# Architecture Cleanup Summary

## Tổng quan các thay đổi

Đã hoàn thành chuẩn hóa architecture bằng cách loại bỏ **redundancy**, **consolidate patterns**, và **improve maintainability**.

### 📋 Danh sách thay đổi

#### 1. **Khử trùng lặp Intent Detection**
```
Before:  _is_current_date_request ở router_node.py + complexity_node.py
After:   is_current_date_request ở utils/intent_patterns.py → import by both
```

**Files tạo mới:**
- `research_agent/utils/intent_patterns.py`
  - `is_current_date_request(message) -> bool`
  - `is_time_sensitive_request(message) -> bool`
  - `is_research_intent_request(message) -> bool`
  - `extract_intent_hints(message) -> dict` (batch detection)

**Files cập nhật:**
- `research_agent/utils/__init__.py` - export intent functions
- `research_agent/nodes/router_node.py` - import từ intent_patterns
- `research_agent/nodes/complexity_node.py` - import từ intent_patterns
- `research_agent/nodes/common.py` - unchanged (already has extract_last_message_content)

**Lợi ích:**
- ✓ Single source of truth cho intent patterns
- ✓ Dễ mở rộng intent detection sau
- ✓ Dễ test riêng biệt

---

#### 2. **Khử trùng lặp Helper Functions**
```
Before:  extract_last_message_content có ở 3 nơi
After:   import từ common.py
```

**Files cập nhật:**
- `research_agent/nodes/router_node.py` - import `extract_last_message_content` từ common
- `research_agent/nodes/complexity_node.py` - import từ common (thay vì define local)

---

#### 3. **Consolidate LLM Nodes**
```
Before:  simple_llm_node + direct_llm_node (95% duplication)
         Both call run_llm_node with different params
         
After:   llm_node (generic) ← simple_llm_node + direct_llm_node (wrappers)
```

**File tạo mới:**
- `research_agent/nodes/llm_node.py`
  - Generic `llm_node()` function
  - Accepts `node_name` + `fallback_answer` params
  - Handles both agentic RAG path + legacy path

**Files cập nhật:**
- `research_agent/nodes/simple_llm_node.py` - wrapper → llm_node(node_name="simple_llm", ...)
- `research_agent/nodes/direct_llm_node.py` - wrapper → llm_node(node_name="direct_llm", ...)
- `research_agent/nodes/__init__.py` - export llm_node

**Lợi ích:**
- ✓ Chuẩn hóa logic generation
- ✓ Dễ add thêm LLM paths mới
- ✓ Tương thích ngược với simple_llm + direct_llm
- ✓ Giảm duplication ~30 LOC

---

#### 4. **Cleanup Parameter Signatures**
- `retrieval_node: RetrievalNode | None = None` (optional khi dùng RAGSubgraph)
- `rag_subgraph: "RAGSubgraph | None" = None` (support duels)

---

## Cấu trúc sau cleanup

```
backend/src/research_agent/
├── utils/
│   ├── __init__.py (updated)
│   ├── intent_patterns.py (NEW)
│   ├── model_runtime.py
│   └── ...
├── nodes/
│   ├── __init__.py (updated)
│   ├── llm_node.py (NEW)
│   ├── common.py
│   ├── router_node.py (updated)
│   ├── complexity_node.py (updated)
│   ├── simple_llm_node.py (updated → wrapper)
│   ├── direct_llm_node.py (updated → wrapper)
│   ├── entry_node.py
│   ├── persist_conversation_node.py
│   ├── planning_node.py
│   ├── research_node.py
│   ├── synthesis_node.py
│   ├── citation_node.py
│   └── current_date_node.py
└── ...
```

---

## Verification ✓

- ✓ No import errors
- ✓ All nodes still callable with same signatures
- ✓ Backward compatible (simple_llm_node + direct_llm_node exist)
- ✓ Zero breaking changes to graph.py and deps.py

---

## Metrics

| Aspect | Before | After | Change |
|--------|--------|-------|--------|
| Intent pattern files | 1 | 1 (consolidated) | -0 |
| extract_last_message_content dups | 3 | 1 | -2 |
| LLM node files | 2 | 3 (1 generic + 2 wrappers) | +1 |
| Total LOC duplication | ~40 | ~5 | -88% |

---

## Future Improvements

1. **Optional cleanup**: `simple_llm_node.py` + `direct_llm_node.py` could be deleted if graph.py updated to call `llm_node` directly
2. **Intent pattern testing**: Create unit tests for `intent_patterns.py`
3. **RAG path optimization**: When `rag_subgraph` is present, skip `retrieval_node` initialization entirely
4. **Consider consolidation**: `research_node` + `planning_node` could share utilities
