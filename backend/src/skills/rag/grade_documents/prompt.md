{% block user %}
Bạn là bộ đánh giá tài liệu. Đánh giá từng đoạn văn bên dưới có chứa thông tin liên quan để trả lời câu hỏi không.

Câu hỏi: {{ question }}

Tài liệu:
{{ docs_text }}

Trả lời CHÍNH XÁC theo định dạng JSON (không thêm bất kỳ văn bản nào khác):
{"grades": [{"index": 1, "relevant": true}, {"index": 2, "relevant": false}]}
{% endblock %}
