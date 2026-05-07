{% block user %}
Đánh giá câu trả lời AI theo hai tiêu chí:
1. Có dựa trên tài liệu được cung cấp (không bịa đặt thông tin ngoài tài liệu)
2. Có trả lời đúng câu hỏi người dùng

Câu hỏi: {{ question }}

Tài liệu tham khảo:
{{ context }}

Câu trả lời AI: {{ generation }}

Trả lời CHÍNH XÁC theo JSON:
{"grade": "grounded_and_useful", "reason": "lý do ngắn gọn"}

Giá trị hợp lệ cho "grade": "grounded_and_useful" | "hallucination" | "not_useful".
{% endblock %}
