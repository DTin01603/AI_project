"""Application dependency container.

`AppContainer` is the single composition root. It owns the SQLite connection
factory, runs migrations once, and lazily wires repositories, services, the
RAG retrieval stack, and the LangGraph runtime. Routers ask the container for
a service via the FastAPI `Depends` returned by `get_*_service()`.

The container itself is cached (`@lru_cache`) so the whole app shares one
factory + one migration run, matching the historic behaviour without changing
the DI pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from config import settings
from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from rag.config import RAGConfig, load_config
from rag.conversation_indexer import ConversationIndexer
from rag.embedding import SentenceTransformerEmbedding
from rag.fts_engine import FTSEngine
from agent.nodes.retrieval_node import RetrievalNode
from rag.vector_store import ChromaVectorStore, build_conversation_collection_name
from repositories.citation_repo import CitationRepository
from repositories.conversation_repo import ConversationRepository
from repositories.document_repo import DocumentRepository
from repositories.message_repo import MessageRepository
from services.research_aggregation_service import ResearchAggregationService
from agent.database import Database
from services.citation_service import CitationService
from services.conversation_indexing_service import ConversationIndexingService
from services.conversation_service import ConversationService
from services.retrieval_service import RetrievalService

if TYPE_CHECKING:
    from agent.subgraph import RAGSubgraph
    from agent.graph import AgentGraph

DEFAULT_DB_PATH = "./data/conversations.db"
_SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"


@dataclass
class GraphDependencies:
    database: ConversationIndexer
    retrieval_node: RetrievalNode
    rag_subgraph: "RAGSubgraph"
    aggregator: ResearchAggregationService
    conversation_service: ConversationService


class AppContainer:
    """Single composition root: factory + migrations + repos + services + graph."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.factory = SQLiteConnectionFactory(db_path)
        run_migrations(self.factory)

        # Repositories — one per table.
        self.conversation_repo = ConversationRepository(self.factory)
        self.message_repo = MessageRepository(self.factory)
        self.citation_repo = CitationRepository(self.factory)
        self.document_repo = DocumentRepository(self.factory)

        # Services — orchestrate repos.
        self.conversation_service = ConversationService(
            self.conversation_repo, self.message_repo, self.factory
        )
        self.citation_service = CitationService(self.citation_repo, self.factory)

        # Lazily-built RAG / agent components below.
        self._skills_ready = False

    # ------------------------------------------------------------------ RAG

    @cached_property
    def rag_config(self) -> RAGConfig:
        return load_config()

    @cached_property
    def embedding_model(self) -> SentenceTransformerEmbedding:
        return SentenceTransformerEmbedding(
            model_name=self.rag_config.embedding_model,
            dimension=self.rag_config.embedding_dimension,
            batch_size=self.rag_config.batch_size,
            cache_size=self.rag_config.cache_size,
        )

    @cached_property
    def conversation_vector_store(self) -> ChromaVectorStore:
        return ChromaVectorStore(
            persist_directory=self.rag_config.vector_store_path,
            collection_name=build_conversation_collection_name(self.db_path),
        )

    @cached_property
    def conversation_indexing_service(self) -> ConversationIndexingService:
        return ConversationIndexingService(
            conversation_service=self.conversation_service,
            message_repo=self.message_repo,
            embedding_model=self.embedding_model,
            vector_store=self.conversation_vector_store,
            chunk_size=self.rag_config.chunk_size,
        )

    # The legacy ConversationIndexer shim still wraps the indexing service so
    # that LangGraph nodes (llm_node, common.run_llm_node) keep their existing
    # `Database`-shaped dependency. It will be removed in step 7b.
    @cached_property
    def conversation_database_shim(self) -> ConversationIndexer:
        base_database = Database(db_path=self.db_path)
        return ConversationIndexer(
            database=base_database,
            embedding_model=self.embedding_model,
            vector_store=self.conversation_vector_store,
            chunk_size=self.rag_config.chunk_size,
        )

    @cached_property
    def fts_engine(self) -> FTSEngine:
        return FTSEngine(db_path=self.db_path)

    @cached_property
    def retrieval_service(self) -> RetrievalService:
        return RetrievalService(
            fts_engine=self.fts_engine,
            config=self.rag_config,
            embedding_model=self.embedding_model,
            vector_store=self.conversation_vector_store,
            connection_factory=self.factory,
        )

    @cached_property
    def retrieval_node(self) -> RetrievalNode:
        return RetrievalNode(service=self.retrieval_service)

    @cached_property
    def rag_subgraph(self) -> "RAGSubgraph":
        from agent.subgraph import RAGSubgraph

        return RAGSubgraph(retrieval_node=self.retrieval_node)

    # ------------------------------------------------------------------ agent

    def graph_dependencies(self) -> GraphDependencies:
        return GraphDependencies(
            database=self.conversation_database_shim,
            retrieval_node=self.retrieval_node,
            rag_subgraph=self.rag_subgraph,
            aggregator=ResearchAggregationService(),
            conversation_service=self.conversation_service,
        )

    @cached_property
    def agent_graph(self) -> "AgentGraph":
        from agent.graph import AgentGraph

        deps = self.graph_dependencies()
        self._ensure_skills_discovered(retrieval_service=self.retrieval_service)
        return AgentGraph(
            dependencies={
                "database": deps.database,
                "retrieval_node": deps.retrieval_node,
                "rag_subgraph": deps.rag_subgraph,
                "aggregator": deps.aggregator,
                "conversation_service": deps.conversation_service,
            }
        )

    # ------------------------------------------------------------------ skills

    def _ensure_skills_discovered(self, retrieval_service: RetrievalService) -> None:
        if self._skills_ready:
            return
        # Lazy import: skills package transitively pulls in optional LLM SDKs
        # (groq/google-genai). Importing here keeps `api.deps` itself usable
        # in environments without those deps (e.g. unit tests).
        from skills import get_registry

        registry = get_registry()
        registry.discover(_SKILLS_ROOT)
        if registry.has("research_search"):
            registry.get("research_search").tavily_api_key = settings.tavily_api_key
        if registry.has("rag.retrieve"):
            registry.get("rag.retrieve").service = retrieval_service
        self._skills_ready = True


@lru_cache
def get_container() -> AppContainer:
    """Process-wide singleton container. Cached so factory + migrations run once."""
    return AppContainer()


def get_agent_graph() -> AgentGraph:
    """Backwards-compat helper — used by chat router and existing imports."""
    return get_container().agent_graph


__all__ = [
    "AppContainer",
    "DEFAULT_DB_PATH",
    "GraphDependencies",
    "get_container",
    "get_agent_graph",
]
