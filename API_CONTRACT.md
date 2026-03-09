# API Contract Policy

Tài liệu này chốt contract backend hiện tại cho chat API.

## 1) Endpoint chính thức

- Primary endpoint: `POST /api/v2/chat`
- Query param: `stream` (`false` mặc định)
  - `stream=false`: trả JSON `ChatResponse`
  - `stream=true`: trả SSE `text/event-stream`

## 2) Versioning policy

- API version hiện tại: `v2`.
- Tất cả response từ `/api/v2/chat` phải có header: `x-api-version: 2`.
- Bất kỳ thay đổi breaking nào trong request/response phải tạo version mới (`/api/v3/chat`), không sửa breaking trực tiếp trên v2.
- Thay đổi non-breaking (thêm field optional) được phép trong v2.

## 3) Request schema (v2)

```json
{
  "message": "string, required",
  "conversation_id": "string, optional",
  "locale": "string, optional",
  "channel": "string, optional",
  "model": "string, optional"
}
```

## 4) JSON response schema (stream=false)

```json
{
  "request_id": "string",
  "conversation_id": "string|null",
  "status": "ok|error",
  "answer": "string",
  "sources": ["string"],
  "error": {
    "code": "string",
    "message": "string"
  },
  "meta": {
    "provider": "string|null",
    "model": "string|null",
    "finish_reason": "string|null"
  }
}
```

## 5) Error policy

### HTTP-level errors (global handlers)

- `400` với payload chuẩn khi request validation fail:
  - `error.code = "BAD_REQUEST"`
- `500` với payload chuẩn khi có unhandled exception:
  - `error.code = "INTERNAL_ERROR"`

### Business/runtime errors trong `/api/v2/chat`

- API vẫn trả payload `ChatResponse` với `status="error"` khi execution fail.
- Mapping lỗi hiện tại:
  - quota/429/timeouts model -> `error.code = "MODEL_ERROR"`
  - lỗi runtime khác -> `error.code = "EXECUTION_ERROR"`

## 6) SSE response contract (stream=true)

- Mỗi event theo format SSE: `data: <json>\n\n`
- Event types:
  - `status`: update tiến độ theo node
  - `done`: kết quả cuối cùng (`answer`, `citations`, `metadata`, `error`)
- Kết thúc stream bằng marker:
  - `data: [DONE]`

## 7) Client integration rule

- Frontend phải dùng một hằng endpoint duy nhất cho chat (`/api/v2/chat`) để tránh drift.
- Không hard-code endpoint cũ `/api/chat` trong code path production.
