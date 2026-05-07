# Architecture Diagrams

Sơ đồ Mermaid minh họa sự thay đổi kiến trúc: **trước vs sau** refactor sang skill-based.

---

## 1. High-level: Before vs After

### 1.1 Trước refactor — prompt scattered

```mermaid
graph TB
    Chat[api v2 chat]
    Entry[entry]
    Complexity[complexity_node]
    SimpleLLM[simple_llm]
    Router[router_node]
    Planning[planning_node]
    DateNode[current_date_node]
    DirectNode[direct_llm_node]
    Research[research_node]
    Synthesis[synthesis_node]
    Citation[citation_node]
    Persist[persist]

    Chat --> Entry
    Entry --> Complexity
    Complexity -->|simple| SimpleLLM
    Complexity -->|complex| Router
    Router -->|research| Planning
    Router -->|current_date| DateNode
    Router -->|direct_llm| DirectNode
    Planning --> Research
    Research --> Synthesis
    Synthesis --> Citation
    SimpleLLM --> Persist
    DateNode --> Persist
    DirectNode --> Persist
    Citation --> Persist

    P1[complexity_analyzer.py - prompt inline]
    P2[planning_agent.py - prompt inline]
    P3[response_composer.py - prompt inline]
    P4[direct_llm.py - prompt inline]
    P5[research_tool.py - prompt inline]
    P6[rag subgraph nodes.py - 3 prompts inline]
    P7[intent_patterns.py - keyword lists]

    Complexity -.-> P1
    Planning -.-> P2
    Synthesis -.-> P3
    DirectNode -.-> P4
    Research -.-> P5
    Router -.-> P7

    classDef node fill:#3b82f6,stroke:#1e40af,color:#fff
    classDef bad fill:#ffcccc,stroke:#c00,color:#000
    class Chat,Entry,Complexity,SimpleLLM,Router,Planning,DateNode,DirectNode,Research,Synthesis,Citation,Persist node
    class P1,P2,P3,P4,P5,P6,P7 bad
```

### 1.2 Sau refactor — skills centralized

```mermaid
graph TB
    Chat[api v2 chat]
    Entry[entry]
    Complexity[complexity_node]
    SimpleLLM[simple_llm]
    Router[router_node]
    Planning[planning_node]
    DateNode[current_date_node]
    DirectNode[direct_llm_node]
    Research[research_node]
    Synthesis[synthesis_node]
    Citation[citation_node]
    Persist[persist]

    Chat --> Entry
    Entry --> Complexity
    Complexity -->|simple| SimpleLLM
    Complexity -->|complex| Router
    Router -->|research| Planning
    Router -->|current_date| DateNode
    Router -->|direct_llm| DirectNode
    Planning --> Research
    Research --> Synthesis
    Synthesis --> Citation
    SimpleLLM --> Persist
    DateNode --> Persist
    DirectNode --> Persist
    Citation --> Persist

    Reg[Skill Registry]
    S1[complexity_classifier]
    S2[query_router]
    S3[planning]
    S4[response_composer]
    S5[direct_answer]
    S6[research_search]
    S7[rag.retrieve]
    S8[rag.answer_with_context]
    S9[rag.transform_query]
    S10[rag.grade_docs_gen]

    Complexity --> Reg
    Router --> Reg
    Planning --> Reg
    Synthesis --> Reg
    DirectNode --> Reg
    Research --> Reg

    Reg --> S1
    Reg --> S2
    Reg --> S3
    Reg --> S4
    Reg --> S5
    Reg --> S6
    Reg --> S7
    Reg --> S8
    Reg --> S9
    Reg --> S10

    classDef node fill:#3b82f6,stroke:#1e40af,color:#fff
    classDef skill fill:#22c55e,stroke:#15803d,color:#000
    classDef reg fill:#f59e0b,stroke:#b45309,color:#000
    class Chat,Entry,Complexity,SimpleLLM,Router,Planning,DateNode,DirectNode,Research,Synthesis,Citation,Persist node
    class S1,S2,S3,S4,S5,S6,S7,S8,S9,S10 skill
    class Reg reg
```

---

## 2. Skill anatomy — cấu trúc một skill

```mermaid
graph LR
    YAML[skill.yaml - name, model, temperature]
    MD[prompt.md - Jinja2 template]
    PY[handler.py - Inputs, Outputs, Handler]

    Invoke[invoke inputs]
    ValidateIn[validate Inputs pydantic]
    Render[render prompt Jinja2]
    CallLLM[call LLM adapter]
    Parse[parse_output]
    ValidateOut[validate Outputs pydantic]
    Fallback[fallback on error]
    Return[return dict]

    YAML --> Invoke
    MD --> Render
    PY --> ValidateIn
    PY --> Parse
    PY --> Fallback

    Invoke --> ValidateIn
    ValidateIn --> Render
    Render --> CallLLM
    CallLLM -->|success| Parse
    CallLLM -->|error| Fallback
    Parse --> ValidateOut
    Fallback --> ValidateOut
    ValidateOut --> Return

    classDef file fill:#22c55e,stroke:#15803d,color:#000
    classDef base fill:#6366f1,stroke:#3730a3,color:#fff
    class YAML,MD,PY file
    class Invoke,ValidateIn,Render,CallLLM,Parse,ValidateOut,Fallback,Return base
```

---

## 3. Registry discovery + skill invocation

```mermaid
sequenceDiagram
    participant App as FastAPI startup
    participant Reg as SkillRegistry
    participant FS as filesystem
    participant Adapter as AdapterFactory

    App->>Reg: discover(skills_root)
    Reg->>FS: walk skills folders
    FS-->>Reg: list of skill dirs

    loop each skill folder
        Reg->>FS: read skill.yaml
        Reg->>FS: load prompt.md
        Reg->>FS: import handler module
        Note over Reg: instantiate Handler with config
    end

    Reg-->>App: ready

    Note over App,Adapter: During request

    App->>Reg: get complexity_classifier
    Reg-->>App: BaseSkill instance
    App->>Reg: skill.invoke message
    Reg->>Adapter: resolve model
    Adapter-->>Reg: cached adapter
    Reg->>Adapter: invoke messages
    Adapter-->>Reg: raw output
    Reg->>Reg: parse plus validate
    Reg-->>App: dict output
```

---

## 4. Node flow — complexity_node trước và sau

### 4.1 Trước

```mermaid
flowchart TB
    Start([complexity_node called])
    Extract[extract message from state]
    CreateAnalyzer[create ComplexityAnalyzer]
    BuildPrompt[build prompt string HARDCODED]
    InvokeAdapter[adapter invoke]
    ParseJSON[json loads]
    Heuristic[heuristic fallback]
    ForceCheck[check force_complex via intent_patterns]
    Return([return query_type])

    Start --> Extract
    Extract --> CreateAnalyzer
    CreateAnalyzer --> BuildPrompt
    BuildPrompt --> InvokeAdapter
    InvokeAdapter -->|success| ParseJSON
    InvokeAdapter -->|exception| Heuristic
    ParseJSON -->|valid| ForceCheck
    ParseJSON -->|invalid| Heuristic
    Heuristic --> ForceCheck
    ForceCheck --> Return

    classDef node fill:#3b82f6,stroke:#1e40af,color:#fff
    classDef bad fill:#ffcccc,stroke:#c00,color:#000
    class Start,Extract,CreateAnalyzer,InvokeAdapter,ParseJSON,Heuristic,Return node
    class BuildPrompt,ForceCheck bad
```

### 4.2 Sau

```mermaid
flowchart TB
    Start([complexity_node called])
    Extract[extract message from state]
    GetSkill[registry get complexity_classifier]
    ValidateIn[validate Inputs pydantic]
    Render[render prompt.md Jinja2]
    Call[call LLM]
    Parse[parse output JSON]
    Fallback[fallback heuristic]
    ValidateOut[validate Outputs pydantic]
    ForceCheck[check force_complex]
    Return([return query_type])

    Start --> Extract
    Extract --> GetSkill
    GetSkill --> ValidateIn
    ValidateIn --> Render
    Render --> Call
    Call -->|success| Parse
    Call -->|exception| Fallback
    Parse --> ValidateOut
    Fallback --> ValidateOut
    ValidateOut --> ForceCheck
    ForceCheck --> Return

    classDef node fill:#3b82f6,stroke:#1e40af,color:#fff
    classDef good fill:#22c55e,stroke:#15803d,color:#000
    class Start,Extract,GetSkill,ForceCheck,Return node
    class ValidateIn,Render,Call,Parse,Fallback,ValidateOut good
```

---

## 5. Directory structure — before vs after

### 5.1 Trước

```mermaid
graph TB
    Root[backend src]
    RA[research_agent]
    RAG[rag]
    Adapters[adapters]
    API[api]

    Root --> RA
    Root --> RAG
    Root --> Adapters
    Root --> API

    RA --> RA_Nodes[nodes]
    RA --> RA_Edges[edges]
    RA --> RA_Graph[graph]
    RA --> CA[complexity_analyzer.py - prompt inline]
    RA --> PA[planning_agent.py - prompt inline]
    RA --> RC[response_composer.py - prompt inline]
    RA --> DL[direct_llm.py - prompt inline]
    RA --> RT[research_tool.py - prompt inline]
    RA --> RA_Utils[intent_patterns.py - keyword lists]

    RAG --> RAG_Sub[subgraph nodes.py - 3 prompts inline]
    RAG --> RAG_QE[query_expander.py]
    RAG --> RAG_HS[hybrid_search.py]
    RAG --> RAG_RR[reranker.py]

    classDef dir fill:#3b82f6,stroke:#1e40af,color:#fff
    classDef bad fill:#ffcccc,stroke:#c00,color:#000
    class Root,RA,RAG,Adapters,API,RA_Nodes,RA_Edges,RA_Graph,RAG_QE,RAG_HS,RAG_RR dir
    class CA,PA,RC,DL,RT,RA_Utils,RAG_Sub bad
```

### 5.2 Sau

```mermaid
graph TB
    Root[backend src]
    Skills[skills NEW]
    RA[research_agent]
    RAG[rag]
    Adapters[adapters]
    API[api]

    Root --> Skills
    Root --> RA
    Root --> RAG
    Root --> Adapters
    Root --> API

    Skills --> S_Base[_base.py]
    Skills --> S_Reg[_registry.py]
    Skills --> S_Loader[_prompt_loader.py]
    Skills --> S_Err[_errors.py]
    Skills --> S_CC[complexity_classifier]
    Skills --> S_QR[query_router]
    Skills --> S_Plan[planning]
    Skills --> S_RC[response_composer]
    Skills --> S_DA[direct_answer]
    Skills --> S_RS[research_search]
    Skills --> S_RAG[rag folder]

    S_RAG --> S_Retrieve[retrieve]
    S_RAG --> S_Answer[answer_with_context]
    S_RAG --> S_QE[query_expand]
    S_RAG --> S_TQ[transform_query]
    S_RAG --> S_GD[grade_documents]
    S_RAG --> S_GG[grade_generation]

    RA --> RA_Nodes[nodes - thin wrappers]
    RA --> RA_Edges[edges - unchanged]
    RA --> RA_Graph[graph - unchanged]

    RAG --> RAG_Sub[subgraph - thin wrappers]
    RAG --> RAG_Primitives[fts vector rerank - unchanged]

    classDef dir fill:#3b82f6,stroke:#1e40af,color:#fff
    classDef new fill:#22c55e,stroke:#15803d,color:#000
    classDef framework fill:#6366f1,stroke:#3730a3,color:#fff
    class Root,RA,RAG,Adapters,API,RA_Nodes,RA_Edges,RA_Graph,RAG_Sub,RAG_Primitives dir
    class Skills,S_CC,S_QR,S_Plan,S_RC,S_DA,S_RS,S_RAG,S_Retrieve,S_Answer,S_QE,S_TQ,S_GD,S_GG new
    class S_Base,S_Reg,S_Loader,S_Err framework
```

---

## 6. Phased migration — lộ trình

```mermaid
gantt
    title Migration roadmap
    dateFormat YYYY-MM-DD
    axisFormat %d-%m

    section Phase 1 MVP
    Add deps                     :p1a, 2026-04-22, 1d
    Framework skeleton           :p1b, after p1a, 1d
    complexity_classifier        :p1c, after p1b, 1d
    Wire test verify             :p1d, after p1c, 1d

    section Phase 2a
    response_composer            :p2a1, after p1d, 1d
    planning                     :p2a2, after p2a1, 1d
    direct_answer                :p2a3, after p2a2, 2d
    research_search              :p2a4, after p2a3, 1d
    query_router                 :p2a5, after p2a4, 1d
    Verify fix sap toi bug       :p2a6, after p2a5, 1d

    section Phase 2b
    rag.query_expand             :p2b1, after p2a6, 1d
    rag.transform_query          :p2b2, after p2b1, 1d
    rag.grade_documents          :p2b3, after p2b2, 1d
    rag.grade_generation         :p2b4, after p2b3, 1d
    rag.answer_with_context      :p2b5, after p2b4, 1d
    rag.retrieve                 :p2b6, after p2b5, 1d
    Wire verify                  :p2b7, after p2b6, 1d

    section Phase 3
    Delete old classes           :p3a, after p2b7, 1d
    Clean signatures             :p3b, after p3a, 1d
    Grep verify final tests      :p3c, after p3b, 1d
```

---

## 7. State flow — skill gọi LLM end-to-end

```mermaid
stateDiagram-v2
    [*] --> NodeInvoked
    NodeInvoked --> ExtractState
    ExtractState --> GetSkill
    GetSkill --> ValidateInputs
    ValidateInputs --> RenderPrompt: success
    ValidateInputs --> ValidationError: fail
    ValidationError --> [*]

    RenderPrompt --> ResolveAdapter
    ResolveAdapter --> CallLLM
    CallLLM --> ParseOutput: success
    CallLLM --> Fallback: exception

    ParseOutput --> ValidateOutputs: success
    ParseOutput --> Fallback: parse_fail
    Fallback --> ValidateOutputs

    ValidateOutputs --> MapToState: success
    ValidateOutputs --> OutputError: fail
    OutputError --> [*]

    MapToState --> NodeReturn
    NodeReturn --> [*]
```

---

## 8. Dependencies graph

```mermaid
graph BT
    LG[langgraph]
    Pyd[pydantic v2]
    Jinja[jinja2 NEW]
    YAML[PyYAML NEW]
    LC[langchain-core]

    Base[_base.py]
    Reg[_registry.py]
    Loader[_prompt_loader.py]
    Err[_errors.py]

    CC[complexity_classifier handler]
    QR[query_router handler]
    Planning[planning handler]
    Others[other skills]

    NComp[complexity_node]
    NRouter[router_node]
    NPlan[planning_node]
    NOther[other nodes]

    AG[google_adapter]
    AGroq[groq_adapter]

    Base --> Pyd
    Base --> LC
    Loader --> Jinja
    Reg --> YAML
    Reg --> Base

    CC --> Base
    QR --> Base
    Planning --> Base
    Others --> Base

    NComp --> Reg
    NRouter --> Reg
    NPlan --> Reg
    NOther --> Reg

    Base --> AG
    Base --> AGroq
    NComp --> LG
    NRouter --> LG
    NPlan --> LG
    NOther --> LG

    classDef framework fill:#6366f1,stroke:#3730a3,color:#fff
    classDef skill fill:#22c55e,stroke:#15803d,color:#000
    classDef node fill:#f59e0b,stroke:#b45309,color:#000
    classDef ext fill:#94a3b8,stroke:#475569,color:#000
    class Base,Reg,Loader,Err framework
    class CC,QR,Planning,Others skill
    class NComp,NRouter,NPlan,NOther node
    class LG,Pyd,Jinja,YAML,LC,AG,AGroq ext
```

---

## Chú thích màu

| Màu | Ý nghĩa |
|---|---|
| 🟦 Xanh dương (blue) | Node có sẵn trong graph / directory hiện tại |
| 🟩 Xanh lá (green) | Thành phần mới thêm (skills) |
| 🟥 Đỏ nhạt (red) | Pain point — prompt hardcode cần refactor |
| 🟨 Vàng (amber) | Skill Registry / LangGraph nodes |
| 🟪 Tím indigo | Framework base classes |
| ⬜ Xám | External libraries, adapters (không thay đổi) |

## Ghi chú kiến trúc

- **LangGraph topology** (graph nodes/edges) KHÔNG đổi — chỉ body của node thay đổi cách gọi logic
- **AgentState shape** KHÔNG đổi — checkpointer cũ tiếp tục hoạt động
- **API contract** KHÔNG đổi — endpoint request/response identical
- **Adapters** KHÔNG đổi — skill gọi qua cùng interface hiện tại

---

## Cách xem preview

Nếu mở trong VSCode mà diagram không render, cài một trong các extension sau:

1. **Markdown Preview Mermaid Support** (bierner.markdown-mermaid) — khuyến nghị, nhẹ
2. **Markdown All in One** (yzhang.markdown-all-in-one) — full featured

Sau khi cài, reload window (Ctrl+Shift+P → "Reload Window") rồi mở preview (Ctrl+Shift+V).

Hoặc push lên GitHub — Mermaid render native trong `.md` files.
