# captureQuestion()

## 0) Metadata
- Owner: Backend Team
- Version: 2.0

## 1) Mục tiêu
- Nhận payload thô từ HTTP.
- Validate message cơ bản, không xử lý business logic model ở bước này.

## 2) Input
```json
{
  "message": "  Tôi cần học FastAPI  ",
  "locale": "vi-VN",
  "channel": "web",
  "model": "gpt-4o-mini"
}
```

## 3) Validate rules
- `message` phải là string.
- Sau trim, `message` không rỗng.
- `len(message) <= 4000`.
- `locale`, `channel`, `model` optional tại bước này.

## 4) Output
```json
{
  "raw_message": "Tôi cần học FastAPI",
  "locale": "vi-VN",
  "channel": "web",
  "model": "gpt-4o-mini",
  "received_at": "2026-02-24T08:00:00Z"
}
```

## 5) Errors
- invalid message -> `BAD_REQUEST`.

## 6) Unit tests bắt buộc
- hợp lệ + trim.
- rỗng.
- quá dài.
- sai kiểu.
- newline normalize `\r\n -> \n`.