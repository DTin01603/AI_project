# Implementation Plan: Research Agent Phase 2

## Overview

Phase 2 nâng cấp hệ thống chat AI cơ bản (Phase 1) thành một intelligent research agent với khả năng tự động tìm kiếm thông tin từ web, truy xuất dữ liệu từ documents, thực hiện tính toán, và orchestrate nhiều tools. Hệ thống sử dụng LangChain ReAct pattern để tự động phân loại câu hỏi và chọn tool phù hợp.

Implementation approach:
- Build trên Phase 1 MVP đã hoàn thành (FastAPI + LangChain + Google Gemini)
- Implement từng tool độc lập trước (Web Search, Calculator, Document Processor)
- Implement RAG system với vector database
- Implement Smart Router để orchestrate tools
- Integrate tất cả components vào research pipeline
- Add conversation memory và citation system
- Testing và optimization

## Tasks

- [ ] 1. Setup project dependencies và configuration
  - Install thêm dependencies: tavily-python, chromadb, langchain-community, pypdf2, python-docx, unstructured, hypothesis
  - Create ResearchSettings class để load environment variables (TAVILY_API_KEY, vector DB config)
  - Add configuration cho chunk size, similarity threshold, timeouts
  - Setup logging cho research operations
  - _Requirements: 10.1, 10.2, 10.3_

- [ ] 2. Implement Calculator Tool
  - [ ] 2.1 Create CalculatorTool class với safe expression evaluation
    - Implement CalculationQuery và CalculationResult data models
    - Support operators: +, -, *, /, **, sqrt, log, sin, cos, tan, abs, ceil, floor
    - Implement safe_dict với math functions và constants (pi, e)
    - Add expression validation để block dangerous patterns (import, exec, eval)
    - Implement _extract_expression để parse từ natural language
    - Format result với max 6 decimal places
    - _Requirements: 5.1, 5.3, 5.4_
  
  - [ ]* 2.2 Write unit tests for Calculator Tool
    - Test basic arithmetic: 2 + 3 * 4 = 14
    - Test order of operations: (2 + 3) * 4 = 20
    - Test functions: sqrt(16) = 4, sin(0) = 0
    - Test precision: 1/3 has max 6 decimals
    - Test invalid expression returns error
    - Test unsafe expression rejected (import, exec)
    - _Requirements: 5.1, 5.4_
  
  - [ ]* 2.3 Write property test for Calculator Tool
    - **Property 20: Calculator operator support**
    - **Property 21: Calculation result precision**
    - **Validates: Requirements 5.1, 5.4**

- [ ] 3. Implement Web Search Tool
  - [ ] 3.1 Create SearchProvider protocol và TavilySearchProvider implementation
    - Define SearchQuery, SearchResult, SearchResponse data models
    - Implement TavilySearchProvider với Tavily API integration
    - Handle API errors và timeouts (raise SearchError)
    - Extract title, snippet, url, published_date, score từ results
    - Limit results to max_results (default 5)
    - _Requirements: 1.1, 1.3, 1.4, 1.8_
  
  - [ ] 3.2 Create WebSearchTool class
    - Accept SearchProvider trong constructor
    - Implement execute method với timing tracking
    - Log search operations với query, num_results, search_time_ms
    - Handle empty results gracefully
    - _Requirements: 1.3, 1.8_
  
  - [ ]* 3.3 Write unit tests for Web Search Tool
    - Test successful search returns results
    - Test each result has title, snippet, url
    - Test max_results respected
    - Test timeout raises SearchError
    - Test API error raises SearchError
    - Test empty results handled
    - _Requirements: 1.3, 1.4, 1.7, 1.8_
  
  - [ ]* 3.4 Write property tests for Web Search Tool
    - **Property 3: Search result structure**
    - **Property 4: Search result count**
    - **Validates: Requirements 1.3, 1.4**

- [ ] 4. Implement Embedding Service
  - [ ] 4.1 Create EmbeddingService class với GoogleGenerativeAIEmbeddings
    - Initialize với Google API key và model "models/embedding-001"
    - Implement embed_query method cho single query
    - Implement embed_documents method cho batch documents
    - Return embedding dimension = 768
    - _Requirements: 2.5_
  
  - [ ]* 4.2 Write unit tests for Embedding Service
    - Test embed_query returns vector of dimension 768
    - Test embed_documents returns list of vectors
    - Test batch processing works correctly
    - _Requirements: 2.5_
  
  - [ ]* 4.3 Write property test for Embedding Service
    - **Property 11: Embedding generation**
    - **Validates: Requirements 2.5**

- [ ] 5. Checkpoint - Ensure basic tools work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement Vector Database interface và Chroma implementation
  - [ ] 6.1 Create VectorDatabase abstract interface
    - Define add_documents method signature
    - Define similarity_search method signature
    - Define delete_document method signature
    - Define health_check method signature
    - _Requirements: 2.6, 3.1_
  
  - [ ] 6.2 Implement ChromaVectorDatabase
    - Initialize Chroma client với persist_directory
    - Create or get collection "documents" với cosine similarity
    - Implement add_documents: store chunks với embeddings và metadata
    - Implement similarity_search: query với filters (user_id, conversation_id)
    - Convert distance to similarity score (1 - distance)
    - Implement delete_document: delete by document_id
    - Implement health_check: verify client connection
    - _Requirements: 2.6, 2.7, 3.1, 3.2, 3.3_
  
  - [ ]* 6.3 Write unit tests for ChromaVectorDatabase
    - Test add_documents stores chunks correctly
    - Test similarity_search returns top_k results
    - Test similarity_search filters by user_id
    - Test delete_document removes all chunks
    - Test health_check returns true when connected
    - _Requirements: 2.6, 3.3_
  
  - [ ]* 6.4 Write property tests for Vector Database
    - **Property 12: Document storage round-trip**
    - **Property 15: Semantic search result count**
    - **Property 16: Similarity score range**
    - **Validates: Requirements 2.6, 3.3, 3.4**

- [ ] 7. Implement Document Processor
  - [ ] 7.1 Create DocumentProcessor class
    - Define DocumentUpload và ProcessedDocument data models
    - Define SUPPORTED_FORMATS mapping (PDF, TXT, DOCX, MD)
    - Set MAX_FILE_SIZE = 10MB
    - Initialize RecursiveCharacterTextSplitter (chunk_size=1000, overlap=100)
    - _Requirements: 2.1, 2.2, 2.4_
  
  - [ ] 7.2 Implement document processing pipeline
    - Validate file size (reject if > 10MB)
    - Validate file format (reject if not supported)
    - Extract text using appropriate loader (PyPDFLoader, TextLoader, etc.)
    - Split text into chunks với text_splitter
    - Generate embeddings cho all chunks using EmbeddingService
    - Store chunks và embeddings vào VectorDatabase với metadata
    - Track processing time và return ProcessedDocument
    - Handle errors gracefully và return status="failed" với error_message
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_
  
  - [ ]* 7.3 Write unit tests for Document Processor
    - Test valid PDF upload succeeds
    - Test file too large rejected (> 10MB)
    - Test unsupported format rejected
    - Test text extraction works
    - Test chunking produces correct sizes (500-1000 tokens)
    - Test embeddings generated for all chunks
    - Test metadata stored correctly (filename, chunk_index, document_id, timestamp)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.7, 2.8_
  
  - [ ]* 7.4 Write property tests for Document Processor
    - **Property 7: File format validation**
    - **Property 8: File size validation**
    - **Property 9: Text extraction success**
    - **Property 10: Chunk size constraints**
    - **Property 13: Chunk metadata completeness**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.7**

- [ ] 8. Implement RAG System
  - [ ] 8.1 Create RAGSystem class
    - Define RAGQuery, RetrievedChunk, RAGResponse data models
    - Initialize với VectorDatabase, EmbeddingService, LLM
    - Build answer prompt template cho RAG
    - _Requirements: 3.1, 3.2_
  
  - [ ] 8.2 Implement RAG query pipeline
    - Generate query embedding từ question
    - Perform similarity_search trong VectorDatabase
    - Filter chunks by similarity_threshold (default 0.7)
    - If no relevant chunks: return "không tìm thấy thông tin" message
    - If has relevant chunks: build context từ chunks và generate answer với LLM
    - Track retrieval time
    - Return RAGResponse với answer, retrieved_chunks, has_relevant_context
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.9_
  
  - [ ]* 8.3 Write unit tests for RAG System
    - Test query generates embedding
    - Test semantic search returns top_k results
    - Test similarity scores in range [0, 1]
    - Test low similarity returns "no relevant info" message
    - Test context passed to LLM
    - Test answer references retrieved chunks
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_
  
  - [ ]* 8.4 Write property tests for RAG System
    - **Property 14: Query embedding generation**
    - **Property 17: Context inclusion in RAG**
    - **Property 18: RAG answer generation**
    - **Validates: Requirements 3.2, 3.6, 3.7**

- [ ] 9. Checkpoint - Ensure RAG pipeline works end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement Conversation Memory
  - [ ] 10.1 Create ConversationMemory class
    - Define Message và Conversation data models
    - Set MAX_MESSAGES = 20 (10 pairs)
    - Initialize với SessionStore
    - _Requirements: 6.1, 6.2_
  
  - [ ] 10.2 Implement memory operations
    - Implement add_message: append message to conversation
    - Enforce MAX_MESSAGES limit: keep only last 20 messages
    - Implement get_history: retrieve messages cho conversation_id
    - Implement clear_history: delete conversation
    - Implement format_history_for_prompt: format messages cho LLM
    - Update conversation.updated_at on each operation
    - _Requirements: 6.1, 6.2, 6.3, 6.5, 6.6, 6.7_
  
  - [ ]* 10.3 Write unit tests for Conversation Memory
    - Test add_message stores in memory
    - Test get_history retrieves messages
    - Test max 20 messages enforced
    - Test clear_history removes all messages
    - Test conversation_id uniqueness
    - Test session persistence
    - _Requirements: 6.1, 6.2, 6.5, 6.7, 6.8_
  
  - [ ]* 10.4 Write property tests for Conversation Memory
    - **Property 23: Conversation history storage**
    - **Property 24: Memory size limit**
    - **Property 26: Conversation memory persistence**
    - **Property 27: Conversation ID uniqueness**
    - **Validates: Requirements 6.1, 6.2, 6.5, 6.6, 6.8**

- [ ] 11. Implement Citation System
  - [ ] 11.1 Create CitationSystem class
    - Define Citation và AnswerWithCitations data models
    - Implement Citation.format method cho web và document citations
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [ ] 11.2 Implement citation methods
    - Implement add_web_citations: format as "[Source: <title> - <URL>]"
    - Implement add_document_citations: format as "[Source: <filename>, page <number>]"
    - Implement _deduplicate_citations: remove duplicate URLs/filenames
    - Place citations at end of answer
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [ ]* 11.3 Write unit tests for Citation System
    - Test web citations formatted correctly
    - Test document citations formatted correctly
    - Test citations deduplicated
    - Test citations placed after answer
    - Test no sources → general knowledge indicator
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 7.7_
  
  - [ ]* 11.4 Write property tests for Citation System
    - **Property 6: Web citation format**
    - **Property 19: Document citation format**
    - **Property 28: Citation deduplication**
    - **Property 29: Citation placement**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6**

- [ ] 12. Implement Smart Router
  - [ ] 12.1 Create SmartRouter class
    - Define QuestionCategory enum (general_knowledge, real_time_info, document_based, calculation)
    - Define RouterInput và RoutingDecision data models
    - Initialize với LLM và ConversationMemory
    - Build classification prompt template
    - _Requirements: 4.1_
  
  - [ ] 12.2 Implement routing logic
    - Get conversation history từ memory
    - Build classification prompt với question và history
    - Use LLM to classify question into category
    - Map category to tools: real_time_info→web_search, document_based→rag, calculation→calculator, general_knowledge→direct_llm
    - Calculate confidence score
    - Log routing decision với question, category, tools, reasoning
    - Return RoutingDecision
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 4.9_
  
  - [ ]* 12.3 Write unit tests for Smart Router
    - Test real-time question → routes to web_search
    - Test document question → routes to rag
    - Test calculation question → routes to calculator
    - Test general question → routes to direct_llm
    - Test routing decision logged with reasoning
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.9_
  
  - [ ]* 12.4 Write property tests for Smart Router
    - **Property 1: Question category classification**
    - **Property 2: Tool routing consistency**
    - **Property 25: Context inclusion in routing**
    - **Property 34: Routing decision logging**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 6.3, 4.9**

- [ ] 13. Checkpoint - Ensure routing and memory work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Implement Research Orchestrator
  - [ ] 14.1 Create ResearchOrchestrator class
    - Define ResearchResult và ToolResult data models
    - Initialize với SmartRouter, all tools, ConversationMemory, CitationSystem
    - _Requirements: 1.2, 4.2, 4.3, 4.4, 4.5_
  
  - [ ] 14.2 Implement tool execution methods
    - Implement _execute_web_search: call WebSearchTool, synthesize answer, add citations
    - Implement _execute_rag: call RAGSystem, add document citations
    - Implement _execute_calculator: call CalculatorTool, format result
    - Implement _execute_direct_llm: call LLM directly với conversation context
    - Implement _synthesize_answer: generate answer từ search results/context
    - _Requirements: 1.2, 1.5, 1.6, 3.7, 3.8, 5.2_
  
  - [ ] 14.3 Implement main execute method
    - Store user message in ConversationMemory
    - Route question using SmartRouter
    - Execute selected tool(s)
    - Handle tool failures với fallback to direct LLM
    - Store assistant message in ConversationMemory
    - Track execution time
    - Return ResearchResult với answer, citations, tools_used
    - _Requirements: 1.2, 4.2, 4.3, 4.4, 4.5, 6.1, 8.1_
  
  - [ ]* 14.4 Write unit tests for Research Orchestrator
    - Test web search execution với citations
    - Test RAG execution với document citations
    - Test calculator execution
    - Test direct LLM execution
    - Test fallback when tool fails
    - Test conversation memory updated
    - _Requirements: 1.2, 1.5, 1.6, 3.7, 3.8, 8.1_
  
  - [ ]* 14.5 Write property test for answer synthesis
    - **Property 5: Answer synthesis from search**
    - **Validates: Requirements 1.5**

- [ ] 15. Implement Error Handling và Retry Logic
  - [ ] 15.1 Create custom exception classes
    - Define ResearchError base exception
    - Define SearchError, RAGError, DocumentProcessingError, VectorDatabaseError, RateLimitError
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [ ] 15.2 Implement RetryHandler class
    - Initialize với max_retries=2, backoff_factor=2.0
    - Implement execute_with_retry với exponential backoff
    - Log retry attempts với wait time
    - Raise last exception after all retries exhausted
    - _Requirements: 8.8_
  
  - [ ] 15.3 Implement GracefulDegradation class
    - Implement execute_with_fallback method
    - Try primary function first
    - On failure, try fallback function
    - Add "[Fallback Mode]" prefix to fallback results
    - Log warnings for degraded operations
    - _Requirements: 8.1, 8.7_
  
  - [ ]* 15.4 Write unit tests for error handling
    - Test SearchError triggers fallback to direct LLM
    - Test RAG no results returns helpful message
    - Test Calculator error returns explanation
    - Test Vector DB connection failure disables RAG
    - Test retry logic với exponential backoff
    - Test error logging completeness
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6, 8.8_
  
  - [ ]* 15.5 Write property tests for error handling
    - **Property 30: Error logging completeness**
    - **Property 31: Retry attempt limit**
    - **Property 32: Exponential backoff timing**
    - **Validates: Requirements 8.6, 8.8**

- [ ] 16. Implement Performance Optimization
  - [ ] 16.1 Create QueryCache class
    - Initialize với TTL (default 3600 seconds)
    - Implement get_cache_key: hash question + tool
    - Implement get: return cached result if within TTL
    - Implement set: store result với timestamp
    - Log cache hits
    - _Requirements: 9.7_
  
  - [ ] 16.2 Implement batch operations
    - Implement embed_documents_batch: process embeddings in batches of 10
    - Optimize vector DB operations với connection pooling
    - _Requirements: 9.4, 9.5_
  
  - [ ]* 16.3 Write unit tests for caching
    - Test cache stores and retrieves results
    - Test cache respects TTL
    - Test cache key generation
    - _Requirements: 9.7_
  
  - [ ]* 16.4 Write property test for caching
    - **Property 33: Query cache round-trip**
    - **Validates: Requirements 9.7**

- [ ] 17. Checkpoint - Ensure orchestration and error handling work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 18. Extend Phase 1 pipeline với Research capabilities
  - [ ] 18.1 Create ResearchChatRequest và ResearchChatResponse models
    - Extend ChatRequest với force_tool option
    - Add ToolUsage và ResearchMeta models
    - Extend ChatResponse với citations và tools_used
    - _Requirements: 1.6, 7.1, 7.2_
  
  - [ ] 18.2 Create ResearchChatPipeline extending ChatPipeline
    - Initialize với ResearchOrchestrator
    - Override process method to call research_orchestrator.execute
    - Compose response với citations
    - _Requirements: 1.2, 1.5, 1.6_

- [ ] 19. Implement API endpoints
  - [ ] 19.1 Implement POST /research/chat endpoint
    - Accept ResearchChatRequest
    - Call ResearchChatPipeline.process
    - Return ResearchChatResponse với answer, citations, meta
    - Handle errors và return appropriate status codes
    - _Requirements: 1.1, 1.2, 1.5, 1.6, 9.1, 9.2, 9.3_
  
  - [ ] 19.2 Implement POST /research/upload endpoint
    - Accept multipart/form-data với file, user_id, conversation_id
    - Validate file format và size
    - Process document asynchronously using BackgroundTasks
    - Return document_id và status immediately
    - _Requirements: 2.1, 2.2, 2.8, 2.9, 9.6_
  
  - [ ] 19.3 Implement GET /research/documents endpoint
    - Accept user_id và optional conversation_id query params
    - Query VectorDatabase for user's documents
    - Return list of documents với metadata
    - _Requirements: 2.7_
  
  - [ ] 19.4 Implement DELETE /research/documents/{document_id} endpoint
    - Delete document từ VectorDatabase
    - Return deletion status
    - _Requirements: 2.6_
  
  - [ ] 19.5 Implement GET /research/health endpoint
    - Check availability của all tools (web_search, rag, calculator, direct_llm)
    - Check API keys và connections
    - Return health status với tool details
    - _Requirements: 10.4, 10.5_

- [ ] 20. Implement API key validation và tool availability
  - [ ] 20.1 Add API key validation at startup
    - Load API keys từ environment variables
    - Validate required keys (GOOGLE_API_KEY)
    - Validate optional keys (TAVILY_API_KEY, PINECONE_API_KEY)
    - _Requirements: 10.1, 10.2_
  
  - [ ] 20.2 Implement tool availability checking
    - If API key missing, mark tool as unavailable
    - Log warnings for unavailable tools
    - Continue operating với available tools only
    - _Requirements: 10.4_
  
  - [ ]* 20.3 Write unit tests for API key handling
    - Test required key missing raises error
    - Test optional key missing disables tool
    - Test tool availability checking
    - _Requirements: 10.1, 10.2, 10.4_
  
  - [ ]* 20.4 Write property tests for configuration
    - **Property 35: API key environment loading**
    - **Property 36: Tool availability with missing keys**
    - **Validates: Requirements 10.1, 10.4**

- [ ] 21. Write integration tests
  - [ ]* 21.1 Write integration test for POST /research/chat với web search
    - Mock Tavily API
    - Send question about real-time info
    - Verify response has answer, citations, correct category
    - Verify web_search tool used
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6_
  
  - [ ]* 21.2 Write integration test for POST /research/chat với RAG
    - Upload a test document first
    - Send question about document content
    - Verify response has answer, document citations
    - Verify rag tool used
    - _Requirements: 2.1, 3.1, 3.7, 3.8_
  
  - [ ]* 21.3 Write integration test for POST /research/chat với calculator
    - Send calculation question
    - Verify correct numerical result in answer
    - Verify calculator tool used
    - _Requirements: 5.1, 5.2, 5.4_
  
  - [ ]* 21.4 Write integration test for POST /research/upload
    - Upload valid PDF file
    - Verify document_id returned
    - Verify status is "processing" or "completed"
    - _Requirements: 2.1, 2.2, 2.9_
  
  - [ ]* 21.5 Write integration test for upload validation
    - Test file too large rejected (> 10MB)
    - Test unsupported format rejected
    - Verify appropriate error messages
    - _Requirements: 2.2, 2.8_
  
  - [ ]* 21.6 Write integration test for GET /research/documents
    - Upload multiple documents
    - Query documents by user_id
    - Verify all documents returned với metadata
    - _Requirements: 2.7_
  
  - [ ]* 21.7 Write integration test for DELETE /research/documents
    - Upload a document
    - Delete it
    - Verify it's removed from database
    - _Requirements: 2.6_
  
  - [ ]* 21.8 Write integration test for GET /research/health
    - Call health endpoint
    - Verify all tools status returned
    - Verify API availability checked
    - _Requirements: 10.4, 10.5_

- [ ] 22. Checkpoint - Ensure all integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 23. Add performance monitoring và metrics
  - [ ] 23.1 Add timing metrics for all operations
    - Track web search time (target < 10s)
    - Track RAG query time (target < 5s)
    - Track direct LLM time (target < 3s)
    - Track document processing time (target < 30s)
    - Log performance metrics when thresholds exceeded
    - _Requirements: 9.1, 9.2, 9.3, 9.8_
  
  - [ ] 23.2 Implement metrics endpoint
    - Track tool usage statistics
    - Track success/failure rates
    - Track average response times
    - Expose metrics at /research/metrics
    - _Requirements: 10.6_

- [ ] 24. Create example .env file và documentation
  - [ ] 24.1 Create .env.example file
    - Document all required environment variables
    - Document all optional environment variables
    - Provide example values
    - _Requirements: 10.1, 10.3_
  
  - [ ] 24.2 Update README với Phase 2 setup instructions
    - Document new dependencies
    - Document API key setup
    - Document vector database options (Chroma vs Pinecone)
    - Document new endpoints
    - Provide usage examples

- [ ] 25. Final integration và end-to-end testing
  - [ ]* 25.1 Test complete research workflow
    - Upload documents
    - Ask document-based questions
    - Ask real-time questions
    - Ask calculation questions
    - Verify conversation memory works
    - Verify citations present
    - _Requirements: All_
  
  - [ ]* 25.2 Test error scenarios end-to-end
    - Test web search failure fallback
    - Test RAG no results handling
    - Test calculator error handling
    - Test retry logic
    - _Requirements: 8.1, 8.2, 8.3, 8.8_
  
  - [ ]* 25.3 Test performance requirements
    - Verify web search < 10s
    - Verify RAG query < 5s
    - Verify direct LLM < 3s
    - Verify document processing < 30s for files < 10MB
    - _Requirements: 9.1, 9.2, 9.3, 2.9_

- [ ] 26. Final checkpoint - Production readiness
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties (run 100+ iterations each)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- Build incrementally: tools first, then orchestration, then API layer
- Mock external services (Tavily, Vector DB, LLM) in unit tests
- Use real services in integration tests (or test doubles)
- Phase 2 extends Phase 1 without breaking existing functionality

## Dependencies

- Phase 1 MVP must be completed and working
- External services: Tavily API (or SerpAPI), Google Gemini API
- Vector database: Chroma (local) or Pinecone (cloud)
- Python 3.10+ required
- All Phase 1 dependencies must be installed

## Success Criteria

- All core functionality implemented and tested
- Agent correctly routes 90%+ questions to appropriate tool
- Web search provides relevant results in 95%+ cases
- RAG system answers document questions with 85%+ accuracy
- Source citations included in 100% of web search and RAG responses
- System maintains response time SLAs 95%+ of the time
- Zero API key exposure in logs or error messages
- Document upload success rate 98%+ for valid formats
- All property tests pass (100+ iterations each)
- Integration tests cover all major workflows
