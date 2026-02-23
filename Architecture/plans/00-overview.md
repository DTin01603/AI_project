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
