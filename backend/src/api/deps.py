from dataclasses import dataclass
from functools import lru_cache

from config import settings
from research_agent.aggregator import Aggregator
from research_agent.complexity_analyzer import ComplexityAnalyzer
from research_agent.database import Database
from research_agent.direct_llm import DirectLLM
from research_agent.planning_agent import PlanningAgent
from research_agent.research_tool import ResearchTool
from research_agent.response_composer import ResponseComposer
from research_agent.graph import ResearchAgentGraph


@dataclass
class GraphDependencies:
    analyzer: ComplexityAnalyzer
    direct_llm: DirectLLM
    database: Database
    research_tool: ResearchTool
    planning_agent: PlanningAgent
    aggregator: Aggregator
    response_composer: ResponseComposer


def _build_orchestrator_dependencies() -> GraphDependencies:
    # Compose concrete dependency graph for orchestrators.
    database = Database(db_path="./data/conversations.db")
    return GraphDependencies(
        analyzer=ComplexityAnalyzer(model=settings.default_model),
        direct_llm=DirectLLM(model=settings.default_model),
        database=database,
        research_tool=ResearchTool(
            tavily_api_key=settings.tavily_api_key,
            llm_api_key=settings.active_llm_api_key(settings.default_model),
            model=settings.default_model,
        ),
        planning_agent=PlanningAgent(model=settings.default_model),
        aggregator=Aggregator(),
        response_composer=ResponseComposer(model=settings.default_model),
    )


@lru_cache
def get_research_agent_graph() -> ResearchAgentGraph:
    # Provide singleton LangGraph v2 graph with shared dependencies.
    dependencies = _build_orchestrator_dependencies()
    return ResearchAgentGraph(
        dependencies={
            "analyzer": dependencies.analyzer,
            "direct_llm": dependencies.direct_llm,
            "database": dependencies.database,
            "research_tool": dependencies.research_tool,
            "planning_agent": dependencies.planning_agent,
            "aggregator": dependencies.aggregator,
            "response_composer": dependencies.response_composer,
        }
    )

__all__ = [
    "get_research_agent_graph",
]
