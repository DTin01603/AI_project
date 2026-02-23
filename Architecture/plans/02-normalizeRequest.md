# normalizeRequest()

## 1) Mục tiêu
- Chuẩn hóa payload đầu vào thành một schema duy nhất để toàn pipeline dùng chung.
- Sinh `request_id` để trace.
- Đặt giá trị mặc định cho field optional.

## 2) Đầu vào (từ captureQuestion)
```json
{
	"raw_message": "Tôi cần gợi ý học Python",
	"locale": "vi-VN",
	"channel": "web",
	"received_at": "2026-02-23T08:00:00Z"
}
```

## 3) Đầu ra (normalized request)
```json
{
	"request_id": "req_01HT...",
	"message": "Tôi cần gợi ý học Python",
	"locale": "vi-VN",
	"channel": "web",
	"constraints": {
		"max_output_tokens": 500,
		"temperature": 0.3
	},
	"meta": {
		"received_at": "2026-02-23T08:00:00Z"
	}
}
```

## 4) Quy tắc chuẩn hóa
- `request_id`: sinh bằng UUID/ULID.
- `message`: map từ `raw_message`.
- `locale`: mặc định `vi-VN` nếu thiếu.
- `channel`: mặc định `web` nếu thiếu; MVP chỉ cho phép `web`.
- `constraints`: đặt hard default để dễ kiểm soát chi phí và độ dài output.

## 5) Luồng xử lý chi tiết
1. Nhận object từ `captureQuestion`.
2. Validate object bắt buộc (`raw_message`, `received_at`).
3. Gán mặc định cho locale/channel nếu cần.
4. Kiểm tra channel có nằm trong tập hỗ trợ (`web`).
5. Tạo `request_id` và object constraints.
6. Trả về normalized request.

## 6) Lỗi và cách xử lý
- Missing field bắt buộc -> `BAD_REQUEST`.
- Channel không hỗ trợ -> `BAD_REQUEST` ("unsupported channel").
- Lỗi tạo `request_id` (hiếm) -> `INTERNAL_ERROR`.

## 7) Unit test bắt buộc
- Input hợp lệ -> output đúng schema.
- Thiếu locale/channel -> được gán mặc định.
- Channel khác `web` -> fail `BAD_REQUEST`.
- Kiểm tra có `request_id` và `constraints` sau normalize.

## 8) Definition of Done
- Tiếp nhận được input từ bước trước và sinh schema ổn định cho bước model.
- Tất cả field đầu ra được type rõ ràng.
- Test pass cho defaulting + validation + unsupported channel.
