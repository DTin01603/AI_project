"""Conversation message indexer with realtime embedding pipeline.

This module provides the ConversationIndexer class that extends the Database
class to automatically embed and index conversation messages into the vector store.
"""

from __future__ import annotations

import logging
from typing import Any

from research_agent.database import Database
from rag.embedding import EmbeddingModel
from rag.vector_store import VectorStore


logger = logging.getLogger(__name__)


class ConversationIndexer:
    """Wrapper around Database that adds realtime vector indexing for conversations.
    
    This class ensures that every new conversation message is:
    1. Saved to SQLite (via Database)
    2. Automatically indexed in FTS (via Database triggers)
    3. Chunked if needed (for long messages)
    4. Embedded using the embedding model
    5. Stored in the vector store for semantic search
    
    This eliminates the need for bootstrap on every restart and ensures
    that vector search always has the latest conversation data.
    """

    def __init__(
        self,
        database: Database,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        chunk_size: int = 512,
    ) -> None:
        """Initialize conversation indexer.
        
        Args:
            database: Database instance for SQLite operations
            embedding_model: Model for generating embeddings
            vector_store: Vector store for semantic search
            chunk_size: Maximum characters per chunk (default: 512)
        """
        self.database = database
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.chunk_size = max(64, chunk_size)

    def save_message(self, conversation_id: str, role: str, content: str) -> str:
        """Save message to SQLite and vector store with realtime embedding.
        
        This method:
        1. Saves to SQLite (triggers FTS indexing automatically)
        2. Chunks the content if it exceeds chunk_size
        3. Embeds all chunks
        4. Stores embeddings in vector store
        
        Args:
            conversation_id: Conversation identifier
            role: Message role (user, assistant, system)
            content: Message content
            
        Returns:
            Message ID
        """
        # Step 1: Save to SQLite (FTS indexing happens via trigger)
        message_id = self.database.save_message(conversation_id, role, content)
        
        # Step 2: Chunk content if needed
        chunks = self._chunk_content(content)
        
        # Step 3: Prepare metadata
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        
        # Step 4: Embed all chunks
        try:
            embeddings = self.embedding_model.embed(chunks)
        except Exception as e:
            logger.error(f"Failed to embed message {message_id}: {e}", exc_info=True)
            # Don't fail the save operation if embedding fails
            return message_id
        
        # Step 5: Prepare data for vector store
        ids = [f"{message_id}::chunk::{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "role": role,
                "created_at": now,
                "source_type": "conversation",
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]
        
        # Step 6: Add to vector store
        try:
            self.vector_store.add(
                ids=ids,
                embeddings=embeddings,
                texts=chunks,
                metadatas=metadatas,
            )
            self.vector_store.persist()
            logger.debug(f"Indexed message {message_id} with {len(chunks)} chunks into vector store")
        except Exception as e:
            logger.error(f"Failed to index message {message_id} in vector store: {e}", exc_info=True)
            # Don't fail the save operation if vector indexing fails
        
        return message_id

    def _chunk_content(self, content: str) -> list[str]:
        """Chunk content if it exceeds chunk_size.
        
        Uses simple sentence-based chunking with overlap for conversations.
        For most chat messages, this will return a single chunk.
        
        Args:
            content: Message content to chunk
            
        Returns:
            List of text chunks
        """
        if not content or len(content) <= self.chunk_size:
            return [content]
        
        # Simple sentence-based chunking
        import re
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence exceeds chunk_size, save current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length + 1  # +1 for space
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [content]

    # Delegate other methods to the underlying database
    def create_conversation(self, conversation_id: str | None = None) -> str:
        """Create a new conversation. Delegates to Database."""
        return self.database.create_conversation(conversation_id)

    def get_conversation_history(self, conversation_id: str) -> list[dict[str, str]]:
        """Get conversation history. Delegates to Database."""
        return self.database.get_conversation_history(conversation_id)

    @property
    def db_path(self) -> str:
        """Get database path. Delegates to Database."""
        return self.database.db_path
