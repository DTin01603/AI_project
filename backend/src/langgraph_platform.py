from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Ensure local imports like `from api.deps ...` resolve in platform runtime.
SRC_ROOT = Path(__file__).resolve().parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from api.deps import get_container
from agent.graph.agent_graph import AgentGraph

logger = logging.getLogger("langgraph.platform")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def create_graph() -> Any:
    """Build a compiled graph target for LangGraph Platform deployment."""
    deps = get_container().graph_dependencies()
    runner = AgentGraph(
        dependencies={
            "retrieval_node": deps.retrieval_node,
            "rag_subgraph": deps.rag_subgraph,
            "aggregator": deps.aggregator,
            "conversation_service": deps.conversation_service,
        }
    )

    # Platform runtime manages state externally; compile graph without local checkpointer.
    graph_builder = runner._build_graph()
    compiled = graph_builder.compile()
    logger.info("LangGraph Platform graph initialized")
    return compiled


graph = create_graph()
