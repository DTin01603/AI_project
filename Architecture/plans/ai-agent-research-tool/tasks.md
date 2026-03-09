# Implementation Plan: AI Agent with Research Tool

## Overview

Hệ thống AI Agent with Research Tool sẽ được implement theo kiến trúc pipeline-based với FastAPI, sử dụng Python async/await cho concurrent operations. Implementation được chia thành 6 phases, từ foundation đến testing, với mỗi phase build trên các phases trước đó. Hệ thống sử dụng SQLite cho conversation storage, Google Gemini API (free tier) cho LLM, và Google Custom Search API (free tier - 100 queries/day) cho web search.

## Tasks

### Phase 1: Foundation & Core Infrastructure (Week 1-2)

- [x] 1. Set up project structure and dependencies
  - Create project directory structure (src/, tests/, config/)
  - Initialize Python virtual environment
  - Create requirements.txt with FastAPI, Pydantic, SQLite, google-generativeai, google-api-python-client, Hypothesis
  - Set up .env file template for configuration (GOOGLE_API_KEY, GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID)
  - Create main.py entry point
  - _Requirements: 12.1, 12.2, 12.3_

- [ ] 2. Implement configuration management
  - [x] 2.1 Create Config model with Pydantic
    - Define all configuration fields (API keys, timeouts, database path)
    - Implement from_env() class method to load from environment variables
    - Add validation for required fields
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [ ]* 2.2 Write unit tests for Config
    - Test loading from environment variables
    - Test validation of required fields
    - Test default values
    - _Requirements: 12.5_

- [ ] 3. Set up database schema and basic operations
  - [-] 3.1 Create Database class with SQLite connection
    - Implement schema creation (conversations and messages tables)
    - Add indexes for performance
    - Implement connection pooling
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [~] 3.2 Implement database CRUD operations
    - Implement create_conversation()
    - Implement save_message()
    - Implement get_conversation_history()
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [ ]* 3.3 Write property test for conversation persistence
    - **Property 19: Conversation Persistence Round-Trip**
    - **Validates: Requirements 10.1, 10.2**
  
  - [ ]* 3.4 Write property test for conversation ID uniqueness
    - **Property 20: Conversation ID Uniqueness**
    - **Validates: Requirements 10.3**
  
  - [ ]* 3.5 Write property test for message timestamps
    - **Property 21: Message Timestamp Presence**
    - **Validates: Requirements 10.4**

- [ ] 4. Implement logging infrastructure
  - [~] 4.1 Set up structured logging with Python logging module
    - Configure log format with timestamps and context
    - Implement log level configuration from environment
    - Create logger instances for each component
    - _Requirements: 14.6_
  
  - [~] 4.2 Add logging helpers for common patterns
    - Create log_request() helper
    - Create log_api_call() helper
    - Create log_error() helper with context sanitization
    - _Requirements: 14.1, 14.4, 14.5_

- [~] 5. Create data models with Pydantic
  - Define all request/response models (ChatRequest, ChatResponse, ErrorResponse)
  - Define all internal models (ParsedRequest, ComplexityResult, ResearchTask, etc.)
  - Add validation rules and field constraints
  - _Requirements: 11.2, 11.3_

- [~] 6. Checkpoint - Verify foundation
  - Ensure all tests pass, ask the user if questions arise.

### Phase 2: Simple Request Flow (Week 2-3)

- [ ] 7. Implement Parser component
  - [~] 7.1 Create Parser class with parse() method
    - Implement whitespace stripping
    - Implement Unicode NFC normalization
    - Implement empty input validation
    - Return ParsedRequest with cleaned_text and original_text
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ]* 7.2 Write property test for parser normalization
    - **Property 2: Parser Normalizes Input**
    - **Validates: Requirements 2.1, 2.2, 2.4**
  
  - [ ]* 7.3 Write property test for empty input rejection
    - **Property 3: Empty Input Rejection**
    - **Validates: Requirements 2.5**
  
  - [ ]* 7.4 Write unit tests for Parser edge cases
    - Test various Unicode characters
    - Test whitespace-only input
    - Test very long input
    - _Requirements: 2.1, 2.2, 2.5_

- [ ] 8. Implement Complexity Analyzer component
  - [~] 8.1 Create ComplexityAnalyzer class with analyze() method
    - Implement _build_analysis_prompt() helper
    - Call Google Gemini API with analysis prompt
    - Parse JSON response to ComplexityResult
    - Add timeout handling (2 seconds)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [ ]* 8.2 Write property test for complexity result structure
    - **Property 5: Complexity Result Structure**
    - **Validates: Requirements 3.4**
  
  - [ ]* 8.3 Write unit tests for Complexity Analyzer
    - Test simple request classification
    - Test complex request classification
    - Test timeout handling
    - _Requirements: 3.2, 3.3, 3.5_

- [ ] 9. Implement Direct LLM component
  - [~] 9.1 Create DirectLLM class with generate_response() method
    - Implement _build_messages() helper to format conversation history
    - Call Google Gemini API with messages array
    - Add timeout handling (10 seconds)
    - Add retry logic with exponential backoff
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [ ]* 9.2 Write property test for Direct LLM includes history
    - **Property 6: Direct LLM Includes History**
    - **Validates: Requirements 4.2**
  
  - [ ]* 9.3 Write unit tests for Direct LLM
    - Test response generation
    - Test retry logic
    - Test timeout handling
    - _Requirements: 4.3, 4.4, 4.5_

- [ ] 10. Implement simple request orchestration
  - [~] 10.1 Create Orchestrator class skeleton
    - Initialize all component dependencies
    - Implement handle_simple_request() method
    - Wire Parser -> ComplexityAnalyzer -> DirectLLM flow
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ]* 10.2 Write property test for orchestrator routing
    - **Property 1: Orchestrator Routes Based on Complexity**
    - **Validates: Requirements 1.3, 1.4**
  
  - [ ]* 10.3 Write integration test for simple request flow
    - Test end-to-end simple request processing
    - Verify response structure
    - _Requirements: 1.1, 1.2, 1.3_

- [~] 11. Checkpoint - Verify simple flow
  - Ensure all tests pass, ask the user if questions arise.

### Phase 3: Research Tool Implementation (Week 3-4)

- [ ] 12. Implement web search functionality
  - [~] 12.1 Create ResearchTool class with _search() method
    - Integrate Google Custom Search API client
    - Implement search query execution (note: 100 queries/day limit on free tier)
    - Parse and format top 3 results
    - Return list of SearchResult objects
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [ ]* 12.2 Write property test for search results limit
    - **Property 9: Search Results Limit**
    - **Validates: Requirements 6.2**
  
  - [ ]* 12.3 Write property test for search result structure
    - **Property 10: Search Result Structure**
    - **Validates: Requirements 6.3**
  
  - [ ]* 12.4 Write unit tests for web search
    - Test successful search
    - Test API failure handling
    - Test empty results
    - _Requirements: 6.1, 6.2, 6.3, 6.6_

- [ ] 13. Implement information extraction
  - [~] 13.1 Add _extract_information() method to ResearchTool
    - Build extraction prompt with search results and goal
    - Call Google Gemini API to extract relevant information
    - Return extracted text
    - _Requirements: 6.4_
  
  - [ ]* 13.2 Write unit tests for information extraction
    - Test extraction with valid results
    - Test extraction with empty results
    - Test LLM API failure handling
    - _Requirements: 6.4_

- [ ] 14. Complete ResearchTool with execute_task()
  - [~] 14.1 Implement execute_task() method
    - Call _search() with task query
    - Call _extract_information() with results and goal
    - Build ResearchResult with extracted info and sources
    - Add timeout handling (10 seconds)
    - Add error handling for API failures
    - _Requirements: 6.1, 6.4, 6.5, 6.6, 6.7_
  
  - [ ]* 14.2 Write property test for research result contains sources
    - **Property 11: Research Result Contains Sources**
    - **Validates: Requirements 6.5**
  
  - [ ]* 14.3 Write property test for research tool resilience
    - **Property 12: Research Tool Resilience**
    - **Validates: Requirements 6.6, 7.4**
  
  - [ ]* 14.4 Write integration tests for ResearchTool
    - Test complete research task execution
    - Test failure scenarios
    - Test timeout handling
    - _Requirements: 6.1, 6.4, 6.5, 6.6, 6.7_

- [~] 15. Checkpoint - Verify research tool
  - Ensure all tests pass, ask the user if questions arise.

### Phase 4: Complex Request Flow (Week 4-5)

- [ ] 16. Implement Planning Agent
  - [~] 16.1 Create PlanningAgent class with create_plan() method
    - Implement _build_planning_prompt() helper
    - Call Google Gemini API to generate research plan
    - Parse JSON response to ResearchPlan
    - Validate plan has 1-5 tasks
    - Add timeout handling (5 seconds)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ]* 16.2 Write property test for research plan size constraint
    - **Property 7: Research Plan Size Constraint**
    - **Validates: Requirements 5.2**
  
  - [ ]* 16.3 Write property test for research task structure
    - **Property 8: Research Task Structure**
    - **Validates: Requirements 5.3**
  
  - [ ]* 16.4 Write unit tests for Planning Agent
    - Test plan generation
    - Test task ordering
    - Test timeout handling
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

- [ ] 17. Implement sequential research execution
  - [~] 17.1 Add execute_research_tasks() method to Orchestrator
    - Iterate through research plan tasks in order
    - Execute each task via ResearchTool
    - Wait for each task to complete before starting next
    - Collect all results (including failures)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ]* 17.2 Write property test for sequential task execution
    - **Property 13: Sequential Task Execution**
    - **Validates: Requirements 7.1, 7.2**
  
  - [ ]* 17.3 Write property test for result collection completeness
    - **Property 14: Result Collection Completeness**
    - **Validates: Requirements 7.3, 7.5**
  
  - [ ]* 17.4 Write unit tests for sequential execution
    - Test execution order
    - Test failure handling
    - Test result collection
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 18. Implement Aggregator component
  - [~] 18.1 Create Aggregator class with aggregate() method
    - Implement _deduplicate() helper to remove duplicate information
    - Implement _organize_by_topic() helper to group information
    - Combine information from all research results
    - Preserve all source URLs
    - Add timeout handling (3 seconds)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [ ]* 18.2 Write property test for aggregator preserves sources
    - **Property 15: Aggregator Preserves Sources**
    - **Validates: Requirements 8.4**
  
  - [ ]* 18.3 Write property test for deduplication reduces size
    - **Property 16: Deduplication Reduces Size**
    - **Validates: Requirements 8.2**
  
  - [ ]* 18.4 Write unit tests for Aggregator
    - Test aggregation with multiple results
    - Test deduplication
    - Test source preservation
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 19. Implement Response Composer component
  - [~] 19.1 Create ResponseComposer class with compose() method
    - Implement _build_composition_prompt() helper
    - Include original request and knowledge base in prompt
    - Call Google Gemini API to generate final response
    - Parse response and extract sources
    - Add timeout handling (15 seconds)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [ ]* 19.2 Write property test for response composer includes context
    - **Property 17: Response Composer Includes Context**
    - **Validates: Requirements 9.2, 9.3**
  
  - [ ]* 19.3 Write property test for response contains source citations
    - **Property 18: Response Contains Source Citations**
    - **Validates: Requirements 9.5**
  
  - [ ]* 19.4 Write unit tests for Response Composer
    - Test response generation
    - Test source citation
    - Test timeout handling
    - _Requirements: 9.1, 9.4, 9.5, 9.6_

- [ ] 20. Complete complex request orchestration
  - [~] 20.1 Implement handle_complex_request() method in Orchestrator
    - Wire PlanningAgent -> execute_research_tasks -> Aggregator -> ResponseComposer flow
    - Add logging for each step
    - Handle partial failures gracefully
    - _Requirements: 1.4, 7.1, 7.5_
  
  - [ ]* 20.2 Write integration test for complex request flow
    - Test end-to-end complex request processing
    - Verify research plan creation
    - Verify sequential execution
    - Verify aggregation and composition
    - _Requirements: 1.4, 7.1, 7.5_

- [~] 21. Checkpoint - Verify complex flow
  - Ensure all tests pass, ask the user if questions arise.

### Phase 5: Error Handling & Resilience (Week 5-6)

- [ ] 22. Implement retry logic for LLM API calls
  - [~] 22.1 Create call_with_retry() utility function
    - Implement exponential backoff (1s, 2s delays)
    - Support max 2 retries (3 total attempts)
    - Log each retry attempt
    - Distinguish retryable vs non-retryable errors
    - _Requirements: 13.1_
  
  - [ ]* 22.2 Write property test for LLM API retry logic
    - **Property 26: LLM API Retry Logic**
    - **Validates: Requirements 13.1**
  
  - [ ]* 22.3 Write unit tests for retry logic
    - Test successful retry after failure
    - Test exhausted retries
    - Test non-retryable errors
    - _Requirements: 13.1_

- [ ] 23. Implement timeout handling for all components
  - [~] 23.1 Create with_timeout() utility wrapper
    - Wrap async operations with asyncio.wait_for()
    - Log timeout events with component name
    - Raise TimeoutError with context
    - _Requirements: 13.4_
  
  - [~] 23.2 Apply timeout wrappers to all component methods
    - Apply to Parser (1s), ComplexityAnalyzer (2s), DirectLLM (10s)
    - Apply to PlanningAgent (5s), ResearchTool (10s per task)
    - Apply to Aggregator (3s), ResponseComposer (15s)
    - _Requirements: 13.4_
  
  - [ ]* 23.3 Write property test for timeout handling
    - **Property 28: Timeout Handling**
    - **Validates: Requirements 13.4**
  
  - [ ]* 23.4 Write unit tests for timeout scenarios
    - Test timeout for each component
    - Test partial results on timeout
    - _Requirements: 13.4_

- [ ] 24. Implement fallback mechanisms
  - [~] 24.1 Add research failure fallback in Orchestrator
    - Detect when all research tasks fail
    - Fallback to DirectLLM with LLM-only knowledge
    - Log fallback event
    - _Requirements: 13.2, 13.3_
  
  - [ ]* 24.2 Write property test for research failure fallback
    - **Property 27: Research Failure Fallback**
    - **Validates: Requirements 13.3**
  
  - [ ]* 24.3 Write integration tests for fallback scenarios
    - Test fallback when all research fails
    - Test partial results when some research fails
    - _Requirements: 13.2, 13.3_

- [ ] 25. Implement error sanitization and logging
  - [~] 25.1 Create sanitize_error() utility function
    - Remove stack traces from user-facing errors
    - Remove internal paths and configuration
    - Generate request IDs for support
    - Log full error context internally
    - _Requirements: 13.5, 14.5_
  
  - [~] 25.2 Add comprehensive error logging
    - Log component failures with context
    - Log API call failures with duration
    - Log timeout events
    - _Requirements: 14.3, 14.4, 14.5_
  
  - [ ]* 25.3 Write property test for error logging context
    - **Property 32: Error Logging Context**
    - **Validates: Requirements 14.5**
  
  - [ ]* 25.4 Write unit tests for error sanitization
    - Test stack trace removal
    - Test internal detail removal
    - _Requirements: 13.5_

- [ ] 26. Implement component failure propagation
  - [~] 26.1 Add error handling in Orchestrator.process_request()
    - Catch exceptions from all components
    - Return ErrorResponse with sanitized message
    - Log full error context
    - _Requirements: 1.5, 13.5_
  
  - [ ]* 26.2 Write property test for component failure propagation
    - **Property 4: Component Failure Propagation**
    - **Validates: Requirements 1.5**
  
  - [ ]* 26.3 Write integration tests for error scenarios
    - Test Parser failure
    - Test ComplexityAnalyzer failure
    - Test DirectLLM failure
    - Test PlanningAgent failure
    - _Requirements: 1.5_

- [~] 27. Checkpoint - Verify error handling
  - Ensure all tests pass, ask the user if questions arise.

### Phase 6: API Layer & Final Integration (Week 6-7)

- [ ] 28. Implement FastAPI application
  - [~] 28.1 Create FastAPI app with /api/chat endpoint
    - Define POST /api/chat route
    - Accept ChatRequest JSON payload
    - Call Orchestrator.process_request()
    - Return ChatResponse JSON
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  
  - [~] 28.2 Add error handling middleware
    - Handle validation errors (400)
    - Handle internal errors (500)
    - Return ErrorResponse JSON
    - _Requirements: 11.5, 11.6_
  
  - [ ]* 28.3 Write property test for API response schema completeness
    - **Property 23: API Response Schema Completeness**
    - **Validates: Requirements 11.3**
  
  - [ ]* 28.4 Write property test for HTTP status code correctness
    - **Property 24: HTTP Status Code Correctness**
    - **Validates: Requirements 11.4, 11.5**
  
  - [ ]* 28.5 Write property test for error response structure
    - **Property 25: Error Response Structure**
    - **Validates: Requirements 11.6, 13.5**

- [ ] 29. Implement complete Orchestrator.process_request()
  - [~] 29.1 Wire all components together
    - Retrieve conversation history from database
    - Route through Parser and ComplexityAnalyzer
    - Route to simple or complex handler
    - Save conversation to database
    - Return ProcessedResponse
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 10.1, 10.2_
  
  - [~] 29.2 Add comprehensive logging
    - Log incoming requests
    - Log complexity classification
    - Log research task execution
    - Log API calls
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  
  - [ ]* 29.3 Write property test for request logging completeness
    - **Property 29: Request Logging Completeness**
    - **Validates: Requirements 14.1**
  
  - [ ]* 29.4 Write property test for research task logging
    - **Property 30: Research Task Logging**
    - **Validates: Requirements 14.3**
  
  - [ ]* 29.5 Write property test for external API call logging
    - **Property 31: External API Call Logging**
    - **Validates: Requirements 14.4**

- [ ] 30. Add conversation history integration
  - [~] 30.1 Integrate database calls in Orchestrator
    - Call get_conversation_history() at start
    - Pass history to DirectLLM and ResponseComposer
    - Call save_message() for user and assistant messages
    - Store complexity and research plan metadata
    - _Requirements: 10.1, 10.2, 10.5_
  
  - [ ]* 30.2 Write property test for complex request metadata storage
    - **Property 22: Complex Request Metadata Storage**
    - **Validates: Requirements 10.5**
  
  - [ ]* 30.3 Write integration tests for conversation continuity
    - Test multi-turn conversation
    - Test conversation history retrieval
    - Test metadata storage
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 31. Write end-to-end API tests
  - [ ]* 31.1 Test successful simple request via API
    - Test POST /api/chat with simple message
    - Verify 200 response
    - Verify response structure
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  
  - [ ]* 31.2 Test successful complex request via API
    - Test POST /api/chat with complex message
    - Verify 200 response
    - Verify sources in response
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  
  - [ ]* 31.3 Test conversation continuity via API
    - Test multiple requests with same conversation_id
    - Verify conversation history is used
    - _Requirements: 11.2, 11.3_
  
  - [ ]* 31.4 Test error scenarios via API
    - Test empty message (400)
    - Test invalid JSON (400)
    - Test server error (500)
    - _Requirements: 11.5, 11.6_

- [ ] 32. Create application startup and configuration
  - [~] 32.1 Implement application initialization
    - Load configuration from environment
    - Validate required configuration (GOOGLE_API_KEY, GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID)
    - Initialize database schema
    - Initialize all components
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [~] 32.2 Add startup validation
    - Verify Google API keys are set
    - Verify database is accessible
    - Test database connection
    - Fail fast if configuration is invalid
    - _Requirements: 12.5_
  
  - [ ]* 32.3 Write unit tests for startup validation
    - Test missing API key
    - Test invalid database path
    - Test successful initialization
    - _Requirements: 12.5_

- [~] 33. Final checkpoint - Complete system verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate component interactions
- All 32 correctness properties from the design document are covered by property tests
- Checkpoints ensure incremental validation at the end of each phase
- Implementation uses Python with FastAPI, Pydantic, SQLite, Google Gemini API (free tier), and Google Custom Search API (free tier - 100 queries/day)
- All components use async/await for non-blocking operations
- Comprehensive error handling and logging throughout
- **Important**: Google Custom Search API free tier has 100 queries/day limit - implement caching for production use
