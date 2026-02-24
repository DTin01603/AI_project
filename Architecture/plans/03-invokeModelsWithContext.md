# invokeModelsWithContext()

## 0) Metadata
- Owner: Backend Team
- Version: 2.0

## 1) Mục tiêu
- Gọi đúng adapter theo model đã chọn.
- Trả `ModelResult` thống nhất, độc lập provider.

## 2) MVP model registry (ví dụ)
- `gpt-4o-mini` -> OpenAI adapter
- `gpt-4.1-mini` -> OpenAI adapter
- `gemini-2.5-flash` -> Google adapter

## 3) Prompt template
- System: "Bạn là trợ lý AI hữu ích, trả lời ngắn gọn và đúng ngôn ngữ user."
- User: `{message}`

## 4) Flow
1. Resolve adapter từ `normalized.model`.
2. Build prompt bằng LangChain.
3. Invoke non-streaming với constraints.
4. Retry 1 lần nếu timeout/provider transient error.
5. Validate output không rỗng.

## 5) Output
```json
{
  "request_id": "req_01HT...",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "answer_text": "Bạn có thể bắt đầu từ...",
  "finish_reason": "stop",
  "usage": {
    "input_tokens": 100,
    "output_tokens": 140
  }
}
```

## 6) Errors
- provider lỗi/timeout -> `MODEL_ERROR`
- output rỗng -> `MODEL_EMPTY_OUTPUT`
- model không tồn tại trong registry -> `UNSUPPORTED_MODEL`

## 7) Unit tests bắt buộc
- happy path theo từng adapter mock.
- transient error + retry đúng 1 lần.
- empty output.
- unsupported model.