# normalizeRequest()

## 0) Metadata
- Owner: Backend Team
- Version: 2.0

## 1) Mục tiêu
- Chuẩn hóa request thành schema nội bộ.
- Resolve model cần dùng từ request hoặc default config.

## 2) Input
- `captured_question`
- header `x-request-id` (optional)
- `model_registry` (danh sách model hỗ trợ)

## 3) Rules
- `request_id`: ưu tiên `x-request-id`, nếu thiếu thì sinh UUID.
- `locale`: default `vi-VN`.
- `channel`: default `web`, chỉ cho `web`.
- `model`: default `settings.default_model` nếu thiếu.
- Nếu `model` không có trong registry -> `UNSUPPORTED_MODEL`.

## 4) Output
```json
{
  "request_id": "req_01HT...",
  "message": "Tôi cần học FastAPI",
  "locale": "vi-VN",
  "channel": "web",
  "model": "gpt-4o-mini",
  "constraints": {
    "temperature": 0.3,
    "max_output_tokens": 500
  },
  "meta": {
    "received_at": "2026-02-24T08:00:00Z"
  }
}
```

## 5) Unit tests bắt buộc
- default locale/channel/model.
- giữ nguyên model hợp lệ.
- reject channel != web.
- reject model không hỗ trợ.