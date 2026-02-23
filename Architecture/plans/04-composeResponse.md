# composeResponse()

## 1) Mục tiêu
- Biến kết quả model thành payload cuối cùng để UI render ngay.
- Chuẩn hóa định dạng thành công/thất bại.
- Luôn giữ `request_id` để trace xuyên suốt.

## 2) Đầu vào
```json
{
	"request_id": "req_01HT...",
	"model": "provider-x",
	"answer_text": "Bạn có thể bắt đầu bằng việc...",
	"finish_reason": "stop",
	"usage": {
		"input_tokens": 120,
		"output_tokens": 180
	}
}
```

## 3) Đầu ra thành công
```json
{
	"request_id": "req_01HT...",
	"status": "ok",
	"answer": "Bạn có thể bắt đầu bằng việc...",
	"error": null,
	"meta": {
		"model": "provider-x",
		"finish_reason": "stop"
	}
}
```

## 4) Đầu ra thất bại
```json
{
	"request_id": "req_01HT...",
	"status": "error",
	"answer": "Xin lỗi, hệ thống tạm thời gặp sự cố. Bạn thử lại giúp mình.",
	"error": {
		"code": "MODEL_ERROR",
		"message": "Model invocation failed"
	},
	"meta": {
		"model": null,
		"finish_reason": null
	}
}
```

## 5) Luồng xử lý chi tiết
1. Kiểm tra object model output có hợp lệ hay không.
2. Nếu thành công: đưa `answer_text` vào trường `answer`.
3. Nếu thất bại: set `status=error`, gán fallback message để UI luôn có text hiển thị.
4. Bổ sung `meta` tối thiểu (model, finish_reason).
5. Trả response payload thống nhất cho bước deliver.

## 6) Quy tắc format MVP
- Không thêm markdown phức tạp.
- Giữ answer ngắn gọn, không bao gồm debug data.
- Nếu text quá dài (> 3000 ký tự), cắt ngưỡng và thêm `...`.

## 7) Unit test bắt buộc
- Có model output -> payload `status=ok` đúng schema.
- Không có model output -> payload `status=error` + fallback text.
- Luôn có `request_id` trong mọi response.

## 8) Definition of Done
- UI có thể render được cả 2 trạng thái success/error không cần if-else phức tạp.
- Response schema ổn định và backward-compatible trong MVP.
