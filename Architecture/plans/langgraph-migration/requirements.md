# Tài liệu Yêu cầu - Migration sang LangGraph Framework

## Giới thiệu

Dự án này migrate hệ thống Research Agent từ kiến trúc pipeline (thực thi tuần tự) sang LangGraph framework để cải thiện hiệu suất, khả năng bảo trì, và mở rộng. Hệ thống hiện tại sử dụng pipeline orchestration với sequential task execution, custom SSE infrastructure, và tích hợp Google Gemini API. Migration sang LangGraph sẽ cho phép parallel execution, centralized state management, declarative routing, và native streaming capabilities.

## Glossary

- **LangGraph**: Framework orchestration cho AI agents sử dụng state machines và directed graphs
- **StateGraph**: LangGraph component định nghĩa nodes và edges với typed state management
- **AgentState**: TypedDict schema chứa shared state flow qua graph nodes
- **Graph_Node**: Function nhận state và return updated state trong LangGraph workflow
- **Conditional_Edge**: Dynamic routing logic dựa trên state values
- **Checkpointer**: LangGraph component persist conversation state cho memory
- **Pipeline_Orchestrator**: Hệ thống hiện tại orchestrate tasks sequentially
- **Research_Agent**: AI agent tự động research và trả lời câu hỏi
- **Complexity_Analyzer**: Component phân loại câu hỏi simple vs complex
- **Planning_Agent**: Component tạo multi-step research plan
- **Research_Tool**: Tool thực hiện web search và extract information
- **Parallel_Execution**: Khả năng chạy multiple research tasks đồng thời
- **SSE_Infrastructure**: Server-Sent Events system cho streaming status updates
- **Router_Node**: Graph node phân loại queries và route đến appropriate tool
- **Tool_Node**: Graph node thực thi specific tool (web_search, rag, calculator)
- **Citation_Node**: Graph node format final answer với source citations

## Requirements

### Requirement 1: LangGraph StateGraph Implementation

**User Story:** Là một developer, tôi muốn migrate orchestration logic sang LangGraph StateGraph, để hệ thống có state management rõ ràng và dễ debug hơn.

#### Acceptance Criteria

1. THE StateGraph SHALL define AgentState TypedDict với fields: messages, query_type, complexity_result, research_plan, research_results, final_answer, citations, execution_metadata
2. THE StateGraph SHALL include nodes: entry_node, complexity_node, router_node, planning_node, research_node, synthesis_node, citation_node
3. THE StateGraph SHALL set entry_node làm entry point của graph
4. THE StateGraph SHALL add conditional edges từ complexity_node routing đến simple_llm_node hoặc router_node
5. THE StateGraph SHALL add conditional edges từ router_node routing đến planning_node, direct_llm_node, hoặc current_date_node
6. THE StateGraph SHALL connect planning_node → research_node → synthesis_node → citation_node → END
7. THE StateGraph SHALL compile với SqliteSaver checkpointer cho conversation memory
8. FOR ALL valid AgentState objects, THE StateGraph SHALL preserve state immutability (nodes return new state copies)

### Requirement 2: AgentState Schema Definition

**User Story:** Là một developer, tôi muốn centralized state schema, để tất cả nodes share consistent data structure.

#### Acceptance Criteria

1. THE AgentState SHALL define messages field với type Annotated[Sequence[BaseMessage], add_messages]
2. THE AgentState SHALL define query_type field với type str (values: "simple", "complex", "current_date", "research_intent")
3. THE AgentState SHALL define complexity_result field với type Optional[ComplexityResult]
4. THE AgentState SHALL define research_plan field với type Optional[List[ResearchTask]]
5. THE AgentState SHALL define research_results field với type List[ResearchResult]
6. THE AgentState SHALL define final_answer field với type str
7. THE AgentState SHALL define citations field với type List[str]
8. THE AgentState SHALL define execution_metadata field với type Dict[str, Any] chứa conversation_id, request_id, user_id, timestamps
9. THE AgentState SHALL define error field với type Optional[str]
10. THE AgentState SHALL use add_messages reducer để automatically aggregate message history

### Requirement 3: Convert Pipeline Orchestrator Methods to Graph Nodes

**User Story:** Là một developer, tôi muốn convert existing orchestrator methods thành independent graph nodes, để improve separation of concerns và testability.

#### Acceptance Criteria

1. THE entry_node SHALL initialize AgentState từ ChatRequest và set initial metadata
2. THE complexity_node SHALL invoke Complexity_Analyzer và update state.complexity_result và state.query_type
3. THE router_node SHALL evaluate query_type và determine routing decision (planning, direct_llm, current_date)
4. THE planning_node SHALL invoke Planning_Agent và update state.research_plan
5. THE research_node SHALL execute research tasks và update state.research_results
6. THE synthesis_node SHALL synthesize final answer từ research_results và update state.final_answer
7. THE citation_node SHALL format citations và append vào state.final_answer
8. WHEN any node encounters error, THE node SHALL update state.error và allow graph to continue hoặc terminate gracefully
9. FOR ALL nodes, THE node SHALL log execution time và update state.execution_metadata

### Requirement 4: Parallel Research Task Execution

**User Story:** Là một user, tôi muốn research tasks chạy parallel thay vì sequential, để nhận được kết quả nhanh hơn 3x.

#### Acceptance Criteria

1. THE research_node SHALL execute multiple ResearchTasks concurrently using asyncio.gather
2. WHEN research_plan contains N tasks, THE research_node SHALL spawn N concurrent coroutines
3. THE research_node SHALL collect results từ all concurrent tasks vào state.research_results
4. WHEN một research task fails, THE research_node SHALL continue executing remaining tasks
5. THE research_node SHALL maintain task order trong results dựa trên ResearchTask.order field
6. THE research_node SHALL complete execution within max(individual_task_times) thay vì sum(individual_task_times)
7. THE research_node SHALL log parallel execution metrics (total_time, num_tasks, success_rate)
8. FOR ALL research plans với 3 tasks, parallel execution SHALL complete trong ≤ 40% thời gian của sequential execution

### Requirement 5: Conditional Routing Logic

**User Story:** Là một developer, tôi muốn declarative routing logic thay vì if/else chains, để code dễ đọc và maintain hơn.

#### Acceptance Criteria

1. THE complexity_conditional_edge SHALL route "simple" queries đến simple_llm_node
2. THE complexity_conditional_edge SHALL route "complex" queries đến router_node
3. THE router_conditional_edge SHALL route "current_date" queries đến current_date_node → END
4. THE router_conditional_edge SHALL route "research_intent" queries đến planning_node
5. THE router_conditional_edge SHALL route "direct_llm" queries đến direct_llm_node → citation_node
6. THE conditional_edge_functions SHALL read state.query_type và return next node name
7. THE conditional_edge_functions SHALL handle invalid query_type bằng cách default đến direct_llm_node
8. FOR ALL routing decisions, THE graph SHALL log routing path và reasoning

### Requirement 6: LangGraph Native Streaming Integration

**User Story:** Là một user, tôi muốn real-time status updates sử dụng LangGraph's native streaming, để thay thế custom SSE infrastructure.

#### Acceptance Criteria

1. THE StateGraph SHALL support .astream() method cho streaming execution
2. WHEN graph executes, THE .astream() SHALL yield state updates sau mỗi node execution
3. THE FastAPI endpoint SHALL consume .astream() và convert thành SSE events
4. THE SSE events SHALL include fields: node_name, status, progress_percentage, message, timestamp
5. THE streaming SHALL emit events cho: complexity_analysis_start, complexity_analysis_complete, planning_start, planning_complete, research_start, research_progress, research_complete, synthesis_start, synthesis_complete
6. WHEN research_node executes parallel tasks, THE streaming SHALL emit progress updates cho mỗi completed task
7. THE streaming SHALL maintain backward compatibility với existing frontend SSE consumer
8. THE streaming SHALL complete final event với type "done" và include full ChatResponse

### Requirement 7: Conversation Memory với Checkpointer

**User Story:** Là một user, tôi muốn agent nhớ conversation history, để tôi có thể hỏi follow-up questions.

#### Acceptance Criteria

1. THE StateGraph SHALL compile với SqliteSaver checkpointer
2. THE checkpointer SHALL persist AgentState sau mỗi node execution
3. THE checkpointer SHALL use conversation_id làm thread_id cho state isolation
4. WHEN user gửi message với existing conversation_id, THE graph SHALL load previous state từ checkpointer
5. THE AgentState.messages SHALL accumulate conversation history using add_messages reducer
6. THE graph SHALL pass config={"configurable": {"thread_id": conversation_id}} khi invoke
7. THE checkpointer SHALL support retrieval của conversation history cho debugging
8. THE checkpointer SHALL cleanup old conversations sau 7 days

### Requirement 8: Maintain Existing Functionality

**User Story:** Là một user, tôi muốn tất cả existing features hoạt động như cũ sau migration, để không bị breaking changes.

#### Acceptance Criteria

1. THE migrated system SHALL preserve complexity analysis logic từ Complexity_Analyzer
2. THE migrated system SHALL preserve planning logic từ Planning_Agent
3. THE migrated system SHALL preserve research execution logic từ Research_Tool
4. THE migrated system SHALL preserve time-sensitive request detection
5. THE migrated system SHALL preserve research intent detection
6. THE migrated system SHALL preserve current date handling
7. THE migrated system SHALL preserve source deduplication logic
8. THE migrated system SHALL preserve citation formatting logic
9. THE migrated system SHALL preserve error handling và fallback behavior
10. THE migrated system SHALL preserve API request/response schemas (ChatRequest, ChatResponse)
11. FOR ALL existing test cases, THE migrated system SHALL pass without modification

### Requirement 9: Error Handling và Fallback

**User Story:** Là một user, tôi muốn graceful error handling khi nodes fail, để luôn nhận được response thay vì system crash.

#### Acceptance Criteria

1. WHEN complexity_node fails, THE graph SHALL default query_type="simple" và continue
2. WHEN planning_node fails, THE graph SHALL create fallback plan với single research task
3. WHEN research_node fails partially, THE graph SHALL synthesize answer từ successful tasks
4. WHEN research_node fails completely, THE graph SHALL fallback đến direct LLM response
5. WHEN synthesis_node fails, THE graph SHALL return concatenated research results
6. THE graph SHALL log all errors với node_name, error_type, error_message, stack_trace
7. THE graph SHALL update state.error field khi errors occur
8. THE graph SHALL include error context trong final ChatResponse.error field
9. FOR ALL node failures, THE graph SHALL complete execution và return partial results thay vì raise exception

### Requirement 10: Performance Optimization

**User Story:** Là một user, tôi muốn faster response times, để có better user experience.

#### Acceptance Criteria

1. THE parallel research execution SHALL reduce total research time xuống ≤ 40% so với sequential
2. THE graph execution SHALL complete simple queries trong ≤ 3 seconds
3. THE graph execution SHALL complete complex queries với 3 research tasks trong ≤ 12 seconds (vs 30+ seconds sequential)
4. THE complexity_node SHALL complete analysis trong ≤ 2 seconds
5. THE planning_node SHALL complete plan generation trong ≤ 5 seconds
6. THE research_node SHALL execute individual research task trong ≤ 10 seconds
7. THE synthesis_node SHALL complete answer generation trong ≤ 5 seconds
8. THE graph SHALL log performance metrics cho mỗi node: execution_time_ms, input_tokens, output_tokens
9. THE graph SHALL expose performance metrics qua /metrics endpoint

### Requirement 11: Testing và Validation

**User Story:** Là một developer, tôi muốn comprehensive tests cho LangGraph implementation, để ensure correctness và prevent regressions.

#### Acceptance Criteria

1. THE test suite SHALL include unit tests cho mỗi graph node function
2. THE test suite SHALL include integration tests cho complete graph execution
3. THE test suite SHALL include tests cho conditional edge routing logic
4. THE test suite SHALL include tests cho parallel research execution
5. THE test suite SHALL include tests cho checkpointer state persistence
6. THE test suite SHALL include tests cho streaming functionality
7. THE test suite SHALL include tests cho error handling và fallback scenarios
8. THE test suite SHALL include performance tests validating parallel speedup
9. THE test suite SHALL include tests cho conversation memory across multiple turns
10. THE test suite SHALL achieve ≥ 90% code coverage cho LangGraph components

### Requirement 12: Migration Path và Backward Compatibility

**User Story:** Là một developer, tôi muốn smooth migration path, để có thể deploy incrementally mà không break production.

#### Acceptance Criteria

1. THE migration SHALL implement LangGraph system trong separate module: research_agent_v2/
2. THE migration SHALL preserve existing Pipeline_Orchestrator trong research_agent/ cho backward compatibility
3. THE FastAPI SHALL expose new endpoint /api/v2/chat sử dụng LangGraph system
4. THE FastAPI SHALL maintain existing endpoint /api/chat sử dụng Pipeline_Orchestrator
5. THE migration SHALL include feature flag ENABLE_LANGGRAPH_AGENT trong environment config
6. WHEN ENABLE_LANGGRAPH_AGENT=true, THE /api/chat endpoint SHALL route đến LangGraph system
7. WHEN ENABLE_LANGGRAPH_AGENT=false, THE /api/chat endpoint SHALL route đến Pipeline_Orchestrator
8. THE migration SHALL include migration guide document với step-by-step instructions
9. THE migration SHALL include rollback procedure trong case of critical issues

### Requirement 13: Observability và Debugging

**User Story:** Là một developer, tôi muốn visibility vào graph execution, để dễ dàng debug issues.

#### Acceptance Criteria

1. THE graph SHALL generate mermaid diagram visualization của graph structure
2. THE graph SHALL expose /api/graph/visualize endpoint returning mermaid diagram
3. THE graph SHALL log state snapshot sau mỗi node execution
4. THE graph SHALL log conditional edge decisions với reasoning
5. THE graph SHALL expose /api/graph/history/{conversation_id} endpoint returning execution history
6. THE graph SHALL include execution trace trong ChatResponse metadata
7. THE graph SHALL support debug mode với verbose logging khi DEBUG_LANGGRAPH=true
8. THE graph SHALL expose metrics: total_executions, avg_execution_time, node_execution_counts, error_rates

### Requirement 14: Modular Code Organization

**User Story:** Là một developer, tôi muốn code được tổ chức theo modules rõ ràng, để dễ dàng navigate, test, và maintain.

#### Acceptance Criteria

1. THE migration SHALL implement LangGraph system trong separate module để không ảnh hưởng existing code
2. THE migration SHALL organize code theo separation of concerns: graph construction, state management, node functions, checkpointing, utilities
3. THE migration SHALL preserve existing research_agent module unchanged cho backward compatibility
4. THE migration SHALL provide clear module boundaries với proper __init__.py exports
5. THE migration SHALL organize test structure matching source code structure
6. THE migration SHALL separate development và production configurations (SQLite vs Postgres checkpointer)
7. FOR ALL new modules, THE migration SHALL include comprehensive docstrings và type hints

## Constraints

### Technical Constraints

1. System MUST use LangGraph 1.0.10 framework (current version)
2. System MUST use langchain 1.2.10 cho BaseMessage types và core functionality
3. System MUST maintain compatibility với Python 3.10+
4. System MUST preserve existing Google Gemini API integration (langchain-google-genai 4.2.1)
5. System MUST preserve existing Groq API integration (groq 0.31.1)
6. System MUST use SqliteSaver cho checkpointer trong development, support Postgres trong production
7. Migration MUST NOT require database schema changes
8. System MUST be compatible với FastAPI 0.135.1 và uvicorn 0.41.0

### Performance Constraints

1. Parallel research execution MUST achieve ≥ 2.5x speedup vs sequential
2. Simple queries MUST complete trong ≤ 3 seconds
3. Complex queries với 3 tasks MUST complete trong ≤ 12 seconds
4. Complexity analysis MUST complete trong ≤ 2 seconds
5. Planning MUST complete trong ≤ 5 seconds
6. Individual research task MUST complete trong ≤ 10 seconds
7. Graph overhead MUST be ≤ 500ms per execution

### Compatibility Constraints

1. API request/response schemas MUST remain unchanged
2. Frontend SSE consumer MUST work without modifications
3. Existing test cases MUST pass without changes
4. Environment variables MUST remain backward compatible
5. Deployment process MUST remain unchanged

### Scope Constraints

1. Migration DOES NOT include RAG system implementation
2. Migration DOES NOT include calculator tool implementation
3. Migration DOES NOT include document upload functionality
4. Migration DOES NOT include multi-agent collaboration
5. Migration DOES NOT include self-reflection capabilities
6. Migration FOCUSES ON orchestration layer only, preserving existing tool implementations

## Dependencies

### External Dependencies

1. langgraph==1.0.10 - Core LangGraph framework (current version)
2. langchain==1.2.10 - LangChain core functionality và BaseMessage types
3. langchain-google-genai==4.2.1 - Google Gemini API integration
4. groq==0.31.1 - Groq API integration
5. fastapi==0.135.1 - FastAPI web framework
6. uvicorn[standard]==0.41.0 - ASGI server
7. pydantic==2.12.5 - Data validation
8. sse-starlette==3.3.2 - SSE support (already available)
9. prometheus-client==0.24.1 - Metrics collection (already available)
10. hypothesis==6.151.9 - Property-based testing (already available)
11. pytest==9.0.2 - Testing framework (already available)

### Internal Dependencies

1. Existing Complexity_Analyzer implementation
2. Existing Planning_Agent implementation
3. Existing Research_Tool implementation
4. Existing adapter system (Google Gemini integration)
5. Existing FastAPI application structure
6. Existing SSE infrastructure

## Success Metrics

1. Parallel research execution achieves ≥ 2.5x speedup trong 95% cases
2. Graph execution completes simple queries trong ≤ 3 seconds cho 99% requests
3. Graph execution completes complex queries trong ≤ 12 seconds cho 95% requests
4. Test coverage ≥ 90% cho LangGraph components
5. Zero breaking changes đến existing API contracts
6. Zero regressions trong existing functionality
7. Checkpointer successfully persists và retrieves conversation state trong 100% cases
8. Streaming emits progress updates với latency ≤ 100ms
9. Migration completes trong ≤ 2 weeks development time
10. Production deployment succeeds với zero downtime using feature flag

