# composeResponse()

## 0) Metadata
- Owner: Backend Team
- Version: 2.0

## 1) Mục tiêu
- Chuẩn hóa payload trả UI cho cả success/error.
- Luôn có `request_id`, `status`, `answer`, `error`, `meta`.

## 2) Success response
- `status = ok`
- `answer = answer_text`
- `error = null`
- `meta = { provider, model, finish_reason }`

## 3) Error response
- `status = error`
- `answer` fallback thân thiện.
- `error = { code, message }`
- `meta` vẫn có key nhưng value có thể null.

## 4) Rules
- truncate answer nếu > 3000 ký tự.
- không trả debug/raw stacktrace ra client.

## 5) Unit tests bắt buộc
- success chuẩn schema.
- error chuẩn schema.
- luôn có request_id.
- truncate hoạt động đúng.