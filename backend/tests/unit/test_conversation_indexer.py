"""Unit tests for ConversationIndexer."""

from pathlib import Path

from rag.conversation_indexer import ConversationIndexer
from rag.embedding import SentenceTransformerEmbedding
from rag.vector_store import ChromaVectorStore
from research_agent.database import Database


def test_conversation_indexer_saves_to_sqlite_and_vector_store(tmp_path: Path):
    """Test that ConversationIndexer saves messages to both SQLite and vector store."""
    # Setup
    db_path = str(tmp_path / "test.db")
    vector_path = str(tmp_path / "vectors")
    
    database = Database(db_path)
    embedding_model = SentenceTransformerEmbedding()
    vector_store = ChromaVectorStore(persist_directory=vector_path, collection_name="test_conversations")
    
    indexer = ConversationIndexer(
        database=database,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )
    
    # Create conversation and save message
    conv_id = indexer.create_conversation()
    message_id = indexer.save_message(conv_id, "user", "How do I fix the bug in calculate_price?")
    
    # Verify SQLite storage
    history = indexer.get_conversation_history(conv_id)
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "How do I fix the bug in calculate_price?"
    
    # Verify vector store storage
    query_embedding = embedding_model.embed_query("bug in calculate_price")
    results = vector_store.search(query_embedding, top_k=5)
    
    assert len(results) > 0
    assert any("calculate_price" in str(r.get("text", "")) for r in results)
    
    # Verify metadata
    result = results[0]
    metadata = result.get("metadata", {})
    assert metadata.get("conversation_id") == conv_id
    assert metadata.get("role") == "user"
    assert metadata.get("source_type") == "conversation"


def test_conversation_indexer_chunks_long_messages(tmp_path: Path):
    """Test that long messages are chunked properly."""
    db_path = str(tmp_path / "test.db")
    vector_path = str(tmp_path / "vectors")
    
    database = Database(db_path)
    embedding_model = SentenceTransformerEmbedding()
    vector_store = ChromaVectorStore(persist_directory=vector_path, collection_name="test_conversations")
    
    indexer = ConversationIndexer(
        database=database,
        embedding_model=embedding_model,
        vector_store=vector_store,
        chunk_size=100,  # Small chunk size for testing
    )
    
    # Create a long message
    long_message = " ".join([f"This is sentence number {i}." for i in range(50)])
    
    conv_id = indexer.create_conversation()
    message_id = indexer.save_message(conv_id, "user", long_message)
    
    # Verify SQLite has full message
    history = indexer.get_conversation_history(conv_id)
    assert len(history) == 1
    assert history[0]["content"] == long_message
    
    # Verify vector store has multiple chunks
    query_embedding = embedding_model.embed_query("sentence")
    results = vector_store.search(query_embedding, top_k=20)
    
    # Should have multiple chunks from the same message
    message_chunks = [r for r in results if r.get("metadata", {}).get("message_id") == message_id]
    assert len(message_chunks) > 1
    
    # Verify chunk metadata
    for chunk in message_chunks:
        metadata = chunk.get("metadata", {})
        assert "chunk_index" in metadata
        assert "total_chunks" in metadata
        assert metadata["total_chunks"] == len(message_chunks)


def test_conversation_indexer_handles_multiple_messages(tmp_path: Path):
    """Test that multiple messages are indexed correctly."""
    db_path = str(tmp_path / "test.db")
    vector_path = str(tmp_path / "vectors")
    
    database = Database(db_path)
    embedding_model = SentenceTransformerEmbedding()
    vector_store = ChromaVectorStore(persist_directory=vector_path, collection_name="test_conversations")
    
    indexer = ConversationIndexer(
        database=database,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )
    
    # Create conversation with multiple messages
    conv_id = indexer.create_conversation()
    indexer.save_message(conv_id, "user", "What is Docker?")
    indexer.save_message(conv_id, "assistant", "Docker is a containerization platform.")
    indexer.save_message(conv_id, "user", "How do I install it?")
    
    # Verify SQLite
    history = indexer.get_conversation_history(conv_id)
    assert len(history) == 3
    
    # Verify vector store can find all messages
    query_embedding = embedding_model.embed_query("Docker")
    results = vector_store.search(query_embedding, top_k=10)
    
    # Should find at least 2 messages about Docker
    docker_results = [r for r in results if "Docker" in str(r.get("text", ""))]
    assert len(docker_results) >= 2


def test_conversation_indexer_delegates_to_database(tmp_path: Path):
    """Test that ConversationIndexer properly delegates to Database."""
    db_path = str(tmp_path / "test.db")
    vector_path = str(tmp_path / "vectors")
    
    database = Database(db_path)
    embedding_model = SentenceTransformerEmbedding()
    vector_store = ChromaVectorStore(persist_directory=vector_path, collection_name="test_conversations")
    
    indexer = ConversationIndexer(
        database=database,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )
    
    # Test create_conversation delegation
    conv_id = indexer.create_conversation("test-conv-123")
    assert conv_id == "test-conv-123"
    
    # Test db_path property delegation
    assert indexer.db_path == db_path
    
    # Test get_conversation_history delegation
    indexer.save_message(conv_id, "user", "Test message")
    history = indexer.get_conversation_history(conv_id)
    assert len(history) == 1
