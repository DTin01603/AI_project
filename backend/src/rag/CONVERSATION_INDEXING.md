# Conversation Realtime Indexing

## Overview

This document describes the realtime embedding pipeline for conversation messages, ensuring that every new message is automatically indexed in both SQLite (for keyword search) and Vector Store (for semantic search).

## Problem Statement

**Before this implementation:**
- Conversations were only saved to SQLite + FTS
- Vector indexing relied on bootstrap (one-time load on app startup)
- New messages were NOT embedded automatically
- Required app restart to index new messages
- Semantic search couldn't find recent conversations

**After this implementation:**
- Every new message is automatically embedded and indexed
- No need for bootstrap after initial setup
- Realtime semantic search on all conversations
- Follows the complete RAG indexing pipeline

## Architecture

### Components

1. **ConversationIndexer** (`rag/conversation_indexer.py`)
   - Wraps the `Database` class
   - Adds realtime embedding pipeline
   - Handles chunking for long messages
   - Stores embeddings in vector store

2. **Integration** (`api/deps.py`)
   - Creates `ConversationIndexer` instead of raw `Database`
   - Shares embedding model and vector store with retrieval pipeline
   - Maintains backward compatibility

### Data Flow

```
User Message
    ↓
ConversationIndexer.save_message()
    ↓
├─→ Database.save_message()
│   ├─→ SQLite INSERT (messages table)
│   └─→ FTS5 trigger (automatic keyword indexing)
│
├─→ Chunk content (if > chunk_size)
│
├─→ Embedding Model
│   └─→ Generate vectors for all chunks
│
└─→ Vector Store
    └─→ Store embeddings with metadata
```

## Implementation Details

### Chunking Strategy

For conversation messages:
- **Short messages** (≤ 512 chars): Single chunk
- **Long messages** (> 512 chars): Sentence-based chunking with overlap
- Each chunk maintains reference to original message_id

### Metadata Structure

Each vector embedding includes:
```python
{
    "message_id": "uuid",
    "conversation_id": "uuid",
    "role": "user|assistant|system",
    "created_at": "ISO timestamp",
    "source_type": "conversation",
    "chunk_index": 0,
    "total_chunks": 1
}
```

### Error Handling

- **Embedding failure**: Logs error but doesn't fail the save operation
- **Vector store failure**: Logs error but doesn't fail the save operation
- **SQLite always succeeds**: Message is always saved to database

This ensures that even if embedding/vector indexing fails, the conversation is not lost.

## Usage

### Basic Usage

```python
from rag.conversation_indexer import ConversationIndexer
from rag.embedding import SentenceTransformerEmbedding
from rag.vector_store import ChromaVectorStore
from research_agent.database import Database

# Create components
database = Database("./data/conversations.db")
embedding_model = SentenceTransformerEmbedding()
vector_store = ChromaVectorStore(
    persist_directory="./data/vectors",
    collection_name="conversation_messages"
)

# Create indexer
indexer = ConversationIndexer(
    database=database,
    embedding_model=embedding_model,
    vector_store=vector_store,
    chunk_size=512
)

# Save message (automatically indexed)
conv_id = indexer.create_conversation()
message_id = indexer.save_message(
    conversation_id=conv_id,
    role="user",
    content="How do I fix the bug in calculate_price?"
)

# Message is now available for:
# 1. Keyword search (FTS)
# 2. Semantic search (Vector)
# 3. Conversation history (SQLite)
```

### Integration with Application

The `ConversationIndexer` is automatically used in the application through dependency injection in `api/deps.py`:

```python
def _build_orchestrator_dependencies() -> GraphDependencies:
    # ... setup code ...
    
    # ConversationIndexer wraps Database
    database = ConversationIndexer(
        database=base_database,
        embedding_model=embedding_model,
        vector_store=conversation_vector_store,
        chunk_size=rag_config.chunk_size,
    )
    
    # Use in graph
    return GraphDependencies(
        database=database,  # Now a ConversationIndexer
        # ... other dependencies ...
    )
```

## Benefits

### 1. Realtime Semantic Search
- New messages are immediately searchable
- No need to restart application
- Consistent with document indexing pipeline

### 2. Complete RAG Pipeline
- Follows the same flow as documents/code:
  - Input → Chunk → [SaveText + Embed] → [SQLite + VectorDB]
- Architectural consistency

### 3. Backward Compatibility
- `ConversationIndexer` delegates to `Database` for all read operations
- Existing code continues to work
- Drop-in replacement

### 4. Robust Error Handling
- Embedding failures don't lose messages
- Graceful degradation
- Comprehensive logging

## Performance Considerations

### Embedding Latency
- Embedding adds ~100-500ms per message
- Runs synchronously (blocks save operation)
- Consider async implementation for high-throughput scenarios

### Vector Store Writes
- Persist called after each message
- May impact performance with many concurrent users
- Consider batching for production

### Chunking Overhead
- Minimal for typical chat messages (< 512 chars)
- Only impacts very long messages

## Testing

### Manual Test
```bash
cd AI_project
python test_manual.py
```

### Unit Tests
```bash
cd AI_project
python -m pytest backend/tests/unit/test_conversation_indexer.py -v
```

## Migration Guide

### For Existing Deployments

1. **No migration needed** - Bootstrap still works for existing messages
2. **New messages** automatically indexed going forward
3. **Optional**: Run bootstrap once to ensure all old messages are indexed

### Removing Bootstrap (Optional)

Once all messages are indexed, you can remove the bootstrap logic from `RetrievalNode._bootstrap_vector_index()` if desired. However, keeping it provides a safety net for:
- Database corruption recovery
- New deployments
- Development environments

## Future Improvements

1. **Async Embedding**: Move embedding to background task
2. **Batch Processing**: Batch multiple messages for efficiency
3. **Incremental Updates**: Only embed changed content
4. **Compression**: Apply compression before embedding
5. **Multi-language Support**: Language-specific chunking strategies

## Related Files

- `backend/src/rag/conversation_indexer.py` - Main implementation
- `backend/src/api/deps.py` - Integration point
- `backend/src/research_agent/database.py` - Base database class
- `backend/src/rag/retrieval_node.py` - Retrieval with bootstrap
- `backend/tests/unit/test_conversation_indexer.py` - Unit tests
- `test_manual.py` - Manual integration test
