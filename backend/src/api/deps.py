from dataclasses import dataclass
from functools import lru_cache

from config import settings
from rag.config import load_config
from rag.conversation_indexer import ConversationIndexer
from rag.embedding import SentenceTransformerEmbedding
from rag.fts_engine import FTSEngine
from rag.retrieval_node import RetrievalNode
from rag.subgraph import RAGSubgraph
from rag.vector_store import ChromaVectorStore, build_conversation_collection_name
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
    database: ConversationIndexer  # Changed from Database to ConversationIndexer
    retrieval_node: RetrievalNode
    rag_subgraph: RAGSubgraph
    research_tool: ResearchTool
    planning_agent: PlanningAgent
    aggregator: Aggregator
    response_composer: ResponseComposer


def _build_orchestrator_dependencies() -> GraphDependencies:
    # Compose concrete dependency graph for orchestrators.
    rag_config = load_config()
    
    # Create base database
    base_database = Database(db_path="./data/conversations.db")
    
    # Create embedding model and vector store for conversations
    embedding_model = SentenceTransformerEmbedding(
        model_name=rag_config.embedding_model,
        dimension=rag_config.embedding_dimension,
        batch_size=rag_config.batch_size,
        cache_size=rag_config.cache_size,
    )
    
    conversation_vector_store = ChromaVectorStore(
        persist_directory=rag_config.vector_store_path,
        collection_name=build_conversation_collection_name(base_database.db_path),
    )
    
    # Wrap database with ConversationIndexer for realtime embedding
    database = ConversationIndexer(
        database=base_database,
        embedding_model=embedding_model,
        vector_store=conversation_vector_store,
        chunk_size=rag_config.chunk_size,
    )
    
    retrieval_node = RetrievalNode(
        fts_engine=FTSEngine(db_path=base_database.db_path),
        config=rag_config,
    )

    direct_llm = DirectLLM(model=settings.default_model)
    rag_subgraph = RAGSubgraph(
        retrieval_node=retrieval_node,
        direct_llm=direct_llm,
    )

    return GraphDependencies(
        analyzer=ComplexityAnalyzer(model=settings.default_model),
        direct_llm=direct_llm,
        database=database,
        retrieval_node=retrieval_node,
        rag_subgraph=rag_subgraph,
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
            "retrieval_node": dependencies.retrieval_node,
            "rag_subgraph": dependencies.rag_subgraph,
            "research_tool": dependencies.research_tool,
            "planning_agent": dependencies.planning_agent,
            "aggregator": dependencies.aggregator,
            "response_composer": dependencies.response_composer,
        }
    )

__all__ = [
    "get_research_agent_graph",
]
