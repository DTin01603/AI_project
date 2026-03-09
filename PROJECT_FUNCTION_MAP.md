# Project Function Map (AI_project)

Tài liệu này ghi chú nhanh: **file nào xử lý chức năng gì** trong toàn bộ project.

## 1) Tổng quan kiến trúc

- **Backend (FastAPI):** nhận request chat thường và chat streaming, điều phối AI agent, lưu hội thoại SQLite.
- **Frontend (React + Vite):** giao diện chat, chọn model, hiển thị status event theo SSE, render response theo chunk.
- **Research Agent Layer:** parser, phân tích độ phức tạp, lập kế hoạch research, gọi web search + LLM, tổng hợp và soạn câu trả lời.
- **Streaming Layer:** quản lý SSE connection, emit status events theo tiến trình xử lý.

---

## 2) Backend - Entry point và routing

### `backend/src/main.py`
- `create_app()`:
  - Khởi tạo FastAPI app.
  - Gắn middleware log request (`log_http_requests`).
  - Gắn exception handlers cho validation (400) và unexpected error (500).
  - Mount router: `core_router`, `chat_v2_router`.

### `backend/src/api/routers/core.py`
- `GET /health`: health check + uptime.
- `GET /ready`: kiểm tra khả dụng model.
- `GET /models`: trả danh sách model registry + trạng thái available.

### `backend/src/api/routers/chat_v2.py`
- `POST /api/v2/chat`:
  - Nhận `ChatRequest`.
  - `stream=false`: chạy `graph.ainvoke(...)`, trả JSON `ChatResponse`.
  - `stream=true`: chạy `graph.astream(...)`, trả SSE qua `SSEAdapter`.
  - Trả header `x-api-version: 2` để client nhận diện contract.

### `backend/src/api/routers/stream_chat.py`
- `POST /chat/stream` (SSE):
  - Tạo stream qua `SSEStreamManager.create_stream()`.
  - Parse query filter `event_types`.
  - Tạo `StatusEventEmitter`.
  - Chạy background task `_run()`:
    - emit `connection_established`
    - gọi `StreamingOrchestrator.process_request_stream(...)`
    - lỗi thì emit `error`
    - luôn `close_stream()` ở `finally`.

### `backend/src/api/deps.py`
- Dependency wiring / composition root:
  - Build dependencies cho LangGraph runtime (`ComplexityAnalyzer`, `DirectLLM`, `Database`, `ResearchTool`, `PlanningAgent`, `Aggregator`, `ResponseComposer`).
  - `get_research_agent_graph()` trả singleton graph để dùng cho cả stream và non-stream.

---

## 3) Backend - Domain / UseCase / Models / Service

### `backend/src/domain/ports.py`
- Định nghĩa contract `ChatServicePort` (`handle_message`).

### `backend/src/application/use_cases/chat_use_cases.py`
- `ChatUseCase.execute(...)`: use case mỏng, gọi vào `ChatServicePort`.

### `backend/src/models/request.py`
- Schema input API: `ChatRequest`.

### `backend/src/models/response.py`
- Schema output API: `ChatResponse`, `ResponseMeta`, `ResponseError`.

### `backend/src/services/deliver_response.py`
- `DeliverResponseService._resolve_status_code(...)`: ánh xạ mã lỗi sang HTTP code.
- `DeliverResponseService.deliver(...)`: trả `JSONResponse` chuẩn.

### `backend/src/config.py`
- Đọc biến môi trường, model registry, timeout/config mặc định.

---

## 4) Backend - Adapter layer

### `backend/src/adapters/base.py`
- Interface chuẩn cho adapter (`BaseAdapter`) + output struct (`AdapterOutput`).

### `backend/src/adapters/google_adapter.py`
- `GeminiAdapter.invoke(...)`:
  - Gọi `ChatGoogleGenerativeAI`.
  - Chuẩn hóa output text + usage metadata.

---

## 5) Backend - Research Agent (LangGraph core)

### `backend/src/research_agent/chat_service.py`
- `ResearchChatService.handle_message(...)`: bridge từ port sang `Orchestrator.process_request(...)`.

### `backend/src/research_agent/orchestrator.py`
- **Trung tâm điều phối non-stream**:
  - Parse request (`Parser`).
  - Detect case đặc biệt ngày hiện tại.
  - Analyze complexity (`ComplexityAnalyzer`) + override theo intent/time-sensitive.
  - Nhánh simple: gọi `DirectLLM.generate_response(...)`.
  - Nhánh complex:
    - lập plan (`PlanningAgent`),
    - chạy task research (`ResearchTool`),
    - aggregate (`Aggregator`),
    - compose (`ResponseComposer`).
  - Lưu lịch sử chat vào `Database`.
  - Chuẩn hóa lỗi qua `sanitize_error(...)`.

### `backend/src/research_agent/parser.py`
- Chuẩn hóa Unicode + trim + validate message rỗng.

### `backend/src/research_agent/complexity_analyzer.py`
- Phân loại simple/complex bằng model + fallback heuristic.

### `backend/src/research_agent/planning_agent.py`
- Sinh research plan 1-5 tasks từ câu hỏi + fallback plan.

### `backend/src/research_agent/research_tool.py`
- Web search (Tavily) + extract thông tin liên quan bằng LLM.
- Trả `ResearchResult` cho từng task.

### `backend/src/research_agent/aggregator.py`
- Gom thông tin từ nhiều task, deduplicate lines/sources.

### `backend/src/research_agent/response_composer.py`
- Soạn câu trả lời cuối từ `knowledge_base`.

### `backend/src/research_agent/direct_llm.py`
- Chat trực tiếp với LLM cho simple path.
- Có retry + timeout wrapper.

### `backend/src/research_agent/database.py`
- SQLite persistence:
  - tạo schema,
  - tạo conversation,
  - lưu message,
  - lấy history theo conversation.

### `backend/src/research_agent/resilience.py`
- Utility hạ tầng: `call_with_retry`, `with_timeout`, `with_timeout_async`.

### `backend/src/research_agent/error_utils.py`
- Chuẩn hóa/sanitized error message + mapping error code.

### `backend/src/research_agent/logging_utils.py`
- Structured logging helpers + redact thông tin nhạy cảm.

### `backend/src/research_agent/models.py`
- Data models nội bộ cho task, result, message records.

---

## 6) Backend - Streaming layer (v2)

### `backend/src/research_agent/streaming/sse_adapter.py`
- Chuyển node update từ LangGraph thành SSE events:
  - `status` event theo node + progress,
  - `done` event chứa answer/citations/metadata,
  - kết thúc bằng `data: [DONE]`.

---

## 7) Frontend - Entry/UI/Hook/Service

### `frontend/src/main.jsx`
- Bootstrap React app.

### `frontend/src/App.jsx`
- Mount `ChatInterface`.

### `frontend/src/components/ChatInterface.jsx`
- Container chính của chat:
  - load model list,
  - gửi message,
  - gọi `startStream(...)`,
  - xử lý `response_chunk` để append nội dung theo thời gian thực,
  - xử lý `response_complete` để finalize message/meta,
  - render `ModelSelector`, `MessageList`, `StatusDisplay`, `MessageInput`.

### `frontend/src/components/MessageInput.jsx`
- Form nhập và submit câu hỏi.

### `frontend/src/components/MessageList.jsx`
- Render hội thoại + sources.

### `frontend/src/components/ModelSelector.jsx`
- Chọn model gửi lên backend.

### `frontend/src/components/StatusDisplay.jsx`
- Hiển thị danh sách status events + trạng thái kết nối/reconnect.

### `frontend/src/components/ResponseDisplay.jsx`
- Component preview streaming response (đang có nhưng không thấy dùng trong `ChatInterface`).

### `frontend/src/hooks/useSSEStream.js`
- Hook quản lý vòng đời stream:
  - gọi `streamMessage(...)`,
  - lưu event list,
  - trạng thái connected/streaming/reconnecting,
  - reconnect exponential backoff (1s, 2s, 4s, 8s, max 4).

### `frontend/src/services/api.js`
- API client:
  - `fetchModels()`
  - `sendMessageStream()` gọi endpoint chuẩn `/api/v2/chat?stream=true`
  - parse block SSE (`data:`).

---

## 8) Tests

### `backend/tests/integration/`
- Test API end-to-end, bao gồm:
  - `test_deliver_response_api.py` (non-stream endpoint behavior)
  - `test_streaming_chat_api.py` (SSE event stream + filtering)

### `backend/tests/unit/`
- Test đơn vị cho module nhỏ (parser, orchestrator logic, service, v.v.).

### `backend/tests/property/`
- Khu vực cho property-based tests.

---

## 9) Tài liệu kiến trúc & triển khai

### `Architecture/`
- Tài liệu design, flow, sequence cho các phần của hệ thống.
- `plans/streaming-status-notifications/`: requirements/design/tasks/workflow cho streaming status.

### Root infra files
- `docker-compose.yml`: chạy backend/frontend bằng Docker.
- `Dockerfile.backend`, `Dockerfile.frontend`: build image cho từng service.
- `requirements.txt`: dependency Python backend.
- `pytest.ini`: cấu hình test backend.
- `scripts/docker-up-clean.sh`: script dọn + chạy compose sạch.

---

## 10) Luồng xử lý nhanh (để tra cứu khi debug)

### Non-stream (`POST /api/v2/chat?stream=false`)
1. `chat_v2.py` nhận request.
2. Gọi `ResearchAgentGraph.ainvoke(...)`.
3. Map final state thành `ChatResponse`.

### Stream (`POST /api/v2/chat?stream=true`)
1. `chat_v2.py` gọi `ResearchAgentGraph.astream(...)`.
2. `SSEAdapter.stream_to_sse(...)` chuyển node updates thành SSE events.
3. Frontend nhận event realtime và cập nhật UI.

---

## 11) Gợi ý mở rộng tài liệu này

Nếu bạn muốn “comment sâu hơn” theo kiểu function-level (mỗi hàm một dòng công dụng), có thể tạo thêm file `PROJECT_FUNCTION_MAP_DETAILED.md` và mình sẽ sinh đầy đủ theo từng module.
