# Project này làm gì? — Giải thích cho người không phải lập trình viên

Dự án này là một **trợ lý AI tiếng Việt** giống ChatGPT, nhưng có **2 siêu năng lực** mà ChatGPT bình thường không có:

1. 🌐 **Tra cứu Internet realtime** (giá vàng hôm nay, lễ hội sắp tới, tin mới...)
2. 📚 **Nhớ tài liệu riêng của bạn** (file PDF, Word, code) và trả lời kèm trích dẫn nguồn

Nó chạy như một website: bạn gõ câu hỏi → AI trả lời → có link nguồn kèm theo.

---

## 1. Hãy tưởng tượng như một toà soạn báo

Khi bạn hỏi một câu, trong hậu trường có **cả một toà soạn** làm việc cùng lúc:

```
                      Bạn gõ câu hỏi
                             │
                             ▼
               ┌─────────────────────────┐
               │  👋 Lễ tân (entry)      │  "Xin chào, để tôi xử lý"
               └─────────────────────────┘
                             │
                             ▼
               ┌─────────────────────────┐
               │  🧐 Biên tập viên       │  "Câu này dễ hay khó?"
               │    (complexity)         │
               └─────────────────────────┘
                     │              │
          (dễ) ──────┘              └────── (khó)
                     │                          │
                     ▼                          ▼
             ┌──────────────┐        ┌───────────────────┐
             │ 🤖 Chatbot   │        │ 🚦 Điều phối viên │
             │  trả lời ngay│        │   (router)        │
             └──────────────┘        │ "Hỏi ngày? Tin    │
                     │               │  tức? Câu thường?"│
                     │               └───────────────────┘
                     │                   │      │      │
                     │                   │      │      └──── (câu thường)
                     │                   │      │                 │
                     │                   │      │                 ▼
                     │                   │      │          ┌──────────────┐
                     │                   │      │          │ 🤖 Trả lời   │
                     │                   │      │          │   thường     │
                     │                   │      │          └──────────────┘
                     │                   │      │                 │
                     │                   │      │  (ngày hôm nay) │
                     │                   │      ▼                 │
                     │                   │ ┌─────────────┐        │
                     │                   │ │ 📅 Về ngày  │        │
                     │                   │ │   hôm nay   │        │
                     │                   │ └─────────────┘        │
                     │                   │       │                │
                     │            (tin   │       │                │
                     │            tức)   │       │                │
                     │                   ▼       │                │
                     │           ┌──────────────┐│                │
                     │           │ 📋 Lập kế    ││                │
                     │           │   hoạch      ││                │
                     │           │  (planning)  ││                │
                     │           └──────────────┘│                │
                     │                   │       │                │
                     │                   ▼       │                │
                     │           ┌──────────────┐│                │
                     │           │ 🔍 Tra Google││                │
                     │           │   + Tavily   ││                │
                     │           │  (research)  ││                │
                     │           └──────────────┘│                │
                     │                   │       │                │
                     │                   ▼       │                │
                     │           ┌──────────────┐│                │
                     │           │ ✍️ Soạn bài  ││                │
                     │           │  (synthesis) ││                │
                     │           └──────────────┘│                │
                     │                   │       │                │
                     │                   ▼       │                │
                     │           ┌──────────────┐│                │
                     │           │ 📎 Thêm nguồn││                │
                     │           │  (citation)  ││                │
                     │           └──────────────┘│                │
                     │                   │       │                │
                     └─────┬─────────────┴───────┴────────────────┘
                           ▼
                  ┌────────────────┐
                  │ 💾 Lưu vào sổ  │   ← mọi câu đều lưu lại để
                  │    (persist)   │     lần sau hỏi còn nhớ
                  └────────────────┘
                           │
                           ▼
                     Câu trả lời
```

**Chú ý**: nhánh "tin tức" đi **tuần tự** 4 bước — Lập kế hoạch xong mới Tra Google, Tra xong mới Soạn, Soạn xong mới Thêm nguồn. Giống toà soạn: phóng viên phải **biết phải phỏng vấn ai** (plan) trước khi **đi phỏng vấn** (research), rồi mới **viết bài** (synthesis), rồi mới **dẫn nguồn** (citation).

**Mỗi ô vuông là một "nhân viên"** chuyên một việc. Cách thiết kế này gọi là **LangGraph** — giống sơ đồ quy trình trong công ty, mỗi bước rõ ràng, có thể sửa một bước mà không đổ vỡ cả hệ thống.

---

## 2. Ví dụ thực tế: bạn hỏi 3 câu khác nhau

### Câu 1: "Chào, bạn khoẻ không?"

```
👋 Lễ tân → 🧐 "Câu này dễ" → 🤖 Chatbot trả lời ngay → 💾 Lưu
```

⏱️ ~2 giây

### Câu 2: "Hôm nay là ngày mấy?"

```
👋 Lễ tân → 🧐 "Câu này khó (cần biết ngày)" → 🚦 "Hỏi về ngày"
         → 📅 Trả về ngày hệ thống → 💾 Lưu
```

⏱️ ~1 giây (không cần AI, lấy ngay từ đồng hồ máy)

### Câu 3: "Đà Nẵng sắp tới có lễ hội gì không?"

```
👋 Lễ tân → 🧐 "Câu này khó" → 🚦 "Cần điều tra (từ khoá 'sắp tới', 'lễ hội')"
         → 📋 Lập kế hoạch: {tìm "lễ hội Đà Nẵng 2026", "sự kiện Đà Nẵng tháng tới"}
         → 🔍 Gọi Google + Tavily lấy 5-10 bài báo
         → ✍️ Đọc các bài → soạn câu trả lời
         → 📎 Kèm link 3-5 nguồn tham khảo
         → 💾 Lưu
```

⏱️ ~15-30 giây

---

## 3. Ngoài tra cứu Internet, AI còn "đọc tài liệu riêng của bạn"

Đây là phần gọi là **RAG** (Retrieval-Augmented Generation).

**Tưởng tượng**: bạn đưa cho AI 1 cuốn sách 500 trang. Nhưng bạn không muốn AI đọc cả 500 trang mỗi lần bạn hỏi (quá chậm, quá tốn tiền). Vậy phải làm sao?

### Bước 1 — **Cắt sách thành miếng nhỏ** (indexing)

```
📖 File PDF / Word / Markdown
       │
       ▼
   ✂️ Cắt thành ~100 đoạn nhỏ (~512 chữ mỗi đoạn)
       │
       ▼
   🧮 Mỗi đoạn được "chấm điểm ý nghĩa" thành một dãy 384 số
      (gọi là "embedding" — giống toạ độ GPS của đoạn văn trên
      bản đồ ý nghĩa: đoạn gần nhau về nội dung thì toạ độ gần nhau)
       │
       ▼
   📦 Lưu vào 2 kho:
      - Kho "từ khoá" (SQLite FTS): tìm nhanh bằng từ chính xác
      - Kho "ý nghĩa" (ChromaDB): tìm nhanh bằng nội dung tương tự
```

### Bước 2 — **Khi bạn hỏi, AI tìm đoạn liên quan** (retrieval)

Giả sử bạn hỏi: *"Project này dùng công nghệ gì?"*

```
❓ Câu hỏi
   │
   ├─► Tìm trong kho từ khoá:    "công nghệ", "dùng"
   │
   └─► Tìm trong kho ý nghĩa:    đoạn có nội dung gần với
                                 "tech stack", "framework", "thư viện"
   │
   ▼
   🔀 Gộp 2 kết quả → sắp xếp theo độ liên quan → lấy top 8 đoạn
   │
   ▼
   🎯 Nhờ "giám khảo AI" (rerank) chọn lại top 3 đoạn chuẩn nhất
   │
   ▼
   📝 Đưa 3 đoạn này cho AI cùng với câu hỏi:
      "Dựa vào 3 đoạn sau, hãy trả lời câu hỏi: ..."
   │
   ▼
   💬 AI trả lời + kèm trích dẫn (đoạn ở file nào, trang mấy)
```

**Vì sao phải làm phức tạp vậy?** → Để AI **không bịa** (hallucination). Nó chỉ được trả lời dựa trên nội dung thật trong tài liệu, chứ không phải tự "sáng tác" ra.

### Self-correcting RAG — AI tự sửa sai

Có lúc AI tìm đoạn văn không đúng. Hệ thống có cơ chế tự kiểm:

```
🔍 Tìm đoạn → ⚖️ "Đoạn này có liên quan không?"
                  │              │
            (có)  │              │  (không)
                  ▼              ▼
            ✍️ Viết trả lời   ✏️ Viết lại câu hỏi cho rõ hơn
                  │              → tìm lại (tối đa 2 lần)
                  ▼
            ⚖️ "Câu trả lời có dựa vào đoạn văn không?
                 Có trả lời đúng câu hỏi không?"
                  │              │
            (có)  │              │  (không)
                  ▼              ▼
            ✅ Trả về người dùng  ✏️ Viết lại → thử lại
```

Giống một học sinh viết bài xong tự đọc lại, thấy sai thì xoá viết lại.

---

## 4. Kiến trúc tổng thể — 3 tầng như một nhà hàng

```
┌──────────────────────────────────────────────────────────────┐
│  🍽️  TẦNG 1: KHÁCH (Frontend - React)                       │
│                                                              │
│  Trang web bạn nhìn thấy. Giống menu nhà hàng:               │
│  gõ câu hỏi, chọn model AI, xem câu trả lời.                 │
└──────────────────────────────────────────────────────────────┘
                           │
                           │  HTTP / Server-Sent Events
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  👨‍🍳  TẦNG 2: BẾP (Backend - FastAPI + LangGraph)            │
│                                                              │
│  - FastAPI: cửa sổ nhận đơn hàng (API endpoints)             │
│  - LangGraph: đầu bếp trưởng điều phối các nhân viên         │
│  - Skills: 12 nhân viên chuyên môn (phân loại, tra cứu, ...)  │
└──────────────────────────────────────────────────────────────┘
                           │
                           │
         ┌─────────────────┼──────────────────┬────────────┐
         ▼                 ▼                  ▼            ▼
┌────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐
│  🧠 LLM        │ │  🔍 Search   │ │  📚 RAG      │ │  💾 DB   │
│  (Gemini/Groq) │ │  (Google +   │ │  (Chroma +   │ │ (SQLite) │
│                │ │   Tavily)    │ │   FTS5)      │ │          │
│  Nguồn         │ │              │ │              │ │  Ghi     │
│  "trí tuệ"     │ │  Nguồn       │ │  Nguồn tài   │ │  chép    │
│                │ │  tin tức     │ │  liệu riêng  │ │  mọi     │
│                │ │              │ │              │ │  cuộc    │
│                │ │              │ │              │ │  hội     │
│                │ │              │ │              │ │  thoại   │
└────────────────┘ └──────────────┘ └──────────────┘ └──────────┘
       TẦNG 3: DỊCH VỤ NGOÀI (các API bên thứ 3) + DATA
```

### Khi nào dùng gì?

| Câu hỏi | Dùng gì |
|---------|---------|
| *"Đạo hàm của x² là gì?"* | Chỉ LLM (Gemini) — kiến thức có sẵn |
| *"Giá Bitcoin hôm nay?"* | LLM + Search (Google/Tavily) — cần realtime |
| *"Trong file ABC.pdf nói gì về chương 3?"* | LLM + RAG (Chroma + FTS5) — cần tài liệu riêng |
| *"Lần trước tôi hỏi bạn về gì?"* | LLM + DB (SQLite lịch sử chat) — cần trí nhớ |

---

## 4.5. Workflow của Skill — hậu trường của từng "nhân viên"

Ở các phần trên tôi dùng ẩn dụ "nhân viên toà soạn". Trong code thật, mỗi nhân viên đó là một **skill** — một folder độc lập, có thể sửa không cần đụng tới phần khác.

### A. Một skill gồm đúng 3 file

```
backend/src/skills/complexity_classifier/
├── skill.yaml      ← NHÃN: tên, phiên bản, cấu hình (dùng model nào, nhiệt độ bao nhiêu)
├── prompt.md       ← KỊCH BẢN: câu lệnh bằng tiếng Anh/Việt mà AI phải làm theo
└── handler.py      ← BỘ NÃO: code Python nhận câu hỏi, gọi AI, xử lý câu trả lời
```

**Nhìn cụ thể**:

`skill.yaml` — 7 dòng cấu hình thôi:
```yaml
name: complexity_classifier
version: 1
description: Phân loại câu hỏi đơn giản hay phức tạp
temperature: 0.0          # AI trả lời "lạnh", không sáng tạo lan man
max_output_tokens: 150    # tối đa 150 từ trả về
llm: true                 # skill này có gọi AI (khác với query_router không cần AI)
```

`prompt.md` — kịch bản cho AI:
```
Phân loại câu hỏi người dùng là đơn giản hay phức tạp.
Trả về JSON với các khoá: is_complex (đúng/sai), confidence (0-1), reason (lý do).

Câu PHỨC TẠP:
- Sự kiện sắp tới, lễ hội
- Giá cả realtime, tin tức mới
- Phân tích so sánh đa bước

Câu ĐƠN GIẢN:
- Chào hỏi, small talk
- Định nghĩa kiến thức phổ thông

Câu hỏi của người dùng: {{ message }}
```

Trong đó `{{ message }}` là chỗ trống — khi chạy, hệ thống **điền câu hỏi thật của bạn** vào đó.

`handler.py` — bộ não (rút gọn để dễ đọc):
```python
class Handler(BaseSkill):
    class Inputs:
        message: str              # đầu vào: câu hỏi của user

    class Outputs:
        is_complex: bool          # đầu ra: đúng/sai
        confidence: float
        reason: str

    # Phần còn lại: BaseSkill tự làm — đọc prompt.md, gọi AI, parse JSON, validate output
```

### B. Một lượt hỏi đi qua skill như thế nào?

Giả sử bạn gõ: *"Đà Nẵng sắp tới có lễ hội gì không?"*

```
  BẠN GÕ CÂU HỎI
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ complexity_node (là một "nhân viên" trong LangGraph)         │
│                                                              │
│ Nhân viên này KHÔNG TỰ LÀM GÌ. Nó chỉ gọi skill:             │
│                                                              │
│   skill = registry.get("complexity_classifier")              │
│   kết_quả = skill.invoke({"message": "Đà Nẵng sắp..."})     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ skill.invoke() trong BaseSkill — 6 BƯỚC:                     │
│                                                              │
│ 1. Kiểm tra input hợp lệ?     {"message": "..."} ✓           │
│                                                              │
│ 2. Đọc prompt.md, điền {{ message }}                         │
│    → "Phân loại... Câu hỏi của người dùng:                   │
│        Đà Nẵng sắp tới có lễ hội gì không?"                 │
│                                                              │
│ 3. Chọn model AI nào để gọi?                                 │
│    - User có ghi model trong request? → dùng                 │
│    - skill.yaml có ghi? → dùng                               │
│    - Không có? → dùng env DEFAULT_MODEL (mặc định Gemini)    │
│                                                              │
│ 4. Gọi API Gemini với prompt đã render                       │
│    → Gemini trả về: '{"is_complex": true,                   │
│                      "confidence": 0.95,                     │
│                      "reason": "Hỏi về lễ hội sắp tới"}'     │
│                                                              │
│ 5. Parse JSON (chịu được khi Gemini gói trong ```json...```) │
│                                                              │
│ 6. Kiểm tra output hợp lệ? → trả về Python dict              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ complexity_node nhận lại kết quả:                            │
│   {"is_complex": true, "confidence": 0.95, "reason": "..."}  │
│                                                              │
│ Cập nhật state của LangGraph:                                │
│   state.query_type = "complex"                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
 LangGraph đi tiếp → router → planning → research → ...
```

### C. Điểm hay: nhân viên và skill có thể thay riêng

**Kịch bản 1**: Bạn muốn AI nghiêm khắc hơn khi phân loại.

👉 Chỉ sửa **1 câu trong `prompt.md`**, **không đụng code Python**:
```diff
- Mark is_complex=true only if request needs multi-step research
+ Mark is_complex=true even for single-fact questions about current events
```

Lưu file → PromptSource nhận ra file đã đổi (check mtime) → lần invoke tiếp theo dùng prompt mới. **Không cần restart**.

**Kịch bản 2**: Bạn muốn đổi sang model mạnh hơn cho riêng skill này.

👉 Sửa **`skill.yaml`**:
```diff
  name: complexity_classifier
+ model: gemini/gemini-2.5-pro    # dùng model "pro" cho skill này
  temperature: 0.0
```

Restart (YAML không auto-reload) → chỉ skill này dùng Pro, các skill khác vẫn dùng mặc định.

**Kịch bản 3**: Skill mới: thêm "nhân viên chuyên dịch tiếng Trung".

👉 Tạo folder `skills/translate_chinese/` với 3 file. Restart. Registry tự discover. Gọi `registry.get("translate_chinese").invoke({...})` được luôn. **Không sửa LangGraph, không sửa FastAPI**.

### D. 12 nhân viên hiện tại trong "toà soạn"

| Nhân viên (skill) | Làm gì | Gọi AI? |
|---|---|---|
| `complexity_classifier` | Phân loại câu hỏi dễ/khó | ✓ |
| `query_router` | Chọn nhánh xử lý (ngày, tin tức, câu thường) | ✗ — dùng danh sách từ khoá trong YAML |
| `planning` | Lập kế hoạch tra cứu (tối đa 5 task) | ✓ |
| `research_search` | Gọi Tavily + AI rút trích thông tin | ✓ |
| `direct_answer` | AI trả lời trực tiếp có history | ✓ |
| `response_composer` | Soạn câu trả lời từ kết quả tra cứu | ✓ |
| `rag.retrieve` | Tìm trong tài liệu bạn upload | ✗ — dùng FTS + ChromaDB |
| `rag.query_expand` | Sinh biến thể câu hỏi | ✗ — thuật toán |
| `rag.transform_query` | Viết lại câu hỏi khi tìm không ra | ✓ |
| `rag.grade_documents` | AI chấm xem đoạn văn có liên quan không | ✓ |
| `rag.grade_generation` | AI kiểm xem câu trả lời có dựa trên tài liệu không | ✓ |
| `rag.answer_with_context` | Sinh câu trả lời từ 3-5 đoạn văn đã chọn | ✓ |

### E. Bức tranh lớn — skill khớp vào đâu trong sơ đồ?

Nhớ sơ đồ "toà soạn" ở phần 1? **Mỗi ô vuông trong đó là một node**, và mỗi node **chỉ gọi 1-2 skill** tương ứng:

```
LangGraph node             →    Skill nó gọi
──────────────────────────────────────────────────────────
complexity_node            →    complexity_classifier
router_node                →    query_router
planning_node              →    planning
research_node              →    research_search  (gọi song song nhiều lần)
synthesis_node             →    response_composer HOẶC direct_answer
simple_llm, direct_llm     →    direct_answer    (+ có thể gọi RAG subgraph)

RAG subgraph (chạy trong simple_llm/direct_llm khi cần):
  retrieve                 →    rag.retrieve
  grade_documents          →    rag.grade_documents
  transform_query          →    rag.transform_query
  generate                 →    rag.answer_with_context
  grade_generation         →    rag.grade_generation
```

### F. Tại sao tách ra như vậy? 3 lợi ích

1. **Sửa 1 chỗ, không sợ vỡ chỗ khác**
   Trước đây prompt nằm rải rác trong 9 file Python. Muốn đổi lời chỉ AI phải đọc code, mò từng dòng, dễ sai. Giờ mỗi skill là 1 folder, 3 file, đọc riêng hiểu riêng.

2. **Người không biết code cũng sửa được prompt**
   `prompt.md` là file markdown tiếng Việt, đọc bình thường. Product manager, content writer đều sửa được. Lập trình viên chỉ cần code cho các skill mới.

3. **Test dễ — dùng "nhân viên giả" (stub)**
   Khi test, không gọi AI thật (tốn tiền, chậm). Thay vào đó:
   ```python
   skill._adapter_factory = lambda m: FakeAdapter("câu trả lời giả")
   ```
   Skill dùng "AI giả" này → test chạy trong 1 giây, không tốn API call.

   Toàn project hiện có **175 unit test** chạy theo kiểu này.

---

## 5. Điểm đặc biệt của project này

### 🎯 1. Prompt tách khỏi code (Skill framework)

Trước đây: prompt (câu lệnh chỉ AI phải làm gì) nằm **rải rác trong 9 file Python** → sửa 1 câu phải đọc code, dễ sai.

Bây giờ: mỗi "nhân viên" là một **folder độc lập** gồm 3 file:

```
skills/complexity_classifier/
├── skill.yaml      ← cấu hình: dùng model nào, timeout bao lâu
├── prompt.md       ← câu lệnh bằng tiếng Việt, ai cũng đọc được
└── handler.py      ← code xử lý input/output
```

**Lợi ích**: muốn AI trả lời khác đi → chỉ sửa `prompt.md`. File tự **reload** trong 1 giây, không cần restart.

### 🔄 2. Đổi keyword routing không cần code

Trước đây: câu "Đà Nẵng **sắp tới** có lễ hội gì" bị AI phân loại sai thành "câu dễ" (thực ra là "khó, cần tra cứu"). Fix phải sửa Python code.

Bây giờ: chỉ cần sửa file YAML:

```yaml
# backend/src/skills/query_router/skill.yaml
research_keywords:
  - sắp tới
  - lễ hội
  - sự kiện
  - upcoming
```

Thêm keyword → restart → xong. Người không code cũng sửa được.

### 🧠 3. Nhớ cả bạn + tài liệu bạn + lịch sử chat

3 nguồn "bộ nhớ":

- **Lịch sử chat** (SQLite) — bạn hỏi tuần trước, tuần này hỏi lại vẫn nhớ
- **Tài liệu bạn upload** (ChromaDB) — PDF/Word/Markdown/Code
- **Internet realtime** (Google/Tavily) — thông tin mới mỗi ngày

AI tự quyết định cần nguồn nào cho câu hỏi cụ thể.

### 🎨 4. Dùng cũng đơn giản

1 dòng lệnh chạy cả hệ thống:

```bash
docker compose up
```

→ Mở trình duyệt → http://localhost:5173 → chat.

---

## 6. Phân biệt với ChatGPT / Claude web

| Tiêu chí | ChatGPT / Claude web | Project này |
|----------|---------------------|-------------|
| Tra cứu Internet | Có (GPT-4o) | Có (qua Google + Tavily) |
| Nhớ tài liệu riêng | Phải upload mỗi lần | Index 1 lần, dùng mãi |
| Trích dẫn nguồn | Ít | Luôn có (RAG) |
| Chạy offline/private | Không | **Có** (bạn tự host) |
| Đổi prompt / logic | Không | **Có** (sửa skill.yaml/prompt.md) |
| Tiếng Việt | Có | **Tối ưu cho tiếng Việt** |
| Chi phí | Trả theo tháng | Trả theo request gọi API (rẻ hơn với dùng cá nhân) |

**Ngắn gọn**: ChatGPT là iPhone khoá máy. Project này là điện thoại Android unlock — bạn mod được.

---

## 7. Ai nên dùng?

- 👨‍💼 **Doanh nghiệp**: chatbot nội bộ biết đọc tài liệu công ty, không gửi data ra ngoài
- 👨‍🏫 **Giáo viên/Học sinh**: hỏi đáp dựa trên giáo trình riêng
- 👨‍💻 **Developer**: hỏi đáp về codebase công ty (index code xong hỏi "hàm X ở file nào?")
- 📚 **Researcher**: thư viện tài liệu cá nhân, hỏi là có nguồn luôn
- 🎓 **Người học AI**: example project đầy đủ cho LangGraph + RAG

---

## 8. Ví dụ 1 cuộc hội thoại thật

```
Bạn: Project này dùng công nghệ gì?

AI: Dựa vào tài liệu của bạn:
    - Backend: FastAPI 0.135, Python 3.12
    - Orchestration: LangGraph 1.0, LangChain 1.2
    - LLM: Google Gemini + Groq
    - RAG: ChromaDB + SQLite FTS5 + sentence-transformers
    - Frontend: React 19, Vite 7
    - Deploy: Docker Compose

    Nguồn: README.md (phần "Công nghệ sử dụng")

Bạn: Giá vàng SJC hôm nay?

AI: Theo tin mới nhất từ 24h.com.vn (cập nhật 14:30 hôm nay),
    vàng SJC mua vào 84.5 triệu, bán ra 86.2 triệu đồng/lượng...

    Nguồn:
    - https://24h.com.vn/...
    - https://vnexpress.net/...

Bạn: Lần trước tôi hỏi gì vậy?

AI: Cách đây 3 phút, bạn hỏi "Project này dùng công nghệ gì?"
    và trước đó bạn hỏi về giá vàng SJC. Bạn cần tôi tìm lại
    chi tiết câu trả lời nào không?
```

---

## 9. Hiểu thêm

Nếu muốn đi sâu hơn:

- 📘 **Cho developer**: [README.md](../../README.md) — hướng dẫn setup + API chi tiết
- 📗 **Cho người muốn hiểu kiến trúc**: [docs/architecture/](../architecture/) — sơ đồ + design doc
- 📕 **Cho người muốn sửa AI**: [docs/archive/plans/skill-refactor-phase1-3/](../archive/plans/skill-refactor-phase1-3/) — plan refactor prompt sang skill framework
- 📙 **Cho người muốn làm agent tương tự**: [ai-agent-guide.md](ai-agent-guide.md)

---

## Tóm tắt 1 câu

> **Đây là ChatGPT mini, chạy trong máy của bạn, biết tra Google, nhớ tài liệu bạn đưa, trả lời có kèm nguồn — và mọi câu lệnh điều khiển AI đều viết bằng tiếng Việt trong các file `.md` dễ sửa.**
