# Skill-Based Architecture Refactor — Plan

Refactor dự án hiện tại thành kiến trúc **skill-based** trong khi vẫn giữ framework **LangGraph**. Mỗi skill là một bundle tự chứa gồm `prompt.md` + `skill.yaml` + `handler.py`.

## Động cơ

Bug gần nhất: câu hỏi "đà nẵng sắp tới có lễ hội gì không" bị route sai vào `simple_llm` thay vì `research` vì:
- Prompt của complexity_classifier nằm hardcode trong [complexity_analyzer.py:29-34](../backend/src/research_agent/complexity_analyzer.py#L29-L34)
- Keyword list trong [intent_patterns.py](../backend/src/research_agent/utils/intent_patterns.py) không có "sắp tới"
- Tinh chỉnh phải sửa code Python + rebuild container

Sau refactor: sửa `prompt.md` hoặc `skill.yaml` → restart container là xong.

## Các file trong folder này

| File | Mục đích |
|---|---|
| [requirements.md](requirements.md) | Yêu cầu functional / non-functional / constraints / success criteria |
| [design.md](design.md) | Kiến trúc target, quyết định kỹ thuật (D1–D8), folder structure, non-goals |
| [architecture-diagrams.md](architecture-diagrams.md) | Sơ đồ Mermaid: before/after, skill anatomy, sequence, gantt, state flow |
| [tasks.md](tasks.md) | Breakdown chi tiết theo phase với checkbox |
| [dev-workflow.md](dev-workflow.md) | Cách chạy docker + test nhanh (docker exec, prompt auto-reload) |

## Tổng quan 3 giai đoạn

| Phase | Nội dung | Effort | Shippable sau phase? |
|---|---|---|---|
| **1 — MVP** | Framework skeleton + migrate 1 skill `complexity_classifier` | 0.5–1 ngày | ✅ |
| **2a** | 5 skill research_agent (response_composer, planning, direct_answer, research_search, query_router) | 1.5–2 ngày | ✅ |
| **2b** | 5 skill RAG (query_expand, transform_query, grade_documents, grade_generation, answer_with_context, retrieve) | 1–1.5 ngày | ✅ |
| **3** | Xóa class cũ + `intent_patterns.py` | 0.5 ngày | ✅ |

**Ship-after-any-phase:** dừng sau bất kỳ phase nào hệ thống vẫn chạy. Phase 1 đủ để chứng minh pattern và sửa bug "sắp tới" bằng cách edit file `.md`.

## Cách dùng folder này

1. Đọc [requirements.md](requirements.md) để thống nhất scope.
2. Đọc [design.md](design.md) để nắm quyết định kiến trúc — nếu có điểm muốn đổi, sửa trước khi bắt đầu code.
3. Khi code: mở [tasks.md](tasks.md), check-off từng task.
4. Mỗi khi hoàn thành một phase, chạy test suite + manual curl test + commit với message `refactor(skills): phase N — <tên>`.
