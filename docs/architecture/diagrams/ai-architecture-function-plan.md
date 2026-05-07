# AI Architecture Function Plan (Simple Project)

## Scope
- Purpose: minimal chat service using FastAPI + LangChain + LangGraph.
- Provider: OpenAI or Google via env config (single provider active at a time).
- Out of scope: retrieval, queues, external business APIs, multi-agent orchestration.

## Conventions
- Each function lists: responsibility, inputs, outputs, dependencies, failure modes, unit tests.
- External model calls are mocked in unit tests.
- LangGraph is used to build a small flow (tool step -> prompt step).
- FastAPI exposes /health and /chat.

## Function Plans (Sequence Order)

### 1) loadSettings()
- Responsibility: read env config and build settings object.
- Inputs: process environment.
- Outputs: settings (provider, model name, api key, streaming flag default).
- Dependencies: os env.
- Failure modes: missing required variables.
- Unit tests:
  - reads defaults when optional values missing.
  - returns provider/model from env.

### 2) validateSettings()
- Responsibility: validate provider and required keys.
- Inputs: settings.
- Outputs: none (raises on invalid).
- Dependencies: none.
- Failure modes: unsupported provider, missing api key.
- Unit tests:
  - rejects unsupported provider.
  - rejects missing key for chosen provider.

### 3) captureRequest()
- Responsibility: accept chat request from FastAPI /chat.
- Inputs: JSON body { message, stream }.
- Outputs: raw request payload.
- Dependencies: Pydantic schema validation.
- Failure modes: empty message, invalid body.
- Unit tests:
  - accepts valid message.
  - rejects empty or whitespace message.

### 4) normalizeRequest()
- Responsibility: normalize message and flags for internal use.
- Inputs: raw request payload.
- Outputs: normalized request (trimmed message, stream flag).
- Dependencies: none.
- Failure modes: message too long.
- Unit tests:
  - trims message and keeps stream flag.
  - rejects oversized message with validation error.

### 5) buildGraph()
- Responsibility: create LangGraph flow (tool step -> prompt step).
- Inputs: none.
- Outputs: compiled graph.
- Dependencies: langgraph.
- Failure modes: graph compile error.
- Unit tests:
  - returns compiled graph.
  - graph executes with empty tool result.

### 6) runToolIfRequested()
- Responsibility: run a simple LangChain tool when message uses a prefix.
- Inputs: normalized message.
- Outputs: tool_result (string or empty).
- Dependencies: tool registry (calculator).
- Failure modes: invalid tool input.
- Unit tests:
  - runs tool when prefix matches.
  - returns empty tool_result for normal chat.
  - fails on unsupported expression.

### 7) buildPrompt()
- Responsibility: build a prompt from message and tool_result.
- Inputs: message, tool_result.
- Outputs: prompt string.
- Dependencies: none.
- Failure modes: none.
- Unit tests:
  - includes tool_result when present.
  - uses clean prompt for normal chat.

### 8) invokeModel()
- Responsibility: call OpenAI or Google model with prompt.
- Inputs: prompt, stream flag.
- Outputs: model response (full text or token stream iterator).
- Dependencies: LangChain model client.
- Failure modes: model error, timeout.
- Unit tests:
  - returns text for non-stream.
  - yields chunks for stream.
  - surfaces model error with clear message.

### 9) streamResponse()
- Responsibility: format streaming output as SSE for FastAPI.
- Inputs: model stream iterator.
- Outputs: SSE event stream.
- Dependencies: FastAPI StreamingResponse.
- Failure modes: client disconnect.
- Unit tests:
  - wraps chunks as SSE data lines.
  - emits [DONE] at end.

### 10) composeResponse()
- Responsibility: format non-stream response payload.
- Inputs: model text.
- Outputs: JSON { reply }.
- Dependencies: FastAPI JSONResponse.
- Failure modes: empty model output.
- Unit tests:
  - returns reply field.
  - handles empty output with fallback text.

### 11) healthCheck()
- Responsibility: return service health.
- Inputs: none.
- Outputs: JSON { status: "ok" }.
- Dependencies: FastAPI.
- Failure modes: none.
- Unit tests:
  - returns ok status.

## Cross-Cutting Unit Tests
- Input size limits enforced before model call.
- Provider switch uses correct client and key.
- Streaming vs non-stream paths are both covered.

## Mocking Guide
- LLM client: success, timeout, error.
- Tool: valid expression, invalid expression.
