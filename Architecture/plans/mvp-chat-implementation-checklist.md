# MVP Chat đa model - Implementation Checklist

## A. Contract
- [ ] Request có `message, locale?, channel?, model?`
- [ ] Response chuẩn: `request_id, status, answer, error, meta`
- [ ] Error code: `BAD_REQUEST, UNSUPPORTED_MODEL, MODEL_ERROR, MODEL_EMPTY_OUTPUT, INTERNAL_ERROR`

## B. Registry & Config
- [ ] Tạo `model_registry` (id -> provider/adapter/config)
- [ ] Có `default_model`
- [ ] Validate model tại normalize step
- [ ] Thêm API `GET /models`

## C. Pipeline 5 bước
- [ ] captureQuestion
- [ ] normalizeRequest (default + validate model/channel)
- [ ] invokeModelsWithContext (adapter + retry 1)
- [ ] composeResponse
- [ ] deliverResponseToUser (HTTP mapping)

## D. API
- [ ] `POST /chat`
- [ ] `GET /models`
- [ ] `GET /health`
- [ ] `GET /ready`

## E. Test
- [ ] Unit test cho 5 step
- [ ] Mock adapter cho OpenAI/Google
- [ ] Integration test `/chat` cho 200/400/502/500
- [ ] Integration test `/models`, `/health`, `/ready`

## F. Observability/Security
- [ ] Log: `request_id, model, provider, latency_ms, error.code`
- [ ] Không log full message/secrets
- [ ] Alert: tỷ lệ 5xx > 5% / 5 phút