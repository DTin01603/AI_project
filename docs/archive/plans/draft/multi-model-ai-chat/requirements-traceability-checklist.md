# Checklist Mapping Requirements → Code (Phase 1 MVP)

Nguồn đối chiếu: `Architecture/plans/requirements.md`
Ngày cập nhật: 2026-02-25

## Tóm tắt nhanh

- Đạt tốt về luồng pipeline, endpoint chính (`/chat`, `/models`, `/health`, `/ready`), response contract, và frontend chat cơ bản.
- Còn thiếu một phần ở các mục: validation API key format khi khởi động, structured JSON logging, sanitize message/security nâng cao, và test coverage/property test theo yêu cầu chi tiết.

## Bảng traceability theo Requirement

| Requirement | Trạng thái | Mapping code chính | Ghi chú |
|---|---|---|---|
| R1 - Tiếp nhận yêu cầu chat | ✅ Đạt | `backend/src/main.py`, `backend/src/models/request.py`, `backend/src/services/capture_question.py` | Có nhận `message/locale/channel/model`, trim + normalize newline, reject rỗng/>4000, BAD_REQUEST 400, ghi `received_at` trong captured data. |
| R2 - Chuẩn hóa yêu cầu đầu vào | ✅ Đạt | `backend/src/services/normalize_request.py` | Có request_id từ header hoặc UUID, default locale/channel/model, reject channel != web, reject unsupported model, set constraints mặc định, lowercase locale. |
| R3 - Quản lý danh sách AI model | ⚠️ Thiếu một phần | `backend/src/main.py`, `backend/src/config.py`, `backend/src/registry/model_registry.py` | Endpoint `/models` hoạt động, trả provider/name/available theo runtime API key. Tuy nhiên `registry/model_registry.py` hiện ở mức scaffold, chưa là nguồn dữ liệu trung tâm đầy đủ. |
| R4 - Gọi AI model với context | ✅ Đạt | `backend/src/services/invoke_models.py`, `backend/src/adapters/google_adapter.py` | Có adapter resolution, LangChain invocation, system prompt, non-streaming, lỗi model/timeout map về code chuẩn, xử lý empty output, có finish_reason + usage tokens. |
| R5 - Tạo response thống nhất | ⚠️ Thiếu một phần | `backend/src/services/compose_response.py`, `backend/src/models/response.py` | Contract response đúng và có truncate 3000. Nhưng câu trả lời thân thiện cho từng code hiện khác wording trong tài liệu yêu cầu (ý nghĩa tương đương). |
| R6 - Xử lý lỗi và HTTP status mapping | ✅ Đạt | `backend/src/services/deliver_response.py`, `backend/src/main.py` | Mapping 400/502/500 đúng, trả JSONResponse, không fallback model khi lỗi. Có log request_id/status/latency khi deliver. |
| R7 - Health check và readiness | ✅ Đạt | `backend/src/main.py` | `/health` trả status + uptime. `/ready` kiểm tra available models nội bộ, không ping provider trực tiếp, trả 503 khi không model khả dụng. |
| R8 - Cấu hình provider linh hoạt | ⚠️ Thiếu một phần | `backend/src/config.py`, `backend/src/adapters/google_adapter.py`, `backend/src/main.py` | Đã đọc env key, timeout, default model, constraints. Còn thiếu validate format API key khi startup và warning log rõ ràng theo tiêu chí. |
| R9 - Logging và monitoring | ⚠️ Thiếu một phần | `backend/src/main.py`, `backend/src/services/capture_question.py`, `backend/src/services/deliver_response.py` | Có log theo bước chính và không log full content. Chưa dùng structured JSON logging chuẩn cho toàn pipeline, chưa có timing chi tiết từng bước. |
| R10 - Validation và security | ⚠️ Thiếu một phần | `backend/src/models/request.py`, `backend/src/services/capture_question.py` | Có Pydantic schema + type check message string + giới hạn độ dài. Chưa có lớp sanitize ký tự nguy hiểm/locale format validation chặt theo regex; HTTPS là phạm vi deployment. |
| R11 - Testing và quality assurance | ⚠️ Thiếu một phần | `backend/tests/unit/*.py`, `backend/tests/integration/test_deliver_response_api.py` | Có unit cho capture/normalize/invoke/compose và integration `/chat`, `/models`, `/health`, `/ready`. Chưa có unit test riêng cho `deliver_response.py`, chưa có property-based test trong `backend/tests/property/`, và chưa có báo cáo coverage >=80%. |
| R12 - Frontend UI với React | ✅ Đạt | `frontend/src/App.jsx`, `frontend/src/components/*.jsx`, `frontend/src/services/api.js` | React + Vite, chat input/history, chọn model, gọi `/chat`, loading indicator, hiển thị answer/error, fetch `/models` lúc khởi động, state nội bộ cho history, validate message rỗng trước submit. |

## Gap checklist ưu tiên (để đạt sát 100% tài liệu)

- [ ] Bổ sung validate format `GOOGLE_API_KEY`/`GEMINI_API_KEY` tại startup + warning log rõ ràng (R8).
- [ ] Chuẩn hóa logging JSON (structured logging) cho toàn pipeline và timing theo từng step (R9).
- [ ] Bổ sung sanitize message + validate locale format chặt (R10).
- [ ] Thêm unit test cho `DeliverResponseService` map status code (R11).
- [ ] Thêm property-based test cho normalize request trong `backend/tests/property/` (R11).
- [ ] Chạy coverage và ghi nhận kết quả >=80% (R11).

## Mapping test hiện có

- Unit tests:
  - `backend/tests/unit/test_capture_question_service.py`
  - `backend/tests/unit/test_normalize_request_service.py`
  - `backend/tests/unit/test_invoke_models_with_context_service.py`
  - `backend/tests/unit/test_compose_response_service.py`
  - `backend/tests/unit/test_chat_service_response_contract.py`
- Integration tests:
  - `backend/tests/integration/test_deliver_response_api.py`
