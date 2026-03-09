# Implementation Plan: Streaming Status Notifications

## Overview

This implementation plan breaks down the Streaming Status Notifications feature into discrete coding tasks. The feature provides real-time status updates via Server-Sent Events (SSE) from a FastAPI backend to a React frontend, supporting both Simple Path (direct LLM) and Complex Path (research with Planning Agent) workflows.

The implementation follows an incremental approach: first establishing the core SSE infrastructure, then adding event emission capabilities, integrating with the orchestrator, implementing path-specific handlers, building frontend components, and finally adding error handling, logging, and testing.

## Tasks

- [x] 1. Set up SSE infrastructure and core data models
  - [x] 1.1 Create StatusEvent data model with Pydantic
    - Define StatusEvent base model with required fields (event_type, timestamp, request_id)
    - Define event-specific data models (ComplexityDeterminedData, ResearchPlanCreatedData, etc.)
    - Add validation rules for all fields
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  
  - [ ]* 1.2 Write property test for StatusEvent schema validation
    - **Property 23: Event Schema Required Fields**
    - **Property 24: Event Schema Optional Fields**
    - **Property 26: Event JSON Serialization Round-Trip**
    - **Validates: Requirements 12.1, 12.2, 12.4**
  
  - [x] 1.3 Create SSEStreamManager component
    - Implement create_stream() method to establish SSE connections
    - Implement emit_event() method to send events to clients
    - Implement _event_generator() async generator for SSE streaming
    - Implement _format_sse_event() to format events as SSE protocol
    - Implement close_stream() method for cleanup
    - Add connection state tracking with asyncio.Queue per connection
    - _Requirements: 1.1, 1.2, 1.3, 1.5_
  
  - [ ]* 1.4 Write property tests for SSEStreamManager
    - **Property 1: SSE Connection Creation**
    - **Property 2: SSE Protocol Headers**
    - **Property 4: Connection Lifecycle**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.5**

- [x] 2. Implement event emission layer
  - [x] 2.1 Create EventType enum with all event types
    - Define all event types (connection, parsing, complexity, path selection, research, response, error)
    - _Requirements: 2.1, 3.1, 4.1, 5.1, 6.1, 8.1, 9.1, 10.1_
  
  - [x] 2.2 Implement StatusEventEmitter component
    - Create emit methods for each event type (emit_connection_established, emit_parsing_request, etc.)
    - Implement event construction with proper data structures
    - Add event validation before emission
    - Delegate to SSEStreamManager for actual emission
    - _Requirements: 2.1, 2.3, 2.4, 3.1, 3.2, 4.1, 4.2, 5.2, 5.3, 6.1, 6.3, 7.1, 8.1, 9.1, 10.1_
  
  - [ ]* 2.3 Write property tests for event emission
    - **Property 5: Parsing Stage Events**
    - **Property 6: Complexity Analysis Events**
    - **Property 7: Path Selection Events**
    - **Property 27: Event Schema Validation**
    - **Validates: Requirements 2.1, 2.3, 3.1, 3.2, 4.1, 5.1, 12.5**

- [x] 3. Create FastAPI streaming endpoint
  - [x] 3.1 Implement StreamingChatRouter
    - Create POST /chat/stream endpoint
    - Accept ChatRequest payload
    - Create SSE connection via SSEStreamManager
    - Return StreamingResponse with correct headers
    - Handle request validation errors
    - _Requirements: 1.1, 1.2, 1.4_
  
  - [x]* 3.2 Write unit tests for StreamingChatRouter
    - Test endpoint creation and request handling
    - Test SSE response headers
    - Test error responses for invalid requests
    - _Requirements: 1.1, 1.2, 1.4_
  
  - [x] 3.3 Integrate router with FastAPI app
    - Register router in main FastAPI application
    - Configure CORS for SSE endpoints
    - _Requirements: 1.1_

- [x] 4. Checkpoint - Verify SSE infrastructure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement orchestrator with event streaming
  - [x] 5.1 Create StreamingOrchestrator component
    - Implement process_request() main workflow
    - Implement _parse_request() with event emission
    - Implement _analyze_complexity() with event emission
    - Add path routing logic (simple vs complex based on threshold 0.3)
    - Implement _execute_simple_path() and _execute_complex_path() stubs
    - _Requirements: 2.1, 2.3, 3.1, 3.2, 4.1, 5.1_
  
  - [ ]* 5.2 Write property tests for orchestrator workflow
    - **Property 8: Simple Path Response Generation**
    - **Property 9: Research Plan Creation Events**
    - **Validates: Requirements 4.2, 4.4, 5.2, 5.3**
  
  - [x] 5.3 Integrate orchestrator with StreamingChatRouter
    - Call orchestrator.process_request() from endpoint
    - Pass request_id and payload
    - Handle orchestrator exceptions
    - _Requirements: 2.1, 3.1_

- [x] 6. Implement Simple Path handler
  - [x] 6.1 Create SimplePathHandler component
    - Implement execute() method
    - Emit simple_path_selected event
    - Emit generating_response event
    - Implement _stream_llm_response() to stream chunks from LLM
    - Emit response_chunk events with sequential indices
    - Emit response_complete event
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 9.1, 9.2, 9.3_
  
  - [ ]* 6.2 Write property tests for Simple Path
    - **Property 14: Response Chunk Streaming**
    - **Property 15: Chunk Sequential Ordering**
    - **Validates: Requirements 4.3, 9.1, 9.2, 9.3, 9.4**
  
  - [x] 6.3 Integrate SimplePathHandler with orchestrator
    - Call handler from _execute_simple_path()
    - Pass event emitter and parsed request
    - _Requirements: 4.1, 4.2_

- [x] 7. Implement Complex Path handler
  - [x] 7.1 Create ComplexPathHandler component
    - Implement execute() method
    - Emit complex_path_selected event
    - Implement _create_research_plan() with event emission
    - Implement _execute_research_tasks() with progress tracking
    - Implement _compose_final_response() with chunk streaming
    - _Requirements: 5.1, 5.2, 5.3, 6.1, 6.3, 6.4, 7.1, 8.1, 8.3_
  
  - [x] 7.2 Implement research task loop with event emission
    - Emit researching_task event for each task (X/N format)
    - Execute research task via ResearchAgent
    - Emit task_complete or task_error events
    - Emit results_found events when results are found
    - Continue with remaining tasks on error
    - Emit research_complete event after all tasks
    - _Requirements: 6.1, 6.3, 6.4, 6.5, 7.1, 7.2, 7.4_
  
  - [ ]* 7.3 Write property tests for Complex Path
    - **Property 10: Research Task Progress Events**
    - **Property 11: Research Completion Event**
    - **Property 12: Results Found Events**
    - **Property 13: Response Composition Events**
    - **Validates: Requirements 6.1, 6.3, 6.4, 7.1, 7.2, 8.1, 8.2**
  
  - [x] 7.4 Integrate ComplexPathHandler with orchestrator
    - Call handler from _execute_complex_path()
    - Pass event emitter, planning agent, research agent, and composer
    - _Requirements: 5.1, 6.1_

- [x] 8. Checkpoint - Verify backend streaming workflow
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement error handling and retry logic
  - [x] 9.1 Add error handling to orchestrator
    - Catch exceptions during processing
    - Emit error events with error code, message, and recoverable flag
    - Implement retry logic for recoverable errors (max 3 attempts)
    - Emit retrying events before each retry
    - Close stream for non-recoverable errors
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [ ]* 9.2 Write property tests for error handling
    - **Property 16: Error Event Emission**
    - **Property 17: Retry Event Emission**
    - **Property 18: Non-Recoverable Error Stream Closure**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4**
  
  - [x] 9.3 Add connection error handling
    - Handle client disconnections gracefully
    - Clean up resources on disconnection
    - Emit connection error events
    - _Requirements: 1.4, 13.1_

- [x] 10. Implement event logging
  - [x] 10.1 Create EventLogger component
    - Implement log_event() method with structured logging
    - Implement log_stream_lifecycle() for connection events
    - Use INFO level for normal events
    - Use ERROR level for error events with stack traces
    - Include request_id, event_type, timestamp in all logs
    - _Requirements: 15.1, 15.2, 15.3, 15.4_
  
  - [ ]* 10.2 Write unit tests for EventLogger
    - Test log formatting and levels
    - Test structured log output
    - _Requirements: 15.1, 15.2, 15.3_
  
  - [x] 10.3 Integrate EventLogger with SSEStreamManager and StatusEventEmitter
    - Log all emitted events
    - Log stream lifecycle events (open, close, error)
    - _Requirements: 15.1, 15.4, 15.5_

- [x] 11. Implement event filtering (optional feature)
  - [x] 11.1 Add filter support to SSEStreamManager
    - Accept event_type filters in create_stream()
    - Filter events before emission based on criteria
    - Always emit response_chunk events regardless of filters
    - Default to no filtering when filters not specified
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  
  - [ ]* 11.2 Write property tests for event filtering
    - **Property 31: Event Filtering**
    - **Property 33: No Filter Default Behavior**
    - **Property 34: Filter Independence from Chunks**
    - **Validates: Requirements 14.1, 14.3, 14.4, 14.5**

- [x] 12. Checkpoint - Backend implementation complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Implement frontend SSE client hook
  - [x] 13.1 Create useSSEStream React hook
    - Implement connection establishment with EventSource
    - Parse incoming SSE events
    - Maintain events array in state
    - Track connection state (isConnected)
    - Implement disconnect() cleanup function
    - Add useEffect cleanup on unmount
    - _Requirements: 1.1, 11.1, 11.3_
  
  - [x] 13.2 Add reconnection logic to useSSEStream
    - Detect connection interruptions
    - Implement exponential backoff (1s, 2s, 4s, 8s)
    - Track reconnection attempts (max 4)
    - Display reconnection indicator
    - Stop retrying after max attempts
    - _Requirements: 13.1, 13.2, 13.3, 13.5_
  
  - [ ]* 13.3 Write unit tests for useSSEStream
    - Test connection establishment
    - Test event parsing and state updates
    - Test reconnection logic with exponential backoff
    - Test cleanup on unmount
    - _Requirements: 1.1, 13.2, 13.3, 13.5_
  
  - [ ]* 13.4 Write property tests for frontend reconnection
    - **Property 28: Reconnection Indicator Display**
    - **Property 29: Exponential Backoff Reconnection**
    - **Property 30: Max Reconnection Attempts**
    - **Validates: Requirements 13.2, 13.3, 13.5**

- [x] 14. Implement frontend status display components
  - [x] 14.1 Create StatusDisplay component
    - Render status messages from events
    - Display timestamps for each event
    - Show progress indicators for research tasks (Task X/N format)
    - Display connection status indicator
    - Highlight error events
    - Show completion indicator when stream closes
    - _Requirements: 11.1, 11.2, 11.4, 11.5_
  
  - [ ]* 14.2 Write unit tests for StatusDisplay
    - Test rendering of different event types
    - Test progress indicator formatting
    - Test timestamp display
    - _Requirements: 11.1, 11.2, 11.4_
  
  - [ ]* 14.3 Write property tests for frontend display
    - **Property 19: Frontend Event Display**
    - **Property 20: Research Task Progress Display**
    - **Property 22: Stream Completion Display**
    - **Validates: Requirements 11.1, 11.2, 11.4, 11.5**

- [x] 15. Implement frontend response display component
  - [x] 15.1 Create ResponseDisplay component
    - Append response chunks incrementally
    - Implement auto-scroll when new chunks arrive
    - Display completion indicator
    - Format markdown content
    - Handle code blocks and citations
    - _Requirements: 11.3, 11.5_
  
  - [ ]* 15.2 Write unit tests for ResponseDisplay
    - Test chunk appending
    - Test auto-scroll behavior
    - Test markdown formatting
    - _Requirements: 11.3_
  
  - [ ]* 15.3 Write property test for chunk appending
    - **Property 21: Response Chunk Appending**
    - **Validates: Requirements 11.3**

- [x] 16. Integrate frontend components into chat UI
  - [x] 16.1 Wire useSSEStream hook into chat page
    - Connect hook to chat submission
    - Pass event handlers
    - Handle connection errors
    - _Requirements: 1.1, 11.1_
  
  - [x] 16.2 Add StatusDisplay and ResponseDisplay to chat UI
    - Position components in layout
    - Style components for visual clarity
    - Add loading states
    - _Requirements: 11.1, 11.3_

- [x] 17. Add event filtering support to frontend (optional)
  - [x] 17.1 Add filter parameter to useSSEStream
    - Accept event_type filters in hook options
    - Pass filters in SSE connection URL
    - _Requirements: 14.2_
  
  - [ ]* 17.2 Write property test for filter specification
    - **Property 32: Filter Specification**
    - **Validates: Requirements 14.2**

- [x] 18. Final checkpoint - End-to-end integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 19. Add comprehensive integration tests
  - [ ]* 19.1 Write integration test for Simple Path flow
    - Test complete flow from request to response
    - Verify all expected events are emitted in order
    - Verify response chunks are streamed correctly
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 19.2 Write integration test for Complex Path flow
    - Test complete flow with research tasks
    - Verify research plan creation and task execution
    - Verify progress tracking (X/N format)
    - Verify final response composition
    - _Requirements: 1.1, 2.1, 3.1, 5.1, 5.2, 6.1, 6.3, 7.1, 8.1_
  
  - [ ]* 19.3 Write integration test for error scenarios
    - Test parsing errors
    - Test research task errors
    - Test retry logic
    - Test non-recoverable errors
    - _Requirements: 2.4, 6.5, 10.1, 10.3, 10.4_
  
  - [ ]* 19.4 Write integration test for connection interruptions
    - Test client disconnection handling
    - Test reconnection with exponential backoff
    - Test max reconnection attempts
    - _Requirements: 13.1, 13.2, 13.3, 13.5_

- [x] 20. Performance optimization and monitoring
  - [x] 20.1 Add performance metrics collection
    - Track active SSE connections count
    - Track event emission latency
    - Track request processing time by path
    - Track error rates
    - _Requirements: 15.1_
  
  - [x] 20.2 Optimize chunk streaming frequency
    - Implement chunk buffering (emit every 50-100ms)
    - Balance responsiveness vs overhead
    - _Requirements: 9.5_
  
  - [x] 20.3 Add connection pooling and cleanup
    - Implement max concurrent connections limit
    - Add connection timeout handling
    - Clean up inactive connections
    - _Requirements: 1.5_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- Checkpoints ensure incremental validation at key milestones
- Backend uses Python with FastAPI and Pydantic
- Frontend uses TypeScript with React
- SSE protocol is used for real-time streaming
- Two execution paths: Simple (direct LLM) and Complex (research with planning)
