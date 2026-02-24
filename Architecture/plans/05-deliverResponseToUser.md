# deliverResponseToUser()

## 0) Metadata
- Owner: Backend Team
- Version: 2.0

## 1) Mục tiêu
- Map payload nội bộ sang HTTP response nhất quán.

## 2) HTTP mapping
- `status=ok` -> 200
- `error.code in [BAD_REQUEST, UNSUPPORTED_MODEL]` -> 400
- `error.code in [MODEL_ERROR, MODEL_EMPTY_OUTPUT]` -> 502
- còn lại -> 500

## 3) Flow
1. Nhận `final_response`.
2. Chọn HTTP status theo mapping.
3. Trả JSON + `Content-Type: application/json`.
4. Log `request_id`, status code, latency.

## 4) Endpoints vận hành
- `GET /health` -> 200 `{ "status": "ok" }`
- `GET /ready` -> 200/503 tùy dependency/config model.

## 5) Unit/Integration tests bắt buộc
- `/chat` success 200.
- bad request/model không hỗ trợ -> 400.
- model error/empty -> 502.
- unexpected error -> 500.
- `/health`, `/ready` đúng semantics.