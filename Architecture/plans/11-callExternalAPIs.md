# callExternalAPIs()

## Trach nhiem
- Goi cac he thong ben ngoai theo task.

## Mo ta chi tiet
- Goi external services voi tham so da validate va auth.
- Xu ly rate-limit, timeout, va chuan hoa response.
- Tra ve raw results de dam bao truy vet.

## Ghi chu trien khai
- Backend: Python client wrappers goi external APIs.
- LangGraph: node goi external systems va luu raw results vao state.

## Dau vao
- Execution request co chi tiet API

## Dau ra
- Raw external results

## Phu thuoc
- External API clients (mocked)

## Loi co the xay ra
- API error
- Rate limit
- Timeout

## Kiem thu don vi
- Handles successful API response mapping.
- Retries or fails on rate limit per policy.
- Handles timeout and propagates error.
