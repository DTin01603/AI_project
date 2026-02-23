# deliverResponseToUser()

## 1) Mục tiêu
- Gửi payload cuối từ backend về UI qua HTTP.
- Đảm bảo mã trạng thái HTTP nhất quán với `status` trong payload.
- Có fallback khi xảy ra lỗi không dự kiến ở tầng transport.

## 2) Đầu vào
`response_payload` từ `composeResponse`.

## 3) Mapping HTTP cho MVP
- `status = ok` -> HTTP 200.
- `status = error` va `error.code = BAD_REQUEST` -> HTTP 400.
- `status = error` va `error.code = MODEL_ERROR` -> HTTP 502.
- `status = error` và lỗi khác -> HTTP 500.

## 4) Luồng xử lý chi tiết
1. Nhận `response_payload`.
2. Xác định HTTP status code theo bảng mapping trên.
3. Gán header cơ bản (`Content-Type: application/json`).
4. Trả body JSON cho client.
5. Log kết quả giao nhận (`request_id`, status code, latency).

## 5) Tình huống lỗi transport
- Nếu serialization lỗi -> trả HTTP 500 với payload error tối thiểu.
- Nếu kết nối client ngắt giữa chừng -> log warning, không retry ở server.

## 6) Unit test bắt buộc
- Payload thành công -> HTTP 200 + schema đúng.
- Payload `BAD_REQUEST` -> HTTP 400.
- Payload `MODEL_ERROR` -> HTTP 502.
- Payload không hợp lệ -> HTTP 500 fallback.

## 7) Definition of Done
- Mapping HTTP rõ ràng và được test đầy đủ.
- UI nhận được JSON nhất quán cho mọi tình huống.
- Log có đủ thông tin để debug một request từ đầu đến cuối.

## 8) API liên quan

### FastAPI route chính
- `@app.post("/chat", response_model=ChatResponse)`
- Handler gọi tuần tự:
	1. `captureQuestion`
	2. `normalizeRequest`
	3. `invokeModelsWithContext`
	4. `composeResponse`
	5. trả HTTP response theo mapping lỗi

### Mapping status code trong handler
- `status=ok` -> `200 OK`
- `error.code=BAD_REQUEST` -> `400 Bad Request`
- `error.code=MODEL_ERROR` -> `502 Bad Gateway`
- lỗi còn lại -> `500 Internal Server Error`

### FastAPI endpoints vận hành
- `GET /health`: kiểm tra process sống.
- `GET /ready`: kiểm tra service sẵn sàng nhận traffic.

### LangGraph terminal node (nếu dùng graph)
- Node tên `deliver_response`.
- Input state: `final_response`.
- Output: object trả về cho FastAPI layer.
