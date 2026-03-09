from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from models.request import ChatRequest
from research_agent.config import get_checkpointer
from research_agent.edges import complexity_edge, router_edge
from research_agent.nodes import (
    citation_node,
    complexity_node,
    current_date_node,
    direct_llm_node,
    entry_node,
    persist_conversation_node,
    planning_node,
    research_node,
    router_node,
    simple_llm_node,
    synthesis_node,
)
from research_agent.state import AgentState


class ResearchAgentGraph:
    """LangGraph runtime for research agent v2."""

    def __init__(self, dependencies: dict[str, Any]) -> None:
        self.dependencies = dependencies
        self._compiled_graph: Any | None = None
        self._compile_lock = asyncio.Lock()
        self._checkpointer_context: Any | None = None

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def _research_node_wrapper(state: AgentState):
            return await research_node(state, self.dependencies["research_tool"])

        graph.add_node("entry", entry_node)
        graph.add_node("complexity", lambda state: complexity_node(state, self.dependencies["analyzer"]))
        graph.add_node("router", router_node)
        graph.add_node("planning", lambda state: planning_node(state, self.dependencies["planning_agent"]))
        graph.add_node("research", _research_node_wrapper)
        graph.add_node(
            "synthesis",
            lambda state: synthesis_node(
                state,
                self.dependencies["aggregator"],
                self.dependencies["response_composer"],
                self.dependencies["direct_llm"],
            ),
        )
        graph.add_node("citation", citation_node)
        graph.add_node(
            "simple_llm",
            lambda state: simple_llm_node(state, self.dependencies["direct_llm"], self.dependencies["database"]),
        )
        graph.add_node(
            "direct_llm",
            lambda state: direct_llm_node(state, self.dependencies["direct_llm"], self.dependencies["database"]),
        )
        graph.add_node("current_date", current_date_node)
        graph.add_node("persist", lambda state: persist_conversation_node(state, self.dependencies["database"]))

        graph.set_entry_point("entry")
        graph.add_edge("entry", "complexity")
        graph.add_conditional_edges("complexity", complexity_edge, {"simple": "simple_llm", "complex": "router"})
        graph.add_conditional_edges(
            "router",
            router_edge,
            {
                "research_intent": "planning",
                "current_date": "current_date",
                "direct_llm": "direct_llm",
            },
        )
        graph.add_edge("planning", "research")
        graph.add_edge("research", "synthesis")
        graph.add_edge("synthesis", "citation")

        graph.add_edge("simple_llm", "persist")
        graph.add_edge("current_date", "persist")
        graph.add_edge("direct_llm", "persist")
        graph.add_edge("citation", "persist")
        graph.add_edge("persist", END)
        return graph

    async def _compile_graph(self) -> Any:
        builder = self._build_graph()
        checkpointer = await get_checkpointer()
        if hasattr(checkpointer, "__aenter__") and hasattr(checkpointer, "__aexit__"):
            self._checkpointer_context = checkpointer
            checkpointer = await checkpointer.__aenter__()
        return builder.compile(checkpointer=checkpointer)

    async def _ensure_compiled(self) -> Any:
        if self._compiled_graph is not None:
            return self._compiled_graph

        async with self._compile_lock:
            if self._compiled_graph is None:
                self._compiled_graph = await self._compile_graph()
        return self._compiled_graph

    @staticmethod
    def _initial_state(payload: ChatRequest, request_id: str | None = None) -> AgentState:
        conversation_id = payload.conversation_id or str(uuid4())
        return {
            "messages": [HumanMessage(content=payload.message)],
            "query_type": "simple",
            "research_plan": [],
            "research_results": [],
            "citations": [],
            "fallback_used": False,
            "execution_metadata": {
                "conversation_id": conversation_id,
                "request_id": request_id or str(uuid4()),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "model": payload.model,
                "node_timings": {},
            },
        }

    @staticmethod
    def _build_run_config(
        *,
        payload: ChatRequest,
        request_id: str,
        conversation_id: str,
        run_name: str,
        stream: bool,
    ) -> dict[str, Any]:
        model_name = str(payload.model or "").strip()
        tags = [
            "research-agent-v2",
            "langgraph",
            "api-v2",
            "mode:stream" if stream else "mode:non-stream",
        ]
        if model_name:
            tags.append(f"model:{model_name}")

        metadata = {
            "request_id": request_id,
            "conversation_id": conversation_id,
            "endpoint": "/api/v2/chat",
            "stream": stream,
            "locale": payload.locale,
            "channel": payload.channel,
            "model": model_name,
        }

        return {
            "run_name": run_name,
            "tags": tags,
            "metadata": metadata,
            "configurable": {"thread_id": conversation_id},
        }

    async def ainvoke(self, payload: ChatRequest, request_id: str | None = None) -> AgentState:
        graph = await self._ensure_compiled()
        initial_state = self._initial_state(payload, request_id)
        effective_request_id = str(initial_state["execution_metadata"]["request_id"])
        thread_id = str(initial_state["execution_metadata"]["conversation_id"])
        run_config = self._build_run_config(
            payload=payload,
            request_id=effective_request_id,
            conversation_id=thread_id,
            run_name="research_agent_v2.invoke",
            stream=False,
        )
        result = await graph.ainvoke(initial_state, config=run_config)
        return result

    async def astream(self, payload: ChatRequest, request_id: str | None = None):
        graph = await self._ensure_compiled()
        initial_state = self._initial_state(payload, request_id)
        thread_id = str(initial_state["execution_metadata"]["conversation_id"])
        effective_request_id = str(initial_state["execution_metadata"]["request_id"])
        run_config = self._build_run_config(
            payload=payload,
            request_id=effective_request_id,
            conversation_id=thread_id,
            run_name="research_agent_v2.stream",
            stream=True,
        )
        async for update in graph.astream(
            initial_state,
            config=run_config,
            stream_mode="updates",
        ):
            yield update
