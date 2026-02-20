# Kiem thu don vi xuyen suot

## Mo ta chi tiet
- Dinh nghia ky vong kiem thu toan he thong cho tat ca ham.
- Tap trung vao do dung identifier, error wrapping, va timeouts.
- Dam bao gioi han context truoc khi model invocation.

## Chien luoc kiem thu
- Unit tests: theo tung plan.
- Integration tests: API endpoints, retrieval pipeline, model invocation stub.
- Contract tests: UI <-> API request/response JSON.
- E2E tests: happy path, timeout path, partial data path.

## Pham vi
- Correlation id propagation across all function outputs.
- Error wrapping includes source and error code.
- Timeout policy is consistent for queue, search, external APIs, models.
- Context size limits enforced before model invocation.
