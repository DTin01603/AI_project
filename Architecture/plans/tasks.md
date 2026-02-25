# Kế hoạch Triển khai - Hệ thống Chat AI Đa Model

## Tổng quan

Triển khai full-stack application bao gồm FastAPI backend với LangChain integration và React frontend. Backend sử dụng pipeline 5 bước tuần tự để xử lý chat requests, tích hợp với Google Gemini API. Frontend cung cấp giao diện web đơn giản cho người dùng tương tác với chat API.

**Tech Stack**:
- Backend: Python 3.11+, FastAPI, LangChain, Pydantic
- Frontend: React 18, Vite, Axios
- Testing: pytest, hypothesis, pytest-cov
- Provider: Google Gemini (gemini-1.5-flash, gemini-1.5-pro)

## Tasks

- [ ] 1. Setup project structure và dependencies
  - [ ] 1.1 Tạo cấu trúc thư mục backend
    - Tạo thư mục `backend/` với các subdirectories: `src/`, `tests/`, `tests/unit/`, `tests/property/`, `tests/integration/`
    - Tạo `src/` với các modules: `models/`, `services/`, `adapters/`, `registry/`, `utils/`
    - _Yêu cầu: Tất cả requirements_
  
  - [ ] 1.2 Tạo cấu trúc thư mục frontend
    - Tạo thư mục `frontend/` với React + Vite
    - Tạo `src/` với các subdirectories: `components/`, `services/`
    - _Yêu cầu: 12.1_
  
  - [ ] 1.3 Setup backend dependencies
    - Tạo `requirements.txt` với: fastapi, uvicorn, pydantic, pydantic-settings, langchain, langchain-google-genai, structlog, python-dotenv
    - Tạo `requirements-dev.txt` với: pytest, pytest-cov, pytest-mock, hypothesis, black, ruff, mypy
    - Tạo `.env.example` với các biến môi trường cần thiết
    - _Yêu cầu: 8.1, 8.5, 8.6, 8.7_
  
  - [ ] 1.4 Setup frontend dependencies
    - Tạo `package.json` với: react, react-dom, axios, vite
    - Tạo `.env.example` với VITE_API_BASE_URL
    - Cấu hình Vite trong `vite.config.js`
    - _Yêu cầu: 12.1, 12.9_

- [ ] 2. Implement backend data models
  - [ ] 2.1 Tạo Pydantic request/response schemas
    - Tạo `src/models/request.py` với `ChatRequest` model (message, locale, channel, model)
    - Tạo `src/models/response.py` với `ChatResponse`, `ErrorDetail`, `ResponseMeta` models
    - Thêm validators cho message (không rỗng, max 4000 ký tự, type string)
    - _Yêu cầu: 1.1, 1.2, 1.3, 10.1, 10.6_
  
  - [ ] 2.2 Tạo internal data models
    - Tạo `src/models/internal.py` với dataclasses: `CapturedQuestion`, `NormalizedRequest`, `Constraints`, `RequestMeta`, `ModelResult`, `TokenUsage`, `FinalResponse`
    - _Yêu cầu: 1.7, 2.8, 4.8, 4.9_
  
  - [ ] 2.3 Tạo error code definitions
    - Tạo `src/utils/errors.py` với enum `ErrorCode` (BAD_REQUEST, UNSUPPORTED_MODEL, MODEL_ERROR, MODEL_EMPTY_OUTPUT, INTERNAL_ERROR)
    - Tạo custom exception classes: `ValidationError`, `ModelError`
    - _Yêu cầu: 1.6, 2.7, 4.6, 4.7, 6.1-6.5_

- [ ] 3. Implement configuration và logging
  - [ ] 3.1 Tạo Settings với Pydantic
    - Tạo `src/config.py` với `Settings` class sử dụng `pydantic-settings`
    - Đọc environment variables: GOOGLE_API_KEY, GOOGLE_TIMEOUT, DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_OUTPUT_TOKENS, LOG_LEVEL
    - Validate API key format khi khởi động
    - _Yêu cầu: 8.1, 8.2, 8.5, 8.6, 8.7_
  
  - [ ] 3.2 Setup structured logging
    - Tạo `src/utils/logging.py` với structlog configuration
    - Configure JSON output format với timestamp, log level, request_id binding
    - Implement helper functions để log không chứa sensitive data
    - _Yêu cầu: 9.6, 9.7, 9.8, 10.4_

- [ ] 4. Implement Model Registry
  - [ ] 4.1 Tạo ModelRegistry class
    - Tạo `src/registry/model_registry.py` với `ModelInfo` dataclass (name, provider, available, adapter_class)
    - Implement methods: `register_model()`, `has_model()`, `get_adapter()`, `list_models()`, `get_available_count()`
    - _Yêu cầu: 3.1, 3.2, 3.6_
  
  - [ ] 4.2 Implement registry initialization
    - Tạo `initialize_registry()` function đọc settings và register Google models nếu API key hợp lệ
    - Log warning nếu API key thiếu hoặc không hợp lệ
    - Đánh dấu model available=false nếu provider không khả dụng
    - _Yêu cầu: 3.3, 3.5, 8.3, 8.4_

- [ ] 5. Implement adapter pattern
  - [ ] 5.1 Tạo BaseAdapter interface
    - Tạo `src/adapters/base.py` với abstract class `BaseAdapter`
    - Define abstract methods: `provider_name` property, `get_llm()` method
    - _Yêu cầu: 4.1, 4.2_
  
  - [ ] 5.2 Implement GoogleAdapter
    - Tạo `src/adapters/google_adapter.py` implement `BaseAdapter`
    - Sử dụng `ChatGoogleGenerativeAI` từ langchain-google-genai
    - Configure timeout và request options
    - _Yêu cầu: 3.3, 4.2, 8.5_

- [ ] 6. Implement pipeline services
  - [ ] 6.1 Implement CaptureQuestionService
    - Tạo `src/services/capture_question.py` với class `CaptureQuestionService`
    - Validate message type là string
    - Normalize newline từ CRLF sang LF
    - Trim whitespace ở đầu và cuối
    - Validate message không rỗng sau trim
    - Validate message length <= 4000 ký tự
    - Raise ValidationError với BAD_REQUEST nếu invalid
    - Return `CapturedQuestion` với received_at timestamp
    - _Yêu cầu: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 10.6_
  
  - [ ]* 6.2 Write property test cho CaptureQuestionService
    - **Property 1: Message whitespace validation**
    - **Property 2: Message newline normalization**
    - **Property 3: Message trimming**
    - **Property 4: Invalid request error handling**
    - **Property 5: Request timestamp recording**
    - **Validates: Yêu cầu 1.2, 1.4, 1.5, 1.6, 1.7**
  
  - [ ]* 6.3 Write unit tests cho CaptureQuestionService
    - Test valid message với trim
    - Test empty message → BAD_REQUEST
    - Test whitespace-only message → BAD_REQUEST
    - Test message quá dài → BAD_REQUEST
    - Test wrong type → BAD_REQUEST
    - Test newline normalization
    - _Yêu cầu: 11.1_
  
  - [ ] 6.4 Implement NormalizeRequestService
    - Tạo `src/services/normalize_request.py` với class `NormalizeRequestService`
    - Resolve request_id từ header hoặc sinh UUID mới
    - Resolve locale default "vi-VN", normalize thành lowercase
    - Resolve channel default "web", reject nếu khác "web"
    - Resolve model từ settings nếu không có, validate tồn tại trong registry
    - Set constraints: temperature=0.3, max_output_tokens=500
    - Raise ValidationError với appropriate error code nếu invalid
    - Return `NormalizedRequest`
    - _Yêu cầu: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 10.7_
  
  - [ ]* 6.5 Write property test cho NormalizeRequestService
    - **Property 6: Request ID preservation**
    - **Property 7: Request ID generation**
    - **Property 8: Default values resolution**
    - **Property 9: Channel validation**
    - **Property 10: Model registry validation**
    - **Property 11: Constraints initialization**
    - **Property 12: Locale normalization**
    - **Validates: Yêu cầu 2.1-2.9**
  
  - [ ]* 6.6 Write unit tests cho NormalizeRequestService
    - Test default locale vi-VN
    - Test default channel web
    - Test default model từ settings
    - Test giữ nguyên model hợp lệ
    - Test reject channel khác web → BAD_REQUEST
    - Test reject model không hỗ trợ → UNSUPPORTED_MODEL
    - Test locale normalization
    - Test request ID từ header
    - Test request ID generation
    - _Yêu cầu: 11.2_
  
  - [ ] 6.7 Implement InvokeModelsWithContextService
    - Tạo `src/services/invoke_models.py` với class `InvokeModelsWithContextService`
    - Lookup adapter từ registry dựa trên model name
    - Build prompt với LangChain `ChatPromptTemplate`: system message "Bạn là trợ lý AI hữu ích, trả lời ngắn gọn và đúng ngôn ngữ user."
    - Invoke model với constraints (temperature, max_tokens)
    - Parse response và extract answer_text, finish_reason, usage (input_tokens, output_tokens)
    - Validate output không rỗng
    - Catch timeout/connection errors → MODEL_ERROR
    - Catch empty output → MODEL_EMPTY_OUTPUT
    - Return `ModelResult`
    - _Yêu cầu: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_
  
  - [ ]* 6.8 Write property test cho InvokeModelsWithContextService
    - **Property 15: Adapter lookup**
    - **Property 16: Prompt template consistency**
    - **Property 17: Model invocation parameters**
    - **Property 18: Model error handling**
    - **Property 19: Empty output validation**
    - **Property 20: Model result structure**
    - **Validates: Yêu cầu 4.1, 4.3, 4.4, 4.6, 4.7, 4.8, 4.9**
  
  - [ ]* 6.9 Write unit tests cho InvokeModelsWithContextService
    - Test happy path với mock adapter
    - Test provider timeout → MODEL_ERROR
    - Test provider error → MODEL_ERROR
    - Test empty output → MODEL_EMPTY_OUTPUT
    - Test unsupported model → UNSUPPORTED_MODEL
    - Test prompt template có system message
    - Test parameters được truyền đúng
    - _Yêu cầu: 11.3_
  
  - [ ] 6.10 Implement ComposeResponseService
    - Tạo `src/services/compose_response.py` với class `ComposeResponseService`
    - Implement `compose_success()`: status="ok", answer, error=null, meta với provider/model/finish_reason
    - Implement `compose_error()`: status="error", friendly answer message, error với code/message, meta với null values
    - Truncate answer nếu > 3000 ký tự
    - Map error codes sang friendly Vietnamese messages
    - Không expose debug info hoặc stacktrace
    - Return `FinalResponse`
    - _Yêu cầu: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_
  
  - [ ]* 6.11 Write property test cho ComposeResponseService
    - **Property 21: Success response structure**
    - **Property 22: Error response structure**
    - **Property 23: Answer truncation**
    - **Property 24: Error message mapping**
    - **Property 25: No debug information exposure**
    - **Validates: Yêu cầu 5.1-5.8**
  
  - [ ]* 6.12 Write unit tests cho ComposeResponseService
    - Test success response đúng schema
    - Test error response đúng schema
    - Test luôn có request_id
    - Test truncate answer > 3000 ký tự
    - Test error message mapping cho từng error code
    - Test không có debug info trong error response
    - _Yêu cầu: 11.4_
  
  - [ ] 6.13 Implement DeliverResponseService
    - Tạo `src/services/deliver_response.py` với class `DeliverResponseService`
    - Map status="ok" → HTTP 200
    - Map error codes: BAD_REQUEST/UNSUPPORTED_MODEL → 400, MODEL_ERROR/MODEL_EMPTY_OUTPUT → 502, INTERNAL_ERROR → 500
    - Set Content-Type application/json
    - Log request_id, HTTP status, latency
    - Log error code và message nếu có lỗi
    - Không log full message content hoặc API keys
    - Return FastAPI `JSONResponse`
    - _Yêu cầu: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8, 9.7, 9.8_
  
  - [ ]* 6.14 Write property test cho DeliverResponseService
    - **Property 26: HTTP status code mapping**
    - **Property 27: No model fallback**
    - **Property 28: JSON content type**
    - **Property 29: Request logging completeness**
    - **Validates: Yêu cầu 6.1-6.8**
  
  - [ ]* 6.15 Write unit tests cho DeliverResponseService
    - Test status ok → HTTP 200
    - Test BAD_REQUEST → HTTP 400
    - Test UNSUPPORTED_MODEL → HTTP 400
    - Test MODEL_ERROR → HTTP 502
    - Test MODEL_EMPTY_OUTPUT → HTTP 502
    - Test INTERNAL_ERROR → HTTP 500
    - Test Content-Type application/json
    - Test logging với request_id, status, latency
    - _Yêu cầu: 11.5_

- [ ] 7. Implement FastAPI endpoints
  - [ ] 7.1 Tạo FastAPI application
    - Tạo `src/main.py` với FastAPI app instance
    - Configure CORS middleware cho frontend (allow origins từ settings)
    - Setup startup event để initialize registry
    - Setup exception handlers cho ValidationError, ModelError, Exception
    - _Yêu cầu: 10.5, 12.9_
  
  - [ ] 7.2 Implement POST /chat endpoint
    - Tạo endpoint nhận `ChatRequest`, trả về `ChatResponse`
    - Extract x-request-id từ header
    - Gọi pipeline 5 bước tuần tự: capture → normalize → invoke → compose → deliver
    - Log tại mỗi bước với request_id
    - Log timing cho mỗi bước
    - Handle exceptions và return appropriate error response
    - _Yêu cầu: 1.1, 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [ ] 7.3 Implement GET /models endpoint
    - Tạo endpoint trả về danh sách models từ registry
    - Format: `{"models": [{"name": str, "provider": str, "available": bool}]}`
    - Return HTTP 200
    - _Yêu cầu: 3.1, 3.4_
  
  - [ ] 7.4 Implement GET /health endpoint
    - Tạo endpoint trả về `{"status": "ok", "uptime_seconds": float}`
    - Calculate uptime từ startup time
    - Return HTTP 200
    - _Yêu cầu: 7.1, 7.2_
  
  - [ ] 7.5 Implement GET /ready endpoint
    - Tạo endpoint kiểm tra registry có ít nhất 1 model available
    - Nếu có: return HTTP 200 với `{"status": "ready", "available_models": int}`
    - Nếu không: return HTTP 503 với `{"status": "not_ready", "available_models": 0, "reason": str}`
    - Không ping provider thật
    - _Yêu cầu: 7.3, 7.4, 7.5, 7.6, 7.7_
  
  - [ ]* 7.6 Write integration tests cho POST /chat
    - Test success case với mock Google adapter
    - Test invalid input → HTTP 400
    - Test unsupported model → HTTP 400
    - Test model error → HTTP 502
    - Test response schema đúng
    - _Yêu cầu: 11.6_
  
  - [ ]* 7.7 Write integration tests cho GET /models
    - Test trả về danh sách models
    - Test response schema đúng
    - _Yêu cầu: 11.7_
  
  - [ ]* 7.8 Write integration tests cho GET /health và /ready
    - Test /health trả về status ok và uptime
    - Test /ready với models available → HTTP 200
    - Test /ready không có models → HTTP 503
    - _Yêu cầu: 11.8_

- [ ] 8. Checkpoint - Backend hoàn thành
  - Đảm bảo tất cả unit tests và integration tests pass
  - Kiểm tra test coverage >= 80%
  - Hỏi user nếu có câu hỏi hoặc cần clarification

- [ ] 9. Implement React frontend
  - [ ] 9.1 Setup React project với Vite
    - Chạy `npm create vite@latest frontend -- --template react`
    - Cấu hình `vite.config.js` với proxy tới backend nếu cần
    - Tạo `.env` với VITE_API_BASE_URL
    - _Yêu cầu: 12.1_
  
  - [ ] 9.2 Tạo API service layer
    - Tạo `src/services/api.js` với axios client
    - Implement `fetchModels()` gọi GET /models
    - Implement `sendMessage(message, model)` gọi POST /chat
    - Implement `checkHealth()` gọi GET /health
    - Handle errors và timeout
    - _Yêu cầu: 12.4, 12.9_
  
  - [ ] 9.3 Implement App.jsx root component
    - Tạo `src/App.jsx` với header "AI Chat Assistant"
    - Render `ChatInterface` component
    - Import và apply CSS
    - _Yêu cầu: 12.2_
  
  - [ ] 9.4 Implement ChatInterface component
    - Tạo `src/components/ChatInterface.jsx`
    - State: messages, selectedModel, availableModels, isLoading, error
    - useEffect on mount: fetch models từ API
    - handleSendMessage: gọi sendMessage API, update messages state
    - Render ModelSelector, MessageList, error message, MessageInput
    - _Yêu cầu: 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.11_
  
  - [ ] 9.5 Implement MessageList component
    - Tạo `src/components/MessageList.jsx`
    - Props: messages, isLoading
    - Render messages với role-based styling (user vs assistant)
    - Auto-scroll tới bottom khi có message mới
    - Hiển thị loading indicator khi isLoading=true
    - _Yêu cầu: 12.2, 12.5_
  
  - [ ] 9.6 Implement MessageInput component
    - Tạo `src/components/MessageInput.jsx`
    - Props: onSend, disabled
    - State: inputValue
    - Validate message không rỗng trước khi gửi
    - Disable input khi isLoading
    - Clear input sau khi gửi
    - maxLength 4000 ký tự
    - _Yêu cầu: 12.2, 12.12_
  
  - [ ] 9.7 Implement ModelSelector component
    - Tạo `src/components/ModelSelector.jsx`
    - Props: models, selectedModel, onModelChange
    - Render dropdown với available models
    - Display format: "model-name (provider)"
    - _Yêu cầu: 12.3_
  
  - [ ] 9.8 Implement responsive CSS styling
    - Tạo `src/App.css` với styles cho tất cả components
    - Responsive design cho desktop và mobile
    - User messages align right, assistant messages align left
    - Loading indicator animation
    - Error message styling
    - _Yêu cầu: 12.10_

- [ ] 10. Integration và testing
  - [ ] 10.1 Test frontend với backend local
    - Start backend server: `uvicorn src.main:app --reload`
    - Start frontend dev server: `npm run dev`
    - Test gửi message và nhận response
    - Test chọn model khác nhau
    - Test error handling (invalid input, model error)
    - _Yêu cầu: 12.4, 12.6, 12.7_
  
  - [ ] 10.2 Verify CORS configuration
    - Kiểm tra frontend có thể gọi backend API
    - Kiểm tra preflight requests hoạt động
    - _Yêu cầu: 12.9_
  
  - [ ]* 10.3 Run full test suite
    - Chạy backend unit tests: `pytest tests/unit -v`
    - Chạy backend property tests: `pytest tests/property -v`
    - Chạy backend integration tests: `pytest tests/integration -v`
    - Kiểm tra coverage: `pytest --cov=src --cov-report=term`
    - _Yêu cầu: 11.10_

- [ ] 11. Documentation và deployment setup
  - [ ] 11.1 Tạo README.md
    - Project overview và features
    - Tech stack
    - Prerequisites (Python 3.11+, Node.js 18+)
    - Installation instructions
    - Environment variables setup
    - Running backend và frontend
    - API documentation links
    - Testing instructions
  
  - [ ] 11.2 Tạo Docker setup
    - Tạo `backend/Dockerfile` cho FastAPI app
    - Tạo `frontend/Dockerfile` cho React app
    - Tạo `docker-compose.yml` để chạy cả backend và frontend
    - Configure environment variables trong docker-compose
  
  - [ ] 11.3 Tạo API documentation
    - FastAPI tự động generate OpenAPI docs tại /docs
    - Verify /docs endpoint hoạt động
    - Thêm descriptions cho endpoints và models

- [ ] 12. Final checkpoint
  - Đảm bảo tất cả tests pass
  - Verify frontend và backend integration hoạt động
  - Kiểm tra error handling end-to-end
  - Review code quality và documentation
  - Hỏi user nếu cần thêm features hoặc improvements

## Ghi chú

- Tasks đánh dấu `*` là optional và có thể skip để nhanh chóng có MVP
- Mỗi task tham chiếu đến requirements cụ thể để đảm bảo traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples và edge cases
- Integration tests validate end-to-end flows
- Checkpoints đảm bảo validation tăng dần
