# MVP Chat - Checklist trien khai ky thuat (task-by-task)

Muc tieu: Trien khai chat co ban hoat dong duoc theo 6 plan giu lai.
Pham vi: 1 endpoint `/chat`, 1 luong xu ly dong bo, khong retrieval/tool calling/streaming.

## A. Chuan bi contract va cau hinh
- [ ] Chot request contract dau vao:
  - [ ] `message: string` (bat buoc)
  - [ ] `locale: string` (optional, default `vi-VN`)
  - [ ] `channel: string` (optional, default `web`, MVP chi ho tro `web`)
- [ ] Chot response contract dau ra:
  - [ ] `request_id: string`
  - [ ] `status: "ok" | "error"`
  - [ ] `answer: string`
  - [ ] `error: { code, message } | null`
  - [ ] `meta: { model, finish_reason }`
- [ ] Chot ma loi dung chung:
  - [ ] `BAD_REQUEST`
  - [ ] `MODEL_ERROR`
  - [ ] `INTERNAL_ERROR`

## B. Trien khai captureQuestion
- [ ] Tao ham `captureQuestion(payload)`
- [ ] Trim `message` dau/cuoi
- [ ] Chuan hoa newline (`\r\n` -> `\n`)
- [ ] Validate:
  - [ ] message phai la string
  - [ ] message sau trim khong rong
  - [ ] do dai message <= 4000 ky tu
- [ ] Tra ve object:
  - [ ] `raw_message`
  - [ ] `locale`
  - [ ] `channel`
  - [ ] `received_at`
- [ ] Unit test cho 4 case: hop le / rong / qua dai / sai kieu

## C. Trien khai normalizeRequest
- [ ] Tao ham `normalizeRequest(captured)`
- [ ] Sinh `request_id` (UUID/ULID)
- [ ] Map `raw_message` -> `message`
- [ ] Gan mac dinh:
  - [ ] locale = `vi-VN` neu thieu
  - [ ] channel = `web` neu thieu
- [ ] Reject channel khong phai `web` voi `BAD_REQUEST`
- [ ] Gan constraints mac dinh:
  - [ ] `max_output_tokens = 500`
  - [ ] `temperature = 0.3`
- [ ] Unit test cho defaulting + invalid channel + co request_id

## D. Trien khai invokeModelsWithContext
- [ ] Tao ham `invokeModelsWithContext(normalized)`
- [ ] Tao prompt template MVP:
  - [ ] system role ngan gon
  - [ ] user role = `message`
- [ ] Goi model client voi constraints
- [ ] Validate output:
  - [ ] co `answer_text`
  - [ ] `answer_text` khong rong
- [ ] Thu retry 1 lan khi provider error/timeout
- [ ] Neu van fail, map thanh `MODEL_ERROR`
- [ ] Unit test:
  - [ ] happy path
  - [ ] provider error + retry
  - [ ] empty output

## E. Trien khai composeResponse
- [ ] Tao ham `composeResponse(modelResult | error)`
- [ ] Thanh cong:
  - [ ] `status = ok`
  - [ ] map `answer = answer_text`
  - [ ] `error = null`
- [ ] That bai:
  - [ ] `status = error`
  - [ ] fallback `answer` than thien
  - [ ] map `error.code` dung chuan
- [ ] Luon giu `request_id`
- [ ] Cat nguong do dai `answer` neu qua 3000 ky tu
- [ ] Unit test cho success + error + missing model output

## F. Trien khai deliverResponseToUser
- [ ] Endpoint `POST /chat` goi tuan tu 5 ham B -> C -> D -> E
- [ ] Mapping HTTP status:
  - [ ] `ok` -> 200
  - [ ] `BAD_REQUEST` -> 400
  - [ ] `MODEL_ERROR` -> 502
  - [ ] khac -> 500
- [ ] Set header `Content-Type: application/json`
- [ ] Log ket qua giao nhan: `request_id`, status code, latency
- [ ] Unit/integration test HTTP mapping day du

## G. Logging, telemetry, va bao mat toi thieu
- [ ] Log bat buoc:
  - [ ] `request_id`
  - [ ] `channel`
  - [ ] `message_length`
  - [ ] `model`
  - [ ] `latency_ms`
- [ ] Khong log full message neu khong can thiet
- [ ] Khong log secrets/API keys

## H. Test integration end-to-end
- [ ] Case 1: request hop le -> HTTP 200 + answer
- [ ] Case 2: message rong -> HTTP 400 + `BAD_REQUEST`
- [ ] Case 3: model fail -> HTTP 502 + `MODEL_ERROR`
- [ ] Case 4: loi khong du kien -> HTTP 500 + `INTERNAL_ERROR`

## I. Definition of Done (MVP)
- [ ] User gui cau hoi va nhan tra loi qua `/chat` thanh cong
- [ ] Loi duoc tra ve dung schema va dung HTTP code
- [ ] Co `request_id` xuyen suot tu vao den ra
- [ ] Unit tests cho 5 ham chinh deu pass
- [ ] Co it nhat 1 integration test cho endpoint `/chat`

## Thu tu implement de nhanh co ket qua
1. B -> C -> E (hoan thien data flow core, co the mock model)
2. D (goi model that)
3. F (dong goi vao API `/chat`)
4. G + H + I (telemetry, test, chot MVP)
