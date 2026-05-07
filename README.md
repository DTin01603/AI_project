# AI Research Agent + RAG

Hệ thống chat AI kết hợp **FastAPI + LangGraph + React (Vite)** với **RAG** trên tài liệu lịch sử Việt Nam. Một LLM call phân loại intent → định tuyến sang `direct_answer`, `local_rag`, `web_search`, hoặc `current_date` → tổng hợp câu trả lời có trích dẫn.

---

## Mục lục

1. [Kiến trúc](#1-kiến-trúc)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Chạy project](#3-chạy-project)
4. [Cấu hình](#4-cấu-hình)
5. [API](#5-api)
6. [RAG](#6-rag)
7. [Kiểm thử](#7-kiểm-thử)
8. [Deploy](#8-deploy)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Kiến trúc

### Stack

| Tầng | Công nghệ |
|------|-----------|
| Backend | FastAPI 0.135, Python 3.12, Uvicorn |
| Orchestration | LangGraph 1.0, LangChain 1.2 |
| LLM | Google Gemini (mặc định), Groq |
| Search | Google Custom Search, Tavily |
| RAG | ChromaDB (vector) + SQLite FTS5, sentence-transformers, cross-encoder rerank |
| Persistence | SQLite checkpointer (mặc định) hoặc Postgres |
| Frontend | React 19, Vite 7 |

### Luồng request

```
Client ──POST /api/v2/chat──► FastAPI ──► ResearchAgentGraph
                                              │
                                              ▼
                                          entry → intent
                                                    │
                          ┌──────────────┬──────────┼──────────────┐
                          ▼              ▼          ▼              ▼
                   direct_answer    local_rag   web_search     current_date
                                                    │
                                          planning → research → synthesis → citation
                          │              │          │              │
                          └──────────────┴────► persist ────► END
                                              │
                                              ▼
                            SSE events (stream) hoặc ChatResponse (JSON)
```

**Routing 1 bước:** node `intent` gọi skill `intent_classifier` (1 LLM call) chọn 1 trong 4 nhánh dựa trên mô tả corpus trong [skill.yaml](backend/src/skills/intent_classifier/skill.yaml). Đây là kiến trúc hiện tại, đã thay thế luồng cũ `complexity → router` 2 bước.

### Skill Framework

Mọi prompt + logic LLM được đóng gói thành **skill** — folder 3 file:

```
backend/src/skills/<name>/
├── skill.yaml     # metadata, model, runtime params
├── prompt.md      # Jinja2 template
└── handler.py     # Handler(BaseSkill) với Inputs/Outputs Pydantic
```

- `SkillRegistry` discover khi startup; folder `rag/transform_query/` → skill `rag.transform_query`.
- Prompt **auto-reload theo mtime** — sửa `prompt.md` không cần restart.
- Model resolution: `request.model` → `skill.yaml` → `DEFAULT_MODEL` env.

**11 skills hiện có:**

| Skill | LLM | Mục đích |
|-------|-----|----------|
| `intent_classifier` | ✓ | Routing 1-step (direct_answer / local_rag / web_search / current_date) |
| `planning` | ✓ | Sinh research plan (cap 5 task) |
| `research_search` | ✓ | Tavily search + LLM extraction |
| `direct_answer` | ✓ | LLM trực tiếp với history trimming + retry/timeout |
| `response_composer` | ✓ | Tổng hợp answer từ knowledge base |
| `rag.retrieve` | ✗ | Wrap `RetrievalNode` (hybrid BM25 + vector) |
| `rag.query_expand` | ✗ | Sinh biến thể query cho multi-query retrieval |
| `rag.transform_query` | ✓ | Rewrite query khi retrieval fail |
| `rag.grade_documents` | ✓ | Đánh giá relevance, fallback threshold 0.4 |
| `rag.grade_generation` | ✓ | Verify answer grounded & useful |
| `rag.answer_with_context` | ✓ | Sinh answer từ context docs + history |

**Thêm skill mới:** tạo folder mới với 3 file, registry tự discover khi restart.

### Persistence

| Data | Path mặc định | Env |
|------|--------------|-----|
| Message history | `./data/conversations.db` | `DATABASE_PATH` |
| Graph checkpoints | `./checkpoints.db` | `LANGGRAPH_DB_PATH` |
| RAG FTS5 | `data/rag.db` | `RAG_DB_PATH` |
| Vector store | `data/vector_store/` | `RAG_VECTOR_STORE_PATH` |

Sơ đồ chi tiết: [docs/architecture/](docs/architecture/).

---

## 2. Cấu trúc thư mục

```
AI_project/
├── backend/src/
│   ├── main.py                    # FastAPI app entry
│   ├── config.py                  # Settings + model registry
│   ├── langgraph_platform.py      # Entry cho LangGraph Platform
│   ├── api/
│   │   ├── deps.py                # DI: build ResearchAgentGraph
│   │   └── routers/               # core, chat_v2, search
│   ├── adapters/                  # LLM adapters (google, groq)
│   ├── models/                    # Request/Response/Internal DTOs
│   ├── skills/                    # 11 skills (xem bảng trên)
│   ├── research_agent/
│   │   ├── graph/                 # LangGraph build + compile
│   │   ├── nodes/                 # 9 thin-wrapper nodes (delegate sang skills)
│   │   ├── edges/                 # intent_edge
│   │   ├── streaming/sse_adapter  # graph updates → SSE events
│   │   ├── checkpointer/          # sqlite / postgres
│   │   ├── aggregator.py          # Gộp research results (no LLM)
│   │   ├── database.py            # conversations.db CRUD
│   │   └── state.py               # AgentState TypedDict
│   └── rag/                       # FTS5 + Chroma + reranker + chunking
│
├── backend/config/rag.yaml.example
├── backend/scripts/index_doc.py   # CLI index tài liệu
├── backend/tests/                 # unit / integration / property / manual
│
├── frontend/src/                  # React 19 + Vite 7
├── scripts/                       # docker-up-clean, clear_index, debug_chunks, langsmith_evaluate
├── docs/
│   ├── architecture/              # diagrams/ + workflows/ + plans/
│   ├── guides/                    # AI agent guide, beginner guide, criteria
│   ├── changelog/
│   └── archive/                   # Plan/report cũ đã xong
├── data/                          # Runtime DB + vector store + sources/
│
├── docker-compose.yml
├── Dockerfile.backend / Dockerfile.frontend
├── requirements.txt
├── langgraph.json                 # Manifest LangGraph Platform
└── .env.example
```

---

## 3. Chạy project

### Yêu cầu

- **Docker Desktop** (khuyến nghị), hoặc Python 3.12+ và Node.js 20+.

### Setup

```bash
cp .env.example .env
# Điền GEMINI_API_KEY (hoặc GROQ_API_KEY) tối thiểu
```

### Docker (khuyến nghị)

```bash
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- Volumes: `./data` (DB) + `hf_cache` (HuggingFace models)

### Local

**Backend:**
```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows
pip install -r requirements.txt
PYTHONPATH=backend/src uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend && npm install && npm run dev
```

---

## 4. Cấu hình

### LLM & Search keys

| Biến | Bắt buộc | Mô tả |
|------|----------|-------|
| `GEMINI_API_KEY` (hoặc `GOOGLE_API_KEY`) | ✓ (hoặc Groq) | Google Gemini |
| `GROQ_API_KEY` | ✓ (hoặc Gemini) | Groq |
| `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` | research | Google Custom Search |
| `TAVILY_API_KEY` | research | Tavily (alternative) |
| `DEFAULT_MODEL` | tuỳ chọn | vd `gemini/gemini-2.5-flash` |

### Persistence & runtime

| Biến | Mặc định |
|------|----------|
| `LANGGRAPH_CHECKPOINTER` | `sqlite` (hoặc `postgres`) |
| `LANGGRAPH_DB_PATH` | `./checkpoints.db` |
| `DATABASE_PATH` | `./data/conversations.db` |
| `LOG_LEVEL` | `INFO` |
| `DEFAULT_MAX_OUTPUT_TOKENS` | `1200` |

### RAG

| Biến | Mặc định |
|------|----------|
| `RAG_DEFAULT_SEARCH_METHOD` | `hybrid` (`fts` / `vector` / `hybrid`) |
| `RAG_FTS_WEIGHT` / `RAG_VECTOR_WEIGHT` | `0.3` / `0.7` |
| `RAG_ENABLE_RERANKING` | `true` |
| `RAG_RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` | `512` / `50` |

Cấu hình đầy đủ: [.env.example](.env.example) và [backend/config/rag.yaml.example](backend/config/rag.yaml.example).

> **Bảo mật:** không commit `.env`. Rotate key ngay nếu lộ.

---

## 5. API

Base URL: `http://localhost:8000`. Response luôn có header `x-api-version: 2`.

### `POST /api/v2/chat`

Query: `?stream=true` để SSE.

**Request:**
```json
{
  "message": "Ngô Quyền đánh bại quân Nam Hán năm nào?",
  "conversation_id": "optional-uuid",
  "model": "gemini/gemini-2.5-flash"
}
```

**Response (non-stream):**
```json
{
  "request_id": "uuid",
  "conversation_id": "uuid",
  "status": "ok",
  "answer": "...",
  "sources": ["..."],
  "meta": { "provider": "gemini", "model": "...", "finish_reason": "stop" }
}
```

**Response (stream, SSE):**
```
data: {"type":"status","node":"intent","progress":15,...}
data: {"type":"status","node":"local_rag","progress":50,...}
data: {"type":"done","data":{"answer":"...","citations":[...]}}
data: [DONE]
```

Stream tự retry 1 lần khi gặp `MODEL_ERROR` (rate-limit/timeout).

**Error codes:** `BAD_REQUEST`, `MODEL_ERROR`, `EXECUTION_ERROR`, `INTERNAL_ERROR`.

### Endpoints khác

| Method | Path | Mô tả |
|--------|------|-------|
| `GET` | `/health` | Liveness + uptime |
| `GET` | `/ready` | Readiness (503 nếu không có provider) |
| `GET` | `/models` | Danh sách model + availability |
| `POST` | `/api/search` | Debug RAG (`fts` / `vector` / `hybrid`) |
| `GET` | `/api/search/health` | FTS engine health |

### Ví dụ

```bash
# Non-stream
curl -X POST 'http://localhost:8000/api/v2/chat' \
  -H 'Content-Type: application/json' \
  -d '{"message":"Khởi nghĩa Hai Bà Trưng năm nào?"}'

# Stream
curl -N -X POST 'http://localhost:8000/api/v2/chat?stream=true' \
  -H 'Content-Type: application/json' \
  -d '{"message":"Tóm tắt văn hóa Đông Sơn"}'
```

Frontend: xem [frontend/src/services/api.js](frontend/src/services/api.js).

---

## 6. RAG

### Pipeline

**Indexing:** `document_loader` (txt/md/pdf/docx/code) → `chunking` → `embedding` → SQLite FTS5 + ChromaDB.

**Retrieval:** Query → (Query Expansion) → FTS + Vector → Hybrid Merge → Cross-Encoder Rerank → Top-K.

**Realtime:** Mỗi message user/assistant được `conversation_indexer` index ngay khi persist.

### Index tài liệu

```bash
python backend/scripts/index_doc.py docs/setup_guide.md   # 1 file
python backend/scripts/index_doc.py docs/                  # cả thư mục
```

### Chọn search method

| Method | Khi nào dùng |
|--------|--------------|
| `fts` | Keyword exact, tên riêng, code |
| `vector` | Semantic / diễn đạt khác nhau |
| `hybrid` | Mặc định, recommended |

### Cross-encoder

Tăng độ chính xác 10-20%. `sentence-transformers` đã có trong `requirements.txt`. Cài tay:

```bash
backend/install_cross_encoder.bat   # Windows
bash backend/install_cross_encoder.sh   # Linux/macOS
```

Fallback về cosine similarity nếu không load được.

Chi tiết: [backend/src/rag/README.md](backend/src/rag/README.md).

---

## 7. Kiểm thử

```bash
pytest -q                                              # Toàn bộ
pytest backend/tests/unit/ -v                          # Unit
pytest backend/tests/integration/ -v                   # Integration
pytest backend/tests/unit/test_skills_framework.py -v  # Skill framework
pytest backend/tests/integration/test_chat_v2_streaming.py -v  # Chat API
```

Trạng thái: 175 unit tests PASS (~9 phút).

**Test thủ công:**
```bash
python backend/tests/manual/test_conversation_indexer.py   # E2E conversation indexing + retrieval
python scripts/clear_index.py                              # Clear RAG index
python scripts/debug_chunks.py                             # Debug chunking
```

**LangSmith eval:** `python scripts/langsmith_evaluate_dataset.py` (cần `LANGSMITH_API_KEY`).

---

## 8. Deploy

Project có sẵn [`langgraph.json`](langgraph.json) và entry [`backend/src/langgraph_platform.py`](backend/src/langgraph_platform.py).

```bash
pip install -U langgraph-cli
langgraph dev                       # Chạy local qua LangGraph runtime
langgraph up                        # Deploy lên Platform
```

Logging xuất hiện trong Server logs view nếu dùng `logging.getLogger("app.xxx")` (không phải `print()`).

---

## 9. Troubleshooting

| Vấn đề | Fix |
|--------|-----|
| `/ready` trả 503 | Thiếu `GEMINI_API_KEY` / `GROQ_API_KEY` hợp lệ |
| `MODEL_ERROR` (429) | Provider rate-limit. Stream auto-retry 1 lần |
| Search không có kết quả | Chưa index. Chạy `python backend/scripts/index_doc.py <path>` |
| Cross-encoder không load | `pip install sentence-transformers`, hoặc chấp nhận fallback cosine |
| ChromaDB chậm lần đầu | Tải embedding model. Volumes `hf_cache` cache cho lần sau |
| Docker không mount `./data` (Windows) | Docker Desktop → Settings → Resources → File sharing |
| Frontend không kết nối backend | Check `VITE_PROXY_TARGET` (Docker) hoặc `VITE_API_BASE_URL` (local) |
| Sửa `prompt.md` không có tác dụng | Xoá `__pycache__`. Prompt auto-reload theo mtime, không cần restart |
| Routing sai | Edit `intent_classifier/skill.yaml` (đặc biệt `corpus_description`). Restart backend (YAML không auto-reload) |
| Skill không discover | Check log `[SKILLS] loaded <name>`. Folder cần `skill.yaml` + `handler.py` với class `Handler(BaseSkill)` |
| Log không hiện trên Platform | Dùng `logging.getLogger("app.xxx")` thay vì `print()` |

---

## Tài liệu tham khảo

- [backend/src/rag/README.md](backend/src/rag/README.md) — Chi tiết module RAG
- [docs/architecture/](docs/architecture/) — Sơ đồ, workflow, plan kiến trúc gốc
- [docs/guides/](docs/guides/) — AI agent guide, beginner guide, tiêu chí agent
- [docs/changelog/](docs/changelog/) — Changelog
- [docs/archive/](docs/archive/) — Plan/report đã hoàn thành
- [.env.example](.env.example), [backend/config/rag.yaml.example](backend/config/rag.yaml.example) — Cấu hình mẫu
