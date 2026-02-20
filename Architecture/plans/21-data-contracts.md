# Data Contracts va Schemas

## Cong nghe schema
- Use Pydantic models for request/response/error schemas.
- Validate types, required fields, enums, va size limits.

## Request Schema
- request_id
- user_input
- channel
- locale
- constraints
- metadata

## Response Schema
- request_id
- status
- answer
- sources
- warnings
- timings

## Error Schema
- error_code
- message
- source
- retryable
- trace_id

## Streaming API Contract
- Endpoint: POST /v1/ask/stream
- Protocol: Server-Sent Events (SSE)
- Event types: "delta", "final", "error"
- delta payload: partial answer chunk + request_id
- final payload: full answer + sources + timings
- error payload: error_code + message + retryable
