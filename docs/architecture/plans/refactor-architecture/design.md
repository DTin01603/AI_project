# Design — refactor-architecture

## 1. Architecture summary

Refactor sang kiến trúc **Model-Repository-Service** phân tầng nghiêm ngặt: Domain entity (dataclass thuần) ở dưới cùng, Repository (1 bảng = 1 SQL gateway) ở giữa, Service (business logic + transaction boundary) ở trên, sau đó là 2 nhánh tiêu thụ song song — `api/routers/` (HTTP) và `agent/nodes/` (LangGraph). Skill chỉ gọi LLM/tool ngoài và **gọi xuống Service** khi cần data, không bao giờ tự mở DB. Toàn bộ connection sinh ra từ `SQLiteConnectionFactory` duy nhất, schema được áp 1 lần ở startup qua `run_migrations()`. Không đổi schema, không đổi public behavior.

**Các thành phần chính:**

- `db/` — Connection factory + schema migration (1 chỗ duy nhất cho PRAGMA và CREATE TABLE).
- `models/` — Domain entity dataclass (Conversation, Message, Citation, Document, SearchResult).
- `repositories/` — 1 bảng = 1 repo (ConversationRepository, MessageRepository, CitationRepository, DocumentRepository).
- `services/` — Business logic + transaction (ConversationService, ConversationIndexingService, DocumentIndexingService, CitationService).
- `api/schemas/` — DTO Pydantic (chat, search) — dời từ `models/request.py` + `models/response.py`.
- `api/routers/` + `api/deps.py` — Hiện trạng + `AppContainer` wire DI.
- `skills/` — Giữ nguyên, chỉ đổi: gọi service thay vì gọi repo/DB trực tiếp.
- `agent/` — Rename từ `research_agent/`, nodes inject service.
- `rag/` — Giữ retrieval logic, xóa 4 file đã chuyển lên service tier.

## 2. Component breakdown

### `db/connection.py:SQLiteConnectionFactory`

- **Responsibility**: Mở SQLite connection với PRAGMA chuẩn. Là điểm duy nhất trong codebase tạo `sqlite3.Connection`.
- **Inputs**: `db_path: str` (init).
- **Outputs**: `connect()` context manager (auto-commit khi exit), `transaction()` context manager (1 atomic block, rollback nếu exception).
- **Dependencies**: stdlib `sqlite3`, `pathlib`, `contextlib`. Không depend project code.
- **Invariants**: Mỗi connection set đủ 4 PRAGMA (`journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`, `row_factory=Row`). Tự tạo parent dir nếu chưa có.

### `db/schema.py:run_migrations`

- **Responsibility**: Idempotent schema setup. Tạo toàn bộ tables/triggers/indexes 1 lần ở startup.
- **Inputs**: `connection_factory: SQLiteConnectionFactory`.
- **Outputs**: None (side effect: schema applied).
- **Dependencies**: `SQLiteConnectionFactory`.
- **Invariants**: Mọi `CREATE TABLE` / `CREATE TRIGGER` / `CREATE INDEX` dùng `IF NOT EXISTS`. Schema phải byte-equal với schema cũ (verify bằng `sqlite_master` diff).

### `models/` (Domain entity)

- **Responsibility**: Dataclass thuần biểu diễn entity nghiệp vụ. Có thể có pure behavior (validation, format) nhưng không I/O.
- **Members**:
  - `conversation.py`: `Conversation`, `Message` (với invariant `role ∈ {user, assistant, system}`, `content` non-empty).
  - `citation.py`: `Citation` + `format(style)` pure.
  - `document.py`: `DocumentRecord`.
  - `search.py`: `SearchResult`, `RetrievedDocument`.
- **Cấm**: import `sqlite3`, `pydantic`, `fastapi`, gọi LLM/HTTP.

### `repositories/` (Data access)

- **Responsibility**: 1 bảng = 1 repo. Chỉ chứa SQL. Trả Domain entity, không trả `sqlite3.Row`.
- **Members**:
  - `_base.py`: helper chung (e.g. `_row_to_dict`).
  - `conversation_repo.py`: CRUD `conversations`.
  - `message_repo.py`: CRUD `messages` + FTS query trên `messages_fts` (gộp `FTSEngine` cũ vì cùng bảng cluster).
  - `citation_repo.py`: CRUD `citations` + `citation_usage`.
  - `document_repo.py`: CRUD `documents`.
- **Inputs**: `connection_factory: SQLiteConnectionFactory` (DI).
- **Cấm**: gọi Service/Skill, business logic phức tạp, gọi LLM, mở connection trực tiếp (phải qua factory).

### `services/` (Business logic)

- **Responsibility**: Orchestrate nhiều repo + transaction boundary. Validate cross-entity rule.
- **Members**:
  - `conversation_service.py`: `persist_turn(user_msg, assistant_msg)` — 1 transaction, save 2 message atomic. `get_history(conversation_id)`.
  - `conversation_indexing_service.py` (ex-`ConversationIndexer`): index conversation chunks vào vector store + FTS.
  - `document_indexing_service.py` (ex-`DocumentIndexer`): chunk + embed + persist document, gọi `document_repo` + `vector_store`.
  - `citation_service.py` (ex-`CitationTracker`): `attach_to_documents(citations, doc_ids)`, `track_usage(citation_id)`.
- **Inputs**: repo(s), `vector_store`, `embedding_client` (DI).
- **Cấm**: mở connection, gọi LLM, biết HTTP/FastAPI.

### `api/schemas/` (DTO Pydantic)

- **Responsibility**: Pydantic model cho HTTP request/response. Validate input boundary.
- **Members**:
  - `chat.py`: `ChatRequest`, `ChatResponse` (dời từ `models/request.py` + `models/response.py`).
  - `search.py`: `SearchRequest`, `SearchResponse` (dời DTO inline trong `routers/search.py`).
- **Cấm**: import `sqlite3`, business logic.

### `api/deps.py:AppContainer`

- **Responsibility**: Wire toàn bộ DI: `connection_factory` → repos → services → routers. Module-level singleton, hoặc lifespan-scoped instance trong `main.py`.
- **Inputs**: config (`DATABASE_PATH`, etc.).
- **Outputs**: `get_conversation_service()`, `get_citation_service()`, etc. cho FastAPI `Depends`.
- **Dependencies**: tất cả tầng dưới.

### `agent/` (rename từ `research_agent/`)

- **Responsibility**: LangGraph state machine. Nodes orchestrate skill + service.
- **Members**: `nodes/`, `graph/`, `edges/`, `checkpointer/`, `streaming/`, `utils/`. Bỏ `database.py` (đã dời qua repo + service).
- **Cấm**: gọi repo trực tiếp, gọi LLM trực tiếp (phải qua skill).

### `skills/` (giữ nguyên)

- **Responsibility**: Wrap LLM call + tool ngoài (web search, current date). Không chạm DB.
- **Inputs**: `service` (nếu cần data).
- **Cấm**: mở DB, gọi repo.

## 3. Data model

**Schema SQLite giữ nguyên byte-by-byte.** Refactor là dịch chuyển code, không đổi data.

### Tables

| Bảng | Cột chính | Index/Trigger | Hiện sống ở | Sau refactor |
|---|---|---|---|---|
| `conversations` | `id`, `user_id`, `title`, `created_at`, `updated_at` | — | `research_agent/database.py` | `db/schema.py` (CREATE) + `repositories/conversation_repo.py` (CRUD) |
| `messages` | `id`, `conversation_id` (FK), `role`, `content`, `created_at` | — | `research_agent/database.py` | `db/schema.py` + `repositories/message_repo.py` |
| `messages_fts` | virtual table FTS5 trên `content` | 3 trigger sync (insert/update/delete) | `research_agent/database.py` (CREATE), `rag/fts_engine.py` (query) | `db/schema.py` (CREATE + triggers) + `repositories/message_repo.py:search_fts()` |
| `citations` | `id`, `source_url`, `title`, `snippet`, `created_at` | — | `rag/citation_tracker.py` | `db/schema.py` + `repositories/citation_repo.py` |
| `citation_usage` | `id`, `citation_id` (FK), `document_id`, `used_at` | — | `rag/citation_tracker.py` | `db/schema.py` + `repositories/citation_repo.py` |
| `documents` | `id`, `source`, `content`, `metadata`, `created_at` | — | `rag/document_indexer.py` | `db/schema.py` + `repositories/document_repo.py` |

### Domain entity (Python dataclass, sau refactor)

```python
# models/conversation.py
@dataclass(frozen=True)
class Message:
    id: int | None
    conversation_id: int
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime

@dataclass(frozen=True)
class Conversation:
    id: int | None
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

# models/citation.py
@dataclass(frozen=True)
class Citation:
    id: int | None
    source_url: str
    title: str
    snippet: str
    created_at: datetime
    def format(self, style: Literal["inline", "footnote"]) -> str: ...

# models/document.py
@dataclass(frozen=True)
class DocumentRecord:
    id: int | None
    source: str
    content: str
    metadata: dict
    created_at: datetime

# models/search.py
@dataclass(frozen=True)
class SearchResult:
    document_id: int
    score: float
    snippet: str

@dataclass(frozen=True)
class RetrievedDocument:
    record: DocumentRecord
    score: float
```

## 4. API / interface

### `SQLiteConnectionFactory`

```python
class SQLiteConnectionFactory:
    def __init__(self, db_path: str) -> None: ...
    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]: ...   # auto-commit on exit
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]: ...  # atomic block
```

### Repository (signature mẫu — `MessageRepository`)

```python
class MessageRepository:
    def __init__(self, factory: SQLiteConnectionFactory) -> None: ...
    def insert(self, msg: Message, *, conn: sqlite3.Connection | None = None) -> int: ...
    def get_by_conversation(self, conversation_id: int) -> list[Message]: ...
    def search_fts(self, query: str, limit: int = 10) -> list[Message]: ...
```

Tất cả mutation method nhận `conn` optional → cho phép service compose nhiều insert trong 1 transaction.

### Service (signature mẫu)

```python
class ConversationService:
    def __init__(self, conv_repo, msg_repo, factory: SQLiteConnectionFactory) -> None: ...

    def persist_turn(self, conversation_id: int, user_msg: Message, assistant_msg: Message) -> None:
        with self._factory.transaction() as conn:
            self._msg_repo.insert(user_msg, conn=conn)
            self._msg_repo.insert(assistant_msg, conn=conn)
        # rollback tự động nếu insert thứ 2 throw

    def get_history(self, conversation_id: int) -> list[Message]: ...
```

### `AppContainer`

```python
class AppContainer:
    def __init__(self, config: AppConfig) -> None:
        self.factory = SQLiteConnectionFactory(config.db_path)
        run_migrations(self.factory)
        self.conv_repo = ConversationRepository(self.factory)
        self.msg_repo = MessageRepository(self.factory)
        self.conversation_service = ConversationService(self.conv_repo, self.msg_repo, self.factory)
        # ... etc
```

FastAPI dependency:

```python
@lru_cache
def get_container() -> AppContainer: ...

def get_conversation_service(c: AppContainer = Depends(get_container)) -> ConversationService:
    return c.conversation_service
```

## 5. Data flow

### Flow A — Persist 1 chat turn (sửa lỗi nửa-transaction)

1. Router `POST /chat` nhận `ChatRequest` (Pydantic).
2. Router gọi `agent.run(request)` → graph chạy, ra `final_state`.
3. `persist_conversation_node` (đã sửa) gọi `conversation_service.persist_turn(conv_id, user_msg, assistant_msg)`.
4. Service mở 1 transaction, insert user_msg, insert assistant_msg, commit.
5. Nếu insert assistant_msg throw → rollback toàn bộ → user_msg cũng không tồn tại trong DB.
6. Router trả `ChatResponse`.

### Flow B — RAG retrieval với FTS

1. Router `POST /search` nhận `SearchRequest`.
2. Router gọi retrieval pipeline → `MessageRepository.search_fts(query)`.
3. Repo query `messages_fts MATCH ?` → trả `list[Message]`.
4. Pipeline rerank → trả `list[RetrievedDocument]`.
5. Router map qua `SearchResponse` (Pydantic) → trả 200.

### Flow C — Document indexing

1. Caller gọi `document_indexing_service.index(source, content)`.
2. Service: chunk → embed → mở transaction → `document_repo.insert(...)` → commit.
3. Service gọi `vector_store.add(chunks, embeddings)` (ngoài transaction SQLite).
4. Trả `document_id`.

### Flow D — Startup

1. `main.py` load config.
2. Tạo `AppContainer(config)` → `__init__` gọi `run_migrations(factory)` (idempotent).
3. FastAPI app lấy container qua `Depends`.

## 6. Error handling & edge cases

- **Insert message thứ 2 throw giữa transaction**: `transaction()` context manager rollback toàn bộ, user_msg không leak. Test: `test_persist_turn_atomic`.
- **`run_migrations` chạy lần thứ N**: tất cả `CREATE TABLE` dùng `IF NOT EXISTS` → no-op, không lỗi.
- **`SQLiteConnectionFactory` với `db_path` không tồn tại parent dir**: `_ensure_parent_dir()` tạo `parents=True, exist_ok=True`.
- **2 process cùng mở DB**: `journal_mode=WAL` + `busy_timeout=5000` xử lý — giữ nguyên hành vi cũ.
- **FTS query với chuỗi đặc biệt** (e.g. `"AND"`, dấu nháy): repo phải escape qua parameter binding, không string concat. Test: `test_search_fts_with_special_chars`.
- **Service nhận `Message` với `role="invalid"`**: dataclass `__post_init__` raise `ValueError` ở construction time, không tới repo. Test: `test_message_invariant_rejects_bad_role`.
- **Citation `format(style="unknown")`**: raise `ValueError`. Test: `test_citation_format_rejects_unknown_style`.
- **Repo nhận `conn=None` vs `conn=existing`**: nếu None → tự mở connect()-scoped; nếu pass → reuse, không commit (để service kiểm soát). Test: cả 2 path.
- **`AppContainer` init lỗi (e.g. db_path readonly)**: bubble exception lên `main.py`, fail fast, không boot app.
- **Rename `research_agent/` → `agent/`**: dùng `git mv` để giữ history, sau đó `grep -r "research_agent" backend/` phải zero hit.

## 7. Security considerations

- **SQL injection**: tất cả query dùng parameterized binding (`?` placeholder). Repo có lint check (grep `f"..."` trong file repo phải zero hit ở vị trí câu SQL).
- **Path traversal qua `db_path`**: `db_path` đến từ config, không từ user input — không cần validate thêm. Document trong code rule này.
- **Connection leak**: context manager đảm bảo `close()` trong `finally`. Test: kiểm tra số connection không tăng sau N request (smoke test).
- **Logging**: không log nội dung message hoặc citation snippet (có thể chứa PII). Giữ behavior log hiện tại.
- **Schema migration không có rollback**: `run_migrations` chỉ thêm bảng `IF NOT EXISTS`, không drop/alter — refactor không thay đổi schema nên không cần rollback path.
- **DTO Pydantic ở `api/schemas/`**: validate input boundary (max length, regex, type) — giữ nguyên validation hiện có khi dời từ `models/request.py`.

## 8. Alternatives considered

- **Keep `models/` mixed (DTO + Domain)** — rejected: tên va chạm gây nhầm lẫn nghiêm trọng (Pydantic `Message` vs dataclass `Message` cùng tên trong cùng package), reviewer không phân biệt được tầng.
- **Tạo `IRepository` Protocol cho mọi repo** — rejected: YAGNI, hiện chỉ có 1 implementation SQLite cho mỗi bảng. Tạo Protocol khi và chỉ khi có implementation thứ 2 (e.g. mock cho test, hoặc Postgres).
- **Tách `FTSEngine` riêng khỏi `MessageRepository`** — rejected: chúng cùng query bảng cluster (`messages` + `messages_fts`), tách 2 class chỉ tạo coupling ngầm (FTS cần messages tồn tại trước). Gộp = đơn giản hơn.
- **Đổi DI sang FastAPI `Depends` thuần (bỏ `@lru_cache`)** — rejected: scope khác, là PR riêng. Refactor này giữ DI pattern cũ.
- **Đổi tên `research_agent/` → `chat_agent/` hoặc `assistant/`** — rejected: `agent/` là tên ngắn nhất đúng scope; `chat_agent/` thừa vì agent này chính là chat agent, `assistant/` quá generic.
- **Big-bang refactor 1 PR** — rejected: review impossible, regression risk cao. 9 PR độc lập theo roadmap.
- **Đổi schema DB cùng lúc** (e.g. thêm `messages.token_count`) — rejected: 1 việc 1 lúc. Refactor xong rồi PR riêng đổi schema.
- **Migration script byte-equality verification** — đang cân nhắc (mục Open question 8.1 ở `requirements.md`).
