# Giải Thích Workflow RAG Tool Theo Mô Hình LangGraph

## 📋 Tổng Quan

RAG Tool trong project của bạn được xây dựng theo mô hình **Agentic RAG với Self-Correction** (tự sửa lỗi), sử dụng framework **LangGraph** để quản lý luồng xử lý phức tạp.

### Đặc điểm chính:
- ✅ **Tự động sửa lỗi**: Nếu kết quả không tốt, hệ thống tự động thử lại
- ✅ **Đánh giá thông minh**: LLM tự đánh giá chất lượng tài liệu và câu trả lời
- ✅ **Hybrid Search**: Kết hợp tìm kiếm từ khóa (BM25) và ngữ nghĩa (vector)
- ✅ **Giới hạn retry**: Tối đa 2 lần thử lại để tránh vòng lặp vô hạn

---

## 🔄 Workflow Chi Tiết

### **Sơ đồ tổng quan:**

```
START
  ↓
[1] retrieve (Tìm kiếm tài liệu)
  ↓
[2] grade_documents (Đánh giá tài liệu)
  ↓
  ├─ Có tài liệu liên quan? ──────────────────────┐
  │                                               │
  YES                                            NO + còn retry
  ↓                                               ↓
[4] generate (Tạo câu trả lời)          [3] transform_query (Viết lại câu hỏi)
  ↓                                               ↓
[5] grade_generation                         quay lại [1]
  ↓
  ├─ Câu trả lời tốt? ────────────────────────────┐
  │                                               │
  YES                                        NO + còn retry
  ↓                                               ↓
END (Trả kết quả)                          [3] transform_query
                                                  ↓
                                             quay lại [1]
```

---

## 🎯 Chi Tiết Từng Node

### **Node 1: `retrieve` - Tìm Kiếm Tài Liệu**

**Chức năng:** Tìm kiếm tài liệu liên quan đến câu hỏi

**Input:**
- `question`: Câu hỏi gốc của người dùng
- `transformed_query`: Câu hỏi đã được viết lại (nếu có)

**Xử lý:**
```python
# Ưu tiên dùng câu hỏi đã viết lại, nếu không có thì dùng câu hỏi gốc
query = state.get("transformed_query") or state["question"]

# Tìm kiếm hybrid (BM25 + vector)
docs = retrieval_node.retrieve(
    query=query,
    method="hybrid",        # Kết hợp keyword + semantic
    top_k=5,               # Lấy 5 tài liệu tốt nhất
    min_score=0.0,         # Không lọc theo điểm
    filters={
        "source_types": ["document", "code_file"]  # Chỉ tìm trong docs và code
    }
)
```

**Output:**
- `documents`: Danh sách 5 tài liệu tìm được (dạng dict với id, content, score, metadata)

**Ví dụ:**
```
Câu hỏi: "Làm thế nào để deploy ứng dụng?"
→ Tìm được 5 tài liệu về deployment, CI/CD, Docker...
```

---

### **Node 2: `grade_documents` - Đánh Giá Tài Liệu**

**Chức năng:** LLM đánh giá từng tài liệu có liên quan đến câu hỏi không

**Input:**
- `documents`: 5 tài liệu từ node retrieve
- `question`: Câu hỏi cần trả lời

**Xử lý:**
```python
# Tạo prompt cho LLM
prompt = """
Bạn là bộ đánh giá tài liệu. Đánh giá từng đoạn văn có liên quan không.

Câu hỏi: {question}

Tài liệu:
[1] Nội dung tài liệu 1...
[2] Nội dung tài liệu 2...
...

Trả lời JSON:
{"grades": [{"index": 1, "relevant": true}, {"index": 2, "relevant": false}, ...]}
"""

# LLM trả về đánh giá
response = llm.generate(prompt)
# → {"grades": [{"index": 1, "relevant": true}, {"index": 3, "relevant": true}]}

# Lọc chỉ giữ tài liệu relevant
relevant_docs = [docs[0], docs[2]]  # Chỉ giữ tài liệu 1 và 3
```

**Output:**
- `relevant_documents`: Danh sách tài liệu được đánh giá là liên quan

**Fallback:** Nếu LLM lỗi, dùng ngưỡng điểm: `score >= 0.4`

---

### **Edge: `decide_to_generate` - Quyết Định Tiếp Theo**

**Chức năng:** Quyết định có nên tạo câu trả lời hay viết lại câu hỏi

**Logic:**
```python
def decide_to_generate(state):
    relevant = state.get("relevant_documents") or []
    retry_count = state.get("retry_count", 0)
    
    # Có ít nhất 1 tài liệu liên quan → Tạo câu trả lời
    if len(relevant) >= 1:
        return "generate"
    
    # Không có tài liệu liên quan + còn retry → Viết lại câu hỏi
    if retry_count < MAX_RETRIES:  # MAX_RETRIES = 2
        return "transform_query"
    
    # Hết retry → Tạo câu trả lời với context hiện có
    return "generate"
```

**Kết quả:**
- `"generate"` → Chuyển đến node 4
- `"transform_query"` → Chuyển đến node 3

---

### **Node 3: `transform_query` - Viết Lại Câu Hỏi**

**Chức năng:** LLM viết lại câu hỏi để tìm kiếm tốt hơn

**Input:**
- `question`: Câu hỏi gốc
- `retry_count`: Số lần đã thử

**Xử lý:**
```python
prompt = """
Bạn là chuyên gia tối ưu hoá truy vấn tìm kiếm.

Câu hỏi gốc: {question}
Lần thử: {retry_count}

Các tài liệu tìm được không đủ liên quan.
Hãy viết lại câu hỏi chi tiết và kỹ thuật hơn.

Chỉ trả về câu hỏi đã viết lại.
"""

rewritten = llm.generate(prompt)
```

**Output:**
- `transformed_query`: Câu hỏi mới
- `retry_count`: Tăng lên 1

**Ví dụ:**
```
Gốc: "Làm sao deploy?"
→ Viết lại: "Quy trình deployment ứng dụng Python lên production server sử dụng Docker và CI/CD pipeline"
```

**Sau đó:** Quay lại node 1 (retrieve) với câu hỏi mới

---

### **Node 4: `generate` - Tạo Câu Trả Lời**

**Chức năng:** Tạo câu trả lời dựa trên tài liệu liên quan

**Input:**
- `question`: Câu hỏi gốc
- `relevant_documents`: Tài liệu đã được đánh giá là liên quan
- `history`: Lịch sử hội thoại (nếu có)

**Xử lý:**
```python
# Xây dựng context từ tài liệu
context_blocks = []
citations = []

for idx, doc in enumerate(relevant_documents, start=1):
    source = doc["metadata"]["file_path"]  # Ví dụ: "docs/deployment.md"
    snippet = doc["content"][:800]  # Lấy 800 ký tự đầu
    
    context_blocks.append(f"[{idx}] {source}\n{snippet}")
    citations.append(source)

# Tạo prompt với context
augmented_question = f"""
Bạn được cung cấp ngữ cảnh từ tài liệu nội bộ.
Ưu tiên trả lời dựa trên các đoạn này.

=== NGỮ CẢNH NỘI BỘ ===
{context_text}

=== CÂU HỎI NGƯỜI DÙNG ===
{question}
"""

# LLM tạo câu trả lời
generation = llm.generate(augmented_question, history)
```

**Output:**
- `generation`: Câu trả lời được tạo
- `citations`: Danh sách nguồn tài liệu (không trùng lặp)

**Ví dụ:**
```
Generation: "Để deploy ứng dụng, bạn cần: 1) Build Docker image, 2) Push lên registry..."
Citations: ["docs/deployment.md", "scripts/deploy.sh"]
```

---

### **Node 5: `grade_generation` - Đánh Giá Câu Trả Lời**

**Chức năng:** LLM tự đánh giá chất lượng câu trả lời

**Input:**
- `question`: Câu hỏi gốc
- `generation`: Câu trả lời vừa tạo
- `relevant_documents`: Tài liệu tham khảo

**Xử lý:**
```python
prompt = """
Đánh giá câu trả lời AI theo hai tiêu chí:
1. Có dựa trên tài liệu (không bịa đặt)
2. Có trả lời đúng câu hỏi

Câu hỏi: {question}

Tài liệu tham khảo:
{context}

Câu trả lời AI: {generation}

Trả lời JSON:
{"grade": "grounded_and_useful", "reason": "..."}

Giá trị hợp lệ: "grounded_and_useful" | "hallucination" | "not_useful"
"""

response = llm.generate(prompt)
# → {"grade": "grounded_and_useful", "reason": "Câu trả lời dựa trên docs/deployment.md"}
```

**Output:**
- `generation_grade`: Một trong 3 giá trị:
  - `"grounded_and_useful"`: Tốt, dựa trên tài liệu và trả lời đúng
  - `"hallucination"`: Bịa đặt thông tin không có trong tài liệu
  - `"not_useful"`: Không trả lời đúng câu hỏi

---

### **Edge: `decide_after_generation_grade` - Quyết Định Cuối Cùng**

**Chức năng:** Quyết định chấp nhận câu trả lời hay thử lại

**Logic:**
```python
def decide_after_generation_grade(state):
    grade = state.get("generation_grade")
    retry_count = state.get("retry_count", 0)
    
    # Câu trả lời tốt → Chấp nhận
    if grade == "grounded_and_useful":
        return "accept"  # → END
    
    # Câu trả lời không tốt + còn retry → Viết lại câu hỏi
    if retry_count < MAX_RETRIES:
        return "transform_query"  # → Node 3 → Node 1
    
    # Hết retry → Chấp nhận dù không tốt (tránh vòng lặp vô hạn)
    return "accept"  # → END
```

---

## 📊 State Management (Quản Lý Trạng Thái)

LangGraph sử dụng một **state dictionary** để truyền dữ liệu giữa các node:

```python
class RAGSubgraphState(TypedDict):
    # Input ban đầu
    question: str                    # Câu hỏi gốc (không đổi)
    history: list[dict]              # Lịch sử hội thoại
    
    # Dữ liệu trung gian
    transformed_query: str           # Câu hỏi đã viết lại
    documents: list[dict]            # Tài liệu tìm được
    relevant_documents: list[dict]   # Tài liệu liên quan
    
    # Output
    generation: str                  # Câu trả lời
    citations: list[str]             # Nguồn tài liệu
    
    # Metadata
    retry_count: int                 # Số lần thử lại
    generation_grade: str            # Đánh giá chất lượng
```

**Cách hoạt động:**
- Mỗi node nhận state, xử lý, và trả về **partial update**
- LangGraph tự động merge update vào state
- State được truyền tiếp cho node tiếp theo

---

## 🔁 Ví Dụ Luồng Thực Tế

### **Scenario 1: Thành công ngay lần đầu**

```
User: "Làm thế nào để chạy tests?"

[1] retrieve
    → Tìm được: test_guide.md, pytest_config.py, run_tests.sh
    
[2] grade_documents
    → LLM: "test_guide.md và pytest_config.py liên quan"
    → relevant_documents = [test_guide.md, pytest_config.py]
    
[Edge] decide_to_generate
    → len(relevant_documents) = 2 >= 1
    → return "generate"
    
[4] generate
    → Context: test_guide.md + pytest_config.py
    → Generation: "Để chạy tests, sử dụng lệnh `pytest tests/`..."
    → Citations: ["test_guide.md", "pytest_config.py"]
    
[5] grade_generation
    → LLM: "Câu trả lời dựa trên tài liệu và trả lời đúng"
    → grade = "grounded_and_useful"
    
[Edge] decide_after_generation_grade
    → grade == "grounded_and_useful"
    → return "accept" → END

✅ Kết quả: Trả về câu trả lời + citations
```

---

### **Scenario 2: Cần viết lại câu hỏi**

```
User: "Deploy như nào?"

[1] retrieve (retry_count=0)
    → Tìm được: random_docs.md, unrelated.py
    
[2] grade_documents
    → LLM: "Không có tài liệu nào liên quan"
    → relevant_documents = []
    
[Edge] decide_to_generate
    → len(relevant_documents) = 0
    → retry_count = 0 < 2
    → return "transform_query"
    
[3] transform_query
    → LLM viết lại: "Quy trình deployment ứng dụng lên production"
    → transformed_query = "Quy trình deployment..."
    → retry_count = 1
    
[1] retrieve (retry_count=1)
    → Tìm với câu hỏi mới
    → Tìm được: deployment_guide.md, docker_setup.md
    
[2] grade_documents
    → LLM: "Cả 2 tài liệu đều liên quan"
    → relevant_documents = [deployment_guide.md, docker_setup.md]
    
[Edge] decide_to_generate
    → len(relevant_documents) = 2 >= 1
    → return "generate"
    
[4] generate
    → Generation: "Để deploy, thực hiện các bước..."
    
[5] grade_generation
    → grade = "grounded_and_useful"
    
[Edge] decide_after_generation_grade
    → return "accept" → END

✅ Kết quả: Thành công sau 1 lần retry
```

---

### **Scenario 3: Hết retry budget**

```
User: "Câu hỏi rất mơ hồ không rõ ràng"

[1] retrieve (retry_count=0)
    → Không tìm được gì phù hợp
    
[2] grade_documents
    → relevant_documents = []
    
[Edge] → transform_query

[3] transform_query (retry_count=1)
    → Viết lại câu hỏi
    
[1] retrieve (retry_count=1)
    → Vẫn không tìm được
    
[2] grade_documents
    → relevant_documents = []
    
[Edge] → transform_query

[3] transform_query (retry_count=2)
    → Viết lại lần 2
    
[1] retrieve (retry_count=2)
    → Vẫn không tìm được
    
[2] grade_documents
    → relevant_documents = []
    
[Edge] decide_to_generate
    → retry_count = 2 >= MAX_RETRIES
    → return "generate" (graceful degradation)
    
[4] generate
    → Tạo câu trả lời với context rỗng
    → Generation: "Xin lỗi, tôi không tìm thấy thông tin..."
    
[5] grade_generation
    → grade = "not_useful"
    
[Edge] decide_after_generation_grade
    → retry_count = 2 >= MAX_RETRIES
    → return "accept" (tránh vòng lặp vô hạn)

⚠️ Kết quả: Trả về câu trả lời không đầy đủ nhưng không bị treo
```

---

## ⚙️ Configuration (Cấu Hình)

Các tham số quan trọng trong `RAGConfig`:

```python
# Tìm kiếm
default_search_method: "hybrid"     # fts | vector | hybrid
fts_weight: 0.3                     # Trọng số keyword search
vector_weight: 0.7                  # Trọng số semantic search
default_top_k: 5                    # Số tài liệu trả về
min_relevance_score: 0.3            # Ngưỡng điểm tối thiểu

# Re-ranking
enable_reranking: True              # Bật/tắt re-ranking
reranker_model: "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Chunking
chunk_size: 512                     # Kích thước chunk (tokens)
chunk_overlap: 50                   # Overlap giữa các chunk

# Advanced features (chưa dùng trong subgraph hiện tại)
enable_query_expansion: False       # Mở rộng câu hỏi
enable_compression: False           # Nén context
enable_citations: False             # Tracking citations chi tiết
```

---

## 🎯 Ưu Điểm Của Thiết Kế Này

### 1. **Self-Correction (Tự Sửa Lỗi)**
- Không chấp nhận kết quả kém chất lượng
- Tự động thử lại với câu hỏi tốt hơn
- Giảm hallucination

### 2. **Graceful Degradation**
- Luôn trả về kết quả (không bị treo)
- Giới hạn retry tránh vòng lặp vô hạn
- Fallback khi LLM lỗi

### 3. **Transparency (Minh Bạch)**
- Trả về citations (nguồn tài liệu)
- Metadata về quá trình (retry_count, grade)
- Dễ debug và monitor

### 4. **Modularity (Tính Mô-đun)**
- Mỗi node độc lập, dễ test
- Dễ thêm/sửa node mới
- Có thể tái sử dụng node

---

## 🚀 Cải Tiến Tiềm Năng

### 1. **Thêm Query Expansion**
```python
# Trong retrieve_node
if config.enable_query_expansion:
    expanded_queries = query_expander.expand(query)
    # Tìm kiếm với nhiều biến thể câu hỏi
```

### 2. **Contextual Compression**
```python
# Trong generate_node
if config.enable_compression:
    compressed_docs = compressor.compress(query, relevant_documents)
    # Chỉ giữ phần liên quan nhất
```

### 3. **Multi-Query Retrieval**
```python
# Phân tách câu hỏi phức tạp
if is_complex_question(question):
    sub_queries = decompose_query(question)
    # Tìm kiếm cho từng sub-query
```

### 4. **Adaptive Retry Strategy**
```python
# Thay đổi strategy dựa trên lý do thất bại
if grade == "hallucination":
    # Tăng trọng số cho grounding
elif grade == "not_useful":
    # Viết lại câu hỏi chi tiết hơn
```

---

## 📚 Tài Liệu Tham Khảo

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **Corrective RAG Paper**: https://arxiv.org/abs/2401.15884
- **Self-RAG Paper**: https://arxiv.org/abs/2310.11511

---

## 🎓 Kết Luận

Workflow RAG Tool của bạn là một **agentic system** thông minh với khả năng:
- ✅ Tự đánh giá chất lượng
- ✅ Tự sửa lỗi khi cần
- ✅ Tối ưu hóa câu hỏi
- ✅ Đảm bảo grounding (dựa trên tài liệu)

Thiết kế này phù hợp cho **production** vì:
- Robust (xử lý lỗi tốt)
- Transparent (có citations và metadata)
- Scalable (dễ mở rộng thêm tính năng)
