"""LangGraph node implementations for the agent.

Intentionally empty: each node module is imported directly by callers
(e.g. `from agent.nodes.citation_node import citation_node`) so that
importing one node does not pull in skills + LLM SDKs transitively. This
matters for unit tests that exercise a single node in environments where
optional vendor SDKs are not installed.
"""
