# Checklist & Template cho một "Plan" tốt (Agent Chat)

Phiên bản: 1.0  
Mục đích: Tài liệu này là checklist chi tiết để thiết kế, đánh giá và vận hành một plan (kế hoạch) trong kiến trúc chat agent gồm các bước rõ ràng, xử lý lỗi, UX, bảo mật và test.

---

## Tóm tắt ngắn gọn
- Mục tiêu: Mô tả ngắn gọn (1 câu) mục đích của plan.  
- Phạm vi: Nêu rõ những gì plan sẽ làm và sẽ không làm.  
- Owner: Người (hoặc team) chịu trách nhiệm.

---

## 1) Inputs & Preconditions
- [ ] Danh sách inputs bắt buộc (entities/slots) đã liệt kê (ví dụ: `from`, `to`, `date`, `passengers`).
- [ ] Điều kiện khởi động (preconditions) rõ ràng (ví dụ: session active, user authenticated).
- [ ] Yêu cầu data/KB/credentials đã xác định.

---

## 2) Kết quả mong đợi (Outputs & Success Criteria)
- [ ] Kết quả cuối cùng cụ thể, có thể kiểm chứng (ví dụ: "ticket created with id").
- [ ] Outputs của từng bước (schema JSON) được mô tả.
- [ ] Các chỉ số success (KPIs) để đo (success rate, completion time).

---

## 3) Phân chia bước (Steps)
- [ ] Các bước được liệt kê theo thứ tự thực thi.
- [ ] Mỗi bước có:
  - id
  - action type (collect / search / call-api / present / confirm)
  - inputs (required/optional)
  - expected outputs
  - timeout
  - retry policy
- [ ] Dependencies / điều kiện nhảy giữa các bước (decision points) được mô tả.

---

## 4) Xử lý lỗi & Fallback
- [ ] Chiến lược khi step thất bại (retry count, backoff).
- [ ] Phân loại lỗi (transient vs permanent).
- [ ] Kịch bản rollback / compensating action nếu có side-effect.
- [ ] Trigger & procedure để escalate sang human agent.

---

## 5) Tương tác với user (UX)
- [ ] Prompt templates để thu thập thông tin thiếu (mẫu câu).
- [ ] Messages cho cases: success, failure, clarification, timeout.
- [ ] Suggested replies / quick replies nếu phù hợp.
- [ ] Locale, tone, personalization (nếu cần).

---

## 6) Bảo mật & Quyền riêng tư
- [ ] Liệt kê PII cần redact / không log.
- [ ] Yêu cầu credential & scope cho external APIs.
- [ ] Compliance notes (GDPR/CCPA) nếu áp dụng.
- [ ] Encryption / storage rules cho sensitive data.

---

## 7) Hiệu năng & Giới hạn
- [ ] SLA / timeout cho toàn bộ plan và từng step.
- [ ] Rate-limit / batching cho calls tới 3rd-party.
- [ ] Dự đoán chi phí nếu gọi LLM (nếu dùng).

---

## 8) Telemetry & Observability
- [ ] Metrics cần collect: success_rate, time_per_step, error_rate, escalation_rate.
- [ ] Logs cần có: correlation_id, step_id, request/response (PII đã redact).
- [ ] Distributed tracing (nếu có).
- [ ] Alert thresholds & dashboards.

---

## 9) Testability & Validation
- [ ] Test cases cho happy path và mọi lỗi đã định nghĩa.
- [ ] Mockable Doer adapters để chạy tests offline.
- [ ] Unit tests cho logic plan, integration tests cho Doer.
- [ ] Acceptance criteria rõ để QA sign-off.

---

## 10) Dependencies & Deployment
- [ ] Liệt kê external deps (endpoints, KB, LLM, DB).
- [ ] Contract/spec cho mỗi API (schema, status codes).
- [ ] Thông tin versions, migration nếu cần.

---

## 11) Operability & Runbook
- [ ] Owner & on-call thông tin.
- [ ] Runbook / playbook cho incidents (how to investigate, rollback steps).
- [ ] Feature flag / canary rollout plan.
- [ ] Rollback procedure.

---

## 12) Documentation & Metadata
- [ ] Mô tả step-by-step trong doc chi tiết.
- [ ] Ví dụ request/response JSON cho mỗi step.
- [ ] Changelog / version của plan.
- [ ] Link tới test cases / tickets liên quan.

---

## 13) Continuous Improvement
- [ ] Cơ chế thu feedback (rating, thumbs).
- [ ] KPIs để theo dõi và cải tiến.
- [ ] Kế hoạch retrain/refine nếu có NLU/LLM.

---

## Quick PASS/FAIL (Review ngắn)
- [ ] Goal & scope rõ
- [ ] Inputs + preconditions liệt kê
- [ ] Steps có sequence + outputs
- [ ] Error handling + retry + escalation defined
- [ ] UX prompts/templates có sẵn
- [ ] Security/PII rules specified
- [ ] Test cases & mocks có sẵn
- [ ] Monitoring & metrics defined
- [ ] Owner & runbook available

---

## Mẫu template ngắn (YAML-like)
```yaml
id: plan_book_flight
title: "Book Flight"
owner: team-travel
goal: "Đặt vé cho user"
scope_includes:
  - search flights
  - present options
  - confirm booking
scope_excludes:
  - payment processing (handled by payments service)
preconditions:
  - session authenticated
inputs:
  - from (required)
  - to (required)
  - date (required)
outputs:
  success_criteria:
    - booking_id returned
steps:
  - id: 1
    action: collect_info
    inputs: [from, to, date]
    timeout: 60s
    retries: 1
    error_handling: ask_clarify
  - id: 2
    action: search_flights
    inputs: [from, to, date]
    timeout: 10s
    retries: 2
    error_handling: fallback_search_cached
  - id: 3
    action: present_options
    outputs: [options]
    error_handling: escalate_to_human
escalations:
  - trigger: no_options_found
    to: human_agent_console
metrics:
  - success_rate
  - avg_time_to_complete
tests:
  - id: t1
    description: happy path (all inputs provided)
  - id: t2
    description: missing required input (ask for clarify)
dependencies:
  - flights-api v1
  - user-profile-db
security_considerations:
  - redact user PII in logs
docs_link: https://link-to-docs
```

---

## Đánh giá (scorecard)
- Clarity (goal & scope): 0..5  
- Completeness (inputs/outputs/steps): 0..5  
- Robustness (error handling/escalation): 0..5  
- Testability: 0..5  
- Operability (monitoring/runbook): 0..5  
Tổng >= 20/25 = Good plan

---

## Quy trình review & rollout ngắn
1. Tác giả hoàn thiện template + test cases.
2. Peer review dựa trên checklist Quick PASS/FAIL.
3. Chạy unit & integration tests (mocks cho Doer).
4. Pilot rollout (canary) với metrics theo dõi 24–72h.
5. Post-mortem & iterate.

---

## Hướng dẫn sử dụng file này
- Copy nội dung này vào GitHub Issue, PR hoặc document trong repo.  
- Sử dụng mẫu YAML để tạo plan mới; attach test cases & mock adapters.  
- Khi review, use the Quick PASS/FAIL section as checklist.

---

Nếu bạn muốn, mình có thể:
- Chuyển file này thành Issue template cho GitHub (YAML) để tạo plan mới tự động.  
- Hoặc xuất thành file JSON/YAML.  
- Hoặc tạo checklist interactive cho Notion / Confluence.

Bạn muốn mình xuất định dạng nào tiếp theo?