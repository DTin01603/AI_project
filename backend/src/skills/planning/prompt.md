{% block user %}
Create a concise research plan in JSON array format only.
Each item must have keys: order (int), query (string), goal (string).
Plan size must be between 1 and 5 tasks.

Question: {{ question }}
{% endblock %}
