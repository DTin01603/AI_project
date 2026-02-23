# Tổng quan MVP chat cơ bản

## 1) Mục tiêu
- Tạo một luồng chat tối thiểu có thể nhận câu hỏi và trả lời ổn định.
- Không bao gồm retrieval, queue, tool calling, hay multi-step planning.
- Ưu tiên để triển khai nhanh, dễ test, dễ debug.

## 2) Phạm vi chức năng giữ lại
- captureQuestion
- normalizeRequest
- invokeModelsWithContext
- composeResponse
- deliverResponseToUser

## 3) Thành phần kiến trúc
- UI (React): nhập câu hỏi, hiển thị trả lời, hiển thị lỗi cơ bản.
- API (Python): endpoint `/chat`, validate đầu vào, gọi pipeline.
- Orchestrator (đơn giản): gọi tuần tự 5 bước trên.
- Model client: adapter gọi LLM provider.

## 4) Luồng dữ liệu MVP
1. UI gửi `{message}` lên API `/chat`.
2. API `captureQuestion` để làm sạch tối thiểu.
3. API `normalizeRequest` để tạo request schema thống nhất.
4. API `invokeModelsWithContext` để gọi model.
5. API `composeResponse` để tạo payload trả về.
6. API `deliverResponseToUser` để response HTTP cho UI.

## 5) Data contract tổng quát

### Request từ UI
```json
{
	"message": "Xin chào, bạn có thể giúp tôi không?",
	"locale": "vi-VN",
	"channel": "web"
}
```

### Response về UI
```json
{
	"request_id": "req_123",
	"answer": "Chào bạn, mình có thể giúp...",
	"status": "ok",
	"error": null
}
```

## 6) Nguyên tắc thiết kế cho MVP
- Đơn giản hóa: một endpoint, một luồng xử lý đồng bộ.
- Bắt buộc có `request_id` để trace log.
- Lỗi được chuẩn hóa theo mã (`BAD_REQUEST`, `MODEL_ERROR`, `INTERNAL_ERROR`).
- Không streaming trong MVP; trả một lần.

## 7) Tiêu chí hoàn thành toàn hệ thống
- API nhận input hợp lệ và trả lời trong SLA nội bộ (ví dụ < 5s với câu hỏi ngắn).
- Có xử lý lỗi đầu vào và lỗi model, không crash process.
- UI hiển thị được trạng thái thành công/thất bại rõ ràng.
- Có test đơn vị cho 5 bước và 1 test integration cho endpoint `/chat`.

## 8) API bên ngoài (FastAPI)

### 8.1) `POST /chat`
- Mục đích: nhận câu hỏi người dùng và trả câu trả lời một lần (non-streaming).
- Request body:
```json
{
	"message": "Xin chào, bạn có thể giúp tôi không?",
	"locale": "vi-VN",
	"channel": "web"
}
```
- Response thành công (HTTP 200):
```json
{
	"request_id": "req_123",
	"status": "ok",
	"answer": "Chào bạn, mình có thể giúp...",
	"error": null,
	"meta": {
		"model": "gpt-4o-mini",
		"finish_reason": "stop"
	}
}
```
- Response lỗi:
  - HTTP 400: `BAD_REQUEST` (input rỗng/sai schema).
  - HTTP 502: `MODEL_ERROR` (provider/model lỗi).
  - HTTP 500: `INTERNAL_ERROR` (lỗi hệ thống).

### 8.2) `GET /health`
- Mục đích: kiểm tra trạng thái service.
- Response (HTTP 200):
```json
{
	"status": "ok"
}
```

### 8.3) `GET /ready`
- Mục đích: kiểm tra service sẵn sàng nhận traffic.
- Kiểm tra tối thiểu: config model, API key, kết nối dependency cần thiết.
- Response:
  - HTTP 200 khi sẵn sàng.
  - HTTP 503 khi chưa sẵn sàng.

## 9) API nội bộ trong pipeline (service layer)
- `captureQuestion(payload) -> CapturedQuestion`
- `normalizeRequest(captured) -> NormalizedRequest`
- `invokeModelsWithContext(normalized) -> ModelResult`
- `composeResponse(model_result | error) -> ResponsePayload`
- `deliverResponseToUser(response_payload) -> HTTPResponse`

Gợi ý kiểu dữ liệu (Pydantic):
- `ChatRequest`
- `ChatResponse`
- `ErrorPayload`
- `NormalizedRequest`
- `ModelResult`

## 10) API sử dụng từ LangChain (khi tích hợp model)
- `ChatPromptTemplate.from_messages(...)`: tạo prompt chuẩn.
- `ChatOpenAI(...)` hoặc provider tương đương: gọi LLM.
- `llm.invoke(messages)`: nhận output một lần.
- `StrOutputParser()` (tuỳ chọn): chuẩn hóa output text.

Luồng tích hợp tối thiểu:
1. Tạo prompt từ `message`.
2. Gọi `llm.invoke(...)` với `temperature`, `max_tokens`.
3. Map output về `ModelResult`.

## 11) API sử dụng từ LangGraph (khi cần orchestration rõ ràng)
- `StateGraph(StateSchema)`: khai báo state dùng chung.
- `add_node(name, fn)`: thêm node xử lý.
- `add_edge(a, b)`: nối luồng tuần tự.
- `add_conditional_edges(...)` (tuỳ chọn): rẽ nhánh theo lỗi/điều kiện.
- `compile()`: build graph runnable.
- `graph.invoke(state)`: chạy graph cho mỗi request.

State tối thiểu đề xuất:
- `request_id`
- `message`
- `normalized_request`
- `model_result`
- `final_response`
- `error`
