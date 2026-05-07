{% block user %}
Extract concise, relevant information for the goal from search results.
Use Vietnamese if goal is Vietnamese. Return plain text only.

Goal: {{ goal }}
SearchResults(JSON): {{ search_results_json }}
{% endblock %}
