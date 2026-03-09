# AI Project

Research agent dùng FastAPI + LangGraph + React (Vite), hỗ trợ:

- Chat thường (JSON response)
- Chat streaming realtime qua SSE
- Routing theo loại câu hỏi (simple/research/current_date/direct_llm)
- Persist hội thoại bằng SQLite + LangGraph checkpointer

## 1) Chuẩn bị môi trường

Tạo file env local:

```bash
cp .env.example .env
```

Điền các biến quan trọng trong `.env`:

- `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY`
- `GROQ_API_KEY`
- `GOOGLE_SEARCH_API_KEY`
- `GOOGLE_SEARCH_ENGINE_ID`
- `DEFAULT_MODEL` (vd: `gemini/gemini-2.5-flash`)
- `LANGGRAPH_CHECKPOINTER` (`sqlite` hoặc `postgres`)
- `LANGGRAPH_DB_PATH` (mặc định `./checkpoints.db`)
- `DATABASE_PATH` (mặc định `./data/conversations.db`)

Lưu ý bảo mật:

- Không commit `.env`
- Nếu key từng lộ, rotate key ngay

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

```bash
pytest -q
```

## 6) Cấu trúc thư mục chính

- `backend/src/research_agent/`: LangGraph runtime (graph, nodes, edges, streaming, checkpointer)
- `backend/src/api/routers/chat_v2.py`: API chat v2 (stream + non-stream)
- `frontend/`: React Vite app
- `Architecture/`: tài liệu thiết kế, migration plan, flow diagrams

## 7) Ghi chú kiến trúc

- Stream mode dùng `graph.astream(..., stream_mode="updates")`
- `SSEAdapter` chuyển từng node update thành SSE event để frontend render realtime
- Persistence:
	- Message history: `DATABASE_PATH`
	- Graph checkpoints: `LANGGRAPH_DB_PATH` hoặc Postgres

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
