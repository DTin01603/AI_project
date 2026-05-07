# Requirements — refactor-architecture

## 1. Overview

Project `AI_project` (LangGraph agent + RAG) hiện có database code rải rác ở nhiều nơi: 3 class tự mở SQLite connection riêng và lặp lại PRAGMA 4 lần (`Database`, `FTSEngine`, `CitationTracker`, `DocumentIndexer`), schema `_ensure_schema()` xuất hiện ở 3 nơi tạo coupling ngầm (`FTSEngine` cần `Database` chạy trước để có bảng `messages` + `messages_fts`), thư mục `models/` trộn DTO Pydantic với dataclass mồ côi, và `persist_conversation_node` save 2 message trong 2 transaction tách rời gây nguy cơ nửa-mồ-côi. Tên `research_agent/` cũng không khớp scope thực tế (3/4 nhánh không phải research). Refactor này dịch chuyển toàn bộ code sang kiến trúc **Model-Repository-Service** với phân tầng rõ ràng, không thay đổi schema DB và không thay đổi public behavior.

## 2. Goals

- Gom toàn bộ logic mở SQLite connection + PRAGMA về **1 chỗ duy nhất** (`db/connection.py`).
- Gom toàn bộ `CREATE TABLE` / triggers / indexes về **1 chỗ duy nhất** (`db/schema.py:run_migrations`), gọi 1 lần ở startup.
- Tách rõ 3 tầng: **Model** (Domain entity dataclass thuần) — **Repository** (1 bảng = 1 repo, chỉ SQL) — **Service** (business logic + transaction).
- Tách DTO Pydantic ra khỏi `models/` (dời sang `api/schemas/`) để khỏi đụng tên với Domain entity.
- Sửa lỗi nửa-transaction trong `persist_conversation_node`: 2 message phải save trong **1 transaction** atomic.
- Đổi tên `research_agent/` → `agent/` để khớp scope thực tế (3/4 nhánh không phải research).
- Toàn bộ test cũ phải xanh sau **mỗi bước**, không chỉ ở cuối.

## 3. Non-goals

- **Không** đổi schema SQLite (giữ nguyên byte-by-byte).
- **Không** tạo abstract base class / Protocol vội — chỉ tạo khi có 2+ implementation thật (YAGNI).
- **Không** đổi DI pattern (FastAPI `Depends` vs `@lru_cache`) trong refactor này — `@lru_cache` hiện tại đủ, đổi DI là PR riêng.
- **Không** big-bang — mỗi bước 1 PR độc lập, có thể merge từng cái.
- **Không** đổi public API behavior của bất kỳ endpoint nào (refactor là internal restructure).
- **Không** đổi LLM provider, không đổi vector store, không đổi RAG pipeline logic.

## 4. User stories

- Là **engineer mới onboard**, tôi muốn nhìn 1 thư mục là biết file nào làm gì (entity ở `models/`, SQL ở `repositories/`, business logic ở `services/`), để giảm thời gian đọc code.
- Là **engineer maintain code**, tôi muốn khi sửa schema chỉ cần đổi `db/schema.py`, không phải hunt 3 nơi `_ensure_schema()`, để giảm rủi ro miss.
- Là **engineer thêm tính năng mới** (ví dụ thêm bảng), tôi muốn pattern rõ ràng "tạo model + repo + service rồi inject vào router", để khỏi phải nghĩ lại structure mỗi lần.
- Là **engineer review PR**, tôi muốn mỗi PR refactor chỉ chạm 1 layer rõ ràng, để review nhanh và phát hiện regression sớm.
- Là **người dùng cuối**, tôi muốn `persist_conversation_node` không bao giờ để lại "user message có, assistant message mất" trong DB, để lịch sử chat luôn nhất quán.

## 5. Functional requirements

- **FR-1**: `SQLiteConnectionFactory` (ở `db/connection.py`) là điểm duy nhất mở connection, set 4 PRAGMA (`journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`, `row_factory=Row`), expose context manager `connect()` (auto-commit) và `transaction()` (1 atomic block).
- **FR-2**: `run_migrations(connection_factory)` ở `db/schema.py` tạo toàn bộ tables/triggers/indexes (`conversations`, `messages`, `messages_fts` + 3 triggers, `citations`, `citation_usage`, `documents`), idempotent (chạy nhiều lần không lỗi), gọi 1 lần ở `main.py` startup.
- **FR-3**: Mỗi bảng có **1 repository** chứa toàn bộ SQL của bảng đó. `MessageRepository` gộp luôn FTS query (vì FTS query bảng `messages_fts` cùng cluster với `messages`).
- **FR-4**: `ConversationService.persist_turn(user_msg, assistant_msg)` save 2 message trong **1 transaction**; nếu lỗi giữa chừng → rollback toàn bộ.
- **FR-5**: Repository chỉ trả Domain entity (dataclass ở `models/`), không trả `sqlite3.Row` ra ngoài.
- **FR-6**: `api/schemas/` chứa toàn bộ DTO Pydantic (request/response), `models/` chỉ chứa Domain entity dataclass.
- **FR-7**: Agent nodes inject Service (không inject Repository, không tự mở connection, không tự gọi LLM).
- **FR-8**: Skill chỉ gọi LLM/tool ngoài; nếu cần data → **gọi Service**, không gọi Repository trực tiếp.
- **FR-9**: Toàn bộ thư mục `research_agent/` rename thành `agent/`; mọi import trong project được cập nhật.
- **FR-10**: Sau refactor, các file sau bị xóa: `rag/fts_engine.py`, `rag/citation_tracker.py`, `rag/document_indexer.py`, `rag/conversation_indexer.py`, `research_agent/database.py`, `models/internal.py`.

## 6. Non-functional requirements

- **Performance**: Không regression. Số connection mở per request không tăng. PRAGMA `WAL` + `busy_timeout=5000` giữ nguyên.
- **Security**: Không thay đổi attack surface. Toàn bộ SQL vẫn dùng parameterized query (không string concat). Không log sensitive payload.
- **Compatibility**: Schema SQLite giữ nguyên byte-by-byte → DB file production có thể swap qua-lại giữa branch cũ và branch mới mà không cần migrate.
- **Backward compat (test)**: Test cũ ở `backend/tests/unit/test_research_agent_database.py`, `test_fts_engine.py`, `test_citation_tracker.py`, `test_conversation_indexer.py` chỉ rename + đổi import, **không đổi assert**.
- **Reviewability**: Mỗi bước trong roadmap = 1 PR, ≤ 500 LOC diff (trừ bước 9 rename thuần).
- **Test coverage**: Mỗi service mới có ít nhất 1 test happy-path + 1 test edge (mock repo throw, verify rollback / error propagation).

## 7. Acceptance criteria

- [ ] Toàn bộ 9 bước trong `tasks.md` hoàn thành, mỗi bước là 1 PR đã merge.
- [ ] Sau bước cuối, các file sau **không còn** tồn tại: `rag/fts_engine.py`, `rag/citation_tracker.py`, `rag/document_indexer.py`, `rag/conversation_indexer.py`, `research_agent/database.py`, `models/internal.py`, thư mục `research_agent/`.
- [ ] `grep -r "sqlite3.connect" backend/src/` chỉ trả về 1 hit duy nhất ở `db/connection.py`.
- [ ] `grep -r "CREATE TABLE" backend/src/` chỉ trả về hit ở `db/schema.py`.
- [ ] `grep -r "PRAGMA" backend/src/` chỉ trả về hit ở `db/connection.py`.
- [ ] Toàn bộ test cũ (unit + integration đã liệt kê) **xanh** sau mỗi bước.
- [ ] Test mới `test_conversation_service::test_persist_turn_atomic` chứng minh: nếu repo throw ở message thứ 2, message thứ 1 cũng bị rollback.
- [ ] Không có file Python nào trong `agent/nodes/` import trực tiếp `sqlite3` hoặc gọi LLM SDK.
- [ ] Không có file Python nào trong `repositories/` import từ `services/` hoặc `skills/`.
- [ ] Smoke test: chạy `main.py`, gọi 1 chat request, 1 search request → cả hai trả về 200 với payload giống branch cũ.

## 8. Open questions

- Có cần migration script chạy 1 lần để verify byte-equality của schema cũ vs mới (sqlite_master diff) trước khi merge bước 1 không? — Đề xuất: **có**, viết 1 test fixture so sánh `sqlite_master` dump giữa branch cũ và branch mới.
- `AppContainer` ở bước 7 nên là module-level singleton hay class instance khởi tạo ở `main.py` lifespan? — Đề xuất: **lifespan-scoped instance** để dễ test (truyền vào fixture), nhưng giữ `@lru_cache` cho factory bên trong.
- Sau bước 9 rename, có cần để alias `research_agent = agent` để tránh vỡ external import (nếu có) không? — Đề xuất: **không**, project nội bộ, alias là technical debt thừa.
