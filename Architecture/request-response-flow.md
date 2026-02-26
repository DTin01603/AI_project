# Request-Response Flow

## Tổng quan

Tài liệu này mô tả đường đi từ lúc user gửi câu hỏi ở UI đến lúc agent trả response về frontend.

## Mermaid Flow

```mermaid
---
id: d5bd3a9e-5835-4bb3-b58b-c65269b5a590
---
flowchart TD
  U[User nhập câu hỏi]
  MI[MessageInput onSubmit]
  CI[ChatInterface handleSendMessage]
  API[frontend services api.js sendMessage]
  R1[POST /chat/advanced backend api routers chat.py]
  DEP[api deps get_advanced_chat_use_case]
  UC[application use_cases AdvancedChatUseCase.execute]
  AAS[advanced service AdvancedAgentService.handle_message_with_context]
  CS[services ChatService.handle_message]
  CAP[capture_question.py capture_question]
  NORM[normalize_request.py normalize_request]
  RG[research graph_agent.py invoke]
  IVK[invoke_models.py invoke_models_with_context]
  GAD[adapters google_adapter.py GeminiAdapter.invoke]
  GAPI[Google Generative Language API]
  CMP[compose_response.py compose_success or compose_error]
  DR[deliver_response.py deliver]
  RESP[HTTP JSON response]
  UI[ChatInterface cập nhật messages meta error]

  U --> MI --> CI --> API --> R1 --> DEP --> UC --> AAS
  AAS -->|advanced disabled| CS
  AAS -->|planner memory reflection| CS
  CS --> CAP --> NORM
  NORM --> RG
  RG -->|tool answer có sẵn| CMP
  RG -->|fallback gọi model| IVK
  CS -->|research disabled hoặc không đủ answer| IVK
  IVK --> GAD --> GAPI --> GAD --> IVK --> CMP --> DR --> RESP --> UI

  R1 -.request_id user_id conversation_id.-> AAS
  API -.x-request-id x-user-id x-conversation-id.-> R1

  CMP -->|status ok| DR
  CMP -->|status error BAD_REQUEST UNSUPPORTED_MODEL MODEL_ERROR| DR
```

## Mermaid Sequence

```mermaid
---
id: a712d97d-8761-453f-b01f-4d76704f8151
---
sequenceDiagram
  autonumber
  actor User as User
  participant UI as frontend/components/ChatInterface.jsx
  participant API as frontend/services/api.js
  participant Router as backend/api/routers/chat.py (/chat/advanced)
  participant UseCase as application/use_cases/AdvancedChatUseCase
  participant Agent as advanced/service.py (AdvancedAgentService)
  participant ChatService as services/chat_service.py
  participant Capture as services/capture_question.py
  participant Normalize as services/normalize_request.py
  participant Research as research/graph_agent.py
  participant Invoke as services/invoke_models.py
  participant GeminiAdapter as adapters/google_adapter.py
  participant GeminiAPI as Google Generative Language API
  participant Compose as services/compose_response.py
  participant Deliver as services/deliver_response.py

  User->>UI: Nhập câu hỏi + chọn model + bấm Gửi
  UI->>API: sendMessage(message, model)
  API->>Router: POST /chat/advanced\n(x-request-id, x-user-id, x-conversation-id)
  Router->>UseCase: execute(payload, request_id, user_id, conversation_id)
  UseCase->>Agent: handle_message_with_context(...)
  Agent->>ChatService: handle_message(payload_enriched)
  ChatService->>Capture: capture_question(payload)
  Capture-->>ChatService: CapturedQuestion
  ChatService->>Normalize: normalize_request(captured)
  Normalize-->>ChatService: NormalizedRequest
  ChatService->>Research: invoke(question, model, ...)

  alt Research có câu trả lời trực tiếp
    Research-->>ChatService: final_answer/tool_results
    ChatService->>Compose: compose_success(...)
  else Cần gọi model
    Research-->>ChatService: chưa đủ answer
    ChatService->>Invoke: invoke_models_with_context(normalized)
    Invoke->>GeminiAdapter: invoke(model, messages, constraints)
    GeminiAdapter->>GeminiAPI: generateContent
    GeminiAPI-->>GeminiAdapter: model output / error
    GeminiAdapter-->>Invoke: AdapterOutput / Exception
    Invoke-->>ChatService: ModelResult / MODEL_ERROR
    ChatService->>Compose: compose_success or compose_error
  end

  Compose-->>Agent: ChatResponse
  Agent-->>UseCase: ChatResponse
  UseCase-->>Router: ChatResponse
  Router->>Deliver: deliver(response, latency_ms)
  Deliver-->>API: JSON + HTTP status (200/400/502/500)
  API-->>UI: response + meta + error
  UI-->>User: Hiển thị answer hoặc lỗi
```

## Các điểm chính

- Frontend gửi request tại `frontend/src/services/api.js` với headers `x-request-id`, `x-user-id`, `x-conversation-id`.
- API vào tại route `POST /chat/advanced` trong `backend/src/api/routers/chat.py`.
- `AdvancedAgentService` có thể enrich context (memory/planner/reflection) trước khi gọi `ChatService`.
- `ChatService` chạy pipeline capture -> normalize -> research graph -> invoke model.
- Adapter Gemini (`backend/src/adapters/google_adapter.py`) là nơi gọi provider thật.
- `ComposeResponseService` chuẩn hóa payload trả về, `DeliverResponseService` map status HTTP.
