{% block user %}
Bạn là chuyên gia tối ưu hoá truy vấn tìm kiếm tài liệu.

Nhiệm vụ: Viết lại câu hỏi hiện tại thành một **câu hỏi standalone** (tự đứng độc lập), có đầy đủ ngữ cảnh cần thiết, để dùng làm truy vấn tìm kiếm trong cơ sở dữ liệu tài liệu.

Quy tắc:
- Nếu câu hỏi hiện tại có đại từ hoặc tham chiếu mơ hồ ("đó", "này", "họ", "những quốc gia đó", "nó", "vấn đề trên", v.v.), hãy thay bằng danh từ cụ thể lấy từ lịch sử hội thoại.
- Giữ nguyên ngôn ngữ gốc (tiếng Việt).
- Bổ sung từ khoá quan trọng từ lịch sử hội thoại nếu giúp việc tìm kiếm chính xác hơn.
- Không đặt câu hỏi ngược cho người dùng, không xin làm rõ — phải tự suy luận từ lịch sử.
- Chỉ trả về **một câu hỏi duy nhất**, không giải thích, không đánh số, không tiền tố.

=== LỊCH SỬ HỘI THOẠI ===
{% if history %}
{% for turn in history[-6:] %}
{% if turn.role == 'user' %}Người dùng: {{ turn.content }}
{% elif turn.role == 'assistant' %}Trợ lý: {{ turn.content }}
{% endif %}
{% endfor %}
{% else %}
(không có lịch sử)
{% endif %}

=== CÂU HỎI HIỆN TẠI ===
{{ question }}

Lần thử viết lại: {{ retry_count }}

Câu hỏi đã viết lại (standalone):
{% endblock %}
