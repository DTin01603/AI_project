# Requirements Document

## Introduction

Hệ thống AI Agent với Research Tool là một intelligent agent system có khả năng tự động phân tích độ phức tạp của user request và quyết định chiến lược xử lý phù hợp. Với các request đơn giản, hệ thống trả lời trực tiếp qua LLM. Với các request phức tạp cần thông tin bổ sung, hệ thống tự động tạo research plan, thực thi web search tuần tự, tổng hợp kết quả và compose response chất lượng cao.

## Glossary

- **Orchestrator**: Component điều phối chính của hệ thống, quản lý workflow và routing giữa các components
- **Parser**: Component làm sạch và chuẩn hóa user input
- **Complexity_Analyzer**: Component phân tích độ phức tạp của request và phân loại thành simple hoặc complex
- **Direct_LLM**: Component xử lý simple requests bằng cách gọi LLM trực tiếp
- **Planning_Agent**: Component tạo research plan cho complex requests
- **Research_Tool**: Component duy nhất thực hiện web search và extract information
- **Aggregator**: Component tổng hợp research results từ nhiều research tasks
- **Response_Composer**: Component sử dụng LLM để viết lại response cuối cùng dựa trên aggregated results
- **Research_Plan**: Danh sách các research tasks cần thực thi tuần tự
- **Research_Task**: Một nhiệm vụ research cụ thể với query và mục tiêu
- **Simple_Request**: Request có thể trả lời trực tiếp bằng LLM knowledge mà không cần thông tin bổ sung
- **Complex_Request**: Request cần thông tin bổ sung từ external sources
- **Conversation_History**: Lịch sử các conversations được lưu trong database

## Requirements

### Requirement 1: Request Orchestration

**User Story:** Là một user, tôi muốn hệ thống tự động điều phối request của tôi qua các components phù hợp, để tôi nhận được response chính xác và hiệu quả.

#### Acceptance Criteria

1. WHEN a user request is received, THE Orchestrator SHALL route the request to the Parser
2. WHEN the Parser completes, THE Orchestrator SHALL route the parsed request to the Complexity_Analyzer
3. WHEN the Complexity_Analyzer returns "simple", THE Orchestrator SHALL route to the Direct_LLM
4. WHEN the Complexity_Analyzer returns "complex", THE Orchestrator SHALL route to the Planning_Agent
5. WHEN any component fails, THE Orchestrator SHALL return an error response with the failure reason

### Requirement 2: Request Parsing

**User Story:** Là một developer, tôi muốn user input được làm sạch và chuẩn hóa, để các components downstream xử lý dữ liệu nhất quán.

#### Acceptance Criteria

1. WHEN a raw user request is received, THE Parser SHALL remove leading and trailing whitespace
2. WHEN a raw user request is received, THE Parser SHALL normalize Unicode characters to NFC form
3. WHEN a raw user request is received, THE Parser SHALL preserve the original semantic meaning
4. THE Parser SHALL return a parsed request object containing the cleaned text and original text
5. WHEN the input is empty after cleaning, THE Parser SHALL return an error indicating invalid input

### Requirement 3: Complexity Analysis

**User Story:** Là một user, tôi muốn hệ thống tự động xác định request của tôi cần research hay không, để tôi nhận được response phù hợp mà không cần chỉ định rõ ràng.

#### Acceptance Criteria

1. WHEN a parsed request is received, THE Complexity_Analyzer SHALL analyze the request content
2. THE Complexity_Analyzer SHALL classify the request as "simple" when the request can be answered using general LLM knowledge
3. THE Complexity_Analyzer SHALL classify the request as "complex" when the request requires current information, specific facts, or external data
4. THE Complexity_Analyzer SHALL return a classification result containing the complexity level and reasoning
5. THE Complexity_Analyzer SHALL complete analysis within 2 seconds

### Requirement 4: Direct LLM Response

**User Story:** Là một user với simple request, tôi muốn nhận được response nhanh chóng từ LLM, để tôi không phải chờ đợi unnecessary research.

#### Acceptance Criteria

1. WHEN a simple request is received, THE Direct_LLM SHALL generate a response using the LLM API
2. THE Direct_LLM SHALL include the conversation history in the LLM context
3. WHEN the LLM API call succeeds, THE Direct_LLM SHALL return the generated response
4. WHEN the LLM API call fails, THE Direct_LLM SHALL return an error with retry information
5. THE Direct_LLM SHALL complete response generation within 10 seconds

### Requirement 5: Research Planning

**User Story:** Là một user với complex request, tôi muốn hệ thống tự động tạo research plan, để hệ thống có thể tìm kiếm thông tin cần thiết một cách có tổ chức.

#### Acceptance Criteria

1. WHEN a complex request is received, THE Planning_Agent SHALL generate a Research_Plan
2. THE Planning_Agent SHALL create between 1 and 5 Research_Tasks in the plan
3. FOR EACH Research_Task, THE Planning_Agent SHALL specify a search query and information goal
4. THE Planning_Agent SHALL order Research_Tasks from most important to least important
5. THE Planning_Agent SHALL return the Research_Plan within 5 seconds

### Requirement 6: Web Search and Information Extraction

**User Story:** Là một developer, tôi muốn có một research tool duy nhất thực hiện web search và extract information, để hệ thống đơn giản và dễ maintain.

#### Acceptance Criteria

1. WHEN a Research_Task is received, THE Research_Tool SHALL perform a web search using the task query
2. THE Research_Tool SHALL retrieve the top 3 search results
3. FOR EACH search result, THE Research_Tool SHALL extract the title, URL, and snippet
4. WHEN search results are retrieved, THE Research_Tool SHALL extract relevant information based on the task goal
5. THE Research_Tool SHALL return extracted information with source URLs
6. WHEN the web search API fails, THE Research_Tool SHALL return an error and allow the workflow to continue with available results
7. THE Research_Tool SHALL complete each research task within 10 seconds

### Requirement 7: Sequential Research Execution

**User Story:** Là một user, tôi muốn research tasks được thực thi tuần tự, để mỗi task có thể sử dụng kết quả từ các tasks trước đó.

#### Acceptance Criteria

1. WHEN a Research_Plan is received, THE Orchestrator SHALL execute Research_Tasks in the specified order
2. THE Orchestrator SHALL wait for each Research_Task to complete before starting the next task
3. THE Orchestrator SHALL collect results from each completed Research_Task
4. WHEN a Research_Task fails, THE Orchestrator SHALL continue with the next task and mark the failed task
5. THE Orchestrator SHALL pass all collected results to the Aggregator after all tasks complete

### Requirement 8: Research Results Aggregation

**User Story:** Là một user, tôi muốn research results được tổng hợp thành một knowledge base nhất quán, để response cuối cùng có thể sử dụng tất cả thông tin đã tìm được.

#### Acceptance Criteria

1. WHEN research results are received, THE Aggregator SHALL combine information from all Research_Tasks
2. THE Aggregator SHALL remove duplicate information across different research results
3. THE Aggregator SHALL organize information by topic or relevance
4. THE Aggregator SHALL preserve source URLs for each piece of information
5. THE Aggregator SHALL return an aggregated knowledge base within 3 seconds

### Requirement 9: Response Composition

**User Story:** Là một user, tôi muốn nhận được response được viết tốt dựa trên research results, để tôi có câu trả lời dễ hiểu và có nguồn tham khảo.

#### Acceptance Criteria

1. WHEN aggregated results are received, THE Response_Composer SHALL generate a response using the LLM API
2. THE Response_Composer SHALL include the original user request in the LLM context
3. THE Response_Composer SHALL include the aggregated knowledge base in the LLM context
4. THE Response_Composer SHALL instruct the LLM to cite sources using the provided URLs
5. THE Response_Composer SHALL return a well-structured response with inline citations
6. THE Response_Composer SHALL complete response generation within 15 seconds

### Requirement 10: Conversation History Storage

**User Story:** Là một user, tôi muốn conversation history được lưu trữ, để tôi có thể tham khảo lại các conversations trước đó và hệ thống có context cho các requests tiếp theo.

#### Acceptance Criteria

1. WHEN a user request is received, THE Orchestrator SHALL retrieve the conversation history from the database
2. WHEN a response is generated, THE Orchestrator SHALL save the request and response to the database
3. THE Orchestrator SHALL associate each conversation with a unique conversation ID
4. THE Orchestrator SHALL store the timestamp for each message
5. THE Orchestrator SHALL store the complexity classification and research plan if applicable

### Requirement 11: API Endpoint

**User Story:** Là một client application, tôi muốn gọi hệ thống qua REST API, để tôi có thể tích hợp AI Agent vào ứng dụng của mình.

#### Acceptance Criteria

1. THE System SHALL expose a POST endpoint at /api/chat for receiving user requests
2. WHEN a request is received at /api/chat, THE System SHALL accept JSON payload with "message" and optional "conversation_id" fields
3. WHEN processing completes, THE System SHALL return JSON response with "response", "conversation_id", "complexity", and optional "sources" fields
4. THE System SHALL return HTTP 200 for successful requests
5. WHEN an error occurs, THE System SHALL return appropriate HTTP error codes (400 for bad requests, 500 for server errors)
6. THE System SHALL include error messages in the response body for failed requests

### Requirement 12: Configuration Management

**User Story:** Là một developer, tôi muốn cấu hình hệ thống qua environment variables hoặc config file, để tôi có thể deploy hệ thống trong các môi trường khác nhau.

#### Acceptance Criteria

1. THE System SHALL read LLM API credentials from environment variables
2. THE System SHALL read web search API credentials from environment variables
3. THE System SHALL read database connection string from environment variables or use default SQLite path
4. THE System SHALL read timeout values for each component from configuration
5. THE System SHALL validate all required configuration values at startup and fail fast if missing

### Requirement 13: Error Handling and Resilience

**User Story:** Là một user, tôi muốn hệ thống xử lý errors gracefully, để tôi vẫn nhận được response hữu ích ngay cả khi một số components fail.

#### Acceptance Criteria

1. WHEN the LLM API fails, THE System SHALL retry up to 2 times with exponential backoff
2. WHEN the web search API fails for a Research_Task, THE System SHALL continue with remaining tasks
3. WHEN all Research_Tasks fail, THE System SHALL attempt to generate a response using only LLM knowledge
4. WHEN a component times out, THE System SHALL log the timeout and return a partial response if possible
5. THE System SHALL never expose internal error details or stack traces to the user

### Requirement 14: Logging and Observability

**User Story:** Là một developer, tôi muốn hệ thống log các events quan trọng, để tôi có thể debug issues và monitor performance.

#### Acceptance Criteria

1. THE System SHALL log each request with timestamp, conversation ID, and user message
2. THE System SHALL log complexity classification results with reasoning
3. THE System SHALL log each Research_Task execution with query, duration, and result status
4. THE System SHALL log all API calls to external services with duration and status
5. THE System SHALL log errors with full context including component name and input data
6. THE System SHALL support configurable log levels (DEBUG, INFO, WARNING, ERROR)
