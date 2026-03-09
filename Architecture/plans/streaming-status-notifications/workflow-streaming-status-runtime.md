# Streaming Status Workflow (Runtime)

Luồng dưới đây mô tả đúng trình tự thực thi của chức năng streaming status trong code hiện tại (backend + frontend).

```mermaid
sequenceDiagram
    autonumber
    participant UI as Frontend UI
    participant Hook as useSSEStream
    participant API as /chat/stream router
    participant SSE as SSEStreamManager
    participant ORCH as StreamingOrchestrator
    participant PRS as Parser
    participant CA as ComplexityAnalyzer
    participant PA as PlanningAgent
    participant RT as ResearchTool
    participant RC as ResponseComposer
    participant LLM as DirectLLM

    UI->>Hook: submit message
    Hook->>API: POST /chat/stream (Accept: text/event-stream)
    API->>SSE: create_stream(request_id)
    SSE-->>Hook: StreamingResponse opened
    API->>SSE: emit connection_established
    API->>ORCH: process_request_stream(payload)

    ORCH->>SSE: emit parsing_request
    ORCH->>PRS: parse(message)

    alt Parsing error
        ORCH->>SSE: emit parsing_error
        ORCH->>SSE: emit response_complete (error payload)
    else Parsing success
        ORCH->>SSE: emit parsing_complete
        ORCH->>SSE: emit analyzing_complexity
        ORCH->>CA: analyze(cleaned_text)
        ORCH->>SSE: emit complexity_determined (simple|complex)

        alt Simple path
            ORCH->>SSE: emit simple_path_selected
            ORCH->>SSE: emit generating_response
            ORCH->>LLM: generate_response(...)
            loop chunk stream
                ORCH->>SSE: emit response_chunk
            end
            ORCH->>SSE: emit response_complete

        else Complex path
            ORCH->>SSE: emit complex_path_selected
            ORCH->>SSE: emit creating_research_plan
            ORCH->>PA: create_plan(cleaned_text)
            ORCH->>SSE: emit research_plan_created

            loop each research task
                ORCH->>SSE: emit researching_task
                ORCH->>RT: execute_task(...)
                alt task success
                    ORCH->>SSE: emit task_complete
                    ORCH->>SSE: emit results_found or no_results_found
                else task error
                    ORCH->>SSE: emit task_error
                end
            end

            ORCH->>SSE: emit research_complete
            alt has knowledge_base + sources
                ORCH->>SSE: emit composing_response
                ORCH->>RC: compose(...)
            else fallback direct generation
                ORCH->>SSE: emit simple_path_selected
                ORCH->>SSE: emit generating_response
                ORCH->>LLM: generate_response(...)
            end

            loop chunk stream
                ORCH->>SSE: emit response_chunk
            end
            ORCH->>SSE: emit response_complete
        end
    end

    API->>SSE: close_stream(request_id)
    SSE-->>Hook: stream closed (None + cleanup)
    Hook-->>UI: update StatusDisplay + MessageList
    Note over Hook,UI: Reconnect backoff: 1s -> 2s -> 4s -> 8s (max 4)
```

## Ghi chú

- Event filter `event_types` được áp dụng ở `SSEStreamManager`; riêng `response_chunk` luôn được gửi.
- Keepalive được gửi định kỳ dưới dạng comment SSE `: keepalive` khi queue chưa có event.
- Mỗi event có schema chuẩn: `event_type`, `timestamp`, `request_id`, `message?`, `data?`, `metadata?`.
