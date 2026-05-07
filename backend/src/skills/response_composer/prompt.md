{% block user %}
Compose a clear final answer for the user question based only on the given knowledge base.
If data is incomplete, mention uncertainty briefly. Use Vietnamese when appropriate.

Question: {{ question }}
KnowledgeBase:
{{ knowledge_base }}
{% endblock %}
