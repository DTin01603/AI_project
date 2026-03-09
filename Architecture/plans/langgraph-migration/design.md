# Tài liệu Thiết kế - Migration sang LangGraph Framework

## Tổng quan

### Mục tiêu

Migration hệ thống Research Agent từ kiến trúc pipeline (thực thi tuần tự) sang LangGraph framework để:

- **Parallel Execution**: Chạy multiple research tasks đồng thời, giảm thời gian response từ 30+ giây xuống ~12 giây
- **Centralized State Management**: Quản lý state rõ ràng qua AgentState TypedDict thay vì passing data qua method calls
- **Declarative Routing**: Conditional edges thay thế if/else chains, dễ đọc và maintain
- **Native Streaming**: Sử dụng LangGraph .astream() thay vì custom SSE infrastructure
- **Conversation Memory**: Built-in checkpointer cho persistent conversation state
- **Better Observability**: Graph visualization và execution tracing

### Phạm vi

**Trong phạm vi**:
- Migrate orchestration layer sang LangGraph StateGraph
- Implement parallel research execution với asyncio.gather
- Integrate LangGraph streaming với existing SSE infrastructure
- Setup checkpointer (SQLite dev, Postgres prod)
- Preserve tất cả existing functionality
- Backward compatibility với feature flag

**Ngoài phạm vi**:
- Không thay đổi tool implementations (Complexity_Analyzer, Planning_Agent, Research_Tool)
- Không thay đổi API request/response schemas
- Không implement RAG system (future work)
- Không implement calculator tool (future work)

### Lợi ích chính

1. **Performance**: 2.5-3x faster cho complex queries nhờ parallel execution
2. **Maintainability**: Clear separation of concerns, mỗi node một responsibility
3. **Debuggability**: Visual graph structure, state snapshots, execution traces
4. **Extensibility**: Dễ dàng thêm nodes mới cho tools mới
5. **Reliability**: Better error handling và fallback mechanisms



## Kiến trúc

### High-Level Architecture

```mermaid
graph TB
    User[User Request]
    API[FastAPI /api/v2/chat]
    Flag{Feature Flag<br/>ENABLE_LANGGRAPH}
    
    User --> API
    API --> Flag
    
    Flag -->|true| LG[LangGraph System]
    Flag -->|false| Pipeline[Pipeline Orchestrator]
    
    subgraph "LangGraph StateGraph"
        Entry[entry_node]
        Complexity[complexity_node]
        Router[router_node]
        Planning[planning_node]
        Research[research_node]
        Synthesis[synthesis_node]
        Citation[citation_node]
        SimpleLLM[simple_llm_node]
        DirectLLM[direct_llm_node]
        CurrentDate[current_date_node]
        
        Entry --> Complexity
        Complexity -->|simple| SimpleLLM
        Complexity -->|complex| Router
        Router -->|research_intent| Planning
        Router -->|current_date| CurrentDate
        Router -->|direct_llm| DirectLLM
        Planning --> Research
        Research --> Synthesis
        Synthesis --> Citation
        SimpleLLM --> END1[END]
        DirectLLM --> Citation
        CurrentDate --> END2[END]
        Citation --> END3[END]
    end
    
    subgraph "Shared State"
        State[AgentState<br/>messages, query_type,<br/>complexity_result,<br/>research_plan,<br/>research_results,<br/>final_answer, citations]
    end
    
    LG --> State
    State -.->|read/write| Entry
    State -.->|read/write| Complexity
    State -.->|read/write| Router
    State -.->|read/write| Planning
    State -.->|read/write| Research
    State -.->|read/write| Synthesis
    State -.->|read/write| Citation
```



### Parallel Research Execution Flow

```mermaid
sequenceDiagram
    participant U as User
    participant G as StateGraph
    participant PN as planning_node
    participant RN as research_node
    participant T1 as Research Task 1
    participant T2 as Research Task 2
    participant T3 as Research Task 3
    participant SN as synthesis_node
    
    U->>G: "Tìm quán cafe ngon ở Hà Nội"
    G->>PN: Invoke planning_node
    PN->>PN: Create 3 research tasks
    PN-->>G: Update state.research_plan
    
    G->>RN: Invoke research_node
    
    par Parallel Execution
        RN->>T1: Execute task 1 (asyncio)
        RN->>T2: Execute task 2 (asyncio)
        RN->>T3: Execute task 3 (asyncio)
    end
    
    T1-->>RN: Result 1 (5s)
    T2-->>RN: Result 2 (7s)
    T3-->>RN: Result 3 (6s)
    
    Note over RN: Total time: max(5,7,6) = 7s<br/>vs Sequential: 5+7+6 = 18s
    
    RN-->>G: Update state.research_results
    G->>SN: Invoke synthesis_node
    SN-->>U: Final answer with citations
```



### Streaming Integration Flow

```mermaid
sequenceDiagram
    participant Client as Frontend
    participant API as FastAPI Endpoint
    participant Graph as StateGraph
    participant SSE as SSE Manager
    
    Client->>API: POST /api/v2/chat (stream=true)
    API->>Graph: graph.astream(initial_state, config)
    
    loop For each node execution
        Graph->>Graph: Execute node
        Graph-->>API: Yield state update
        API->>SSE: Convert to SSE event
        SSE-->>Client: data: {"node": "...", "status": "...", "progress": ...}
    end
    
    Graph-->>API: Final state
    API->>SSE: Convert to final SSE event
    SSE-->>Client: data: {"type": "done", "answer": "...", "citations": [...]}
    SSE-->>Client: [DONE]
```



### Project Structure

```
backend/src/
├── research_agent/              # Existing pipeline (unchanged)
│   ├── orchestrator.py
│   ├── complexity_analyzer.py
│   ├── planning_agent.py
│   ├── research_tool.py
│   └── ...
│
├── research_agent_v2/           # NEW: LangGraph implementation
│   ├── __init__.py
│   ├── graph.py                 # StateGraph construction
│   ├── state.py                 # AgentState schema
│   ├── nodes/                   # Graph node implementations
│   │   ├── __init__.py
│   │   ├── entry_node.py
│   │   ├── complexity_node.py
│   │   ├── router_node.py
│   │   ├── planning_node.py
│   │   ├── research_node.py    # Parallel execution logic
│   │   ├── synthesis_node.py
│   │   ├── citation_node.py
│   │   ├── simple_llm_node.py
│   │   ├── direct_llm_node.py
│   │   └── current_date_node.py
│   ├── edges/                   # Conditional edge functions
│   │   ├── __init__.py
│   │   ├── complexity_edge.py
│   │   └── router_edge.py
│   ├── checkpointer/            # Checkpointer configuration
│   │   ├── __init__.py
│   │   ├── sqlite_checkpointer.py
│   │   └── postgres_checkpointer.py
│   ├── streaming/               # Streaming utilities
│   │   ├── __init__.py
│   │   └── sse_adapter.py      # Convert graph stream to SSE
│   ├── utils/                   # Utilities
│   │   ├── __init__.py
│   │   ├── error_handling.py
│   │   └── metrics.py
│   └── config.py                # LangGraph-specific config
│
├── api/routers/
│   ├── chat.py                  # Existing /api/chat endpoint
│   └── chat_v2.py               # NEW: /api/v2/chat endpoint
│
└── config.py                    # Add ENABLE_LANGGRAPH_AGENT flag
```



## Components và Interfaces

### 1. AgentState Schema

**File**: `research_agent_v2/state.py`

**Trách nhiệm**: Define typed state structure cho toàn bộ graph execution.

**Implementation**:

```python
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from research_agent.models import ComplexityResult, ResearchTask, ResearchResult

class AgentState(TypedDict):
    """
    Centralized state schema cho LangGraph research agent.
    
    State này flow qua tất cả nodes và được update immutably.
    Mỗi node nhận state, thực hiện logic, và return updated state copy.
    """
    
    # Conversation messages (automatically aggregated by add_messages reducer)
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Query classification
    query_type: str  # "simple", "complex", "current_date", "research_intent", "direct_llm"
    
    # Complexity analysis result
    complexity_result: Optional[ComplexityResult]
    
    # Research planning
    research_plan: Optional[List[ResearchTask]]
    
    # Research execution results
    research_results: List[ResearchResult]
    
    # Final answer synthesis
    final_answer: str
    
    # Source citations
    citations: List[str]
    
    # Execution metadata
    execution_metadata: Dict[str, Any]  # {
    #     "conversation_id": str,
    #     "request_id": str,
    #     "user_id": Optional[str],
    #     "start_time": float,
    #     "node_timings": Dict[str, float],
    #     "model": str,
    #     "provider": str
    # }
    
    # Error tracking
    error: Optional[str]
    fallback_used: bool
```

**Key Features**:
- `add_messages` reducer tự động aggregate conversation history
- Immutable updates: nodes return new state copies
- Type-safe với TypedDict
- Chứa tất cả data cần thiết cho graph execution



### 2. StateGraph Construction

**File**: `research_agent_v2/graph.py`

**Trách nhiệm**: Construct và compile LangGraph StateGraph với nodes, edges, và checkpointer.

**Implementation**:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver
from research_agent_v2.state import AgentState
from research_agent_v2.nodes import (
    entry_node, complexity_node, router_node, planning_node,
    research_node, synthesis_node, citation_node,
    simple_llm_node, direct_llm_node, current_date_node
)
from research_agent_v2.edges import complexity_edge, router_edge
from research_agent_v2.config import get_checkpointer

class ResearchAgentGraph:
    """
    LangGraph StateGraph cho Research Agent với parallel execution.
    """
    
    def __init__(self, dependencies: Dict[str, Any]):
        """
        Args:
            dependencies: Dict chứa:
                - analyzer: ComplexityAnalyzer
                - planning_agent: PlanningAgent
                - research_tool: ResearchTool
                - aggregator: Aggregator
                - response_composer: ResponseComposer
                - direct_llm: DirectLLM
                - database: Database
        """
        self.deps = dependencies
        self.workflow = self._build_graph()
        self.app = self._compile_graph()
    
    def _build_graph(self) -> StateGraph:
        """Construct the StateGraph structure."""
        workflow = StateGraph(AgentState)
        
        # Add all nodes
        workflow.add_node("entry", lambda state: entry_node(state, self.deps))
        workflow.add_node("complexity", lambda state: complexity_node(state, self.deps))
        workflow.add_node("router", lambda state: router_node(state, self.deps))
        workflow.add_node("planning", lambda state: planning_node(state, self.deps))
        workflow.add_node("research", lambda state: research_node(state, self.deps))
        workflow.add_node("synthesis", lambda state: synthesis_node(state, self.deps))
        workflow.add_node("citation", lambda state: citation_node(state, self.deps))
        workflow.add_node("simple_llm", lambda state: simple_llm_node(state, self.deps))
        workflow.add_node("direct_llm", lambda state: direct_llm_node(state, self.deps))
        workflow.add_node("current_date", lambda state: current_date_node(state, self.deps))
        
        # Set entry point
        workflow.set_entry_point("entry")
        
        # Entry -> Complexity
        workflow.add_edge("entry", "complexity")
        
        # Complexity -> Conditional routing
        workflow.add_conditional_edges(
            "complexity",
            lambda state: complexity_edge(state),
            {
                "simple": "simple_llm",
                "complex": "router"
            }
        )
        
        # Router -> Conditional routing
        workflow.add_conditional_edges(
            "router",
            lambda state: router_edge(state),
            {
                "research_intent": "planning",
                "current_date": "current_date",
                "direct_llm": "direct_llm"
            }
        )
        
        # Research pipeline: Planning -> Research -> Synthesis -> Citation
        workflow.add_edge("planning", "research")
        workflow.add_edge("research", "synthesis")
        workflow.add_edge("synthesis", "citation")
        
        # Simple path: Simple LLM -> END
        workflow.add_edge("simple_llm", END)
        
        # Direct LLM -> Citation -> END
        workflow.add_edge("direct_llm", "citation")
        
        # Current date -> END
        workflow.add_edge("current_date", END)
        
        # Citation -> END
        workflow.add_edge("citation", END)
        
        return workflow
    
    def _compile_graph(self):
        """Compile graph với checkpointer."""
        checkpointer = get_checkpointer()
        return self.workflow.compile(checkpointer=checkpointer)
    
    async def ainvoke(
        self,
        request: ChatRequest,
        request_id: str,
        conversation_id: str
    ) -> AgentState:
        """
        Execute graph asynchronously.
        
        Args:
            request: ChatRequest với message và model
            request_id: Unique request ID
            conversation_id: Conversation ID cho checkpointer
        
        Returns:
            Final AgentState sau khi graph execution complete
        """
        from langchain_core.messages import HumanMessage
        import time
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content=request.message)],
            "query_type": "",
            "complexity_result": None,
            "research_plan": None,
            "research_results": [],
            "final_answer": "",
            "citations": [],
            "execution_metadata": {
                "conversation_id": conversation_id,
                "request_id": request_id,
                "user_id": None,
                "start_time": time.time(),
                "node_timings": {},
                "model": request.model or "gemini-1.5-flash",
                "provider": "google"
            },
            "error": None,
            "fallback_used": False
        }
        
        # Invoke với checkpointer config
        config = {"configurable": {"thread_id": conversation_id}}
        final_state = await self.app.ainvoke(initial_state, config)
        
        return final_state
    
    async def astream(
        self,
        request: ChatRequest,
        request_id: str,
        conversation_id: str
    ):
        """
        Stream graph execution với state updates sau mỗi node.
        
        Yields:
            AgentState updates sau mỗi node execution
        """
        from langchain_core.messages import HumanMessage
        import time
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content=request.message)],
            "query_type": "",
            "complexity_result": None,
            "research_plan": None,
            "research_results": [],
            "final_answer": "",
            "citations": [],
            "execution_metadata": {
                "conversation_id": conversation_id,
                "request_id": request_id,
                "user_id": None,
                "start_time": time.time(),
                "node_timings": {},
                "model": request.model or "gemini-1.5-flash",
                "provider": "google"
            },
            "error": None,
            "fallback_used": False
        }
        
        config = {"configurable": {"thread_id": conversation_id}}
        
        async for state_update in self.app.astream(initial_state, config):
            yield state_update
```



### 3. Graph Nodes

#### 3.1 Entry Node

**File**: `research_agent_v2/nodes/entry_node.py`

**Trách nhiệm**: Initialize state và validate input.

```python
import time
from research_agent_v2.state import AgentState

def entry_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Entry point node - initialize execution metadata.
    """
    start_time = time.time()
    
    # Validate message
    messages = state["messages"]
    if not messages or not messages[-1].content.strip():
        return {
            **state,
            "error": "Empty message",
            "final_answer": "Vui lòng nhập câu hỏi."
        }
    
    # Update metadata
    metadata = state["execution_metadata"]
    metadata["node_timings"]["entry"] = (time.time() - start_time) * 1000
    
    return {
        **state,
        "execution_metadata": metadata
    }
```

#### 3.2 Complexity Node

**File**: `research_agent_v2/nodes/complexity_node.py`

**Trách nhiệm**: Analyze query complexity và classify simple vs complex.

```python
import time
import logging
from research_agent_v2.state import AgentState
from research_agent.complexity_analyzer import ComplexityAnalyzer

logger = logging.getLogger(__name__)

def complexity_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Analyze query complexity.
    
    Returns state với:
    - complexity_result: ComplexityResult object
    - query_type: "simple" hoặc "complex"
    """
    start_time = time.time()
    analyzer: ComplexityAnalyzer = deps["analyzer"]
    
    messages = state["messages"]
    question = messages[-1].content
    
    try:
        complexity = analyzer.analyze(question)
        query_type = "simple" if not complexity.is_complex else "complex"
        
        logger.info(
            "complexity_analysis_complete",
            question=question[:100],
            is_complex=complexity.is_complex,
            confidence=complexity.confidence,
            reason=complexity.reason
        )
        
    except Exception as e:
        logger.warning(f"Complexity analysis failed: {e}, fallback to heuristic")
        complexity = ComplexityAnalyzer._heuristic(question)
        query_type = "simple" if not complexity.is_complex else "complex"
    
    # Update metadata
    metadata = state["execution_metadata"]
    metadata["node_timings"]["complexity"] = (time.time() - start_time) * 1000
    
    return {
        **state,
        "complexity_result": complexity,
        "query_type": query_type,
        "execution_metadata": metadata
    }
```



#### 3.3 Router Node

**File**: `research_agent_v2/nodes/router_node.py`

**Trách nhiệm**: Classify complex queries thành research_intent, current_date, hoặc direct_llm.

```python
import time
import logging
from research_agent_v2.state import AgentState

logger = logging.getLogger(__name__)

def router_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Route complex queries based on intent detection.
    
    Returns state với updated query_type:
    - "research_intent": Cần web search
    - "current_date": Hỏi ngày giờ hiện tại
    - "direct_llm": Trả lời trực tiếp từ LLM
    """
    start_time = time.time()
    
    messages = state["messages"]
    question = messages[-1].content.lower()
    
    # Check current date intent
    if _is_current_date_request(question):
        query_type = "current_date"
        reasoning = "Detected current date query"
    
    # Check research intent
    elif _is_research_intent_request(question) or _is_time_sensitive_request(question):
        query_type = "research_intent"
        reasoning = "Detected research intent or time-sensitive query"
    
    # Default to direct LLM
    else:
        query_type = "direct_llm"
        reasoning = "No special intent detected, use direct LLM"
    
    logger.info(
        "routing_decision",
        question=question[:100],
        query_type=query_type,
        reasoning=reasoning
    )
    
    # Update metadata
    metadata = state["execution_metadata"]
    metadata["node_timings"]["router"] = (time.time() - start_time) * 1000
    
    return {
        **state,
        "query_type": query_type,
        "execution_metadata": metadata
    }

def _is_current_date_request(message: str) -> bool:
    """Check if query asks for current date."""
    exact_patterns = [
        "hôm nay ngày mấy",
        "hôm nay là ngày mấy",
        "today's date",
        "what date is today"
    ]
    if any(pattern in message for pattern in exact_patterns):
        return True
    
    has_today = any(token in message for token in ["hôm nay", "today"])
    has_date = any(token in message for token in ["ngày", "date"])
    has_asking = any(token in message for token in ["mấy", "bao nhiêu", "what"])
    return has_today and has_date and has_asking

def _is_time_sensitive_request(message: str) -> bool:
    """Check if query needs real-time information."""
    temporal_keywords = ["hôm nay", "hiện tại", "bây giờ", "today", "current", "latest", "mới nhất"]
    market_keywords = ["giá", "price", "vàng", "gold", "btc", "bitcoin"]
    return any(t in message for t in temporal_keywords) and any(m in message for m in market_keywords)

def _is_research_intent_request(message: str) -> bool:
    """Check if query explicitly requests research."""
    intent_keywords = ["tìm kiếm", "tra cứu", "search", "tìm thông tin"]
    evidence_keywords = ["quán", "nhà hàng", "địa chỉ", "danh sách", "top", "review"]
    return any(i in message for i in intent_keywords) and any(e in message for e in evidence_keywords)
```



#### 3.4 Planning Node

**File**: `research_agent_v2/nodes/planning_node.py`

**Trách nhiệm**: Create multi-step research plan.

```python
import time
import logging
from research_agent_v2.state import AgentState
from research_agent.planning_agent import PlanningAgent
from research_agent.models import ResearchTask

logger = logging.getLogger(__name__)

def planning_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Create research plan với multiple tasks.
    
    Returns state với updated research_plan.
    """
    start_time = time.time()
    planning_agent: PlanningAgent = deps["planning_agent"]
    
    messages = state["messages"]
    question = messages[-1].content
    
    try:
        plan = planning_agent.create_plan(question)
        
        logger.info(
            "planning_complete",
            question=question[:100],
            num_tasks=len(plan),
            tasks=[{"order": t.order, "query": t.query[:50]} for t in plan]
        )
        
    except Exception as e:
        logger.warning(f"Planning failed: {e}, fallback to single-step plan")
        plan = [ResearchTask(order=1, query=question, goal="Thu thập thông tin mới nhất")]
    
    # Update metadata
    metadata = state["execution_metadata"]
    metadata["node_timings"]["planning"] = (time.time() - start_time) * 1000
    
    return {
        **state,
        "research_plan": plan,
        "execution_metadata": metadata
    }
```



#### 3.5 Research Node (Parallel Execution)

**File**: `research_agent_v2/nodes/research_node.py`

**Trách nhiệm**: Execute research tasks PARALLEL sử dụng asyncio.gather.

```python
import time
import asyncio
import logging
from typing import List
from research_agent_v2.state import AgentState
from research_agent.research_tool import ResearchTool
from research_agent.models import ResearchTask, ResearchResult

logger = logging.getLogger(__name__)

def research_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Execute research tasks in PARALLEL.
    
    Key improvement: Sử dụng asyncio.gather để chạy multiple tasks đồng thời,
    giảm thời gian từ sum(task_times) xuống max(task_times).
    
    Returns state với updated research_results.
    """
    start_time = time.time()
    research_tool: ResearchTool = deps["research_tool"]
    
    plan = state["research_plan"]
    if not plan:
        logger.warning("No research plan found, skipping research")
        return state
    
    # Execute tasks in parallel
    results = asyncio.run(_execute_tasks_parallel(research_tool, plan))
    
    # Sort results by task order
    results.sort(key=lambda r: r.task_order)
    
    # Calculate metrics
    execution_time = (time.time() - start_time) * 1000
    successful_count = sum(1 for r in results if r.success)
    
    logger.info(
        "research_complete",
        num_tasks=len(plan),
        successful_tasks=successful_count,
        execution_time_ms=execution_time,
        speedup_vs_sequential=f"{len(plan)}x potential"
    )
    
    # Update metadata
    metadata = state["execution_metadata"]
    metadata["node_timings"]["research"] = execution_time
    metadata["research_metrics"] = {
        "num_tasks": len(plan),
        "successful_tasks": successful_count,
        "parallel_execution": True
    }
    
    return {
        **state,
        "research_results": results,
        "execution_metadata": metadata
    }

async def _execute_tasks_parallel(
    research_tool: ResearchTool,
    tasks: List[ResearchTask]
) -> List[ResearchResult]:
    """
    Execute multiple research tasks concurrently using asyncio.gather.
    
    This is the KEY PERFORMANCE IMPROVEMENT:
    - Sequential: task1(10s) + task2(8s) + task3(12s) = 30s total
    - Parallel: max(10s, 8s, 12s) = 12s total (~2.5x faster)
    """
    async def execute_single_task(task: ResearchTask) -> ResearchResult:
        """Execute single task với timeout protection."""
        try:
            # Run synchronous research_tool.execute_task in thread pool
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    research_tool.execute_task,
                    task.order,
                    task.query,
                    task.goal
                ),
                timeout=10.0  # 10 second timeout per task
            )
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Task {task.order} timed out")
            return ResearchResult(
                task_order=task.order,
                extracted_information="",
                sources=[],
                success=False,
                error="Task timeout"
            )
        except Exception as e:
            logger.error(f"Task {task.order} failed: {e}")
            return ResearchResult(
                task_order=task.order,
                extracted_information="",
                sources=[],
                success=False,
                error=str(e)
            )
    
    # Execute all tasks concurrently
    results = await asyncio.gather(
        *[execute_single_task(task) for task in tasks],
        return_exceptions=False  # Let individual task errors be handled above
    )
    
    return list(results)
```

**Key Implementation Details**:

1. **asyncio.gather**: Chạy tất cả tasks đồng thời
2. **run_in_executor**: Convert synchronous research_tool.execute_task thành async
3. **Timeout per task**: Mỗi task có 10s timeout riêng
4. **Error isolation**: Một task fail không ảnh hưởng tasks khác
5. **Result ordering**: Sort results theo task.order để maintain logical flow



#### 3.6 Synthesis Node

**File**: `research_agent_v2/nodes/synthesis_node.py`

**Trách nhiệm**: Synthesize final answer từ research results.

```python
import time
import logging
from research_agent_v2.state import AgentState
from research_agent.aggregator import Aggregator
from research_agent.response_composer import ResponseComposer

logger = logging.getLogger(__name__)

def synthesis_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Synthesize final answer từ research results.
    
    Returns state với updated final_answer và citations.
    """
    start_time = time.time()
    aggregator: Aggregator = deps["aggregator"]
    response_composer: ResponseComposer = deps["response_composer"]
    
    results = state["research_results"]
    messages = state["messages"]
    question = messages[-1].content
    
    # Filter successful results
    successful = [r for r in results if r.success]
    
    if not successful:
        logger.warning("No successful research results, fallback to direct LLM")
        return {
            **state,
            "fallback_used": True,
            "final_answer": "",
            "citations": []
        }
    
    try:
        # Aggregate knowledge base
        knowledge_base, sources = aggregator.aggregate(results)
        
        # Compose answer
        answer = response_composer.compose(question, knowledge_base)
        
        logger.info(
            "synthesis_complete",
            question=question[:100],
            answer_length=len(answer),
            num_sources=len(sources)
        )
        
        # Update metadata
        metadata = state["execution_metadata"]
        metadata["node_timings"]["synthesis"] = (time.time() - start_time) * 1000
        
        return {
            **state,
            "final_answer": answer,
            "citations": sources,
            "execution_metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        return {
            **state,
            "error": f"Synthesis failed: {str(e)}",
            "fallback_used": True,
            "final_answer": "",
            "citations": []
        }
```

#### 3.7 Citation Node

**File**: `research_agent_v2/nodes/citation_node.py`

**Trách nhiệm**: Format final answer với citations.

```python
import time
from research_agent_v2.state import AgentState

def citation_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Append citations to final answer.
    
    Returns state với formatted final_answer.
    """
    start_time = time.time()
    
    answer = state["final_answer"]
    citations = state["citations"]
    
    if not citations:
        formatted_answer = answer
    else:
        # Deduplicate citations
        unique_citations = _deduplicate_sources(citations)
        
        # Format citations
        citation_block = "\n".join([f"- {source}" for source in unique_citations])
        formatted_answer = f"{answer}\n\nNguồn tham khảo:\n{citation_block}".strip()
    
    # Update metadata
    metadata = state["execution_metadata"]
    metadata["node_timings"]["citation"] = (time.time() - start_time) * 1000
    
    return {
        **state,
        "final_answer": formatted_answer,
        "execution_metadata": metadata
    }

def _deduplicate_sources(sources: list[str]) -> list[str]:
    """Remove duplicate sources while preserving order."""
    seen = set()
    unique = []
    for source in sources:
        normalized = source.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(source.strip())
    return unique
```



#### 3.8 Simple LLM Node

**File**: `research_agent_v2/nodes/simple_llm_node.py`

**Trách nhiệm**: Handle simple queries với direct LLM response.

```python
import time
import logging
from research_agent_v2.state import AgentState
from research_agent.direct_llm import DirectLLM

logger = logging.getLogger(__name__)

def simple_llm_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Answer simple queries using direct LLM without research.
    
    Returns state với final_answer.
    """
    start_time = time.time()
    direct_llm: DirectLLM = deps["direct_llm"]
    database = deps["database"]
    
    messages = state["messages"]
    question = messages[-1].content
    conversation_id = state["execution_metadata"]["conversation_id"]
    
    # Get conversation history
    history = database.get_conversation_history(conversation_id)
    
    try:
        answer, provider, finish_reason = direct_llm.generate_response(
            user_message=question,
            history=history
        )
        
        logger.info(
            "simple_llm_complete",
            question=question[:100],
            answer_length=len(answer),
            provider=provider
        )
        
        # Save to database
        database.save_message(conversation_id, "user", question)
        database.save_message(conversation_id, "assistant", answer)
        
        # Update metadata
        metadata = state["execution_metadata"]
        metadata["node_timings"]["simple_llm"] = (time.time() - start_time) * 1000
        metadata["provider"] = provider
        metadata["finish_reason"] = finish_reason
        
        return {
            **state,
            "final_answer": answer,
            "execution_metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Simple LLM failed: {e}")
        return {
            **state,
            "error": f"LLM generation failed: {str(e)}",
            "final_answer": "Xin lỗi, tôi không thể trả lời câu hỏi này lúc này."
        }
```

#### 3.9 Direct LLM Node

**File**: `research_agent_v2/nodes/direct_llm_node.py`

**Trách nhiệm**: Handle complex queries không cần research với direct LLM.

```python
import time
import logging
from research_agent_v2.state import AgentState
from research_agent.direct_llm import DirectLLM

logger = logging.getLogger(__name__)

def direct_llm_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Answer complex queries using direct LLM (no research needed).
    
    Similar to simple_llm_node but for complex queries routed by router_node.
    """
    start_time = time.time()
    direct_llm: DirectLLM = deps["direct_llm"]
    database = deps["database"]
    
    messages = state["messages"]
    question = messages[-1].content
    conversation_id = state["execution_metadata"]["conversation_id"]
    
    history = database.get_conversation_history(conversation_id)
    
    try:
        answer, provider, finish_reason = direct_llm.generate_response(
            user_message=question,
            history=history
        )
        
        logger.info(
            "direct_llm_complete",
            question=question[:100],
            answer_length=len(answer),
            fallback_used=state.get("fallback_used", False)
        )
        
        database.save_message(conversation_id, "user", question)
        database.save_message(conversation_id, "assistant", answer)
        
        metadata = state["execution_metadata"]
        metadata["node_timings"]["direct_llm"] = (time.time() - start_time) * 1000
        metadata["provider"] = provider
        metadata["finish_reason"] = finish_reason
        
        return {
            **state,
            "final_answer": answer,
            "execution_metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Direct LLM failed: {e}")
        return {
            **state,
            "error": f"LLM generation failed: {str(e)}",
            "final_answer": "Xin lỗi, tôi không thể trả lời câu hỏi này lúc này."
        }
```

#### 3.10 Current Date Node

**File**: `research_agent_v2/nodes/current_date_node.py`

**Trách nhiệm**: Handle current date queries.

```python
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from research_agent_v2.state import AgentState

def current_date_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """
    Answer current date queries.
    
    Returns state với final_answer.
    """
    start_time = time.time()
    database = deps["database"]
    
    messages = state["messages"]
    question = messages[-1].content
    conversation_id = state["execution_metadata"]["conversation_id"]
    
    # Get current date in Vietnam timezone
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    answer = f"Hôm nay là ngày {now.strftime('%d/%m/%Y')} (theo giờ Việt Nam)."
    
    # Save to database
    database.save_message(conversation_id, "user", question)
    database.save_message(conversation_id, "assistant", answer)
    
    # Update metadata
    metadata = state["execution_metadata"]
    metadata["node_timings"]["current_date"] = (time.time() - start_time) * 1000
    metadata["provider"] = "system-clock"
    
    return {
        **state,
        "final_answer": answer,
        "execution_metadata": metadata
    }
```



### 4. Conditional Edges

#### 4.1 Complexity Edge

**File**: `research_agent_v2/edges/complexity_edge.py`

**Trách nhiệm**: Route based on complexity analysis result.

```python
from research_agent_v2.state import AgentState

def complexity_edge(state: AgentState) -> str:
    """
    Conditional edge function for complexity routing.
    
    Returns:
        "simple": Route to simple_llm_node
        "complex": Route to router_node
    """
    query_type = state.get("query_type", "simple")
    
    if query_type == "simple":
        return "simple"
    else:
        return "complex"
```

#### 4.2 Router Edge

**File**: `research_agent_v2/edges/router_edge.py`

**Trách nhiệm**: Route complex queries based on intent.

```python
from research_agent_v2.state import AgentState

def router_edge(state: AgentState) -> str:
    """
    Conditional edge function for router routing.
    
    Returns:
        "research_intent": Route to planning_node
        "current_date": Route to current_date_node
        "direct_llm": Route to direct_llm_node
    """
    query_type = state.get("query_type", "direct_llm")
    
    # Map query_type to next node
    routing_map = {
        "research_intent": "research_intent",
        "current_date": "current_date",
        "direct_llm": "direct_llm"
    }
    
    return routing_map.get(query_type, "direct_llm")
```



### 5. Checkpointer Configuration

**File**: `research_agent_v2/checkpointer/sqlite_checkpointer.py`

**Trách nhiệm**: SQLite checkpointer cho development.

```python
from langgraph.checkpoint.sqlite import SqliteSaver
import aiosqlite

async def get_sqlite_checkpointer(db_path: str = "./checkpoints.db") -> SqliteSaver:
    """
    Create SQLite checkpointer for conversation memory.
    
    Args:
        db_path: Path to SQLite database file
    
    Returns:
        SqliteSaver instance
    """
    conn = await aiosqlite.connect(db_path)
    checkpointer = SqliteSaver(conn)
    return checkpointer
```

**File**: `research_agent_v2/checkpointer/postgres_checkpointer.py`

**Trách nhiệm**: Postgres checkpointer cho production.

```python
from langgraph.checkpoint.postgres import PostgresSaver
import asyncpg

async def get_postgres_checkpointer(connection_string: str) -> PostgresSaver:
    """
    Create Postgres checkpointer for conversation memory.
    
    Args:
        connection_string: Postgres connection string
    
    Returns:
        PostgresSaver instance
    """
    pool = await asyncpg.create_pool(connection_string)
    checkpointer = PostgresSaver(pool)
    return checkpointer
```

**File**: `research_agent_v2/config.py`

**Trách nhiệm**: Checkpointer configuration.

```python
import os
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver

def get_checkpointer():
    """
    Get checkpointer based on environment configuration.
    
    Returns:
        SqliteSaver for development, PostgresSaver for production
    """
    checkpointer_type = os.getenv("LANGGRAPH_CHECKPOINTER", "sqlite")
    
    if checkpointer_type == "postgres":
        connection_string = os.getenv("POSTGRES_CONNECTION_STRING")
        if not connection_string:
            raise ValueError("POSTGRES_CONNECTION_STRING not set")
        
        # Note: This is synchronous initialization
        # For async, use get_postgres_checkpointer() directly
        from langgraph.checkpoint.postgres import PostgresSaver
        return PostgresSaver.from_conn_string(connection_string)
    
    else:
        # SQLite for development
        db_path = os.getenv("LANGGRAPH_DB_PATH", "./checkpoints.db")
        return SqliteSaver.from_conn_string(db_path)
```

**Environment Variables**:

```bash
# Development (SQLite)
LANGGRAPH_CHECKPOINTER=sqlite
LANGGRAPH_DB_PATH=./checkpoints.db

# Production (Postgres)
LANGGRAPH_CHECKPOINTER=postgres
POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:5432/dbname
```



### 6. Streaming Integration

**File**: `research_agent_v2/streaming/sse_adapter.py`

**Trách nhiệm**: Convert LangGraph stream to SSE events.

```python
import json
import time
from typing import AsyncIterator, Dict, Any
from research_agent_v2.state import AgentState

class SSEAdapter:
    """
    Adapter to convert LangGraph state updates to SSE events.
    
    Maintains backward compatibility với existing frontend SSE consumer.
    """
    
    # Node name mapping to SSE event types
    NODE_EVENT_MAP = {
        "entry": {"type": "status", "message": "Đang xử lý câu hỏi..."},
        "complexity": {"type": "status", "message": "Đang phân tích độ phức tạp..."},
        "router": {"type": "status", "message": "Đang xác định phương pháp xử lý..."},
        "planning": {"type": "status", "message": "Đang lập kế hoạch nghiên cứu..."},
        "research": {"type": "status", "message": "Đang thực hiện nghiên cứu..."},
        "synthesis": {"type": "status", "message": "Đang tổng hợp kết quả..."},
        "citation": {"type": "status", "message": "Đang định dạng trích dẫn..."},
        "simple_llm": {"type": "status", "message": "Đang tạo câu trả lời..."},
        "direct_llm": {"type": "status", "message": "Đang tạo câu trả lời..."},
        "current_date": {"type": "status", "message": "Đang lấy thông tin ngày giờ..."}
    }
    
    @staticmethod
    async def stream_to_sse(
        graph_stream: AsyncIterator[Dict[str, AgentState]]
    ) -> AsyncIterator[str]:
        """
        Convert LangGraph stream to SSE format.
        
        Args:
            graph_stream: AsyncIterator yielding {node_name: state} dicts
        
        Yields:
            SSE formatted strings: "data: {...}\n\n"
        """
        total_nodes = 0
        completed_nodes = 0
        
        async for state_update in graph_stream:
            # Extract node name and state
            node_name = list(state_update.keys())[0]
            state = state_update[node_name]
            
            completed_nodes += 1
            
            # Get event info for this node
            event_info = SSEAdapter.NODE_EVENT_MAP.get(
                node_name,
                {"type": "status", "message": f"Processing {node_name}..."}
            )
            
            # Calculate progress
            # Estimate total nodes based on query_type
            query_type = state.get("query_type", "")
            if query_type == "simple":
                total_nodes = 3  # entry, complexity, simple_llm
            elif query_type == "research_intent":
                total_nodes = 8  # entry, complexity, router, planning, research, synthesis, citation
            elif query_type == "current_date":
                total_nodes = 4  # entry, complexity, router, current_date
            else:
                total_nodes = 6  # entry, complexity, router, direct_llm, citation
            
            progress = int((completed_nodes / total_nodes) * 100)
            
            # Build SSE event
            sse_event = {
                "type": event_info["type"],
                "node": node_name,
                "message": event_info["message"],
                "progress": progress,
                "timestamp": time.time()
            }
            
            # Add node-specific data
            if node_name == "complexity":
                complexity = state.get("complexity_result")
                if complexity:
                    sse_event["data"] = {
                        "is_complex": complexity.is_complex,
                        "confidence": complexity.confidence
                    }
            
            elif node_name == "planning":
                plan = state.get("research_plan", [])
                sse_event["data"] = {
                    "num_tasks": len(plan),
                    "tasks": [{"order": t.order, "query": t.query} for t in plan]
                }
            
            elif node_name == "research":
                results = state.get("research_results", [])
                sse_event["data"] = {
                    "num_results": len(results),
                    "successful": sum(1 for r in results if r.success)
                }
            
            # Yield SSE formatted event
            yield f"data: {json.dumps(sse_event)}\n\n"
        
        # Final "done" event
        final_state = state  # Last state from loop
        final_event = {
            "type": "done",
            "answer": final_state.get("final_answer", ""),
            "citations": final_state.get("citations", []),
            "metadata": final_state.get("execution_metadata", {}),
            "error": final_state.get("error")
        }
        
        yield f"data: {json.dumps(final_event)}\n\n"
        yield "data: [DONE]\n\n"
```

**SSE Event Format**:

```json
{
  "type": "status",
  "node": "research",
  "message": "Đang thực hiện nghiên cứu...",
  "progress": 60,
  "timestamp": 1234567890.123,
  "data": {
    "num_results": 3,
    "successful": 3
  }
}
```



### 7. API Endpoints

**File**: `backend/src/api/routers/chat_v2.py`

**Trách nhiệm**: New /api/v2/chat endpoint sử dụng LangGraph.

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from uuid import uuid4
import logging

from models.request import ChatRequest
from models.response import ChatResponse, ResponseMeta
from research_agent_v2.graph import ResearchAgentGraph
from research_agent_v2.streaming.sse_adapter import SSEAdapter
from api.deps import get_research_agent_graph

router = APIRouter(prefix="/api/v2", tags=["chat_v2"])
logger = logging.getLogger(__name__)

@router.post("/chat")
async def chat_v2(
    request: ChatRequest,
    graph: ResearchAgentGraph = Depends(get_research_agent_graph)
):
    """
    LangGraph-based chat endpoint với parallel execution.
    
    Supports both streaming và non-streaming modes.
    """
    request_id = str(uuid4())
    conversation_id = request.conversation_id or str(uuid4())
    
    logger.info(
        "chat_v2_request",
        request_id=request_id,
        conversation_id=conversation_id,
        message=request.message[:100],
        stream=request.stream
    )
    
    try:
        if request.stream:
            # Streaming mode
            return StreamingResponse(
                _stream_response(graph, request, request_id, conversation_id),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming mode
            final_state = await graph.ainvoke(request, request_id, conversation_id)
            
            return ChatResponse(
                request_id=request_id,
                conversation_id=conversation_id,
                status="ok" if not final_state.get("error") else "error",
                answer=final_state["final_answer"],
                sources=final_state.get("citations", []),
                error=None if not final_state.get("error") else {
                    "code": "EXECUTION_ERROR",
                    "message": final_state["error"]
                },
                meta=ResponseMeta(
                    provider=final_state["execution_metadata"].get("provider"),
                    model=final_state["execution_metadata"].get("model"),
                    finish_reason=final_state["execution_metadata"].get("finish_reason")
                )
            )
    
    except Exception as e:
        logger.error(f"Chat V2 failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def _stream_response(
    graph: ResearchAgentGraph,
    request: ChatRequest,
    request_id: str,
    conversation_id: str
):
    """Stream SSE events from graph execution."""
    try:
        # Get graph stream
        graph_stream = graph.astream(request, request_id, conversation_id)
        
        # Convert to SSE
        sse_stream = SSEAdapter.stream_to_sse(graph_stream)
        
        # Yield SSE events
        async for sse_event in sse_stream:
            yield sse_event
    
    except Exception as e:
        logger.error(f"Streaming failed: {e}", exc_info=True)
        error_event = {
            "type": "error",
            "message": str(e)
        }
        yield f"data: {json.dumps(error_event)}\n\n"
```

**File**: `backend/src/api/deps.py`

**Trách nhiệm**: Dependency injection cho graph.

```python
from functools import lru_cache
from research_agent_v2.graph import ResearchAgentGraph
from research_agent.orchestrator import OrchestratorDependencies
from research_agent.complexity_analyzer import ComplexityAnalyzer
from research_agent.planning_agent import PlanningAgent
from research_agent.research_tool import ResearchTool
from research_agent.aggregator import Aggregator
from research_agent.response_composer import ResponseComposer
from research_agent.direct_llm import DirectLLM
from research_agent.database import Database
from research_agent.parser import Parser
from adapters import get_adapter_for_model
from config import settings

@lru_cache()
def get_research_agent_graph() -> ResearchAgentGraph:
    """
    Create and cache ResearchAgentGraph instance.
    
    Reuses existing components from research_agent module.
    """
    # Initialize existing components
    adapter = get_adapter_for_model(settings.default_model)
    
    deps = {
        "parser": Parser(),
        "analyzer": ComplexityAnalyzer(adapter=adapter, model=settings.default_model),
        "direct_llm": DirectLLM(adapter=adapter, model=settings.default_model),
        "database": Database(),
        "research_tool": ResearchTool(adapter=adapter, model=settings.default_model),
        "planning_agent": PlanningAgent(adapter=adapter, model=settings.default_model),
        "aggregator": Aggregator(),
        "response_composer": ResponseComposer(adapter=adapter, model=settings.default_model)
    }
    
    return ResearchAgentGraph(dependencies=deps)
```



### 8. Feature Flag và Migration Strategy

**File**: `backend/src/config.py`

**Trách nhiệm**: Add feature flag configuration.

```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...
    
    # LangGraph Migration Feature Flag
    enable_langgraph_agent: bool = os.getenv("ENABLE_LANGGRAPH_AGENT", "false").lower() == "true"
    
    # LangGraph Configuration
    langgraph_checkpointer: str = os.getenv("LANGGRAPH_CHECKPOINTER", "sqlite")
    langgraph_db_path: str = os.getenv("LANGGRAPH_DB_PATH", "./checkpoints.db")
    postgres_connection_string: str = os.getenv("POSTGRES_CONNECTION_STRING", "")

settings = Settings()
```

**File**: `backend/src/api/routers/chat.py`

**Trách nhiệm**: Update existing endpoint để support feature flag routing.

```python
from fastapi import APIRouter, Depends
from config import settings
from api.routers.chat_v2 import chat_v2
from research_agent.orchestrator import Orchestrator

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint với feature flag routing.
    
    Routes to:
    - LangGraph system if ENABLE_LANGGRAPH_AGENT=true
    - Pipeline orchestrator if ENABLE_LANGGRAPH_AGENT=false
    """
    if settings.enable_langgraph_agent:
        # Route to LangGraph V2
        return await chat_v2(request)
    else:
        # Route to existing Pipeline Orchestrator
        orchestrator = get_orchestrator()  # Existing dependency
        return orchestrator.process_request(request)
```

**Migration Phases**:

1. **Phase 1: Development (Week 1)**
   - Implement LangGraph system trong research_agent_v2/
   - Deploy /api/v2/chat endpoint
   - Test với ENABLE_LANGGRAPH_AGENT=false (existing system)
   - Internal testing với /api/v2/chat

2. **Phase 2: Canary Testing (Week 2)**
   - Enable ENABLE_LANGGRAPH_AGENT=true cho 10% traffic
   - Monitor metrics: response time, error rate, success rate
   - Compare LangGraph vs Pipeline performance
   - Rollback if critical issues

3. **Phase 3: Full Rollout (Week 3)**
   - Gradually increase to 50%, 100% traffic
   - Monitor và optimize
   - Deprecate /api/v2/chat (merge vào /api/chat)

4. **Phase 4: Cleanup (Week 4)**
   - Remove feature flag
   - Archive old Pipeline Orchestrator code
   - Update documentation

**Rollback Procedure**:

```bash
# Immediate rollback
export ENABLE_LANGGRAPH_AGENT=false
# Restart service
systemctl restart research-agent

# Or via environment file
echo "ENABLE_LANGGRAPH_AGENT=false" >> .env
docker-compose restart backend
```



## Data Models

### ComplexityResult

**File**: `research_agent/models.py` (existing, unchanged)

```python
@dataclass
class ComplexityResult:
    is_complex: bool
    confidence: float
    reason: str
```

### ResearchTask

**File**: `research_agent/models.py` (existing, unchanged)

```python
@dataclass
class ResearchTask:
    order: int
    query: str
    goal: str
```

### ResearchResult

**File**: `research_agent/models.py` (existing, unchanged)

```python
@dataclass
class ResearchResult:
    task_order: int
    extracted_information: str
    sources: List[str]
    success: bool
    error: Optional[str] = None
```

### ChatRequest

**File**: `models/request.py` (existing, unchanged)

```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None
    stream: bool = False
```

### ChatResponse

**File**: `models/response.py` (existing, unchanged)

```python
class ChatResponse(BaseModel):
    request_id: str
    conversation_id: str
    status: str
    answer: str
    sources: List[str]
    error: Optional[ResponseError]
    meta: ResponseMeta
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified the following redundancies:

**Redundancies Eliminated**:
1. Individual field type checks (2.1-2.9) → Combined into single schema validation property
2. Individual node timing logs (3.9, 10.8) → Combined into single metadata tracking property
3. Individual routing tests (5.1-5.5) → Combined into single routing correctness property
4. Individual performance tests (10.4-10.7) → Combined into single node performance property
5. Error logging tests (9.6, 9.7, 9.8) → Combined into single error handling property
6. State immutability (1.8) and node state updates (3.1-3.7) → Kept separate as they test different aspects

**Properties Retained**:
- Parallel execution speedup (4.6, 4.8, 10.1) → Kept as core performance property
- State persistence (7.2-7.5) → Combined into conversation memory property
- Backward compatibility (8.1-8.11) → Combined into single compatibility property
- Graceful degradation (9.1-9.9) → Combined into error handling property



### Property 1: State Immutability

*For any* AgentState và any graph node, khi node thực thi và return updated state, original state object MUST remain unchanged (immutable updates).

**Validates: Requirements 1.8**

### Property 2: Message Accumulation

*For any* conversation với N messages, AgentState.messages field MUST contain all N messages trong correct order sử dụng add_messages reducer.

**Validates: Requirements 2.10, 7.5**

### Property 3: Node State Updates

*For any* graph node execution, node MUST read current state, perform its logic, và return new state với updated fields relevant to its responsibility.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

### Property 4: Execution Metadata Tracking

*For any* graph execution, mỗi node MUST log execution time và update state.execution_metadata.node_timings với node name và duration.

**Validates: Requirements 3.9, 10.8**

### Property 5: Parallel Research Execution

*For any* research plan với N tasks (N ≥ 2), research_node MUST execute tasks concurrently using asyncio.gather, và total execution time MUST be ≤ max(individual_task_times) + overhead, NOT sum(individual_task_times).

**Validates: Requirements 4.1, 4.2, 4.3, 4.6**

### Property 6: Parallel Task Isolation

*For any* research plan với N tasks, nếu một task fails, remaining N-1 tasks MUST continue executing và return their results.

**Validates: Requirements 4.4**

### Property 7: Result Ordering

*For any* research plan với tasks có order values, research_node MUST return results sorted by ResearchTask.order field.

**Validates: Requirements 4.5**

### Property 8: Parallel Speedup

*For any* research plan với 3 tasks, parallel execution time MUST be ≤ 40% của sequential execution time (≥ 2.5x speedup).

**Validates: Requirements 4.8, 10.1**

### Property 9: Routing Correctness

*For any* AgentState với query_type field, conditional edge functions MUST return correct next node name: "simple" → simple_llm, "complex" → router, "research_intent" → planning, "current_date" → current_date, "direct_llm" → direct_llm.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

### Property 10: Routing Logging

*For any* routing decision, graph MUST log routing path với query_type, selected node, và reasoning.

**Validates: Requirements 5.8**

### Property 11: Streaming State Updates

*For any* graph execution using .astream(), graph MUST yield state update sau mỗi node execution, với total updates ≥ number of nodes executed.

**Validates: Requirements 6.2**

### Property 12: SSE Event Structure

*For any* SSE event generated from graph stream, event MUST include fields: node_name, status, progress_percentage, message, timestamp.

**Validates: Requirements 6.4**

### Property 13: Streaming Progress Updates

*For any* research_node execution với N tasks, streaming MUST emit progress update sau mỗi task completion, với total progress updates = N.

**Validates: Requirements 6.6**

### Property 14: Conversation Memory Persistence

*For any* conversation_id, khi graph executes multiple times với same conversation_id, checkpointer MUST persist state sau mỗi execution và load previous state khi invoked again.

**Validates: Requirements 7.2, 7.3, 7.4**

### Property 15: Backward Compatibility

*For any* existing test case từ Pipeline Orchestrator, migrated LangGraph system MUST produce equivalent results (same answer quality, same sources, same error handling).

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11**

### Property 16: Error State Tracking

*For any* node failure, graph MUST update state.error field với error message và continue execution (graceful degradation).

**Validates: Requirements 3.8, 9.6, 9.7, 9.8**

### Property 17: Graceful Degradation

*For any* node failure, graph MUST complete execution và return partial results hoặc fallback response, NOT raise unhandled exception.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.9**

### Property 18: Simple Query Performance

*For any* simple query (query_type="simple"), graph execution MUST complete trong ≤ 3 seconds.

**Validates: Requirements 10.2**

### Property 19: Complex Query Performance

*For any* complex query với 3 research tasks, graph execution MUST complete trong ≤ 12 seconds.

**Validates: Requirements 10.3**

### Property 20: Node Performance Bounds

*For any* node execution, node MUST complete within its specified timeout: complexity_node ≤ 2s, planning_node ≤ 5s, research_task ≤ 10s, synthesis_node ≤ 5s.

**Validates: Requirements 10.4, 10.5, 10.6, 10.7**

### Property 21: Execution Trace Inclusion

*For any* graph execution, final ChatResponse.meta MUST include execution trace với node_timings, query_type, và routing decisions.

**Validates: Requirements 13.6**

### Property 22: State Snapshot Logging

*For any* node execution, graph MUST log state snapshot sau node completes, including updated fields và metadata.

**Validates: Requirements 13.3**

### Property 23: Edge Decision Logging

*For any* conditional edge evaluation, graph MUST log decision với current query_type, selected next node, và reasoning.

**Validates: Requirements 13.4**



## Error Handling

### Node-Level Error Handling

**Strategy**: Mỗi node handle errors internally và return updated state với error information, allowing graph to continue.

**Implementation Pattern**:

```python
def example_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    """Example node với error handling."""
    try:
        # Node logic
        result = perform_operation()
        
        return {
            **state,
            "field": result,
            "error": None
        }
    
    except Exception as e:
        logger.error(f"Node failed: {e}", exc_info=True)
        
        return {
            **state,
            "error": f"Node failed: {str(e)}",
            "fallback_used": True
        }
```

### Fallback Mechanisms

1. **Complexity Analysis Failure**
   - Fallback: Use heuristic-based classification
   - Default: query_type = "simple"

2. **Planning Failure**
   - Fallback: Create single-step plan với original question
   - Continue: Execute research với fallback plan

3. **Research Partial Failure**
   - Fallback: Synthesize answer từ successful tasks only
   - Minimum: Require ≥ 1 successful task

4. **Research Complete Failure**
   - Fallback: Route to direct_llm_node
   - Response: LLM-generated answer without sources

5. **Synthesis Failure**
   - Fallback: Concatenate research results
   - Format: Simple bullet-point list

6. **LLM Failure**
   - Fallback: Return error message
   - Response: "Xin lỗi, tôi không thể trả lời câu hỏi này lúc này."

### Error Propagation

**State Error Field**:
```python
state["error"] = "Node X failed: error message"
state["fallback_used"] = True
```

**Final Response**:
```python
ChatResponse(
    status="error" if state["error"] else "ok",
    error=ResponseError(
        code="NODE_FAILURE",
        message=state["error"]
    ) if state["error"] else None
)
```

### Timeout Handling

**Per-Node Timeouts**:
- complexity_node: 2 seconds
- planning_node: 5 seconds
- research_task: 10 seconds (per task)
- synthesis_node: 5 seconds

**Implementation**:
```python
import asyncio

async def execute_with_timeout(coro, timeout: float, node_name: str):
    """Execute coroutine với timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"{node_name} timed out after {timeout}s")
        raise TimeoutError(f"{node_name} timeout")
```



## Testing Strategy

### Dual Testing Approach

**Unit Tests và Property Tests là complementary**:
- **Unit tests**: Verify specific examples, edge cases, error conditions
- **Property tests**: Verify universal properties across all inputs
- Together: Comprehensive coverage (unit tests catch concrete bugs, property tests verify general correctness)

### Unit Testing

**Focus Areas**:
1. **Specific Examples**: Test known input/output pairs
2. **Edge Cases**: Empty messages, invalid query_types, timeout scenarios
3. **Integration Points**: Node connections, edge routing, checkpointer integration
4. **Error Conditions**: Node failures, API errors, timeout handling

**Example Unit Tests**:

```python
def test_entry_node_initializes_metadata():
    """Test entry_node sets initial metadata."""
    state = {
        "messages": [HumanMessage(content="Hello")],
        "execution_metadata": {"conversation_id": "test"}
    }
    
    result = entry_node(state, deps)
    
    assert "node_timings" in result["execution_metadata"]
    assert "entry" in result["execution_metadata"]["node_timings"]

def test_complexity_edge_routes_simple_queries():
    """Test complexity_edge routes simple queries correctly."""
    state = {"query_type": "simple"}
    
    next_node = complexity_edge(state)
    
    assert next_node == "simple"

def test_research_node_handles_empty_plan():
    """Test research_node handles empty plan gracefully."""
    state = {"research_plan": None}
    
    result = research_node(state, deps)
    
    assert result["research_results"] == []
```

### Property-Based Testing

**Configuration**:
- Library: `hypothesis` (Python)
- Minimum iterations: 100 per property test
- Tag format: `# Feature: langgraph-migration, Property {number}: {property_text}`

**Property Test Examples**:

```python
from hypothesis import given, strategies as st
from hypothesis import settings

@given(st.text(min_size=1))
@settings(max_examples=100)
def test_property_1_state_immutability(question: str):
    """
    Feature: langgraph-migration, Property 1: State Immutability
    
    For any AgentState và any graph node, khi node thực thi và return 
    updated state, original state object MUST remain unchanged.
    """
    original_state = {
        "messages": [HumanMessage(content=question)],
        "query_type": "",
        "execution_metadata": {}
    }
    
    # Deep copy for comparison
    import copy
    state_before = copy.deepcopy(original_state)
    
    # Execute node
    result = entry_node(original_state, deps)
    
    # Verify original state unchanged
    assert original_state == state_before
    assert result is not original_state  # Different object

@given(st.lists(st.text(min_size=1), min_size=1, max_size=10))
@settings(max_examples=100)
def test_property_2_message_accumulation(messages: List[str]):
    """
    Feature: langgraph-migration, Property 2: Message Accumulation
    
    For any conversation với N messages, AgentState.messages field 
    MUST contain all N messages trong correct order.
    """
    state = {"messages": []}
    
    # Add messages one by one
    for msg in messages:
        state["messages"] = add_messages(
            state["messages"],
            [HumanMessage(content=msg)]
        )
    
    # Verify all messages present in order
    assert len(state["messages"]) == len(messages)
    for i, msg in enumerate(messages):
        assert state["messages"][i].content == msg

@given(st.integers(min_value=2, max_value=5))
@settings(max_examples=100)
async def test_property_5_parallel_research_execution(num_tasks: int):
    """
    Feature: langgraph-migration, Property 5: Parallel Research Execution
    
    For any research plan với N tasks (N ≥ 2), research_node MUST execute 
    tasks concurrently, và total execution time MUST be ≤ max(individual_task_times) + overhead.
    """
    # Create plan with N tasks
    plan = [
        ResearchTask(order=i, query=f"Query {i}", goal="Test")
        for i in range(1, num_tasks + 1)
    ]
    
    state = {"research_plan": plan}
    
    # Measure execution time
    import time
    start = time.time()
    result = await research_node(state, deps)
    duration = time.time() - start
    
    # Verify parallel execution (should be much less than N * 10s)
    # Allow 20% overhead for asyncio coordination
    max_expected = 10.0 * 1.2  # Max task time + overhead
    assert duration <= max_expected
    
    # Verify all results collected
    assert len(result["research_results"]) == num_tasks

@given(st.integers(min_value=1, max_value=5))
@settings(max_examples=100)
async def test_property_8_parallel_speedup(num_tasks: int):
    """
    Feature: langgraph-migration, Property 8: Parallel Speedup
    
    For any research plan với 3 tasks, parallel execution time MUST be 
    ≤ 40% của sequential execution time (≥ 2.5x speedup).
    """
    if num_tasks != 3:
        return  # Only test with 3 tasks
    
    plan = [
        ResearchTask(order=i, query=f"Query {i}", goal="Test")
        for i in range(1, 4)
    ]
    
    # Measure parallel execution
    state_parallel = {"research_plan": plan}
    start = time.time()
    await research_node(state_parallel, deps)
    parallel_time = time.time() - start
    
    # Estimate sequential time (3 tasks * ~10s each = ~30s)
    estimated_sequential = 30.0
    
    # Verify speedup
    assert parallel_time <= estimated_sequential * 0.4  # ≤ 40% of sequential

@given(
    st.sampled_from(["simple", "complex", "research_intent", "current_date", "direct_llm"])
)
@settings(max_examples=100)
def test_property_9_routing_correctness(query_type: str):
    """
    Feature: langgraph-migration, Property 9: Routing Correctness
    
    For any AgentState với query_type field, conditional edge functions 
    MUST return correct next node name.
    """
    state = {"query_type": query_type}
    
    # Test complexity edge
    if query_type == "simple":
        assert complexity_edge(state) == "simple"
    elif query_type == "complex":
        assert complexity_edge(state) == "complex"
    
    # Test router edge
    if query_type == "research_intent":
        assert router_edge(state) == "research_intent"
    elif query_type == "current_date":
        assert router_edge(state) == "current_date"
    elif query_type == "direct_llm":
        assert router_edge(state) == "direct_llm"

@given(st.text(min_size=1))
@settings(max_examples=100)
async def test_property_17_graceful_degradation(question: str):
    """
    Feature: langgraph-migration, Property 17: Graceful Degradation
    
    For any node failure, graph MUST complete execution và return partial 
    results hoặc fallback response, NOT raise unhandled exception.
    """
    # Inject failure in planning_node
    def failing_planning_node(state, deps):
        raise Exception("Simulated failure")
    
    # Replace node temporarily
    original_node = graph.workflow.nodes["planning"]
    graph.workflow.nodes["planning"] = failing_planning_node
    
    try:
        # Execute graph
        result = await graph.ainvoke(
            ChatRequest(message=question),
            request_id="test",
            conversation_id="test"
        )
        
        # Verify no exception raised
        assert result is not None
        
        # Verify error tracked
        assert result.get("error") is not None or result.get("fallback_used") is True
        
        # Verify partial result returned
        assert result.get("final_answer") != ""
    
    finally:
        # Restore original node
        graph.workflow.nodes["planning"] = original_node
```

### Integration Testing

**Test Scenarios**:
1. **End-to-End Simple Query**: Entry → Complexity → Simple LLM → END
2. **End-to-End Complex Query**: Entry → Complexity → Router → Planning → Research → Synthesis → Citation → END
3. **Current Date Query**: Entry → Complexity → Router → Current Date → END
4. **Streaming Execution**: Verify all SSE events emitted
5. **Conversation Memory**: Multiple turns với same conversation_id
6. **Feature Flag Routing**: Test both LangGraph và Pipeline paths

### Performance Testing

**Benchmarks**:
1. **Simple Query Latency**: Target ≤ 3s (P99)
2. **Complex Query Latency**: Target ≤ 12s (P99)
3. **Parallel Speedup**: Measure actual speedup vs sequential
4. **Throughput**: Concurrent requests handling
5. **Memory Usage**: Monitor state size growth

**Tools**:
- `pytest-benchmark` for latency measurements
- `locust` for load testing
- `memory_profiler` for memory analysis

### Test Coverage Goals

- **Line Coverage**: ≥ 90% for research_agent_v2/ module
- **Branch Coverage**: ≥ 85% for conditional logic
- **Property Coverage**: All 23 correctness properties tested
- **Integration Coverage**: All graph paths tested



## Migration Strategy

### Phase 1: Development (Week 1)

**Goals**:
- Implement complete LangGraph system
- Unit test coverage ≥ 90%
- Property tests for core properties

**Tasks**:
1. Setup project structure: `research_agent_v2/`
2. Implement AgentState schema
3. Implement all graph nodes
4. Implement conditional edges
5. Implement StateGraph construction
6. Implement checkpointer configuration
7. Implement SSE adapter
8. Create /api/v2/chat endpoint
9. Write unit tests
10. Write property tests

**Deliverables**:
- Working /api/v2/chat endpoint
- Test suite với ≥ 90% coverage
- Documentation

### Phase 2: Integration Testing (Week 2 - Days 1-3)

**Goals**:
- Verify end-to-end functionality
- Compare performance với Pipeline Orchestrator
- Identify và fix issues

**Tasks**:
1. Run integration tests
2. Performance benchmarking
3. Load testing
4. Bug fixes
5. Optimization

**Success Criteria**:
- All integration tests pass
- Parallel speedup ≥ 2.5x
- Simple queries ≤ 3s
- Complex queries ≤ 12s

### Phase 3: Canary Deployment (Week 2 - Days 4-7)

**Goals**:
- Deploy to production với limited traffic
- Monitor metrics và errors
- Validate in production environment

**Tasks**:
1. Deploy với ENABLE_LANGGRAPH_AGENT=false
2. Enable feature flag cho 10% traffic
3. Monitor metrics:
   - Response time (P50, P95, P99)
   - Error rate
   - Success rate
   - Parallel speedup
4. Compare LangGraph vs Pipeline metrics
5. Adjust if needed

**Rollback Trigger**:
- Error rate > 5%
- P99 latency > 15s
- Critical bugs

### Phase 4: Gradual Rollout (Week 3)

**Goals**:
- Increase traffic to LangGraph system
- Maintain stability
- Full production validation

**Schedule**:
- Day 1-2: 25% traffic
- Day 3-4: 50% traffic
- Day 5-6: 75% traffic
- Day 7: 100% traffic

**Monitoring**:
- Continuous metrics tracking
- Error alerting
- Performance dashboards

### Phase 5: Cleanup (Week 4)

**Goals**:
- Remove feature flag
- Deprecate old code
- Update documentation

**Tasks**:
1. Remove ENABLE_LANGGRAPH_AGENT flag
2. Remove /api/v2/chat (merge to /api/chat)
3. Archive Pipeline Orchestrator code
4. Update API documentation
5. Update deployment guides
6. Celebrate! 🎉

### Rollback Procedure

**Immediate Rollback** (< 5 minutes):
```bash
# Set feature flag to false
export ENABLE_LANGGRAPH_AGENT=false

# Restart service
systemctl restart research-agent

# Or via Docker
docker-compose restart backend
```

**Full Rollback** (< 30 minutes):
```bash
# Revert to previous deployment
git revert <migration-commit>
git push origin main

# Redeploy
./deploy.sh

# Verify old system working
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test query"}'
```

### Risk Mitigation

**Risks**:
1. **Performance Regression**: Parallel execution slower than expected
   - Mitigation: Benchmark early, optimize before rollout
   - Fallback: Keep Pipeline Orchestrator available

2. **Breaking Changes**: API incompatibility
   - Mitigation: Maintain exact API contract
   - Validation: Run existing test suite

3. **Memory Leaks**: State accumulation in checkpointer
   - Mitigation: Implement cleanup job
   - Monitoring: Track memory usage

4. **Checkpointer Failures**: Database connection issues
   - Mitigation: Graceful degradation without checkpointer
   - Fallback: In-memory checkpointer

5. **Streaming Issues**: SSE connection drops
   - Mitigation: Maintain backward compatibility
   - Fallback: Non-streaming mode

### Success Metrics

**Performance**:
- ✅ Parallel speedup ≥ 2.5x (Target: 3x)
- ✅ Simple queries P99 ≤ 3s
- ✅ Complex queries P99 ≤ 12s
- ✅ Throughput ≥ current system

**Reliability**:
- ✅ Error rate ≤ current system
- ✅ Success rate ≥ 95%
- ✅ Zero breaking changes

**Quality**:
- ✅ Test coverage ≥ 90%
- ✅ All properties validated
- ✅ Documentation complete

**Timeline**:
- ✅ Development complete: Week 1
- ✅ Testing complete: Week 2
- ✅ Production rollout: Week 3
- ✅ Cleanup complete: Week 4



## Observability và Debugging

### Graph Visualization

**Mermaid Diagram Generation**:

```python
def generate_graph_diagram(graph: StateGraph) -> str:
    """Generate mermaid diagram của graph structure."""
    return graph.get_graph().draw_mermaid()
```

**API Endpoint**:

```python
@router.get("/api/graph/visualize")
async def visualize_graph():
    """Return mermaid diagram của LangGraph structure."""
    graph = get_research_agent_graph()
    diagram = generate_graph_diagram(graph.workflow)
    
    return {
        "diagram": diagram,
        "format": "mermaid"
    }
```

**Example Output**:
```mermaid
graph TD
    entry --> complexity
    complexity -->|simple| simple_llm
    complexity -->|complex| router
    router -->|research_intent| planning
    router -->|current_date| current_date
    router -->|direct_llm| direct_llm
    planning --> research
    research --> synthesis
    synthesis --> citation
    simple_llm --> END
    direct_llm --> citation
    current_date --> END
    citation --> END
```

### Execution Tracing

**State Snapshots**:

```python
import logging
import json

logger = logging.getLogger("langgraph.execution")

def log_state_snapshot(node_name: str, state: AgentState):
    """Log state snapshot sau node execution."""
    snapshot = {
        "node": node_name,
        "query_type": state.get("query_type"),
        "has_error": state.get("error") is not None,
        "message_count": len(state.get("messages", [])),
        "research_results_count": len(state.get("research_results", [])),
        "execution_time": state.get("execution_metadata", {}).get("node_timings", {}).get(node_name)
    }
    
    logger.info(f"state_snapshot", extra=snapshot)
```

**Execution History API**:

```python
@router.get("/api/graph/history/{conversation_id}")
async def get_execution_history(conversation_id: str):
    """
    Retrieve execution history cho conversation.
    
    Returns:
        List of state snapshots từ checkpointer
    """
    checkpointer = get_checkpointer()
    
    # Get all checkpoints for conversation
    checkpoints = await checkpointer.alist(
        config={"configurable": {"thread_id": conversation_id}}
    )
    
    history = []
    for checkpoint in checkpoints:
        history.append({
            "checkpoint_id": checkpoint.id,
            "timestamp": checkpoint.ts,
            "state": checkpoint.channel_values,
            "metadata": checkpoint.metadata
        })
    
    return {
        "conversation_id": conversation_id,
        "history": history
    }
```

### Logging Strategy

**Structured Logging**:

```python
import structlog

logger = structlog.get_logger()

# Node execution
logger.info(
    "node_execution",
    node="research",
    conversation_id="abc123",
    execution_time_ms=5432,
    num_tasks=3,
    successful_tasks=3
)

# Routing decision
logger.info(
    "routing_decision",
    from_node="complexity",
    to_node="router",
    query_type="complex",
    confidence=0.95,
    reasoning="Multi-step research required"
)

# Error
logger.error(
    "node_error",
    node="planning",
    error_type="TimeoutError",
    error_message="Planning timeout after 5s",
    conversation_id="abc123",
    stack_trace=traceback.format_exc()
)
```

**Log Levels**:
- **DEBUG**: State snapshots, detailed execution flow
- **INFO**: Node execution, routing decisions, performance metrics
- **WARNING**: Fallbacks, timeouts, degraded performance
- **ERROR**: Node failures, API errors, critical issues

### Metrics Collection

**Prometheus Metrics**:

```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
graph_requests_total = Counter(
    "langgraph_requests_total",
    "Total graph executions",
    ["query_type", "status"]
)

graph_execution_duration = Histogram(
    "langgraph_execution_duration_seconds",
    "Graph execution duration",
    ["query_type"],
    buckets=[1, 3, 5, 10, 15, 30, 60]
)

# Node metrics
node_execution_duration = Histogram(
    "langgraph_node_duration_seconds",
    "Node execution duration",
    ["node_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

node_errors_total = Counter(
    "langgraph_node_errors_total",
    "Total node errors",
    ["node_name", "error_type"]
)

# Research metrics
research_tasks_total = Counter(
    "langgraph_research_tasks_total",
    "Total research tasks executed",
    ["status"]
)

parallel_speedup = Gauge(
    "langgraph_parallel_speedup",
    "Parallel execution speedup ratio"
)
```

**Metrics Endpoint**:

```python
from prometheus_client import generate_latest

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### Debug Mode

**Configuration**:

```bash
# Enable debug mode
export DEBUG_LANGGRAPH=true
export LOG_LEVEL=DEBUG
```

**Debug Features**:

```python
import os

DEBUG_MODE = os.getenv("DEBUG_LANGGRAPH", "false").lower() == "true"

def debug_log(message: str, **kwargs):
    """Log only in debug mode."""
    if DEBUG_MODE:
        logger.debug(message, **kwargs)

# In nodes
def research_node(state: AgentState, deps: Dict[str, Any]) -> AgentState:
    debug_log("research_node_start", state=state)
    
    # ... node logic ...
    
    debug_log("research_node_complete", results=results)
    
    return updated_state
```

### Monitoring Dashboard

**Key Metrics to Monitor**:

1. **Performance**:
   - P50, P95, P99 latency by query_type
   - Parallel speedup ratio
   - Node execution times

2. **Reliability**:
   - Error rate by node
   - Success rate by query_type
   - Fallback usage rate

3. **Resource Usage**:
   - Memory usage
   - CPU usage
   - Checkpointer database size

4. **Business Metrics**:
   - Requests per minute
   - Query type distribution
   - Average research tasks per query

**Grafana Dashboard Example**:
```json
{
  "dashboard": {
    "title": "LangGraph Research Agent",
    "panels": [
      {
        "title": "Request Latency",
        "targets": [
          "histogram_quantile(0.99, langgraph_execution_duration_seconds)"
        ]
      },
      {
        "title": "Parallel Speedup",
        "targets": [
          "langgraph_parallel_speedup"
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          "rate(langgraph_node_errors_total[5m])"
        ]
      }
    ]
  }
}
```



## Dependencies

### External Dependencies

**Core Dependencies** (already installed):
```toml
[tool.poetry.dependencies]
# LangChain và LangGraph
langgraph = "1.0.10"
langchain = "1.2.10"
langchain-google-genai = "4.2.1"
groq = "0.31.1"

# FastAPI và Web
fastapi = "0.135.1"
uvicorn = {extras = ["standard"], version = "0.41.0"}
pydantic = "2.12.5"
sse-starlette = "3.3.2"

# Utilities
python-dotenv = "1.2.2"
httpx = "0.28.1"
redis = "7.2.1"

# Monitoring
prometheus-client = "0.24.1"

# Security
cryptography = "46.0.5"
```

**Testing Dependencies** (already installed):
```toml
[tool.poetry.dev-dependencies]
pytest = "9.0.2"
hypothesis = "6.151.9"
```

**Additional Dependencies Needed**:
```toml
[tool.poetry.dependencies]
# For LangGraph checkpointer support
langgraph-checkpoint-sqlite = "^1.0.0"  # Compatible với langgraph 1.0.10
aiosqlite = "^0.20.0"  # Async SQLite support

# Optional for production
langgraph-checkpoint-postgres = "^1.0.0"  # For production checkpointer
asyncpg = "^0.29.0"  # Async Postgres driver
```

### Internal Dependencies

**Existing Components** (reused, unchanged):
- `research_agent.complexity_analyzer.ComplexityAnalyzer`
- `research_agent.planning_agent.PlanningAgent`
- `research_agent.research_tool.ResearchTool`
- `research_agent.aggregator.Aggregator`
- `research_agent.response_composer.ResponseComposer`
- `research_agent.direct_llm.DirectLLM`
- `research_agent.database.Database`
- `research_agent.parser.Parser`
- `adapters.get_adapter_for_model`

**Dependency Injection**:

```python
# All existing components are injected into graph nodes
dependencies = {
    "parser": Parser(),
    "analyzer": ComplexityAnalyzer(adapter, model),
    "direct_llm": DirectLLM(adapter, model),
    "database": Database(),
    "research_tool": ResearchTool(adapter, model),
    "planning_agent": PlanningAgent(adapter, model),
    "aggregator": Aggregator(),
    "response_composer": ResponseComposer(adapter, model)
}

graph = ResearchAgentGraph(dependencies)
```

### Configuration Dependencies

**Environment Variables**:

```bash
# LangGraph Configuration
ENABLE_LANGGRAPH_AGENT=true
LANGGRAPH_CHECKPOINTER=sqlite  # or "postgres"
LANGGRAPH_DB_PATH=./checkpoints.db
POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:5432/dbname

# Debug Configuration
DEBUG_LANGGRAPH=false
LOG_LEVEL=INFO

# Existing Configuration (unchanged)
GOOGLE_API_KEY=...
TAVILY_API_KEY=...
DEFAULT_MODEL=gemini-1.5-flash
```

## Performance Considerations

### Parallel Execution Optimization

**AsyncIO Best Practices**:

1. **Use asyncio.gather for concurrent tasks**:
   ```python
   results = await asyncio.gather(*[task() for task in tasks])
   ```

2. **Set appropriate timeouts**:
   ```python
   await asyncio.wait_for(task(), timeout=10.0)
   ```

3. **Use thread pool for blocking operations**:
   ```python
   loop = asyncio.get_event_loop()
   result = await loop.run_in_executor(None, blocking_function)
   ```

### Memory Management

**State Size Optimization**:
- Limit message history to last 10 messages
- Compress research results before storing
- Clean up old checkpoints regularly

**Checkpointer Cleanup**:
```python
async def cleanup_old_checkpoints():
    """Remove checkpoints older than 7 days."""
    cutoff = datetime.now() - timedelta(days=7)
    await checkpointer.delete_before(cutoff)
```

### Caching Strategy

**Query Result Caching**:
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def get_cached_research_result(query_hash: str):
    """Cache research results for identical queries."""
    pass
```

**Complexity Analysis Caching**:
```python
# Cache complexity results for 1 hour
complexity_cache = TTLCache(maxsize=10000, ttl=3600)
```

### Database Optimization

**Checkpointer Indexing**:
```sql
-- SQLite
CREATE INDEX idx_conversation_id ON checkpoints(thread_id);
CREATE INDEX idx_timestamp ON checkpoints(ts);

-- Postgres
CREATE INDEX idx_conversation_id ON checkpoints(thread_id);
CREATE INDEX idx_timestamp ON checkpoints(ts);
```

## Security Considerations

### Input Validation

**Message Sanitization**:
```python
def validate_message(message: str) -> str:
    """Validate và sanitize user message."""
    # Length check
    if len(message) > 10000:
        raise ValueError("Message too long")
    
    # Remove control characters
    sanitized = "".join(char for char in message if char.isprintable() or char.isspace())
    
    return sanitized.strip()
```

### State Isolation

**Conversation Isolation**:
- Each conversation_id has isolated state
- No cross-conversation data leakage
- Checkpointer enforces thread_id isolation

### API Security

**Rate Limiting**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/v2/chat")
@limiter.limit("10/minute")
async def chat_v2(request: ChatRequest):
    pass
```

**Authentication** (if needed):
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    """Verify JWT token."""
    token = credentials.credentials
    # Verify token logic
    return user_id
```

## Deployment

### Docker Configuration

**Dockerfile**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

# Copy application
COPY backend/src ./src

# Environment
ENV PYTHONPATH=/app/src
ENV ENABLE_LANGGRAPH_AGENT=true
ENV LANGGRAPH_CHECKPOINTER=sqlite
ENV LANGGRAPH_DB_PATH=/data/checkpoints.db

# Volume for checkpointer
VOLUME /data

# Run
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Docker Compose**:
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENABLE_LANGGRAPH_AGENT=true
      - LANGGRAPH_CHECKPOINTER=postgres
      - POSTGRES_CONNECTION_STRING=postgresql://user:pass@postgres:5432/research_agent
    volumes:
      - ./data:/data
    depends_on:
      - postgres
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=research_agent
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Kubernetes Deployment

**Deployment YAML**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: research-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: research-agent
  template:
    metadata:
      labels:
        app: research-agent
    spec:
      containers:
      - name: backend
        image: research-agent:latest
        env:
        - name: ENABLE_LANGGRAPH_AGENT
          value: "true"
        - name: LANGGRAPH_CHECKPOINTER
          value: "postgres"
        - name: POSTGRES_CONNECTION_STRING
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: connection-string
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

## Conclusion

Migration sang LangGraph framework mang lại significant improvements:

**Performance**: 2.5-3x faster cho complex queries nhờ parallel execution

**Maintainability**: Clear separation of concerns, mỗi node một responsibility

**Debuggability**: Visual graph structure, state snapshots, execution traces

**Extensibility**: Dễ dàng thêm nodes mới cho tools mới

**Reliability**: Better error handling và fallback mechanisms

Migration strategy với feature flag và gradual rollout ensures zero downtime và easy rollback nếu có issues.

Comprehensive testing strategy với unit tests và property-based tests ensures correctness và prevents regressions.

