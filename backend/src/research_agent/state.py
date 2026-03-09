from typing import Any, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, NotRequired, TypedDict

from research_agent.models import ResearchResult, ResearchTask


class AgentState(TypedDict):
    """Centralized graph state shared across all LangGraph nodes.

    Fields:
        messages: Conversation history accumulated with LangGraph `add_messages` reducer.
        query_type: Routing classifier for execution path selection.
        complexity_result: Raw complexity analysis payload.
        research_plan: Ordered list of research tasks created by planning node.
        research_results: Collected outputs from research execution.
        final_answer: Final answer text generated for the user.
        citations: Source URLs or references appended to the final answer.
        execution_metadata: Timing, tracing, and runtime diagnostics data.
        error: Optional error message when any node fails.
        fallback_used: Indicates if fallback strategy was used during execution.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    query_type: NotRequired[Literal["simple", "complex", "research_intent", "current_date", "direct_llm"]]
    complexity_result: NotRequired[dict[str, Any] | None]
    research_plan: NotRequired[list[ResearchTask]]
    research_results: NotRequired[list[ResearchResult]]
    final_answer: NotRequired[str]
    citations: NotRequired[list[str]]
    execution_metadata: NotRequired[dict[str, Any]]
    error: NotRequired[str | None]
    fallback_used: NotRequired[bool]
