# captureQuestion()

## 1) Mục tiêu
- Nhận dữ liệu message thuần từ UI/API.
- Loại bỏ nhiễu dữ liệu rác tối thiểu để tránh lỗi sớm.
- Tạo object đầu vào ban đầu có metadata cơ bản cho các bước sau.

## 2) Input contract
```json
{
	"message": "  Tôi cần gợi ý học Python  ",
	"locale": "vi-VN",
	"channel": "web"
}
```

### Quy tắc validate
- `message` bắt buộc là string.
- Sau khi trim, `message` không được rỗng.
- Độ dài `message` <= 4000 ký tự (MVP).
- `locale`, `channel` là optional; nếu thiếu sẽ để bước normalizeRequest gán mặc định.

## 3) Output contract
```json
{
	"raw_message": "Tôi cần gợi ý học Python",
	"locale": "vi-VN",
	"channel": "web",
	"received_at": "2026-02-23T08:00:00Z"
}
```

## 4) Luồng xử lý chi tiết
1. Đọc body request từ API.
2. Lấy `message` và trim space đầu/cuối.
3. Chuẩn hóa xuống dòng (`\r\n` -> `\n`).
4. Kiểm tra rỗng và giới hạn độ dài.
5. Tạo payload kết quả kèm timestamp.

## 5) Pseudocode
```text
if message is not string: raise BAD_REQUEST
msg = trim(message)
msg = normalize_newline(msg)
if msg is empty: raise BAD_REQUEST
if len(msg) > 4000: raise BAD_REQUEST
return { raw_message: msg, locale, channel, received_at }
```

## 6) Lỗi và cách trả về
- Empty message -> `BAD_REQUEST`, thông điệp: "message must not be empty".
- Message quá dài -> `BAD_REQUEST`, thông điệp: "message exceeds max length".
- Sai kiểu dữ liệu -> `BAD_REQUEST`, thông điệp: "message must be a string".

## 7) Logging tối thiểu
- Log `request_id` (nếu đã có), `channel`, `message_length`.
- Không log full message nếu chưa cần thiết (tránh lộ dữ liệu nhạy cảm).

## 8) Unit test bắt buộc
- Nhập hợp lệ -> pass và được trim.
- Nhập toàn khoảng trắng -> fail `BAD_REQUEST`.
- Nhập > 4000 ký tự -> fail `BAD_REQUEST`.
- Nhập kiểu khác string -> fail `BAD_REQUEST`.

## 9) Definition of Done
- Hàm trả về payload đúng schema đã định nghĩa.
- Tất cả case validate lỗi trả về mã lỗi nhất quán.
- Unit test xanh cho 4 nhóm case trên.

## 10) API liên quan

### FastAPI
- Dùng body model `ChatRequest` cho endpoint `POST /chat`.
- Validate ở ranh giới API trước khi vào pipeline.

Ví dụ schema:
```python
class ChatRequest(BaseModel):
	message: str
	locale: str | None = "vi-VN"
	channel: str | None = "web"
```

### Service API nội bộ
- `captureQuestion(payload: ChatRequest | dict) -> CapturedQuestion`

### LangGraph node (nếu dùng graph)
- Node tên `capture_question`.
- Input state tối thiểu: `message`, `locale`, `channel`.
- Output state thêm: `captured_question`.
