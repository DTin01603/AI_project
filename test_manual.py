"""Manual test for ConversationIndexer."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, 'backend/src')

from rag.conversation_indexer import ConversationIndexer
from rag.embedding import SentenceTransformerEmbedding
from rag.vector_store import ChromaVectorStore
from research_agent.database import Database


def test_basic():
    """Test basic functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        vector_path = str(Path(tmpdir) / "vectors")
        
        print("✓ Creating database...")
        database = Database(db_path)
        
        print("✓ Creating embedding model...")
        embedding_model = SentenceTransformerEmbedding()
        
        print("✓ Creating vector store...")
        vector_store = ChromaVectorStore(
            persist_directory=vector_path,
            collection_name="test_conversations"
        )
        
        print("✓ Creating ConversationIndexer...")
        indexer = ConversationIndexer(
            database=database,
            embedding_model=embedding_model,
            vector_store=vector_store,
        )
        
        print("✓ Creating conversation...")
        conv_id = indexer.create_conversation()
        
        print("✓ Saving message...")
        message_id = indexer.save_message(
            conv_id,
            "user",
            "How do I fix the bug in calculate_price function?"
        )
        
        print(f"✓ Message saved with ID: {message_id}")
        
        print("✓ Checking SQLite...")
        history = indexer.get_conversation_history(conv_id)
        assert len(history) == 1
        assert "calculate_price" in history[0]["content"]
        print(f"  - SQLite has {len(history)} message(s) ✓")
        
        print("✓ Checking Vector Store...")
        query_embedding = embedding_model.embed_query("bug in calculate_price")
        results = vector_store.search(query_embedding, top_k=5)
        print(f"  - Vector store returned {len(results)} result(s)")
        
        if results:
            result = results[0]
            print(f"  - Top result text: {result.get('text', '')[:100]}...")
            print(f"  - Top result score: {result.get('score', 0):.4f}")
            metadata = result.get('metadata', {})
            print(f"  - Metadata: conversation_id={metadata.get('conversation_id')}, role={metadata.get('role')}")
            assert "calculate_price" in str(result.get("text", ""))
            print("  - Vector search works! ✓")
        else:
            print("  - WARNING: No results from vector search!")
        
        print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_basic()
