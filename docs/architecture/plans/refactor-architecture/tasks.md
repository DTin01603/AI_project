# Tasks — refactor-architecture

> Convention: mỗi task có 1 block Unit test đi kèm (pytest, AAA: Arrange / Act / Assert),
> tối thiểu 1 happy-path + 1 edge case. Mỗi task = 1 PR độc lập, test cũ phải xanh
> trước và sau. Schema SQLite giữ nguyên byte-by-byte.

---

## Task 1 — Tạo `db/connection.py` + `db/schema.py` (gom PRAGMA + CREATE TABLE)

**What:** Tạo `SQLiteConnectionFactory` ở `backend/src/db/connection.py` (1 chỗ duy nhất set 4 PRAGMA `WAL` / `synchronous=NORMAL` / `busy_timeout=5000` / `row_factory=Row`, expose `connect()` auto-commit + `transaction()` atomic). Tạo `run_migrations(factory)` ở `backend/src/db/schema.py` gom toàn bộ `CREATE TABLE` / triggers / indexes từ 3 nơi (`research_agent/database.py:_initialize_schema`, `rag/citation_tracker.py:_ensure_schema`, `rag/document_indexer.py:_ensure_schema`) vào 1 file, dùng `IF NOT EXISTS`. Sửa `Database._connect`, `FTSEngine._connect`, `CitationTracker._connect`, `DocumentIndexer._connect` để gọi vào factory; `_ensure_schema` của 3 class còn lại trở thành no-op. Gọi `run_migrations()` ở `backend/src/main.py` startup.

**Where:**
- `backend/src/db/connection.py` (new)
- `backend/src/db/schema.py` (new)
- `backend/src/research_agent/database.py` (sửa `_connect`, `_initialize_schema` no-op)
- `backend/src/rag/fts_engine.py` (sửa `_connect`)
- `backend/src/rag/citation_tracker.py` (sửa `_connect`, `_ensure_schema` no-op)
- `backend/src/rag/document_indexer.py` (sửa `_connect`, `_ensure_schema` no-op)
- `backend/src/main.py` (gọi `run_migrations` ở startup)

**Done when:**
- `grep -r "sqlite3.connect" backend/src/` chỉ trả về 1 hit ở `db/connection.py`.
- `grep -r "PRAGMA" backend/src/` chỉ trả về hit ở `db/connection.py`.
- `grep -r "CREATE TABLE" backend/src/` chỉ trả về hit ở `db/schema.py`.
- Toàn bộ test cũ (`test_research_agent_database.py`, `test_fts_engine.py`, `test_citation_tracker.py`, `test_document_indexing_retrieval.py`, `test_search_api.py`) xanh, **không sửa assert**.
- Public API của 4 class cũ giữ nguyên signature.

### Unit test 1.1 — `should_set_all_pragmas_when_connect`
- Framework: pytest
- Arrange: `factory = SQLiteConnectionFactory(tmp_path / "test.db")`.
- Act: `with factory.connect() as conn: rows = conn.execute("PRAGMA journal_mode").fetchall(); ...` (query 4 pragma).
- Assert: `journal_mode == "wal"`, `synchronous == 1` (NORMAL), `busy_timeout == 5000`, `conn.row_factory is sqlite3.Row`.

### Unit test 1.2 — `should_rollback_when_transaction_raises`
- Framework: pytest
- Arrange: factory + tạo bảng `t(id INT)`. Insert 1 row "before".
- Act: gọi `with factory.transaction() as conn: conn.execute("INSERT INTO t VALUES (1)"); raise RuntimeError("boom")` trong `pytest.raises(RuntimeError)`.
- Assert: `SELECT count(*) FROM t` = 1 (row "before" còn, row "1" bị rollback).

### Unit test 1.3 — `should_be_idempotent_when_run_migrations_called_twice`
- Framework: pytest
- Arrange: factory trên DB rỗng, gọi `run_migrations(factory)`.
- Act: gọi `run_migrations(factory)` lần 2.
- Assert: không raise. Query `sqlite_master` trả đúng tập bảng/trigger giống lần 1 (compare set equality).

---

## Task 2 — Tạo `models/conversation.py` + `models/search.py` + `repositories/message_repo.py` (gộp FTSEngine), xóa `rag/fts_engine.py` + `research_agent/database.py`

**What:** Tạo Domain entity `Message`, `Conversation` (dataclass frozen với invariant role/content) ở `models/conversation.py`. Tạo `SearchResult`, `RetrievedDocument` ở `models/search.py`. Tạo `ConversationRepository` (CRUD `conversations`) và `MessageRepository` (CRUD `messages` + `search_fts()` gộp từ `FTSEngine`). Mọi mutation method nhận `conn` optional cho transaction compose. Cập nhật caller cũ (`Database`, `FTSEngine`) chuyển sang gọi repo. Xóa `rag/fts_engine.py` và `research_agent/database.py` (thay bằng repo).

**Where:**
- `backend/src/models/conversation.py` (new)
- `backend/src/models/search.py` (new)
- `backend/src/repositories/_base.py` (new, helper)
- `backend/src/repositories/conversation_repo.py` (new)
- `backend/src/repositories/message_repo.py` (new)
- `backend/src/rag/fts_engine.py` (DELETE)
- `backend/src/research_agent/database.py` (DELETE)
- Mọi caller: `agent/nodes/`, `rag/retrieval_node.py`, `api/routers/` (đổi import)

**Done when:**
- 2 file đã xóa không còn trong tree.
- Test cũ `test_fts_engine.py` rename thành `test_message_repo_fts.py`, **chỉ đổi import**, assert giữ nguyên, xanh.
- Test cũ `test_research_agent_database.py` chia thành `test_conversation_repo.py` + `test_message_repo.py`, đổi import, xanh.
- `MessageRepository.search_fts(query)` trả `list[Message]` (không phải `sqlite3.Row`).

### Unit test 2.1 — `should_return_messages_when_search_fts_matches`
- Framework: pytest
- Arrange: factory + `run_migrations`. Insert 3 message qua `MessageRepository.insert`: "hello world", "foo bar", "world peace".
- Act: `repo.search_fts("world")`.
- Assert: trả 2 `Message` instance (không phải Row), `content` chứa "world".

### Unit test 2.2 — `should_escape_special_chars_when_search_fts_with_quote`
- Framework: pytest
- Arrange: factory + insert message `content = "it's a test"`.
- Act: `repo.search_fts("it's")` (chuỗi có dấu nháy đơn).
- Assert: không raise `sqlite3.OperationalError`. Trả 1 message hoặc 0 (tuỳ FTS5 tokenizer) — quan trọng là **không SQL injection**.

### Unit test 2.3 — `should_raise_when_message_role_is_invalid`
- Framework: pytest
- Arrange: chuẩn bị kwargs `role="hacker"`.
- Act: `Message(id=None, conversation_id=1, role="hacker", content="x", created_at=now)`.
- Assert: `pytest.raises(ValueError, match="role")`.

### Unit test 2.4 — `should_use_passed_conn_when_insert_with_conn_arg`
- Framework: pytest
- Arrange: factory, mở `with factory.transaction() as conn`. Insert 1 message với `conn=conn`, sau đó **không commit** (mock raise trước commit).
- Act: bắt exception, mở connection mới ngoài transaction.
- Assert: `SELECT count(*) FROM messages` = 0 (rollback hoạt động vì insert dùng cùng conn).

---

## Task 3 — Tạo `services/conversation_service.py` với `persist_turn` 1-transaction, sửa `persist_conversation_node`

**What:** Tạo `ConversationService` ở `backend/src/services/conversation_service.py` với method `persist_turn(conversation_id, user_msg, assistant_msg)` mở 1 transaction, insert cả 2 message, rollback nếu lỗi giữa chừng. Method `get_history(conversation_id)`. Sửa `persist_conversation_node` (ở `agent/nodes/`) chuyển từ gọi 2 lần `Database.add_message` sang 1 lần `service.persist_turn`.

**Where:**
- `backend/src/services/__init__.py` (new)
- `backend/src/services/conversation_service.py` (new)
- `backend/src/research_agent/nodes/persist_conversation_node.py` (sửa)

**Done when:**
- `persist_conversation_node` không còn import từ `repositories/`, chỉ inject `ConversationService`.
- Integration test `test_search_api.py` xanh.
- Behavior: nếu insert message thứ 2 throw, message thứ 1 bị rollback (test mới).

### Unit test 3.1 — `should_persist_both_messages_when_persist_turn_succeeds`
- Framework: pytest
- Arrange: factory + repos + service. user_msg + assistant_msg hợp lệ, `conversation_id=1`.
- Act: `service.persist_turn(1, user_msg, assistant_msg)`.
- Assert: `msg_repo.get_by_conversation(1)` trả 2 message đúng thứ tự, đúng role.

### Unit test 3.2 — `should_rollback_user_message_when_assistant_insert_fails`
- Framework: pytest (đây là test "gác cổng" mà PLAN gốc chỉ định: `test_persist_turn_atomic`)
- Arrange: factory + real `conv_repo`, mock `msg_repo.insert` để: lần 1 chạy bình thường (insert user_msg vào conn), lần 2 raise `sqlite3.IntegrityError("boom")`.
- Act: `with pytest.raises(sqlite3.IntegrityError): service.persist_turn(1, user_msg, assistant_msg)`.
- Assert: mở connection mới, `SELECT count(*) FROM messages WHERE conversation_id=1` = 0 (cả 2 bị rollback, không leak user_msg).

---

## Task 4 — Tạo `models/citation.py` + `repositories/citation_repo.py` + `services/citation_service.py`, xóa `rag/citation_tracker.py`

**What:** Tạo `Citation` dataclass với pure method `format(style)` (`inline` | `footnote`). Tạo `CitationRepository` (CRUD `citations` + `citation_usage`). Tạo `CitationService` với method `attach_to_documents(citations, doc_ids)` (1 transaction insert citations + usage rows), `track_usage(citation_id)`. Xóa `rag/citation_tracker.py`, cập nhật caller.

**Where:**
- `backend/src/models/citation.py` (new)
- `backend/src/repositories/citation_repo.py` (new)
- `backend/src/services/citation_service.py` (new)
- `backend/src/rag/citation_tracker.py` (DELETE)
- Caller trong `rag/retrieval_node.py`, `agent/nodes/` (đổi sang service)

**Done when:**
- File `citation_tracker.py` không còn.
- Test cũ `test_citation_tracker.py` chia thành `test_citation_repo.py` + `test_citation_service.py`, đổi import, xanh.

### Unit test 4.1 — `should_attach_citations_atomically_when_all_valid`
- Framework: pytest
- Arrange: factory + `run_migrations`. service. 3 citation + 3 doc_id.
- Act: `service.attach_to_documents(citations, doc_ids)`.
- Assert: `citations` table có 3 row, `citation_usage` có 3 row link đúng.

### Unit test 4.2 — `should_format_inline_when_style_is_inline`
- Framework: pytest
- Arrange: `c = Citation(id=1, source_url="https://x.com", title="X", snippet="...", created_at=now)`.
- Act: `c.format("inline")`.
- Assert: trả chuỗi chứa `"X"` và `"https://x.com"`, không chứa newline (inline = 1 dòng).

### Unit test 4.3 — `should_raise_when_format_style_unknown`
- Framework: pytest
- Arrange: citation hợp lệ.
- Act: `c.format("unknown")`.
- Assert: `pytest.raises(ValueError, match="style")`.

---

## Task 5 — Tạo `models/document.py` + `repositories/document_repo.py` + `services/document_indexing_service.py`, xóa `rag/document_indexer.py`

**What:** Tạo `DocumentRecord` dataclass. Tạo `DocumentRepository` (CRUD `documents`). Tạo `DocumentIndexingService` (chunk → embed → persist + add vào vector store). Xóa `rag/document_indexer.py`. Service nhận DI: `document_repo`, `vector_store`, `embedding_client`.

**Where:**
- `backend/src/models/document.py` (new)
- `backend/src/repositories/document_repo.py` (new)
- `backend/src/services/document_indexing_service.py` (new)
- `backend/src/rag/document_indexer.py` (DELETE)
- `backend/src/api/routers/` (caller — đổi import)

**Done when:**
- `document_indexer.py` không còn.
- Integration test `test_document_indexing_retrieval.py` xanh, không sửa assert.

### Unit test 5.1 — `should_persist_document_and_add_to_vector_store_when_index`
- Framework: pytest
- Arrange: real factory + `document_repo`. Mock `vector_store.add` và `embedding_client.embed` (trả vector cố định).
- Act: `service.index(source="docs/a.md", content="hello world")`.
- Assert: `document_repo.get(doc_id)` trả `DocumentRecord` với content đúng. `vector_store.add` được gọi đúng 1 lần với chunks + embeddings tương ứng.

### Unit test 5.2 — `should_not_persist_document_when_embedding_fails`
- Framework: pytest
- Arrange: mock `embedding_client.embed` raise `RuntimeError("api down")`.
- Act: `with pytest.raises(RuntimeError): service.index(source="x", content="y")`.
- Assert: `document_repo.list_all()` trả empty list (rollback / không persist khi embedding fail).

---

## Task 6 — Tạo `services/conversation_indexing_service.py`, xóa `rag/conversation_indexer.py`

**What:** Dời logic từ `rag/conversation_indexer.py` thành `ConversationIndexingService` ở `services/`. Inject `message_repo`, `vector_store`, `embedding_client`. Xóa file cũ. Cập nhật caller.

**Where:**
- `backend/src/services/conversation_indexing_service.py` (new)
- `backend/src/rag/conversation_indexer.py` (DELETE)
- Caller (agent node hoặc API router)

**Done when:**
- `conversation_indexer.py` không còn.
- Test cũ `test_conversation_indexer.py` rename thành `test_conversation_indexing_service.py`, đổi import, xanh.

### Unit test 6.1 — `should_index_all_messages_when_index_conversation_called`
- Framework: pytest
- Arrange: factory + insert 3 message qua `message_repo`. Mock `vector_store.add` + `embedding_client.embed`.
- Act: `service.index_conversation(conversation_id=1)`.
- Assert: `vector_store.add` gọi 1 lần với 3 chunks tương ứng 3 message.

### Unit test 6.2 — `should_skip_when_conversation_has_no_messages`
- Framework: pytest
- Arrange: factory rỗng (không insert message). Mock `vector_store.add`.
- Act: `service.index_conversation(conversation_id=999)`.
- Assert: `vector_store.add` không được gọi (`assert_not_called`). Không raise.

---

## Task 7 — Refactor `api/deps.py` thành `AppContainer`, wire toàn bộ DI

**What:** Tạo class `AppContainer` ở `backend/src/api/deps.py`: `__init__(config)` khởi tạo factory → run_migrations → repos → services. Expose `get_*_service()` dependency cho FastAPI router. Giữ nguyên `@lru_cache` pattern hiện tại — **không** đổi sang lifespan/Depends pure (đó là PR riêng).

**Where:**
- `backend/src/api/deps.py` (refactor)
- `backend/src/main.py` (init `AppContainer` ở startup, gọi `run_migrations` qua container)
- Mọi router trong `backend/src/api/routers/` (đổi `Depends(get_database)` → `Depends(get_*_service)`)

**Done when:**
- Không router nào còn import trực tiếp `Database`, `FTSEngine`, `CitationTracker`, `DocumentIndexer`.
- Smoke test: `pytest backend/tests/integration/test_search_api.py` xanh.
- `main.py` chỉ gọi 1 dòng `container = AppContainer(config)` — không tự `sqlite3.connect`.

### Unit test 7.1 — `should_share_single_factory_across_services_when_container_initialized`
- Framework: pytest
- Arrange: `container = AppContainer(test_config)`.
- Act: lấy `container.conversation_service._factory` và `container.citation_service._factory`.
- Assert: `is` same object (1 factory dùng chung, không tạo nhiều).

### Unit test 7.2 — `should_run_migrations_exactly_once_when_container_initialized`
- Framework: pytest
- Arrange: spy/patch `db.schema.run_migrations`.
- Act: tạo `AppContainer(config)` 1 lần.
- Assert: `run_migrations` called exactly once với đúng factory.

---

## Task 8 — Tạo `api/schemas/`, dời `models/request.py` + `models/response.py` + DTO inline trong `routers/search.py`, xóa `models/internal.py`

**What:** Tạo `backend/src/api/schemas/chat.py` chứa `ChatRequest`, `ChatResponse` (dời từ `models/request.py` + `models/response.py`). Tạo `api/schemas/search.py` chứa `SearchRequest`, `SearchResponse` (dời DTO inline). Xóa `models/request.py`, `models/response.py`, `models/internal.py` (mồ côi). Cập nhật mọi import.

**Where:**
- `backend/src/api/schemas/__init__.py` (new)
- `backend/src/api/schemas/chat.py` (new — dời)
- `backend/src/api/schemas/search.py` (new — dời + extract)
- `backend/src/models/request.py` (DELETE)
- `backend/src/models/response.py` (DELETE)
- `backend/src/models/internal.py` (DELETE)
- `backend/src/api/routers/chat.py`, `routers/search.py` (đổi import)

**Done when:**
- `grep -r "from .*models\.request" backend/src/` zero hit.
- `grep -r "from .*models\.response" backend/src/` zero hit.
- `models/` chỉ còn entity dataclass (`conversation.py`, `citation.py`, `document.py`, `search.py`).
- Pydantic validation behavior giữ nguyên (test API integration xanh).

### Unit test 8.1 — `should_validate_chat_request_payload_when_pydantic_parses`
- Framework: pytest
- Arrange: payload dict hợp lệ `{"conversation_id": 1, "message": "hi"}`.
- Act: `ChatRequest(**payload)`.
- Assert: instance tạo thành công, `.message == "hi"`.

### Unit test 8.2 — `should_raise_validation_error_when_message_is_empty`
- Framework: pytest
- Arrange: payload `{"conversation_id": 1, "message": ""}`.
- Act: `ChatRequest(**payload)`.
- Assert: `pytest.raises(pydantic.ValidationError)`.

---

## Task 9 — Đổi tên `research_agent/` → `agent/` (git mv + sửa import toàn project)

**What:** `git mv backend/src/research_agent backend/src/agent`. Search-replace toàn bộ import `from research_agent.` → `from agent.` trong `backend/src/` và `backend/tests/`. Cập nhật cả test file path nếu cần. **Chỉ làm sau khi bước 1-8 đã merge.**

**Where:**
- `backend/src/research_agent/` → `backend/src/agent/` (rename qua `git mv` để giữ history)
- Mọi file `.py` có import `research_agent` (toàn project)
- `backend/tests/unit/test_research_agent_*.py` → `test_agent_*.py` (rename + đổi import)

**Done when:**
- `grep -r "research_agent" backend/` zero hit (cả `src/` lẫn `tests/`).
- Toàn bộ test xanh: unit + integration.
- `git log --follow backend/src/agent/<any_file>.py` cho thấy history nguyên vẹn từ thời `research_agent/`.

### Unit test 9.1 — `should_import_agent_module_when_renamed`
- Framework: pytest
- Arrange: không có gì.
- Act: `import agent; from agent.graph import build_graph` (hoặc symbol cũ tương đương).
- Assert: import thành công, `agent.__name__ == "agent"`.

### Unit test 9.2 — `should_have_no_research_agent_references_in_codebase`
- Framework: pytest (smoke test dạng grep)
- Arrange: helper chạy `subprocess.run(["grep", "-r", "research_agent", "backend/src", "backend/tests"], capture_output=True)`.
- Act: chạy.
- Assert: `result.stdout == b""` và `result.returncode == 1` (grep zero hit). Edge case: nếu repo có `.git/` index lỗi cũ thì exclude.

---

## Definition of done

- [ ] Tất cả 9 task hoàn thành, mỗi task = 1 PR đã merge.
- [ ] Tất cả unit test mới (1.1 → 9.2) xanh.
- [ ] Tất cả test cũ liệt kê ở `requirements.md §6` xanh sau **mỗi** PR (gác cổng regression).
- [ ] Acceptance criteria từ `requirements.md §7` được verify (đặc biệt: 3 lệnh grep zero/single hit).
- [ ] Smoke test thủ công: chạy `main.py`, gọi 1 chat + 1 search → so payload với branch trước refactor (byte-equal hoặc semantic-equal documented).
- [ ] `git log --follow` trên các file đã rename cho thấy history nguyên vẹn.
- [ ] Không file nào trong `repositories/` import từ `services/` hoặc `skills/` (kiểm bằng grep).
- [ ] Không file nào trong `agent/nodes/` import `sqlite3` hoặc gọi LLM SDK trực tiếp (kiểm bằng grep).
