# AI Project - Research Agent với RAG

Hệ thống AI Agent thông minh sử dụng FastAPI + LangGraph + React (Vite), tích hợp RAG (Retrieval Augmented Generation) để trả lời câu hỏi dựa trên kiến thức từ hội thoại và tài liệu đã index.

## Tính năng chính

### Chat & Streaming
- Chat thường (JSON response)
- Chat streaming realtime qua SSE (Server-Sent Events)
- Routing thông minh theo loại câu hỏi (simple/research/current_date/direct_llm)
- Persist hội thoại bằng SQLite + LangGraph checkpointer

### RAG System (Retrieval Augmented Generation)
- **Hybrid Search**: Kết hợp FTS (Full-Text Search) và Vector Search
- **Cross-Encoder Re-ranking**: Cải thiện độ chính xác 10-20%
- **Realtime Conversation Indexing**: Tự động index mọi tin nhắn mới
- **Document Indexing**: Index tài liệu (txt, md, pdf, docx) và code files
- **Query Expansion**: Mở rộng câu hỏi để tìm kiếm tốt hơn
- **Citation Tracking**: Theo dõi nguồn trích dẫn trong câu trả lời

Xem chi tiết tại [RAG_SYSTEM_OVERVIEW.md](RAG_SYSTEM_OVERVIEW.md)

## 1) Chuẩn bị môi trường

### Tạo file env local

```bash
cp .env.example .env
```

### Các biến môi trường quan trọng

#### LLM & Search APIs
- `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY` - API key cho Google Gemini
- `GROQ_API_KEY` - API key cho Groq (optional)
- `GOOGLE_SEARCH_API_KEY` - API key cho Google Search
- `GOOGLE_SEARCH_ENGINE_ID` - Search Engine ID
- `DEFAULT_MODEL` - Model mặc định (vd: `gemini/gemini-2.5-flash`)

#### Database & Persistence
- `LANGGRAPH_CHECKPOINTER` - Loại checkpointer (`sqlite` hoặc `postgres`)
- `LANGGRAPH_DB_PATH` - Đường dẫn database cho checkpoints (mặc định `./checkpoints.db`)
- `DATABASE_PATH` - Đường dẫn database cho conversations (mặc định `./data/conversations.db`)

#### RAG Configuration (Optional)
- `RAG_DB_PATH` - Database cho RAG (mặc định `data/rag.db`)
- `RAG_VECTOR_STORE_PATH` - Thư mục lưu vector store (mặc định `data/vector_store`)
- `RAG_DEFAULT_SEARCH_METHOD` - Phương thức search (`fts`, `vector`, hoặc `hybrid`)
- `RAG_ENABLE_RERANKING` - Bật/tắt cross-encoder re-ranking (mặc định `true`)
- `RAG_RERANKER_MODEL` - Model re-ranker (mặc định `cross-encoder/ms-marco-MiniLM-L-6-v2`)
- `RAG_ENABLE_QUERY_EXPANSION` - Bật/tắt query expansion (mặc định `true`)

Xem file `backend/config/rag.yaml.example` để biết đầy đủ các tùy chọn cấu hình RAG.

### Lưu ý bảo mật

- Không commit `.env` vào git
- Nếu key từng bị lộ, rotate key ngay lập tức
- Sử dụng `.env.example` làm template

## 2) Chạy project

### Cách khuyến nghị: Docker Compose

```bash
docker compose up --build
```

Nếu cần dọn process/container cũ trước khi chạy:

```bash
./scripts/docker-up-clean.sh
```

Services:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### Chạy backend local (không Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=backend/src uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 3) API hiện tại

### Chat endpoint chính

- `POST /api/v2/chat`
- Header response: `x-api-version: 2`

Query param:

- `stream=false` (mặc định): trả JSON `ChatResponse`
- `stream=true`: trả `text/event-stream` (SSE)

Request body:

```json
{
	"message": "Giá vàng hôm nay bao nhiêu?",
	"conversation_id": "optional-id",
	"locale": "vi-VN",
	"channel": "web",
	"model": "gemini/gemini-2.5-flash"
}
```

### Health/Readiness/Models

- `GET /health`
- `GET /ready`
- `GET /models`

### Versioning & error policy

- Contract chi tiết được chốt tại `API_CONTRACT.md`
- Breaking change phải tạo version mới (`/api/v3/...`), không break trực tiếp v2
- JSON errors chuẩn dùng các code: `BAD_REQUEST`, `INTERNAL_ERROR`, `MODEL_ERROR`, `EXECUTION_ERROR`

## 4) Ví dụ gọi API

### Non-stream

```bash
curl -X POST 'http://localhost:8000/api/v2/chat' \
	-H 'Content-Type: application/json' \
	-d '{
		"message":"Tóm tắt tình hình AI 2026",
		"model":"gemini/gemini-2.5-flash"
	}'
```

### Streaming SSE

```bash
curl -N -X POST 'http://localhost:8000/api/v2/chat?stream=true' \
	-H 'Content-Type: application/json' \
	-d '{
		"message":"Tìm 3 quán phở ngon ở Hà Nội",
		"model":"gemini/gemini-2.5-flash"
	}'
```

SSE stream sẽ phát:

- nhiều event `status` (progress theo node)
- 1 event `done` (answer/citations/metadata)
- kết thúc bằng `data: [DONE]`

## 5) Kiểm thử

### Chạy toàn bộ test suite

```bash
pytest -q
```

### Chạy test theo module

```bash
# Test RAG system
pytest backend/tests/integration/test_retrieval_with_metrics.py -v
pytest backend/tests/integration/test_hybrid_retrieval_node.py -v
pytest backend/tests/integration/test_document_indexing_retrieval.py -v

# Test API endpoints
pytest backend/tests/integration/test_deliver_response_api.py -v
pytest backend/tests/integration/test_streaming_chat_api.py -v

# Test unit
pytest backend/tests/unit/ -v
```

### Test thủ công

```bash
# Test conversation indexing và retrieval
python test_manual.py

# Index một document
python backend/scripts/index_doc.py path/to/document.md
```

## 6) Cấu trúc thư mục chính

### Backend
- `backend/src/research_agent/`: LangGraph runtime (graph, nodes, edges, streaming, checkpointer)
- `backend/src/api/routers/chat_v2.py`: API chat v2 (stream + non-stream)
- `backend/src/rag/`: Hệ thống RAG hoàn chỉnh
  - `fts_engine.py`: Full-text search với SQLite FTS5
  - `vector_store.py`: Vector search với ChromaDB
  - `hybrid_search.py`: Kết hợp FTS + Vector search
  - `reranker.py`: Cross-encoder re-ranking
  - `embedding.py`: Embedding models (sentence-transformers)
  - `document_indexer.py`: Index tài liệu và code
  - `conversation_indexer.py`: Realtime conversation indexing
  - `retrieval_node.py`: LangGraph node cho retrieval
  - `query_expander.py`: Mở rộng câu hỏi
  - `chunking.py`: Chiến lược chunking (recursive, code-aware)
- `backend/src/adapters/`: Adapter cho các LLM providers
- `backend/src/models/`: Request/Response schemas
- `backend/config/`: Configuration files (rag.yaml.example)
- `backend/data/`: Databases và vector stores
- `backend/scripts/`: Utility scripts (index_doc.py)

### Frontend
- `frontend/`: React Vite app với SSE streaming support

### Documentation
- `Architecture/`: Tài liệu thiết kế, migration plan, flow diagrams
- `docs/`: Tài liệu chi tiết về các tính năng
- `API_CONTRACT.md`: API contract và versioning policy
- `PROJECT_FUNCTION_MAP.md`: Map chi tiết các file và chức năng
- `UPGRADE_CROSS_ENCODER.md`: Hướng dẫn nâng cấp cross-encoder
- `complete-ai-agent-guide.md`: Hướng dẫn xây dựng AI Agent hoàn chỉnh

## 7) Ghi chú kiến trúc

### Streaming Architecture
- Stream mode dùng `graph.astream(..., stream_mode="updates")`
- `SSEAdapter` chuyển từng node update thành SSE event để frontend render realtime

### Persistence Layers
- **Message history**: `DATABASE_PATH` (SQLite)
- **Graph checkpoints**: `LANGGRAPH_DB_PATH` (SQLite) hoặc Postgres
- **RAG database**: `RAG_DB_PATH` (SQLite với FTS5)
- **Vector store**: `RAG_VECTOR_STORE_PATH` (ChromaDB)

### RAG Pipeline
1. **Indexing Flow**: Document/Message → Chunking → Embedding → [SQLite FTS + Vector Store]
2. **Retrieval Flow**: Query → Query Expansion → [FTS Search + Vector Search] → Hybrid Merge → Re-ranking → Top Results
3. **Realtime Indexing**: Mọi tin nhắn mới tự động được index vào cả FTS và Vector store

### Search Methods
- **FTS (Full-Text Search)**: Keyword-based search với SQLite FTS5, tốt cho exact matches
- **Vector Search**: Semantic search với embeddings, tốt cho ý nghĩa tương tự
- **Hybrid Search**: Kết hợp cả hai với weighted scoring (mặc định: FTS 30%, Vector 70%)
- **Re-ranking**: Cross-encoder đánh giá lại top candidates để cải thiện độ chính xác

## 8) Deploy lên LangGraph Platform (Server logs view)

Project đã có sẵn manifest deploy `langgraph.json` và graph entrypoint `backend/src/langgraph_platform.py`.

### Chuẩn bị

1. Đảm bảo `.env` có đầy đủ key model/search bạn dùng (`GEMINI_API_KEY` hoặc `GROQ_API_KEY`, `TAVILY_API_KEY` nếu cần).
2. Cài CLI:

```bash
pip install -U langgraph-cli
```

### Chạy local bằng LangGraph runtime

```bash
langgraph dev
```

Khi runtime chạy, mở Studio/UI và chọn graph `research-agent`.

### Deploy lên LangGraph Platform

```bash
langgraph up
```

Sau khi deploy thành công, vào Studio của deployment đó:

1. Chạy thử graph 1 lần (invoke hoặc stream).
2. Mở `Server logs view` để xem:
   - Agent server operational logs.
   - User application logs từ Python `logging` trong code.

### Ghi log để hiện trong Server logs view

Bạn có thể ghi log ở bất kỳ node/module nào:

```python
import logging

logger = logging.getLogger("app.research")
logger.info("Start research node", extra={"query": "gia vang hom nay"})
```

`backend/src/langgraph_platform.py` đã cấu hình logging cơ bản để log text xuất hiện trong server logs.


## 9) RAG System - Hướng dẫn sử dụng

### Cài đặt Cross-Encoder (Khuyến nghị)

Cross-encoder cải thiện độ chính xác tìm kiếm 10-20%. Xem chi tiết tại [UPGRADE_CROSS_ENCODER.md](UPGRADE_CROSS_ENCODER.md).

**Cài đặt nhanh:**
```bash
cd backend
pip install sentence-transformers
```

Hệ thống sẽ tự động fallback về cosine similarity nếu không có `sentence-transformers`.

### Index tài liệu

```bash
# Index một file
python backend/scripts/index_doc.py docs/setup_guide.md

# Index thư mục
python backend/scripts/index_doc.py docs/
```

### Cấu hình RAG

Tạo file `backend/config/rag.yaml` từ template:

```bash
cp backend/config/rag.yaml.example backend/config/rag.yaml
```

Hoặc dùng environment variables với prefix `RAG_`:

```bash
RAG_DEFAULT_SEARCH_METHOD=hybrid
RAG_ENABLE_RERANKING=true
RAG_FTS_WEIGHT=0.3
RAG_VECTOR_WEIGHT=0.7
```

### Search Methods

- **FTS**: Tốt cho exact keyword matches
  ```bash
  RAG_DEFAULT_SEARCH_METHOD=fts
  ```

- **Vector**: Tốt cho semantic similarity
  ```bash
  RAG_DEFAULT_SEARCH_METHOD=vector
  ```

- **Hybrid** (Khuyến nghị): Kết hợp cả hai
  ```bash
  RAG_DEFAULT_SEARCH_METHOD=hybrid
  RAG_FTS_WEIGHT=0.3
  RAG_VECTOR_WEIGHT=0.7
  ```

### Tối ưu hóa Performance

**Nếu latency cao:**
```bash
RAG_RERANK_TOP_N=50  # Giảm số candidates re-rank
RAG_RERANKER_MODEL=cross-encoder/ms-marco-TinyBERT-L-2-v2  # Dùng model nhỏ hơn
```

**Nếu memory cao:**
```bash
RAG_CACHE_SIZE=500  # Giảm cache size
RAG_RERANKER_MODEL=cross-encoder/ms-marco-TinyBERT-L-2-v2  # ~50MB thay vì 80MB
```

**Tắt re-ranking nếu cần:**
```bash
RAG_ENABLE_RERANKING=false
```

### Monitoring

Check logs khi khởi động để xác nhận cấu hình:

```
INFO - Loading cross-encoder model: cross-encoder/ms-marco-MiniLM-L-6-v2
INFO - Cross-encoder loaded successfully
INFO - RAG system initialized: hybrid search with re-ranking enabled
```

Xem thêm chi tiết tại:
- [RAG_SYSTEM_OVERVIEW.md](RAG_SYSTEM_OVERVIEW.md) - Tổng quan về RAG system
- [backend/src/rag/README.md](backend/src/rag/README.md) - RAG system documentation
- [backend/src/rag/IMPLEMENTATION_STATUS.md](backend/src/rag/IMPLEMENTATION_STATUS.md) - Implementation status
- [backend/src/rag/CONVERSATION_INDEXING.md](backend/src/rag/CONVERSATION_INDEXING.md) - Conversation indexing details
