from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from api.schemas.chat import ChatRequest
from agent.config import get_checkpointer
from agent.edges import intent_edge
from agent.nodes.citation_node import citation_node
from agent.nodes.current_date_node import current_date_node
from agent.nodes.entry_node import entry_node
from agent.nodes.intent_node import intent_node
from agent.nodes.llm_node import llm_node
from agent.nodes.persist_conversation_node import persist_conversation_node
from agent.nodes.planning_node import planning_node
from agent.nodes.research_node import research_node
from agent.nodes.synthesis_node import synthesis_node
from agent.state import AgentState


class ResearchAgentGraph:
    """LangGraph runtime for research agent v2."""

    def __init__(self, dependencies: dict[str, Any]) -> None:
        self.dependencies = dependencies
        self._compiled_graph: Any | None = None
        self._compile_lock = asyncio.Lock()
        self._checkpointer_context: Any | None = None

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        graph.add_node("entry", entry_node)
        graph.add_node("intent", intent_node)
        graph.add_node("planning", planning_node)
        graph.add_node("research", research_node)
        graph.add_node(
            "synthesis",
            lambda state: synthesis_node(state, self.dependencies["aggregator"]),
        )
        graph.add_node("citation", citation_node)
        graph.add_node(
            "local_rag",
            lambda state: llm_node(
                state,
                self.dependencies["database"],
                node_name="local_rag",
                fallback_answer="Xin lỗi, không tìm thấy thông tin phù hợp trong tài liệu.",
                retrieval_node=self.dependencies.get("retrieval_node"),
                rag_subgraph=self.dependencies.get("rag_subgraph"),
            ),
        )
        graph.add_node(
            "direct_answer",
            lambda state: llm_node(
                state,
                self.dependencies["database"],
                node_name="direct_answer",
                fallback_answer="Xin lỗi, mình chưa thể tạo phản hồi lúc này.",
                retrieval_node=None,
                rag_subgraph=None,
            ),
        )
        graph.add_node("current_date", current_date_node)
        graph.add_node(
            "persist",
            lambda state: persist_conversation_node(
                state, self.dependencies["conversation_service"]
            ),
        )

        graph.set_entry_point("entry")
        graph.add_edge("entry", "intent")
        graph.add_conditional_edges(
            "intent",
            intent_edge,
            {
                "direct_answer": "direct_answer",
                "local_rag": "local_rag",
                "web_search": "planning",
                "current_date": "current_date",
            },
        )
        graph.add_edge("planning", "research")
        graph.add_edge("research", "synthesis")
        graph.add_edge("synthesis", "citation")

        graph.add_edge("direct_answer", "persist")
        graph.add_edge("local_rag", "persist")
        graph.add_edge("current_date", "persist")
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
