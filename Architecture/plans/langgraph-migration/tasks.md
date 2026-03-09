# Kế hoạch Triển khai - Migration sang LangGraph Framework

## Tổng quan

Migration hệ thống Research Agent từ kiến trúc pipeline (thực thi tuần tự) sang LangGraph framework để cải thiện hiệu suất thông qua parallel execution, centralized state management, và native streaming capabilities. Dự án được tổ chức thành 5 phases chính với timeline 2-4 tuần.

**Mục tiêu chính**:
- Giảm thời gian response từ 30+ giây xuống ~12 giây cho complex queries
- Parallel execution cho research tasks (2.5-3x speedup)
- Maintain 100% backward compatibility với existing functionality
- Zero breaking changes đến API contracts

**Ngôn ngữ triển khai**: Python 3.10+

## Tasks

### Phase 1: Project Setup và Core Infrastructure (Tuần 1, Ngày 1-2)

- [ ] 1. Thiết lập cấu trúc dự án và dependencies
  - Tạo module `research_agent_v2/` với subdirectories: `graph/`, `nodes/`, `edges/`, `checkpointer/`, `streaming/`, `utils/`
  - Tạo các file `__init__.py` cho tất cả modules
  - Cập nhật `pyproject.toml` với NEW dependencies (existing dependencies đã có):
    - `langgraph-checkpoint-sqlite>=1.0.0` (compatible với langgraph 1.0.10)
    - `aiosqlite>=0.20.0` (async SQLite support)
    - Optional: `langgraph-checkpoint-postgres>=1.0.0`, `asyncpg>=0.29.0` (production)
  - Verify existing dependencies compatible:
    - ✅ `langgraph==1.0.10` (already installed)
    - ✅ `langchain==1.2.10` (already installed)
    - ✅ `fastapi==0.135.1` (already installed)
    - ✅ `hypothesis==6.151.9` (already installed)
    - ✅ `pytest==9.0.2` (already installed)
  - Tạo file `research_agent_v2/config.py` cho LangGraph configuration
  - _Requirements: 14.1, 14.2, 14.3, 14.4_

- [ ] 2. Implement AgentState schema
  - [ ] 2.1 Tạo file `research_agent_v2/state.py` với AgentState TypedDict
    - Define fields: messages (với add_messages reducer), query_type, complexity_result, research_plan, research_results, final_answer, citations, execution_metadata, error, fallback_used
    - Import types từ langchain_core.messages và research_agent.models
    - Add comprehensive docstrings cho mỗi field
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

  - [ ]* 2.2 Write property test cho AgentState schema
    - **Property 1: State Immutability**
    - **Validates: Requirements 1.8**


- [ ] 3. Setup checkpointer configuration
  - [ ] 3.1 Implement SQLite checkpointer cho development
    - Tạo file `research_agent_v2/checkpointer/sqlite_checkpointer.py`
    - Implement `get_sqlite_checkpointer()` function với aiosqlite connection
    - Default database path: `./checkpoints.db`
    - _Requirements: 7.1, 7.2_

  - [ ] 3.2 Implement Postgres checkpointer cho production
    - Tạo file `research_agent_v2/checkpointer/postgres_checkpointer.py`
    - Implement `get_postgres_checkpointer()` function với asyncpg connection pool
    - Support connection string từ environment variable
    - _Requirements: 7.1, 7.2_

  - [ ] 3.3 Implement checkpointer factory trong config.py
    - Implement `get_checkpointer()` function routing giữa SQLite và Postgres
    - Support environment variables: LANGGRAPH_CHECKPOINTER, LANGGRAPH_DB_PATH, POSTGRES_CONNECTION_STRING
    - _Requirements: 7.1, 7.3, 14.6_

  - [ ]* 3.4 Write unit tests cho checkpointer configuration
    - Test SQLite checkpointer initialization
    - Test Postgres checkpointer initialization
    - Test environment variable routing
    - _Requirements: 7.1, 7.2, 7.3_

### Phase 2: Graph Nodes Implementation (Tuần 1, Ngày 3-5)

- [ ] 4. Implement entry và complexity nodes
  - [ ] 4.1 Implement entry_node
    - Tạo file `research_agent_v2/nodes/entry_node.py`
    - Initialize execution metadata với conversation_id, request_id, timestamps
    - Validate message không empty
    - Log execution time vào state.execution_metadata.node_timings
    - _Requirements: 3.1, 3.9_

  - [ ] 4.2 Implement complexity_node
    - Tạo file `research_agent_v2/nodes/complexity_node.py`
    - Invoke ComplexityAnalyzer từ dependencies
    - Update state.complexity_result và state.query_type ("simple" hoặc "complex")
    - Handle errors với fallback to heuristic classification
    - Log execution time và complexity analysis results
    - _Requirements: 3.2, 8.1, 9.1_

  - [ ]* 4.3 Write unit tests cho entry và complexity nodes
    - Test entry_node initializes metadata correctly
    - Test complexity_node updates state correctly
    - Test complexity_node error handling và fallback
    - _Requirements: 3.1, 3.2, 9.1_

  - [ ]* 4.4 Write property test cho node state updates
    - **Property 3: Node State Updates**
    - **Validates: Requirements 3.1, 3.2**

- [ ] 5. Implement router node
  - [ ] 5.1 Implement router_node
    - Tạo file `research_agent_v2/nodes/router_node.py`
    - Implement intent detection functions: `_is_current_date_request()`, `_is_time_sensitive_request()`, `_is_research_intent_request()`
    - Update state.query_type thành "research_intent", "current_date", hoặc "direct_llm"
    - Log routing decision với reasoning
    - _Requirements: 3.3, 8.4, 8.5_

  - [ ]* 5.2 Write unit tests cho router_node
    - Test current date detection
    - Test time-sensitive detection
    - Test research intent detection
    - Test default routing to direct_llm
    - _Requirements: 3.3, 8.4, 8.5_

  - [ ]* 5.3 Write property test cho routing correctness
    - **Property 9: Routing Correctness**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**


- [ ] 6. Implement planning node
  - [ ] 6.1 Implement planning_node
    - Tạo file `research_agent_v2/nodes/planning_node.py`
    - Invoke PlanningAgent từ dependencies
    - Update state.research_plan với list of ResearchTask objects
    - Handle errors với fallback to single-step plan
    - Log execution time và plan details (num_tasks, task queries)
    - _Requirements: 3.4, 8.2, 9.2_

  - [ ]* 6.2 Write unit tests cho planning_node
    - Test planning_node creates valid plan
    - Test planning_node error handling và fallback
    - Test planning_node logs execution metrics
    - _Requirements: 3.4, 9.2_

- [ ] 7. Implement research node với parallel execution
  - [ ] 7.1 Implement research_node với asyncio.gather
    - Tạo file `research_agent_v2/nodes/research_node.py`
    - Implement `_execute_tasks_parallel()` async function sử dụng asyncio.gather
    - Implement `execute_single_task()` với timeout protection (10s per task)
    - Execute tasks concurrently và collect results
    - Sort results theo ResearchTask.order
    - Handle individual task failures without affecting other tasks
    - Log execution time, num_tasks, successful_tasks, parallel execution metrics
    - _Requirements: 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 8.3, 9.3_

  - [ ]* 7.2 Write unit tests cho research_node
    - Test research_node handles empty plan
    - Test research_node executes tasks và collects results
    - Test research_node handles individual task failures
    - Test research_node sorts results by order
    - Test research_node timeout handling
    - _Requirements: 4.4, 4.5, 9.3_

  - [ ]* 7.3 Write property test cho parallel execution
    - **Property 5: Parallel Research Execution**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.6**

  - [ ]* 7.4 Write property test cho task isolation
    - **Property 6: Parallel Task Isolation**
    - **Validates: Requirements 4.4**

  - [ ]* 7.5 Write property test cho parallel speedup
    - **Property 8: Parallel Speedup**
    - **Validates: Requirements 4.8, 10.1**

- [ ] 8. Implement synthesis và citation nodes
  - [ ] 8.1 Implement synthesis_node
    - Tạo file `research_agent_v2/nodes/synthesis_node.py`
    - Invoke Aggregator để aggregate knowledge base từ research_results
    - Invoke ResponseComposer để compose final answer
    - Handle case khi no successful results (fallback to direct LLM)
    - Update state.final_answer và state.citations
    - Log execution time và synthesis metrics
    - _Requirements: 3.6, 8.8, 9.4, 9.5_

  - [ ] 8.2 Implement citation_node
    - Tạo file `research_agent_v2/nodes/citation_node.py`
    - Implement `_deduplicate_sources()` function
    - Format citations và append vào final_answer
    - Handle case khi no citations
    - Log execution time
    - _Requirements: 3.7, 8.7, 8.8_

  - [ ]* 8.3 Write unit tests cho synthesis và citation nodes
    - Test synthesis_node aggregates results correctly
    - Test synthesis_node handles no successful results
    - Test citation_node formats citations correctly
    - Test citation_node deduplicates sources
    - _Requirements: 3.6, 3.7, 8.7, 8.8, 9.4, 9.5_


- [ ] 9. Implement simple LLM, direct LLM, và current date nodes
  - [ ] 9.1 Implement simple_llm_node
    - Tạo file `research_agent_v2/nodes/simple_llm_node.py`
    - Invoke DirectLLM từ dependencies
    - Get conversation history từ database
    - Generate response và save to database
    - Update state.final_answer và execution metadata
    - Handle errors với fallback message
    - _Requirements: 8.9, 9.6_

  - [ ] 9.2 Implement direct_llm_node
    - Tạo file `research_agent_v2/nodes/direct_llm_node.py`
    - Similar logic to simple_llm_node nhưng cho complex queries
    - Support fallback mode khi research fails
    - _Requirements: 8.9, 9.4, 9.6_

  - [ ] 9.3 Implement current_date_node
    - Tạo file `research_agent_v2/nodes/current_date_node.py`
    - Get current date trong Vietnam timezone (Asia/Ho_Chi_Minh)
    - Format answer: "Hôm nay là ngày DD/MM/YYYY (theo giờ Việt Nam)."
    - Save to database
    - Update state.final_answer
    - _Requirements: 8.6_

  - [ ]* 9.4 Write unit tests cho LLM và date nodes
    - Test simple_llm_node generates response
    - Test direct_llm_node generates response
    - Test current_date_node returns correct format
    - Test error handling cho LLM nodes
    - _Requirements: 8.6, 8.9, 9.6_

- [ ] 10. Implement conditional edges
  - [ ] 10.1 Implement complexity_edge
    - Tạo file `research_agent_v2/edges/complexity_edge.py`
    - Read state.query_type và return "simple" hoặc "complex"
    - _Requirements: 5.1, 5.2_

  - [ ] 10.2 Implement router_edge
    - Tạo file `research_agent_v2/edges/router_edge.py`
    - Read state.query_type và return "research_intent", "current_date", hoặc "direct_llm"
    - Handle invalid query_type với default to "direct_llm"
    - _Requirements: 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 10.3 Write unit tests cho conditional edges
    - Test complexity_edge routing logic
    - Test router_edge routing logic
    - Test router_edge handles invalid query_type
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [ ] 11. Checkpoint - Ensure all nodes và edges implemented
  - Verify tất cả 10 nodes đã được implement
  - Verify 2 conditional edges đã được implement
  - Run unit tests cho tất cả nodes và edges
  - Ensure all tests pass, ask the user if questions arise.

### Phase 3: StateGraph Construction và Integration (Tuần 1, Ngày 6-7)

- [ ] 12. Implement StateGraph construction
  - [ ] 12.1 Implement ResearchAgentGraph class
    - Tạo file `research_agent_v2/graph.py`
    - Implement `__init__()` nhận dependencies dict
    - Implement `_build_graph()` để construct StateGraph với tất cả nodes và edges
    - Add nodes: entry, complexity, router, planning, research, synthesis, citation, simple_llm, direct_llm, current_date
    - Set entry_point to "entry"
    - Add edges: entry → complexity, planning → research → synthesis → citation → END
    - Add conditional edges: complexity (simple/complex), router (research_intent/current_date/direct_llm)
    - Add terminal edges: simple_llm → END, current_date → END, citation → END
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [ ] 12.2 Implement graph compilation với checkpointer
    - Implement `_compile_graph()` method
    - Compile StateGraph với checkpointer từ config
    - _Requirements: 1.7, 7.1_

  - [ ]* 12.3 Write unit tests cho StateGraph construction
    - Test graph has all required nodes
    - Test graph has correct edges
    - Test graph compiles successfully
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_


- [ ] 13. Implement graph execution methods
  - [ ] 13.1 Implement ainvoke() method
    - Create initial AgentState từ ChatRequest
    - Set execution metadata (conversation_id, request_id, timestamps, model)
    - Invoke graph với checkpointer config (thread_id = conversation_id)
    - Return final AgentState
    - _Requirements: 7.4, 7.6_

  - [ ] 13.2 Implement astream() method
    - Create initial AgentState từ ChatRequest
    - Stream graph execution với checkpointer config
    - Yield state updates sau mỗi node execution
    - _Requirements: 6.1, 6.2, 7.4, 7.6_

  - [ ]* 13.3 Write unit tests cho graph execution
    - Test ainvoke() returns final state
    - Test astream() yields state updates
    - Test checkpointer config passed correctly
    - _Requirements: 6.1, 6.2, 7.4, 7.6_

  - [ ]* 13.4 Write property test cho streaming state updates
    - **Property 11: Streaming State Updates**
    - **Validates: Requirements 6.2**

- [ ] 14. Implement dependency injection
  - [ ] 14.1 Create dependency factory trong api/deps.py
    - Implement `get_research_agent_graph()` function với @lru_cache
    - Initialize tất cả existing components: Parser, ComplexityAnalyzer, DirectLLM, Database, ResearchTool, PlanningAgent, Aggregator, ResponseComposer
    - Create dependencies dict và pass vào ResearchAgentGraph
    - _Requirements: 14.2, 14.3_

  - [ ]* 14.2 Write unit tests cho dependency injection
    - Test get_research_agent_graph() returns valid graph
    - Test dependencies are initialized correctly
    - Test caching works correctly
    - _Requirements: 14.2, 14.3_

### Phase 4: Streaming và API Integration (Tuần 1, Ngày 6-7)

- [ ] 15. Implement SSE adapter
  - [ ] 15.1 Implement SSEAdapter class
    - Tạo file `research_agent_v2/streaming/sse_adapter.py`
    - Define NODE_EVENT_MAP mapping node names to SSE event types và messages
    - Implement `stream_to_sse()` static method
    - Convert graph state updates to SSE events với fields: type, node, message, progress, timestamp, data
    - Calculate progress percentage based on query_type và completed nodes
    - Add node-specific data (complexity results, planning tasks, research results)
    - Emit final "done" event với answer, citations, metadata
    - _Requirements: 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 15.2 Write unit tests cho SSE adapter
    - Test NODE_EVENT_MAP coverage
    - Test stream_to_sse() generates correct SSE format
    - Test progress calculation
    - Test node-specific data inclusion
    - Test final "done" event
    - _Requirements: 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 15.3 Write property test cho SSE event structure
    - **Property 12: SSE Event Structure**
    - **Validates: Requirements 6.4**

- [ ] 16. Implement /api/v2/chat endpoint
  - [ ] 16.1 Create chat_v2 router
    - Tạo file `api/routers/chat_v2.py`
    - Implement POST /api/v2/chat endpoint
    - Generate request_id và conversation_id
    - Support streaming mode (return StreamingResponse với SSE)
    - Support non-streaming mode (return ChatResponse)
    - Handle errors và return appropriate HTTP status codes
    - Log request và response metrics
    - _Requirements: 12.3, 12.4_

  - [ ] 16.2 Implement streaming response helper
    - Implement `_stream_response()` async generator
    - Get graph stream từ graph.astream()
    - Convert to SSE using SSEAdapter
    - Yield SSE events
    - Handle streaming errors
    - _Requirements: 6.3, 6.8_

  - [ ]* 16.3 Write integration tests cho /api/v2/chat endpoint
    - Test non-streaming mode returns ChatResponse
    - Test streaming mode returns SSE events
    - Test error handling
    - Test conversation_id persistence
    - _Requirements: 12.3, 12.4, 6.8_


- [ ] 17. Implement feature flag routing
  - [ ] 17.1 Add feature flag configuration
    - Update `config.py` với Settings field: `enable_langgraph_agent: bool`
    - Read từ environment variable: ENABLE_LANGGRAPH_AGENT (default: false)
    - Add LangGraph configuration fields: langgraph_checkpointer, langgraph_db_path, postgres_connection_string
    - _Requirements: 12.5, 12.6, 12.7_

  - [ ] 17.2 Update existing /api/chat endpoint với feature flag routing
    - Update `api/routers/chat.py`
    - Check settings.enable_langgraph_agent
    - If true: route to chat_v2()
    - If false: route to existing Pipeline Orchestrator
    - _Requirements: 12.5, 12.6, 12.7_

  - [ ]* 17.3 Write integration tests cho feature flag routing
    - Test routing to LangGraph khi flag=true
    - Test routing to Pipeline khi flag=false
    - Test environment variable configuration
    - _Requirements: 12.5, 12.6, 12.7_

- [ ] 18. Checkpoint - Ensure API integration complete
  - Verify /api/v2/chat endpoint works
  - Verify streaming và non-streaming modes work
  - Verify feature flag routing works
  - Test với real requests
  - Ensure all tests pass, ask the user if questions arise.

### Phase 5: Testing và Validation (Tuần 2, Ngày 1-3)

- [ ] 19. Write comprehensive property-based tests
  - [ ]* 19.1 Write property test cho message accumulation
    - **Property 2: Message Accumulation**
    - **Validates: Requirements 2.10, 7.5**

  - [ ]* 19.2 Write property test cho execution metadata tracking
    - **Property 4: Execution Metadata Tracking**
    - **Validates: Requirements 3.9, 10.8**

  - [ ]* 19.3 Write property test cho result ordering
    - **Property 7: Result Ordering**
    - **Validates: Requirements 4.5**

  - [ ]* 19.4 Write property test cho routing logging
    - **Property 10: Routing Logging**
    - **Validates: Requirements 5.8**

  - [ ]* 19.5 Write property test cho streaming progress updates
    - **Property 13: Streaming Progress Updates**
    - **Validates: Requirements 6.6**

  - [ ]* 19.6 Write property test cho conversation memory persistence
    - **Property 14: Conversation Memory Persistence**
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.5**

  - [ ]* 19.7 Write property test cho backward compatibility
    - **Property 15: Backward Compatibility**
    - **Validates: Requirements 8.10, 8.11**

  - [ ]* 19.8 Write property test cho error state tracking
    - **Property 16: Error State Tracking**
    - **Validates: Requirements 9.6, 9.7, 9.8**

  - [ ]* 19.9 Write property test cho graceful degradation
    - **Property 17: Graceful Degradation**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.9**

  - [ ]* 19.10 Write property test cho node performance
    - **Property 18: Node Performance**
    - **Validates: Requirements 10.4, 10.5, 10.6, 10.7**


- [ ] 20. Write integration tests cho complete graph execution
  - [ ]* 20.1 Write integration test cho simple query flow
    - Test flow: Entry → Complexity → Simple LLM → END
    - Verify final_answer generated
    - Verify execution metadata tracked
    - _Requirements: 8.1, 8.9, 11.1_

  - [ ]* 20.2 Write integration test cho complex research query flow
    - Test flow: Entry → Complexity → Router → Planning → Research → Synthesis → Citation → END
    - Verify research plan created
    - Verify parallel research execution
    - Verify final answer với citations
    - _Requirements: 8.2, 8.3, 8.7, 8.8, 11.2_

  - [ ]* 20.3 Write integration test cho current date query flow
    - Test flow: Entry → Complexity → Router → Current Date → END
    - Verify correct date format
    - _Requirements: 8.6, 11.3_

  - [ ]* 20.4 Write integration test cho direct LLM query flow
    - Test flow: Entry → Complexity → Router → Direct LLM → Citation → END
    - Verify LLM response generated
    - _Requirements: 8.9, 11.4_

  - [ ]* 20.5 Write integration test cho streaming execution
    - Test graph.astream() yields state updates
    - Verify SSE events emitted cho mỗi node
    - Verify final "done" event
    - _Requirements: 6.1, 6.2, 6.3, 6.7, 11.5_

  - [ ]* 20.6 Write integration test cho conversation memory
    - Test multiple turns với same conversation_id
    - Verify state persisted và loaded từ checkpointer
    - Verify message history accumulated
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 11.6_

  - [ ]* 20.7 Write integration test cho error handling scenarios
    - Test complexity analysis failure → fallback
    - Test planning failure → fallback plan
    - Test research partial failure → synthesize từ successful tasks
    - Test research complete failure → direct LLM fallback
    - Test synthesis failure → concatenated results
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 11.7_

- [ ] 21. Performance testing và benchmarking
  - [ ]* 21.1 Write performance test cho parallel speedup
    - Measure sequential execution time (mock)
    - Measure parallel execution time (actual)
    - Verify speedup ≥ 2.5x cho 3 tasks
    - _Requirements: 4.8, 10.1_

  - [ ]* 21.2 Write performance test cho simple query latency
    - Measure end-to-end latency cho simple queries
    - Verify P99 ≤ 3 seconds
    - _Requirements: 10.2_

  - [ ]* 21.3 Write performance test cho complex query latency
    - Measure end-to-end latency cho complex queries với 3 tasks
    - Verify P99 ≤ 12 seconds
    - _Requirements: 10.3_

  - [ ]* 21.4 Write performance test cho individual node latency
    - Measure complexity_node latency (target ≤ 2s)
    - Measure planning_node latency (target ≤ 5s)
    - Measure research_node per-task latency (target ≤ 10s)
    - Measure synthesis_node latency (target ≤ 5s)
    - _Requirements: 10.4, 10.5, 10.6, 10.7_

- [ ] 22. Verify test coverage và quality
  - Run pytest với coverage report
  - Verify line coverage ≥ 90% cho research_agent_v2/ module
  - Verify branch coverage ≥ 85%
  - Verify all 23 correctness properties tested
  - Fix any coverage gaps
  - _Requirements: 11.9, 11.10_

- [ ] 23. Checkpoint - Ensure all tests pass
  - Run full test suite (unit + property + integration + performance)
  - Verify all tests pass
  - Review test coverage report
  - Ensure all tests pass, ask the user if questions arise.


### Phase 6: Observability và Debugging (Tuần 2, Ngày 4-5)

- [ ] 24. Implement logging và metrics
  - [ ] 24.1 Implement structured logging cho graph execution
    - Add structlog configuration
    - Log node execution với fields: node, conversation_id, execution_time_ms, status
    - Log routing decisions với fields: from_node, to_node, query_type, reasoning
    - Log errors với fields: node, error_type, error_message, stack_trace
    - _Requirements: 13.4, 13.5_

  - [ ] 24.2 Implement Prometheus metrics
    - Tạo file `research_agent_v2/utils/metrics.py`
    - Define metrics: graph_requests_total, graph_execution_duration, node_execution_duration, node_errors_total, research_tasks_total, parallel_speedup
    - Instrument graph execution với metrics collection
    - _Requirements: 10.8, 13.8_

  - [ ] 24.3 Create /metrics endpoint
    - Add metrics endpoint trong api/routers/
    - Expose Prometheus metrics
    - _Requirements: 10.9, 13.8_

  - [ ]* 24.4 Write unit tests cho logging và metrics
    - Test structured logging format
    - Test metrics collection
    - Test /metrics endpoint
    - _Requirements: 13.4, 13.8_

- [ ] 25. Implement graph visualization
  - [ ] 25.1 Implement graph diagram generation
    - Implement `generate_graph_diagram()` function sử dụng graph.get_graph().draw_mermaid()
    - _Requirements: 13.1_

  - [ ] 25.2 Create /api/graph/visualize endpoint
    - Return mermaid diagram của graph structure
    - _Requirements: 13.1, 13.2_

  - [ ]* 25.3 Write unit tests cho graph visualization
    - Test diagram generation
    - Test /api/graph/visualize endpoint
    - _Requirements: 13.1, 13.2_

- [ ] 26. Implement execution history tracking
  - [ ] 26.1 Implement state snapshot logging
    - Implement `log_state_snapshot()` function
    - Log state sau mỗi node execution với key fields
    - _Requirements: 13.3_

  - [ ] 26.2 Create /api/graph/history/{conversation_id} endpoint
    - Retrieve execution history từ checkpointer
    - Return list of state snapshots với timestamps
    - _Requirements: 13.5_

  - [ ]* 26.3 Write integration tests cho execution history
    - Test state snapshot logging
    - Test history retrieval endpoint
    - _Requirements: 13.3, 13.5_

- [ ] 27. Implement debug mode
  - [ ] 27.1 Add debug configuration
    - Add DEBUG_LANGGRAPH environment variable
    - Implement `debug_log()` function
    - Add verbose logging trong debug mode
    - _Requirements: 13.7_

  - [ ]* 27.2 Write unit tests cho debug mode
    - Test debug logging enabled/disabled
    - Test verbose output trong debug mode
    - _Requirements: 13.7_

### Phase 7: Documentation và Migration Guide (Tuần 2, Ngày 6-7)

- [ ] 28. Create migration documentation
  - [ ] 28.1 Write migration guide
    - Document migration phases (Development, Canary, Rollout, Cleanup)
    - Document feature flag usage
    - Document rollback procedure
    - Document environment variables
    - _Requirements: 12.8, 12.9_

  - [ ] 28.2 Write deployment guide
    - Document Docker configuration
    - Document Docker Compose setup
    - Document Kubernetes deployment
    - Document checkpointer configuration (SQLite vs Postgres)
    - _Requirements: 12.8_

  - [ ] 28.3 Write API documentation
    - Document /api/v2/chat endpoint
    - Document /api/graph/visualize endpoint
    - Document /api/graph/history endpoint
    - Document /metrics endpoint
    - Document request/response schemas
    - _Requirements: 12.8_

  - [ ] 28.4 Update README với LangGraph information
    - Add LangGraph architecture overview
    - Add setup instructions
    - Add usage examples
    - Add troubleshooting guide
    - _Requirements: 12.8_


- [ ] 29. Create code documentation
  - [ ] 29.1 Add comprehensive docstrings
    - Add docstrings cho tất cả modules, classes, functions
    - Follow Google docstring format
    - Include type hints
    - Include examples where appropriate
    - _Requirements: 14.7_

  - [ ] 29.2 Generate API reference documentation
    - Use Sphinx hoặc MkDocs để generate API docs
    - Include module structure
    - Include class và function references
    - _Requirements: 14.7_

- [ ] 30. Checkpoint - Ensure documentation complete
  - Review migration guide
  - Review deployment guide
  - Review API documentation
  - Review code documentation
  - Ensure all tests pass, ask the user if questions arise.

### Phase 8: Deployment Preparation (Tuần 3, Ngày 1-2)

- [ ] 31. Setup development environment
  - [ ] 31.1 Configure SQLite checkpointer cho development
    - Set LANGGRAPH_CHECKPOINTER=sqlite
    - Set LANGGRAPH_DB_PATH=./checkpoints.db
    - Test checkpointer initialization
    - _Requirements: 14.6_

  - [ ] 31.2 Configure environment variables
    - Create .env.example với all required variables
    - Document each variable
    - _Requirements: 12.5, 14.6_

  - [ ]* 31.3 Write integration tests cho development environment
    - Test SQLite checkpointer works
    - Test environment variable loading
    - _Requirements: 14.6_

- [ ] 32. Setup production environment configuration
  - [ ] 32.1 Configure Postgres checkpointer cho production
    - Set LANGGRAPH_CHECKPOINTER=postgres
    - Set POSTGRES_CONNECTION_STRING
    - Create database migration scripts if needed
    - _Requirements: 14.6_

  - [ ] 32.2 Create Docker configuration
    - Create Dockerfile cho backend
    - Create docker-compose.yml với backend và postgres services
    - Configure volumes cho checkpointer data
    - _Requirements: 12.8_

  - [ ] 32.3 Create Kubernetes configuration
    - Create Deployment YAML
    - Create Service YAML
    - Create ConfigMap và Secret YAMLs
    - Configure resource limits
    - _Requirements: 12.8_

  - [ ]* 32.4 Test production configuration locally
    - Test Docker build và run
    - Test docker-compose setup
    - Test Postgres checkpointer connection
    - _Requirements: 14.6_

- [ ] 33. Setup monitoring và alerting
  - [ ] 33.1 Configure Prometheus scraping
    - Add Prometheus configuration
    - Configure scrape interval
    - Test metrics collection
    - _Requirements: 13.8_

  - [ ] 33.2 Create Grafana dashboard
    - Create dashboard với key metrics: request latency, parallel speedup, error rate, throughput
    - Add panels cho node execution times
    - Add panels cho resource usage
    - _Requirements: 13.8_

  - [ ] 33.3 Configure alerting rules
    - Alert on high error rate (> 5%)
    - Alert on high latency (P99 > 15s)
    - Alert on low parallel speedup (< 2x)
    - _Requirements: 13.8_

- [ ] 34. Checkpoint - Ensure deployment ready
  - Verify development environment works
  - Verify production configuration complete
  - Verify monitoring setup complete
  - Test deployment locally
  - Ensure all tests pass, ask the user if questions arise.


### Phase 9: Canary Deployment (Tuần 3, Ngày 3-4)

- [ ] 35. Deploy với feature flag disabled
  - [ ] 35.1 Deploy to production với ENABLE_LANGGRAPH_AGENT=false
    - Deploy code với LangGraph implementation
    - Keep feature flag disabled
    - Verify existing Pipeline Orchestrator still works
    - Monitor metrics
    - _Requirements: 12.5, 12.6_

  - [ ] 35.2 Verify backward compatibility
    - Run existing test suite
    - Verify all tests pass
    - Verify API responses unchanged
    - Verify no performance regression
    - _Requirements: 8.10, 8.11_

- [ ] 36. Enable canary deployment (10% traffic)
  - [ ] 36.1 Enable feature flag cho 10% traffic
    - Configure load balancer hoặc feature flag service
    - Route 10% requests to LangGraph system
    - Monitor metrics closely
    - _Requirements: 12.6_

  - [ ] 36.2 Monitor canary metrics
    - Compare LangGraph vs Pipeline metrics
    - Monitor response time (P50, P95, P99)
    - Monitor error rate
    - Monitor success rate
    - Monitor parallel speedup
    - Track any anomalies
    - _Requirements: 10.9, 13.8_

  - [ ] 36.3 Validate canary performance
    - Verify parallel speedup ≥ 2.5x
    - Verify simple queries P99 ≤ 3s
    - Verify complex queries P99 ≤ 12s
    - Verify error rate ≤ existing system
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ] 36.4 Collect user feedback và logs
    - Review error logs
    - Check for any unexpected behavior
    - Validate conversation memory works
    - Validate streaming works
    - _Requirements: 6.7, 7.8_

- [ ] 37. Decision point - Continue or rollback
  - Review canary metrics
  - If error rate > 5% OR P99 latency > 15s OR critical bugs: Execute rollback
  - If metrics acceptable: Continue to gradual rollout
  - Document decision và reasoning
  - _Requirements: 12.9_

### Phase 10: Gradual Rollout (Tuần 3, Ngày 5-7)

- [ ] 38. Increase to 25% traffic
  - [ ] 38.1 Update feature flag to 25% traffic
    - Gradually increase traffic
    - Monitor metrics continuously
    - _Requirements: 12.6_

  - [ ] 38.2 Monitor và validate 25% rollout
    - Verify metrics stable
    - Check for any issues
    - _Requirements: 10.9, 13.8_

- [ ] 39. Increase to 50% traffic
  - [ ] 39.1 Update feature flag to 50% traffic
    - Continue gradual increase
    - Monitor metrics
    - _Requirements: 12.6_

  - [ ] 39.2 Monitor và validate 50% rollout
    - Verify metrics stable
    - Check for any issues
    - _Requirements: 10.9, 13.8_

- [ ] 40. Increase to 75% traffic
  - [ ] 40.1 Update feature flag to 75% traffic
    - Continue gradual increase
    - Monitor metrics
    - _Requirements: 12.6_

  - [ ] 40.2 Monitor và validate 75% rollout
    - Verify metrics stable
    - Check for any issues
    - _Requirements: 10.9, 13.8_

- [ ] 41. Increase to 100% traffic
  - [ ] 41.1 Update feature flag to 100% traffic
    - Complete rollout to all traffic
    - Monitor metrics closely
    - _Requirements: 12.6_

  - [ ] 41.2 Monitor và validate 100% rollout
    - Verify all metrics stable
    - Verify no regressions
    - Verify success rate ≥ 95%
    - _Requirements: 10.9, 13.8_

  - [ ] 41.3 Soak test for 48 hours
    - Monitor system stability
    - Check for memory leaks
    - Check for performance degradation
    - Verify checkpointer cleanup works
    - _Requirements: 7.8_

- [ ] 42. Checkpoint - Ensure rollout successful
  - Review all metrics
  - Verify success criteria met
  - Document any issues và resolutions
  - Ensure all tests pass, ask the user if questions arise.


### Phase 11: Cleanup và Finalization (Tuần 4)

- [ ] 43. Remove feature flag
  - [ ] 43.1 Remove ENABLE_LANGGRAPH_AGENT feature flag
    - Update config.py để remove feature flag
    - Update /api/chat endpoint để always use LangGraph
    - Remove conditional routing logic
    - _Requirements: 12.5_

  - [ ] 43.2 Deprecate /api/v2/chat endpoint
    - Merge /api/v2/chat functionality vào /api/chat
    - Add deprecation notice cho /api/v2/chat
    - Plan removal date
    - _Requirements: 12.3, 12.4_

  - [ ]* 43.3 Write tests cho updated routing
    - Test /api/chat uses LangGraph
    - Test backward compatibility maintained
    - _Requirements: 8.10, 8.11_

- [ ] 44. Archive old Pipeline Orchestrator code
  - [ ] 44.1 Move Pipeline Orchestrator to archive
    - Create archive/ directory
    - Move research_agent/ module to archive/research_agent_v1/
    - Update imports if needed
    - Keep code for reference và potential rollback
    - _Requirements: 12.1, 12.2_

  - [ ] 44.2 Update documentation to reflect changes
    - Update README to remove Pipeline references
    - Update API documentation
    - Update architecture diagrams
    - _Requirements: 12.8_

- [ ] 45. Implement checkpointer cleanup job
  - [ ] 45.1 Create cleanup script
    - Implement script để delete checkpoints older than 7 days
    - Schedule as cron job hoặc Kubernetes CronJob
    - _Requirements: 7.8_

  - [ ] 45.2 Test cleanup job
    - Test cleanup removes old checkpoints
    - Test cleanup preserves recent checkpoints
    - _Requirements: 7.8_

- [ ] 46. Performance optimization
  - [ ] 46.1 Analyze performance metrics
    - Review P99 latency
    - Review parallel speedup
    - Identify bottlenecks
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ] 46.2 Optimize identified bottlenecks
    - Optimize slow nodes
    - Optimize checkpointer queries
    - Optimize state serialization
    - _Requirements: 10.7_

  - [ ]* 46.3 Validate optimizations
    - Re-run performance tests
    - Verify improvements
    - _Requirements: 10.1, 10.2, 10.3_

- [ ] 47. Final validation
  - [ ] 47.1 Run complete test suite
    - Run all unit tests
    - Run all property tests
    - Run all integration tests
    - Run all performance tests
    - Verify 100% pass rate
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

  - [ ] 47.2 Verify success metrics
    - ✅ Parallel speedup ≥ 2.5x
    - ✅ Simple queries P99 ≤ 3s
    - ✅ Complex queries P99 ≤ 12s
    - ✅ Error rate ≤ existing system
    - ✅ Success rate ≥ 95%
    - ✅ Test coverage ≥ 90%
    - ✅ Zero breaking changes
    - _Requirements: 10.1, 10.2, 10.3, 11.9, 11.10_

  - [ ] 47.3 Update final documentation
    - Update README với final architecture
    - Update deployment guide
    - Update troubleshooting guide
    - Document lessons learned
    - _Requirements: 12.8_

- [ ] 48. Checkpoint - Migration complete
  - Review all success metrics
  - Verify all requirements met
  - Document final state
  - Celebrate successful migration! 🎉
  - Ensure all tests pass, ask the user if questions arise.


## Notes

### Task Organization

Tasks được tổ chức theo 11 phases:

1. **Phase 1-2**: Core implementation (Tuần 1) - Setup, nodes, edges, graph construction
2. **Phase 3-4**: Integration (Tuần 1) - Streaming, API endpoints, feature flag
3. **Phase 5**: Testing (Tuần 2, Ngày 1-3) - Property tests, integration tests, performance tests
4. **Phase 6-7**: Observability (Tuần 2, Ngày 4-7) - Logging, metrics, documentation
5. **Phase 8**: Deployment prep (Tuần 3, Ngày 1-2) - Environment setup, monitoring
6. **Phase 9-10**: Rollout (Tuần 3, Ngày 3-7) - Canary deployment, gradual rollout
7. **Phase 11**: Cleanup (Tuần 4) - Remove feature flag, archive old code, optimize

### Optional Tasks

Tasks marked với `*` là optional và có thể skip cho faster MVP:
- Tất cả property-based tests (có thể implement sau)
- Tất cả unit tests cho individual components (có thể implement incrementally)
- Performance optimization tasks (có thể optimize sau khi deploy)

Tuy nhiên, strongly recommended implement tất cả tests để ensure correctness và prevent regressions.

### Testing Strategy

- **Unit tests**: Test individual components (nodes, edges, adapters)
- **Property tests**: Test universal properties across all inputs (sử dụng hypothesis library)
- **Integration tests**: Test complete graph execution flows
- **Performance tests**: Validate latency và speedup requirements

### Checkpoints

Checkpoints được đặt sau mỗi major phase để:
- Verify implementation complete
- Run tests và ensure pass
- Ask user if questions arise
- Provide natural break points

### Requirements Traceability

Mỗi task references specific requirements để maintain traceability:
- Format: `_Requirements: X.Y, X.Z_`
- Giúp verify tất cả requirements được implement
- Giúp track coverage

### Parallel Execution

Một số tasks có thể thực hiện parallel:
- Node implementations (tasks 4-9) có thể implement parallel
- Test writing có thể parallel với implementation
- Documentation có thể parallel với testing

### Success Criteria

Migration được coi là successful khi:
- ✅ Tất cả 48 tasks complete
- ✅ Test coverage ≥ 90%
- ✅ Parallel speedup ≥ 2.5x
- ✅ Simple queries P99 ≤ 3s
- ✅ Complex queries P99 ≤ 12s
- ✅ Error rate ≤ existing system
- ✅ Success rate ≥ 95%
- ✅ Zero breaking changes
- ✅ Production deployment stable for 48 hours

### Rollback Plan

Nếu gặp critical issues trong bất kỳ phase nào:

1. **Immediate rollback** (< 5 minutes):
   ```bash
   export ENABLE_LANGGRAPH_AGENT=false
   systemctl restart research-agent
   ```

2. **Full rollback** (< 30 minutes):
   ```bash
   git revert <migration-commit>
   git push origin main
   ./deploy.sh
   ```

3. **Rollback triggers**:
   - Error rate > 5%
   - P99 latency > 15s
   - Critical bugs affecting users
   - Memory leaks
   - Data corruption

### Timeline Summary

- **Week 1**: Core implementation (Phases 1-4)
- **Week 2**: Testing và observability (Phases 5-7)
- **Week 3**: Deployment và rollout (Phases 8-10)
- **Week 4**: Cleanup và optimization (Phase 11)

Total: 2-4 tuần depending on team size và priorities.

