# Tổng quan MVP Chat AI (đa model)

## 0) Metadata
- Owner: Backend Team
- Version: 2.0
- Môi trường: MVP internal

## 1) Mục tiêu
- Xây dựng chat API đơn giản bằng FastAPI + LangChain.
- Cho phép user chọn model AI theo từng request.
- Trả response nhất quán để frontend xử lý ổn định.

## 2) Scope
### In scope
- `POST /chat` non-streaming.
- `GET /models` trả danh sách model hỗ trợ.
- Pipeline 5 bước: `captureQuestion -> normalizeRequest -> invokeModelsWithContext -> composeResponse -> deliverResponseToUser`.

### Out of scope
- Retrieval/Vector DB, tool calling, multi-agent, queue scheduling, memory dài hạn.
- Streaming SSE ở phase này.

## 3) Request/Response contract

### Request
```json
{
  "message": "Giải thích Python list comprehension",
  "locale": "vi-VN",
  "channel": "web",
  "model": "gpt-4o-mini"
}
```

### Response success
```json
{
  "request_id": "req_123",
  "status": "ok",
  "answer": "List comprehension là...",
  "error": null,
  "meta": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "finish_reason": "stop"
  }
}
```

### Response error
```json
{
  "request_id": "req_123",
  "status": "error",
  "answer": "Xin lỗi, hệ thống đang bận. Bạn thử lại giúp mình.",
  "error": {
    "code": "MODEL_ERROR",
    "message": "Provider timeout"
  },
  "meta": {
    "provider": null,
    "model": null,
    "finish_reason": null
  }
}
```

## 4) Error code + HTTP mapping
- `BAD_REQUEST` -> 400
- `UNSUPPORTED_MODEL` -> 400
- `MODEL_ERROR` -> 502
- `MODEL_EMPTY_OUTPUT` -> 502
- `INTERNAL_ERROR` -> 500

## 5) API
- `POST /chat`
- `GET /models`
- `GET /health`
- `GET /ready`

## 6) DoD
- Chọn model theo request hoạt động đúng.
- `/models` phản ánh đúng registry runtime.
- `/chat` trả đúng schema ở cả success/error.
- Có unit test cho 5 bước + integration test cho `/chat`.