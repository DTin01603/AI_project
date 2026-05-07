# Workflow Input Tài Liệu Vào Database

## 📋 Tổng Quan

Khi bạn input một tài liệu (PDF, DOCX, Markdown, Code file...) vào hệ thống RAG, nó sẽ trải qua một **pipeline xử lý 5 bước** để biến thành dữ liệu có thể tìm kiếm được.

### ⚠️ LƯU Ý QUAN TRỌNG:

**Workflow input document KHÔNG sử dụng LangGraph!**

- ✅ **LangGraph** chỉ được dùng cho **retrieval workflow** (tìm kiếm & trả lời câu hỏi)
- ❌ **Document indexing** là **pipeline tuần tự đơn giản** (không cần graph)
- 📝 Lý do: Indexing là quy trình tuyến tính, không có branching logic hay self-correction

### So sánh:

| Workflow | Sử dụng LangGraph? | Lý do |
|----------|-------------------|-------|
| **Document Indexing** | ❌ KHÔNG | Pipeline tuần tự: Load → Chunk → Embed → Store |
| **RAG Retrieval** | ✅ CÓ | Có branching, retry, self-correction |

### Sơ đồ tổng quan:

```
📄 File Input
    ↓
[1] LOAD - Đọc & Parse file
    ↓
[2] CHUNK - Chia nhỏ thành đoạn
    ↓
[3] EMBED - Chuyển thành vector
    ↓
[4] STORE - Lưu vào Vector DB
    ↓
[5] METADATA - Lưu thông tin vào SQLite
    ↓
✅ Hoàn tất - Sẵn sàng tìm kiếm

(Pipeline tuần tự - KHÔNG dùng LangGraph)
```

---

## 🚀 Cách Sử Dụng

### Command Line:

```bash
# Index 1 file
python scripts/index_doc.py --file "D:/docs/guide.md"

# Index nhiều files
python scripts/index_doc.py \
  --file "D:/docs/guide.md" \
  --file "D:/docs/api.pdf" \
  --file "D:/code/main.py"

# Chỉ định database path
python scripts/index_doc.py \
  --file "D:/docs/guide.md" \
  --db-path "./data/conversations.db" \
  --vector-store-path "./data/vector_store"
```

### Python Code:

```python
from rag.document_indexer import DocumentIndexer
from rag.embedding import SentenceTransformerEmbedding
from rag.vector_store import ChromaVectorStore

# Setup
embedding_model = SentenceTransformerEmbedding()
vector_store = ChromaVectorStore(
    persist_directory="./data/vector_store",
    collection_name="indexed_documents"
)

indexer = DocumentIndexer(
    db_path="./data/conversations.db",
    embedding_model=embedding_model,
    vector_store=vector_store
)

# Index files
results, errors = indexer.index_files([
    "D:/docs/guide.md",
    "D:/docs/api.pdf"
])
```

---

## 🔄 Chi Tiết 5 Bước Xử Lý


### **Bước 1: LOAD - Đọc & Parse File** 📖

**Chức năng:** Đọc file và chuyển thành text thuần

**Component:** `DocumentLoader` với nhiều loại loader:

#### **1.1. Chọn Loader Phù Hợp**

Hệ thống tự động chọn loader dựa trên extension:

```python
# Loader chain (theo thứ tự ưu tiên)
loaders = [
    PDFLoader(),      # .pdf
    DOCXLoader(),     # .docx
    MarkdownLoader(), # .md, .markdown
    CodeLoader(),     # .py, .js, .ts, .java
    TextLoader()      # .txt, .log, .csv, .rst (fallback)
]
```

#### **1.2. Xử Lý Từng Loại File**

**A. PDF Files (.pdf)**
```python
# Sử dụng pypdf hoặc PyPDF2
reader = PdfReader("document.pdf")
pages = []
for page in reader.pages:
    pages.append(page.extract_text())
text = "\n\n".join(pages)

# Metadata
extra = {
    "loader": "pdf",
    "page_count": len(pages)
}
```

**B. DOCX Files (.docx)**
```python
# Sử dụng python-docx
doc = docx.Document("document.docx")
paragraphs = [p.text for p in doc.paragraphs]
text = "\n".join(paragraphs)

# Metadata
extra = {
    "loader": "docx",
    "author": doc.core_properties.author,
    "title": doc.core_properties.title
}
```

**C. Markdown Files (.md)**
```python
# Đọc file
raw = file.read_text()

# Extract frontmatter (nếu có)
# ---
# title: My Doc
# author: John
# ---
frontmatter, body = extract_frontmatter(raw)

text = body
extra = {
    "loader": "markdown",
    "frontmatter": frontmatter
}
```

**D. Code Files (.py, .js, .ts, .java)**
```python
# Đọc code
text = file.read_text()

# Extract features
if ext == ".py":
    # Parse Python AST
    tree = ast.parse(text)
    signatures = ["def function_name(...)", "class ClassName"]
    comments = ["# Comment 1", "# Comment 2"]
else:
    # Regex cho các ngôn ngữ khác
    signatures = re.findall(r"function\s+\w+|class\s+\w+", text)
    comments = re.findall(r"//\s*(.+)", text)

extra = {
    "loader": "code",
    "language": "python",
    "signatures": signatures[:200],
    "comments": comments[:200]
}
```

**E. Text Files (.txt, .log)**
```python
# Detect encoding
for encoding in ("utf-8", "utf-16", "latin-1"):
    try:
        text = file.read_bytes().decode(encoding)
        break
    except UnicodeDecodeError:
        continue

# Fallback: chardet
import chardet
detected = chardet.detect(raw_bytes)
text = raw_bytes.decode(detected["encoding"])
```

#### **1.3. Build Metadata**

```python
metadata = DocumentMetadata(
    file_name="guide.md",
    file_path="/path/to/guide.md",
    source_type="document",  # hoặc "code_file"
    file_size=12345,         # bytes
    created_at="2024-01-01T10:00:00Z",
    modified_at="2024-01-15T14:30:00Z",
    file_extension=".md",
    extra={...}              # Metadata đặc thù của loader
)
```

#### **1.4. Output**

```python
Document(
    id="",  # Sẽ được tạo ở bước sau
    text="Full text content...",
    metadata=metadata,
    source_type="document"
)
```

---

### **Bước 2: CHUNK - Chia Nhỏ Thành Đoạn** ✂️

**Chức năng:** Chia document lớn thành các chunk nhỏ để tìm kiếm hiệu quả

**Tại sao cần chunk?**
- Document dài → Embedding không hiệu quả
- Tìm kiếm cần độ chính xác cao → Chunk nhỏ tốt hơn
- LLM có giới hạn context → Chunk giúp chọn lọc

#### **2.1. Chọn Chunking Strategy**

```python
# Dựa vào config
if config.chunking_strategy == "code-aware":
    strategy = CodeAwareChunking(
        chunk_size=512,
        chunk_overlap=50
    )
else:
    strategy = RecursiveCharacterChunking(
        chunk_size=512,
        chunk_overlap=50
    )
```

#### **2.2. RecursiveCharacterChunking (Mặc định)**

**Thuật toán:**

```
1. Nếu text <= chunk_size → Trả về 1 chunk
2. Nếu text > chunk_size:
   a. Thử chia theo paragraph (\n\n)
   b. Nếu không được, chia theo sentence (. ! ?)
   c. Nếu vẫn không được, chia theo word (space)
   d. Cuối cùng, chia cứng theo ký tự
3. Thêm overlap giữa các chunk
```

**Ví dụ:**

```python
text = """
Paragraph 1: This is a long paragraph about AI...

Paragraph 2: This is another paragraph about ML...

Paragraph 3: Final paragraph about DL...
"""

# chunk_size=100, chunk_overlap=20
chunks = [
    "Paragraph 1: This is a long paragraph about AI...",
    "...about AI...\n\nParagraph 2: This is another...",
    "...another paragraph about ML...\n\nParagraph 3: Final..."
]
```

**Overlap giúp:**
- Giữ ngữ cảnh giữa các chunk
- Tránh mất thông tin ở ranh giới

#### **2.3. CodeAwareChunking (Cho Code Files)**

**Thuật toán:**

```
1. Tìm các định nghĩa (def, class, function, interface)
2. Chia theo định nghĩa
3. Nếu định nghĩa quá dài → Dùng RecursiveCharacterChunking
```

**Ví dụ:**

```python
# Input: Python file
"""
def function_a():
    # 10 lines
    pass

class MyClass:
    # 50 lines
    pass

def function_b():
    # 5 lines
    pass
"""

# Output chunks:
chunks = [
    "def function_a():\n    # 10 lines\n    pass",
    "class MyClass:\n    # 50 lines\n    pass",
    "def function_b():\n    # 5 lines\n    pass"
]
```

**Ưu điểm:**
- Giữ nguyên cấu trúc code
- Mỗi chunk là 1 unit logic (function/class)
- Dễ hiểu khi retrieve

#### **2.4. Output**

```python
chunks = [
    Chunk(
        id="doc_hash::chunk::0",
        document_id="doc_hash",
        text="First chunk text...",
        chunk_index=0,
        start_offset=0,
        end_offset=512,
        metadata={
            "source_type": "document",
            "file_name": "guide.md",
            "file_path": "/path/to/guide.md",
            "chunk_strategy": "recursive"
        }
    ),
    Chunk(
        id="doc_hash::chunk::1",
        document_id="doc_hash",
        text="Second chunk text...",
        chunk_index=1,
        start_offset=462,  # 512 - 50 (overlap)
        end_offset=974,
        metadata={...}
    ),
    # ... more chunks
]
```

---

### **Bước 3: EMBED - Chuyển Thành Vector** 🧠

**Chức năng:** Chuyển text thành vector số để máy tính hiểu ngữ nghĩa

#### **3.1. Embedding Model**

```python
# Mặc định: sentence-transformers
embedding_model = SentenceTransformerEmbedding(
    model_name="all-MiniLM-L6-v2",  # 384 dimensions
    dimension=384,
    batch_size=32,
    cache_size=1000
)
```

#### **3.2. Batch Processing**

```python
# Lấy text từ tất cả chunks
texts = [chunk.text for chunk in chunks]

# Ví dụ: 10 chunks
texts = [
    "First chunk text...",
    "Second chunk text...",
    # ... 8 more
]

# Embed theo batch (32 chunks/batch)
embeddings = embedding_model.embed(texts)

# Output: numpy array shape (10, 384)
# Mỗi chunk → 1 vector 384 chiều
embeddings = [
    [0.123, -0.456, 0.789, ...],  # 384 numbers
    [0.234, -0.567, 0.890, ...],
    # ... 8 more vectors
]
```

#### **3.3. Caching**

```python
# Nếu text đã được embed trước đó
cache_key = hash(text)
if cache_key in cache:
    return cache[cache_key]

# Nếu chưa có, embed và cache
embedding = model.encode(text)
cache[cache_key] = embedding
```

**Lợi ích:**
- Tránh embed lại text giống nhau
- Tăng tốc độ xử lý
- Tiết kiệm tài nguyên

---

### **Bước 4: STORE - Lưu Vào Vector Database** 💾

**Chức năng:** Lưu embeddings vào vector store để tìm kiếm nhanh

#### **4.1. Vector Store (Chroma)**

```python
vector_store = ChromaVectorStore(
    persist_directory="./data/vector_store",
    collection_name="indexed_documents"
)
```

#### **4.2. Add Documents**

```python
# Chuẩn bị dữ liệu
ids = ["doc_hash::chunk::0", "doc_hash::chunk::1", ...]
texts = ["First chunk...", "Second chunk...", ...]
embeddings = [[0.123, ...], [0.234, ...], ...]  # numpy array
metadatas = [
    {
        "document_id": "doc_hash",
        "chunk_index": 0,
        "source_type": "document",
        "file_name": "guide.md",
        "file_path": "/path/to/guide.md",
        "created_at": "2024-01-01T10:00:00Z",
        # ... more metadata
    },
    # ... more metadata dicts
]

# Lưu vào vector store
vector_store.add(
    ids=ids,
    embeddings=embeddings,
    texts=texts,
    metadatas=metadatas
)

# Persist to disk
vector_store.persist()
```

#### **4.3. Cấu Trúc Lưu Trữ**

```
data/vector_store/
└── indexed_documents/
    ├── chroma.sqlite3        # Metadata database
    ├── index/                # HNSW index
    │   └── vectors.bin       # Vector embeddings
    └── data/
        └── chunks.parquet    # Text content
```

#### **4.4. Indexing Algorithm (HNSW)**

```
HNSW (Hierarchical Navigable Small World)
- Tạo graph nhiều tầng
- Tìm kiếm nhanh O(log N)
- Phù hợp cho millions of vectors
```

**Ví dụ tìm kiếm:**

```python
# Query
query = "How to deploy application?"
query_embedding = model.embed_query(query)

# Tìm kiếm trong vector store
results = vector_store.search(
    query_embedding=query_embedding,
    top_k=5
)

# Kết quả: 5 chunks gần nhất (cosine similarity)
```

---

### **Bước 5: METADATA - Lưu Thông Tin Vào SQLite** 📊

**Chức năng:** Lưu metadata của document để quản lý và tracking

#### **5.1. Database Schema**

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,              -- SHA256 hash
    file_path TEXT NOT NULL,          -- "/path/to/guide.md"
    file_name TEXT NOT NULL,          -- "guide.md"
    source_type TEXT NOT NULL,        -- "document" | "code_file"
    file_size INTEGER NOT NULL,       -- 12345 bytes
    created_at TEXT NOT NULL,         -- ISO timestamp
    modified_at TEXT NOT NULL,        -- ISO timestamp
    indexed_at TEXT NOT NULL,         -- Khi nào được index
    chunk_count INTEGER NOT NULL,     -- Số chunks
    metadata_json TEXT                -- Extra metadata as JSON
);

CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE INDEX idx_documents_modified_at ON documents(modified_at);
```

#### **5.2. Generate Document ID**

```python
# Tạo unique ID từ content + metadata
payload = "|".join([
    document.metadata.file_path,
    document.metadata.modified_at,
    document.text,
    document.source_type
])

document_id = hashlib.sha256(payload.encode()).hexdigest()
# → "a1b2c3d4e5f6..."
```

**Tại sao dùng hash?**
- Unique: Mỗi document khác nhau → hash khác nhau
- Deterministic: Cùng content → cùng hash
- Detect changes: File thay đổi → hash thay đổi

#### **5.3. Upsert Document**

```python
conn.execute("""
    INSERT INTO documents (
        id, file_path, file_name, source_type, file_size,
        created_at, modified_at, indexed_at, chunk_count, metadata_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        file_path = excluded.file_path,
        modified_at = excluded.modified_at,
        indexed_at = excluded.indexed_at,
        chunk_count = excluded.chunk_count,
        metadata_json = excluded.metadata_json
""", (
    "a1b2c3d4e5f6...",
    "/path/to/guide.md",
    "guide.md",
    "document",
    12345,
    "2024-01-01T10:00:00Z",
    "2024-01-15T14:30:00Z",
    "2024-01-20T09:00:00Z",  # Now
    5,  # 5 chunks
    '{"loader": "markdown", "frontmatter": {...}}'
))
```

**ON CONFLICT:**
- Nếu document đã tồn tại (cùng ID) → Update
- Nếu chưa tồn tại → Insert
- Hữu ích khi re-index file đã thay đổi

---

## 📊 Ví Dụ Hoàn Chỉnh

### Input:

```markdown
# File: guide.md (1500 characters)

# Deployment Guide

## Prerequisites
- Docker installed
- AWS account

## Steps
1. Build image: `docker build -t app .`
2. Push to registry: `docker push app`
3. Deploy to ECS

## Troubleshooting
- Check logs: `docker logs`
- Restart: `docker restart`
```

### Processing:

```
[1] LOAD
    ✓ Detected: MarkdownLoader
    ✓ Extracted frontmatter: {}
    ✓ Text: "# Deployment Guide\n\n## Prerequisites..."
    ✓ Metadata: file_name="guide.md", size=1500

[2] CHUNK (chunk_size=512, overlap=50)
    ✓ Chunk 0: "# Deployment Guide\n\n## Prerequisites..."
    ✓ Chunk 1: "...AWS account\n\n## Steps..."
    ✓ Chunk 2: "...Deploy to ECS\n\n## Troubleshooting..."
    ✓ Total: 3 chunks

[3] EMBED
    ✓ Batch embed 3 chunks
    ✓ Model: all-MiniLM-L6-v2 (384 dim)
    ✓ Output: 3 vectors of shape (384,)

[4] STORE (Vector DB)
    ✓ Collection: indexed_documents
    ✓ Added 3 vectors with metadata
    ✓ Persisted to disk

[5] METADATA (SQLite)
    ✓ Document ID: a1b2c3d4e5f6...
    ✓ Inserted into documents table
    ✓ chunk_count: 3
```

### Output:

```json
{
  "indexed_count": 1,
  "error_count": 0,
  "results": [
    {
      "document_id": "a1b2c3d4e5f6...",
      "file_path": "/path/to/guide.md",
      "source_type": "document",
      "chunk_count": 3
    }
  ],
  "errors": []
}
```

### Kết quả trong Database:

**SQLite (documents table):**
```
id: a1b2c3d4e5f6...
file_path: /path/to/guide.md
file_name: guide.md
source_type: document
chunk_count: 3
indexed_at: 2024-01-20T09:00:00Z
```

**Chroma (vector store):**
```
Collection: indexed_documents
Documents: 3 chunks
- a1b2c3d4e5f6::chunk::0 → [0.123, -0.456, ...]
- a1b2c3d4e5f6::chunk::1 → [0.234, -0.567, ...]
- a1b2c3d4e5f6::chunk::2 → [0.345, -0.678, ...]
```

---

## 🔍 Sau Khi Index: Tìm Kiếm

### Query:

```python
query = "How to deploy to AWS?"
```

### Retrieval Process:

```
1. Embed query → [0.111, -0.222, ...]
2. Search vector store (cosine similarity)
3. Top results:
   - Chunk 1: "...Deploy to ECS..." (score: 0.89)
   - Chunk 0: "...Prerequisites..." (score: 0.72)
4. Return chunks với metadata
```

### Retrieved Context:

```python
[
    {
        "content": "...Deploy to ECS...",
        "score": 0.89,
        "metadata": {
            "file_name": "guide.md",
            "file_path": "/path/to/guide.md",
            "chunk_index": 1
        }
    }
]
```

---

## ⚙️ Configuration

### RAG Config (config/rag.yaml):

```yaml
# Chunking
chunk_size: 512              # Kích thước chunk (characters)
chunk_overlap: 50            # Overlap giữa chunks
chunking_strategy: recursive # recursive | code-aware

# Embedding
embedding_provider: sentence-transformers
embedding_model: all-MiniLM-L6-v2
embedding_dimension: 384
batch_size: 32               # Số chunks embed cùng lúc
cache_size: 1000             # Cache embeddings

# Vector Store
vector_store_type: chroma
vector_store_path: ./data/vector_store

# Database
db_path: ./data/conversations.db
```

---

## 🎯 Ưu Điểm Của Thiết Kế

### 1. **Modular & Extensible**
- Dễ thêm loader mới (Excel, PowerPoint...)
- Dễ thêm chunking strategy mới
- Dễ swap embedding model

### 2. **Robust Error Handling**
```python
results, errors = indexer.index_files(files)
# Nếu 1 file lỗi, các file khác vẫn được index
```

### 3. **Efficient Processing**
- Batch embedding → Nhanh hơn
- Caching → Tránh duplicate work
- Parallel processing (có thể thêm)

### 4. **Metadata Rich**
- Lưu đầy đủ thông tin file
- Dễ filter khi search
- Dễ tracking và debugging

### 5. **Re-indexing Support**
```python
# File thay đổi → Hash thay đổi → Update
# ON CONFLICT → Upsert
```

---

## 🚨 Lưu Ý Quan Trọng

### 1. **File Size Limits**
```python
# File quá lớn → Nhiều chunks → Chậm
# Khuyến nghị: < 10MB per file
```

### 2. **Encoding Issues**
```python
# Hệ thống tự detect encoding
# Fallback: chardet library
# Worst case: UTF-8 with errors='replace'
```

### 3. **Duplicate Detection**
```python
# Cùng content + metadata → Cùng hash
# Tự động skip nếu đã index
```

### 4. **Vector Store Size**
```python
# 1000 documents × 5 chunks × 384 dim × 4 bytes
# ≈ 7.3 MB
# Scalable đến millions of documents
```

---

## 🎓 Kết Luận

Workflow indexing document của bạn là một **production-ready pipeline** với:

✅ **5 bước rõ ràng**: Load → Chunk → Embed → Store → Metadata
✅ **Multi-format support**: PDF, DOCX, Markdown, Code, Text
✅ **Smart chunking**: Recursive + Code-aware strategies
✅ **Efficient embedding**: Batch processing + caching
✅ **Scalable storage**: Vector DB (Chroma) + SQLite
✅ **Error handling**: Graceful failures, detailed logging
✅ **Re-indexing**: Automatic update detection

Thiết kế này cho phép bạn index hàng ngàn documents và tìm kiếm semantic search với độ chính xác cao!


---

## 🔄 So Sánh: Document Indexing vs RAG Retrieval

### **Document Indexing (KHÔNG dùng LangGraph)**

```python
# Simple sequential pipeline
class DocumentIndexer:
    def index_document(self, document):
        # Bước 1: Load
        document = load_document(file_path)
        
        # Bước 2: Chunk
        chunks = chunking_strategy.chunk(document)
        
        # Bước 3: Embed
        embeddings = embedding_model.embed(texts)
        
        # Bước 4: Store
        vector_store.add(ids, embeddings, texts, metadatas)
        
        # Bước 5: Metadata
        self._upsert_document_metadata(document)
        
        return result
```

**Đặc điểm:**
- ✅ Tuần tự (sequential)
- ✅ Không có branching
- ✅ Không cần retry logic
- ✅ Đơn giản, dễ debug
- ✅ Chỉ cần try-catch cho error handling

---

### **RAG Retrieval (SỬ DỤNG LangGraph)**

```python
# Complex graph with branching and self-correction
class RAGSubgraph:
    def _build(self):
        builder = StateGraph(RAGSubgraphState)
        
        # Nodes
        builder.add_node("retrieve", retrieve_node)
        builder.add_node("grade_documents", grade_documents_node)
        builder.add_node("transform_query", transform_query_node)
        builder.add_node("generate", generate_node)
        builder.add_node("grade_generation", grade_generation_node)
        
        # Conditional edges (branching logic)
        builder.add_conditional_edges(
            "grade_documents",
            decide_to_generate,  # Quyết định: generate hay transform_query?
            {
                "generate": "generate",
                "transform_query": "transform_query"
            }
        )
        
        # Loop back for retry
        builder.add_edge("transform_query", "retrieve")
        
        return builder.compile()
```

**Đặc điểm:**
- ✅ Có branching (if-else logic)
- ✅ Có retry loops (self-correction)
- ✅ State management phức tạp
- ✅ Conditional edges
- ✅ Cần LangGraph để quản lý flow

---

## 🤔 Tại Sao Document Indexing KHÔNG Cần LangGraph?

### **1. Không Có Branching Logic**

**Indexing:**
```
Load → Chunk → Embed → Store → Metadata
(Luôn đi theo thứ tự này, không có nhánh)
```

**Retrieval:**
```
Retrieve → Grade
           ↓
    Có relevant? ──YES→ Generate
           ↓
          NO
           ↓
    Transform Query → Retrieve (loop back)
```

### **2. Không Cần Self-Correction**

**Indexing:**
- File load lỗi → Báo lỗi, skip file
- Chunk lỗi → Báo lỗi, skip file
- Không cần "thử lại với cách khác"

**Retrieval:**
- Không tìm được tài liệu → Viết lại câu hỏi, thử lại
- Câu trả lời không tốt → Viết lại câu hỏi, thử lại
- Cần logic phức tạp để quyết định retry

### **3. Không Cần State Management Phức Tạp**

**Indexing:**
```python
# State đơn giản: chỉ truyền document qua các bước
document → chunks → embeddings → stored
```

**Retrieval:**
```python
# State phức tạp: cần track nhiều thứ
state = {
    "question": "...",
    "transformed_query": "...",
    "documents": [...],
    "relevant_documents": [...],
    "generation": "...",
    "retry_count": 2,
    "generation_grade": "hallucination"
}
```

### **4. Error Handling Đơn Giản**

**Indexing:**
```python
try:
    result = index_file(file_path)
    results.append(result)
except Exception as exc:
    errors.append((file_path, str(exc)))
    # Continue với file tiếp theo
```

**Retrieval:**
```python
# Cần xử lý nhiều trường hợp:
if grade == "hallucination" and retry_count < MAX_RETRIES:
    return "transform_query"  # Thử lại
elif retry_count >= MAX_RETRIES:
    return "accept"  # Chấp nhận dù không tốt
else:
    return "accept"  # OK
```

---

## 📊 Khi Nào Nên Dùng LangGraph?

### ✅ **NÊN dùng LangGraph khi:**

1. **Có branching logic**
   - Cần quyết định đi đường nào dựa trên kết quả
   - Ví dụ: "Nếu tài liệu không liên quan → viết lại câu hỏi"

2. **Có retry/loop logic**
   - Cần thử lại với cách khác
   - Ví dụ: "Thử lại tối đa 2 lần"

3. **Có nhiều paths khác nhau**
   - Workflow phức tạp với nhiều nhánh
   - Ví dụ: Research agent với nhiều tools

4. **Cần state management phức tạp**
   - State thay đổi qua nhiều nodes
   - Cần track history, retry count, etc.

### ❌ **KHÔNG cần LangGraph khi:**

1. **Pipeline tuần tự đơn giản**
   - A → B → C → D (không có nhánh)
   - Ví dụ: Document indexing

2. **Không có conditional logic**
   - Luôn đi theo một đường duy nhất
   - Ví dụ: Data processing pipeline

3. **Không cần retry**
   - Lỗi → Báo lỗi, không thử lại
   - Ví dụ: Batch processing

4. **State đơn giản**
   - Chỉ truyền data qua các bước
   - Không cần track nhiều thông tin

---

## 🎯 Kết Luận

### **Document Indexing Workflow của bạn:**

```python
# ❌ KHÔNG dùng LangGraph
class DocumentIndexer:
    def index_document(self, document):
        # Simple sequential pipeline
        document = load_document(file_path)
        chunks = chunk(document)
        embeddings = embed(chunks)
        store(embeddings)
        save_metadata(document)
        return result
```

**Lý do:**
- ✅ Pipeline tuần tự, không có branching
- ✅ Không cần retry logic
- ✅ Error handling đơn giản (try-catch)
- ✅ Dễ hiểu, dễ maintain
- ✅ Performance tốt (không overhead của graph)

### **RAG Retrieval Workflow của bạn:**

```python
# ✅ SỬ DỤNG LangGraph
class RAGSubgraph:
    def _build(self):
        builder = StateGraph(RAGSubgraphState)
        # Complex graph with branching, retry, self-correction
        ...
        return builder.compile()
```

**Lý do:**
- ✅ Có branching (generate vs transform_query)
- ✅ Có retry loops (tối đa 2 lần)
- ✅ Self-correction (grade → retry nếu không tốt)
- ✅ State management phức tạp
- ✅ Cần LangGraph để quản lý flow

---

## 💡 Khuyến Nghị

**Đừng over-engineer!**

- Nếu workflow đơn giản → Dùng class/function bình thường
- Nếu workflow phức tạp → Dùng LangGraph

Document indexing của bạn đã được thiết kế đúng: **Simple pipeline, no LangGraph needed!** 🎉
