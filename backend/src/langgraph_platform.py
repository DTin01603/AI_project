from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Ensure local imports like `from api.deps ...` resolve in platform runtime.
SRC_ROOT = Path(__file__).resolve().parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from api.deps import _build_orchestrator_dependencies
from research_agent.graph.research_agent_graph import ResearchAgentGraph

logger = logging.getLogger("langgraph.platform")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def create_graph() -> Any:
    """Build a compiled graph target for LangGraph Platform deployment."""
    deps = _build_orchestrator_dependencies()
    runner = ResearchAgentGraph(
        dependencies={
            "analyzer": deps.analyzer,
            "direct_llm": deps.direct_llm,
            "database": deps.database,
            "research_tool": deps.research_tool,
            "planning_agent": deps.planning_agent,
            "aggregator": deps.aggregator,
            "response_composer": deps.response_composer,
        }
    )

    # Platform runtime manages state externally; compile graph without local checkpointer.
    graph_builder = runner._build_graph()
    compiled = graph_builder.compile()
    logger.info("LangGraph Platform graph initialized")
    return compiled


graph = create_graph()
