# invokeModelsWithContext()

## 1) Mục tiêu
- Gọi model với request đã chuẩn hóa.
- Trả về kết quả text có cấu trúc tối thiểu cho composeResponse.
- Đảm bảo lỗi model được bắt và map về mã lỗi nội bộ.

## 2) Phạm vi MVP
- Không gọi retrieval.
- Không gọi tool/function calling.
- Không multi-turn memory.

## 3) Đầu vào
```json
{
	"request_id": "req_01HT...",
	"message": "Tôi cần gợi ý học Python",
	"locale": "vi-VN",
	"channel": "web",
	"constraints": {
		"max_output_tokens": 500,
		"temperature": 0.3
	}
}
```

## 4) Prompt template MVP
```text
System: Bạn là trợ lý AI hữu ích, trả lời ngắn gọn, rõ ràng, đúng ngôn ngữ người dùng.
User: {{message}}
```

## 5) Đầu ra
```json
{
	"request_id": "req_01HT...",
	"model": "<provider-model-name>",
	"answer_text": "Bạn có thể bắt đầu bằng việc...",
	"finish_reason": "stop",
	"usage": {
		"input_tokens": 120,
		"output_tokens": 180
	}
}
```

## 6) Luồng xử lý chi tiết
1. Tạo prompt từ `message`.
2. Gọi model client với `temperature`, `max_output_tokens`.
3. Validate `answer_text` không rỗng.
4. Chuẩn hóa metadata (`model`, `usage`, `finish_reason`).
5. Trả về object kết quả.

## 7) Chiến lược lỗi MVP
- Timeout/provider error -> thử lại 1 lần (retry 1).
- Nếu vẫn fail -> trả `MODEL_ERROR` cho bước compose.
- Nếu output rỗng -> map `MODEL_EMPTY_OUTPUT`.

## 8) Logging tối thiểu
- `request_id`, model name, latency ms, token usage.
- Không log full prompt nếu không cần.

## 9) Unit test bắt buộc
- Model client trả output hợp lệ -> pass.
- Provider throw exception -> retry và map lỗi đúng.
- Output rỗng -> fail đúng mã lỗi.

## 10) Definition of Done
- Gọi model thành công với request hợp lệ.
- Có mapping lỗi nhất quán cho timeout/provider/empty output.
- Unit test pass cho 3 nhóm case chính.

## 11) API liên quan

### LangChain APIs
- `ChatPromptTemplate.from_messages(...)`: build prompt từ system + user message.
- `ChatOpenAI(model=..., temperature=...)` (hoặc provider tương đương): tạo model client.
- `llm.invoke(messages)`: gọi model non-streaming.

Ví dụ luồng gọi tối thiểu:
```python
prompt = ChatPromptTemplate.from_messages([
	("system", "Bạn là trợ lý AI hữu ích, trả lời ngắn gọn."),
	("human", "{message}")
])
messages = prompt.format_messages(message=normalized_request.message)
result = llm.invoke(messages)
```

### Service API nội bộ
- `invokeModelsWithContext(normalized: NormalizedRequest) -> ModelResult`

### LangGraph node (nếu dùng graph)
- Node tên `invoke_model`.
- Input state: `normalized_request`.
- Output state thêm: `model_result` hoặc `error`.
