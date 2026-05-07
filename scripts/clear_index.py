"""Clear old indexed document chunks before re-indexing."""
import sys, os
os.chdir('d:/AI_project1/AI_project')
sys.path.insert(0, 'backend/src')

import chromadb
import sqlite3

# 1. Delete vector store collection
client = chromadb.PersistentClient(path='./data/vector_store')
try:
    client.delete_collection('indexed_documents')
    print('Deleted indexed_documents collection from ChromaDB')
except Exception as e:
    print(f'Collection delete info: {e}')

# 2. Delete document records from SQLite
conn = sqlite3.connect('./data/conversations.db')
deleted = conn.execute("DELETE FROM documents WHERE source_type='document'").rowcount
conn.commit()
conn.close()
print(f'Deleted {deleted} document records from SQLite')
print('Ready to re-index.')
