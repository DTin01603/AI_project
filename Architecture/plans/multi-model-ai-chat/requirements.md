# Tài liệu Yêu cầu - Hệ thống Chat AI Đa Model

## Giới thiệu

Hệ thống Chat AI Đa Model là một nền tảng chat đơn giản cho phép người dùng tương tác với nhiều AI model khác nhau thông qua một API thống nhất. Đây là Phase 1 MVP, hệ thống sử dụng FastAPI 0.116+ làm backend framework, tích hợp LangChain 0.3+ để quản lý workflow, và hỗ trợ provider Google với các model như gemini-2.5-flash và gemini-2.5-flash-lite thông qua langchain-google-genai 4.0+.

Hệ thống được xây dựng dựa trên kiến trúc pipeline 5 bước: capture question → normalize request → invoke models with context → compose response → deliver response to user. Phase 1 tập trung vào non-streaming chat với một provider duy nhất, không bao gồm retrieval, vector DB, tool calling, hay multi-agent.

Hệ thống bao gồm hai phần chính:
- **Backend API**: FastAPI + LangChain xử lý logic chat
- **Frontend UI**: React application đơn giản để người dùng tương tác với chat API

## Bảng thuật ngữ

- **Chat_API**: API backend xử lý các yêu cầu chat từ người dùng
- **Model_Registry**: Danh sách các AI model được hỗ trợ bởi hệ thống
- **Provider**: Nhà cung cấp dịch vụ AI, trong Phase 1 chỉ hỗ trợ Google (Gemini)
- **Adapter**: Component kết nối với provider cụ thể (ví dụ: Google Gemini adapter)
- **Request_Normalizer**: Component chuẩn hóa yêu cầu đầu vào
- **Model_Invoker**: Component gọi AI model với context
- **Response_Composer**: Component tạo response thống nhất
- **LangChain**: Framework để xây dựng ứng dụng LLM
- **Pipeline**: Chuỗi xử lý tuần tự các bước từ request đến response
- **Locale**: Ngôn ngữ và vùng miền của người dùng (ví dụ: vi-VN, en-US)
- **Channel**: Kênh giao tiếp, trong Phase 1 chỉ hỗ trợ "web"
- **Finish_Reason**: Lý do model kết thúc sinh text (stop, length, error)
- **Constraints**: Các tham số điều khiển model như temperature và max_output_tokens

## Yêu cầu

### Yêu cầu 1: Tiếp nhận yêu cầu chat

**User Story:** Là một người dùng, tôi muốn gửi tin nhắn chat đến hệ thống với model AI mong muốn, để nhận được phản hồi từ AI model đó.

#### Tiêu chí chấp nhận

1. WHEN một yêu cầu POST được gửi đến endpoint /chat, THE Chat_API SHALL chấp nhận request với các trường: message, locale, channel, và model
2. THE Chat_API SHALL từ chối request nếu trường message trống hoặc chỉ chứa khoảng trắng sau khi trim
3. THE Chat_API SHALL từ chối request nếu trường message vượt quá 4000 ký tự
4. THE Chat_API SHALL chuẩn hóa newline trong message từ CRLF thành LF
5. THE Chat_API SHALL loại bỏ khoảng trắng thừa ở đầu và cuối message
6. THE Chat_API SHALL trả về HTTP 400 với error code BAD_REQUEST khi request không hợp lệ
7. THE Chat_API SHALL ghi lại timestamp received_at khi nhận request

### Yêu cầu 2: Chuẩn hóa yêu cầu đầu vào

**User Story:** Là một hệ thống backend, tôi muốn chuẩn hóa các yêu cầu đầu vào, để đảm bảo tính nhất quán trong xử lý.

#### Tiêu chí chấp nhận

1. WHEN Request_Normalizer nhận được raw request, THE Request_Normalizer SHALL tạo request_id từ header x-request-id nếu có
2. WHERE header x-request-id không tồn tại, THE Request_Normalizer SHALL sinh UUID mới làm request_id
3. WHERE trường locale không được cung cấp, THE Request_Normalizer SHALL sử dụng giá trị mặc định "vi-VN"
4. WHERE trường channel không được cung cấp, THE Request_Normalizer SHALL sử dụng giá trị mặc định "web"
5. THE Request_Normalizer SHALL từ chối request nếu channel khác "web" trong Phase 1
6. WHERE trường model không được cung cấp, THE Request_Normalizer SHALL sử dụng model mặc định từ settings
7. WHEN model được chỉ định không tồn tại trong Model_Registry, THE Request_Normalizer SHALL trả về error code UNSUPPORTED_MODEL
8. THE Request_Normalizer SHALL thêm constraints với temperature bằng 0.3 và max_output_tokens bằng 500
9. THE Request_Normalizer SHALL chuyển đổi locale thành định dạng chuẩn lowercase với dấu gạch ngang

### Yêu cầu 3: Quản lý danh sách AI model

**User Story:** Là một người dùng, tôi muốn xem danh sách các AI model có sẵn, để chọn model phù hợp với nhu cầu của mình.

#### Tiêu chí chấp nhận

1. WHEN một yêu cầu GET được gửi đến endpoint /models, THE Chat_API SHALL trả về danh sách tất cả model trong Model_Registry
2. THE Model_Registry SHALL chứa thông tin về provider, model name, và trạng thái available cho mỗi model
3. THE Model_Registry SHALL hỗ trợ các model Google Gemini bao gồm gemini-2.5-flash và gemini-2.5-flash-lite trong Phase 1
4. THE Chat_API SHALL trả về HTTP 200 với danh sách model ở định dạng JSON
5. WHERE một model bị lỗi hoặc không khả dụng, THE Model_Registry SHALL đánh dấu trạng thái available là false
6. THE Model_Registry SHALL phản ánh đúng trạng thái runtime của các model

### Yêu cầu 4: Gọi AI model với context

**User Story:** Là một hệ thống backend, tôi muốn gọi AI model được chỉ định với context phù hợp, để nhận được response chất lượng.

#### Tiêu chí chấp nhận

1. WHEN Model_Invoker nhận được normalized request, THE Model_Invoker SHALL xác định adapter tương ứng với model được chọn
2. THE Model_Invoker SHALL sử dụng LangChain để tạo kết nối với provider
3. THE Model_Invoker SHALL sử dụng prompt template với system message "Bạn là trợ lý AI hữu ích, trả lời ngắn gọn và đúng ngôn ngữ user."
4. WHEN gọi model, THE Model_Invoker SHALL truyền message và locale làm context với constraints từ normalized request
5. THE Model_Invoker SHALL thực hiện non-streaming invocation trong Phase 1
6. IF model trả về lỗi hoặc timeout, THEN THE Model_Invoker SHALL trả về error code MODEL_ERROR
7. IF model trả về response rỗng, THEN THE Model_Invoker SHALL trả về error code MODEL_EMPTY_OUTPUT
8. THE Model_Invoker SHALL ghi lại finish_reason từ model response
9. WHEN model response thành công, THE Model_Invoker SHALL trả về text output, metadata, và usage tokens bao gồm input_tokens và output_tokens

### Yêu cầu 5: Tạo response thống nhất

**User Story:** Là một frontend developer, tôi muốn nhận response theo format nhất quán, để dễ dàng xử lý và hiển thị cho người dùng.

#### Tiêu chí chấp nhận

1. WHEN xử lý thành công, THE Response_Composer SHALL tạo response với các trường: request_id, status="ok", answer, error=null, và meta
2. WHEN xử lý thất bại, THE Response_Composer SHALL tạo response với các trường: request_id, status="error", answer với thông báo thân thiện, error với code và message, và meta với các giá trị null
3. THE Response_Composer SHALL bao gồm provider, model, và finish_reason trong trường meta khi thành công
4. THE Response_Composer SHALL truncate answer nếu vượt quá 3000 ký tự
5. WHERE xảy ra lỗi MODEL_ERROR, THE Response_Composer SHALL trả về answer "Xin lỗi, hệ thống đang bận. Bạn thử lại giúp mình."
6. WHERE xảy ra lỗi UNSUPPORTED_MODEL, THE Response_Composer SHALL trả về answer "Model bạn chọn không được hỗ trợ. Vui lòng chọn model khác."
7. WHERE xảy ra lỗi BAD_REQUEST, THE Response_Composer SHALL trả về answer với mô tả lỗi cụ thể
8. THE Response_Composer SHALL không trả debug information hoặc raw stacktrace ra client

### Yêu cầu 6: Xử lý lỗi và HTTP status mapping

**User Story:** Là một hệ thống backend, tôi muốn xử lý lỗi một cách nhất quán và trả về HTTP status code phù hợp, để client có thể xử lý lỗi đúng cách.

#### Tiêu chí chấp nhận

1. WHEN error code là BAD_REQUEST, THE Chat_API SHALL trả về HTTP status 400
2. WHEN error code là UNSUPPORTED_MODEL, THE Chat_API SHALL trả về HTTP status 400
3. WHEN error code là MODEL_ERROR, THE Chat_API SHALL trả về HTTP status 502
4. WHEN error code là MODEL_EMPTY_OUTPUT, THE Chat_API SHALL trả về HTTP status 502
5. WHEN error code là INTERNAL_ERROR, THE Chat_API SHALL trả về HTTP status 500
6. THE Chat_API SHALL không fallback sang model khác khi model hiện tại lỗi trong Phase 1
7. THE Chat_API SHALL trả về response với Content-Type application/json
8. THE Chat_API SHALL ghi log request_id, HTTP status code, và latency cho mỗi request

### Yêu cầu 7: Health check và readiness

**User Story:** Là một DevOps engineer, tôi muốn kiểm tra trạng thái của service, để đảm bảo hệ thống hoạt động bình thường.

#### Tiêu chí chấp nhận

1. WHEN một yêu cầu GET được gửi đến endpoint /health, THE Chat_API SHALL trả về HTTP 200 với status "ok"
2. THE Chat_API SHALL trả về thời gian uptime trong response của /health
3. WHEN một yêu cầu GET được gửi đến endpoint /ready, THE Chat_API SHALL kiểm tra config và dependency của hệ thống
4. THE Chat_API SHALL kiểm tra Model_Registry có ít nhất một model khả dụng trong endpoint /ready
5. THE Chat_API SHALL không ping provider thật trong endpoint /ready để tránh tăng latency
6. IF không có model nào khả dụng trong registry, THEN THE Chat_API SHALL trả về HTTP 503 cho endpoint /ready
7. THE Chat_API SHALL trả về số lượng model khả dụng trong response của /ready

### Yêu cầu 8: Cấu hình provider linh hoạt

**User Story:** Là một developer, tôi muốn cấu hình các provider thông qua environment variables, để dễ dàng thay đổi cấu hình mà không cần sửa code.

#### Tiêu chí chấp nhận

1. THE Chat_API SHALL đọc API key của provider Google từ environment variable GOOGLE_API_KEY
2. THE Chat_API SHALL validate API key format khi khởi động
3. IF API key không hợp lệ hoặc thiếu, THEN THE Chat_API SHALL ghi log warning và không thêm model của provider đó vào Model_Registry
4. WHERE provider không có API key, THE Model_Registry SHALL không bao gồm các model của provider đó
5. THE Chat_API SHALL hỗ trợ cấu hình timeout cho provider thông qua environment variables
6. THE Chat_API SHALL hỗ trợ cấu hình default model thông qua environment variable
7. THE Chat_API SHALL hỗ trợ cấu hình constraints mặc định như temperature và max_output_tokens thông qua environment variables

### Yêu cầu 9: Logging và monitoring

**User Story:** Là một developer, tôi muốn có logging chi tiết cho mỗi request, để dễ dàng debug và monitor hệ thống.

#### Tiêu chí chấp nhận

1. THE Pipeline SHALL ghi log tại mỗi bước với request_id
2. THE Pipeline SHALL ghi log thời gian xử lý của mỗi bước
3. WHEN gọi model, THE Pipeline SHALL ghi log provider, model name, và input length
4. WHEN nhận response từ model, THE Pipeline SHALL ghi log output length và finish_reason
5. IF xảy ra lỗi, THEN THE Pipeline SHALL ghi log error code và error message
6. THE Pipeline SHALL sử dụng structured logging ở định dạng JSON để dễ dàng parse và analyze
7. THE Pipeline SHALL không ghi log full message content để tránh log sensitive information
8. THE Pipeline SHALL không ghi log API key hoặc secrets trong bất kỳ trường hợp nào

### Yêu cầu 10: Validation và security

**User Story:** Là một security engineer, tôi muốn đảm bảo hệ thống validate input và bảo vệ khỏi các cuộc tấn công, để hệ thống an toàn và ổn định.

#### Tiêu chí chấp nhận

1. THE Chat_API SHALL validate tất cả input fields theo Pydantic schema
2. THE Chat_API SHALL sanitize message để loại bỏ các ký tự đặc biệt nguy hiểm
3. THE Chat_API SHALL không expose API key hoặc sensitive information trong response
4. THE Chat_API SHALL không ghi log API key hoặc secrets trong log files
5. THE Chat_API SHALL sử dụng HTTPS cho tất cả API endpoints trong production
6. THE Chat_API SHALL validate message type là string trước khi xử lý
7. THE Chat_API SHALL validate locale format trước khi sử dụng

### Yêu cầu 11: Testing và quality assurance

**User Story:** Là một developer, tôi muốn có test coverage cao cho hệ thống, để đảm bảo chất lượng code và tránh regression bugs.

#### Tiêu chí chấp nhận

1. THE Pipeline SHALL có unit test cho service captureQuestion với các test case: message hợp lệ với trim, message rỗng, message quá dài, sai kiểu dữ liệu, và normalize newline từ CRLF sang LF
2. THE Pipeline SHALL có unit test cho service normalizeRequest với các test case: default locale vi-VN, default channel web, default model từ settings, giữ nguyên model hợp lệ, reject channel khác web, và reject model không hỗ trợ
3. THE Pipeline SHALL có unit test cho service invokeModelsWithContext với các test case: happy path với adapter mock, transient error trả MODEL_ERROR, provider timeout trả MODEL_ERROR, empty output trả MODEL_EMPTY_OUTPUT, và unsupported model trả UNSUPPORTED_MODEL
4. THE Pipeline SHALL có unit test cho service composeResponse với các test case: success response đúng schema, error response đúng schema, luôn có request_id, và truncate answer hoạt động đúng khi vượt quá 3000 ký tự
5. THE Pipeline SHALL có unit test cho service deliverResponseToUser với các test case: status ok trả HTTP 200, BAD_REQUEST và UNSUPPORTED_MODEL trả HTTP 400, MODEL_ERROR và MODEL_EMPTY_OUTPUT trả HTTP 502, INTERNAL_ERROR trả HTTP 500
6. THE Chat_API SHALL có integration test cho endpoint /chat với các scenario: success case, model error, invalid input, và unsupported model
7. THE Chat_API SHALL có integration test cho endpoint /models để verify danh sách model trả về đúng
8. THE Chat_API SHALL có integration test cho endpoint /health và /ready để verify semantics đúng
9. THE Model_Invoker SHALL mock external API calls trong unit test để tránh phụ thuộc vào provider thật
10. THE Test Suite SHALL đạt ít nhất 80% code coverage
11. THE Test Suite SHALL bao gồm property-based test cho Request_Normalizer để kiểm tra round-trip normalization

### Yêu cầu 12: Frontend UI với React

**User Story:** Là một người dùng, tôi muốn có giao diện web đơn giản để chat với AI, để dễ dàng gửi tin nhắn và nhận phản hồi mà không cần dùng API trực tiếp.

#### Tiêu chí chấp nhận

1. THE Frontend SHALL được xây dựng bằng React với Vite
2. THE Frontend SHALL có giao diện chat đơn giản với message input và chat history display
3. THE Frontend SHALL cho phép người dùng chọn model từ danh sách models có sẵn
4. WHEN người dùng gửi message, THE Frontend SHALL gọi POST /chat endpoint với message và model đã chọn
5. THE Frontend SHALL hiển thị loading indicator khi đang chờ response từ API
6. WHEN nhận được response thành công, THE Frontend SHALL hiển thị answer trong chat history
7. WHEN nhận được error response, THE Frontend SHALL hiển thị error message thân thiện cho người dùng
8. THE Frontend SHALL fetch danh sách models từ GET /models endpoint khi khởi động
9. THE Frontend SHALL sử dụng CORS-enabled API calls để kết nối với backend
10. THE Frontend SHALL có responsive design hoạt động tốt trên desktop và mobile
11. THE Frontend SHALL lưu chat history trong component state (không persist khi reload)
12. THE Frontend SHALL validate message không rỗng trước khi gửi request
