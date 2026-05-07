"""Debug script: inspect retrieved chunks for a query."""
import sys, os
os.chdir('d:/AI_project1/AI_project')
sys.path.insert(0, 'backend/src')

import chromadb
from rag.embedding import SentenceTransformerEmbedding
from rag.config import load_config

OUT = open('scripts/debug_output.txt', 'w', encoding='utf-8')
def p(*a, **kw):
    print(*a, **kw, file=OUT)

config = load_config()
embed = SentenceTransformerEmbedding(
    model_name=config.embedding_model,
    dimension=config.embedding_dimension,
)

client = chromadb.PersistentClient(path='./data/vector_store')
col = client.get_collection('indexed_documents')

p(f"Total chunks: {col.count()}")

# 1. Full-text filter for chunks containing keywords
for keyword in ['ke', 'kê', 'đậu', 'lương thực', 'ngoài']:
    results = col.get(
        where_document={"$contains": keyword},
        limit=5,
        include=["documents", "metadatas"],
    )
    if results["documents"]:
        p(f"\n=== keyword '{keyword}' => {len(results['documents'])} chunks ===")
        for doc in results["documents"][:3]:
            p(doc[:300])
            p()

# 2. Vector similarity search
p("\n\n=== PHU NAM chunks with keyword search ===")
phunam_results = col.get(
    where_document={"$contains": "Phù Nam"},
    limit=30,
    include=["documents", "metadatas"],
)
p(f"Found {len(phunam_results['documents'])} Phù Nam chunks")
for doc in phunam_results["documents"]:
    if any(kw in doc for kw in ['kê', 'đậu', 'lương thực', 'cây trồng']):
        p("[✓ MATCH Phù Nam + crop keyword]")
        p(doc[:500])
        p("---")

# Directly check for the key sentence across the boundary
p("\n=== Checking 'cấy lúa' + 'Phù Nam' in same chunk ===")
cay_lua_results = col.get(where_document={"$contains": "cấy lúa"}, limit=20, include=["documents"])
p(f"'cấy lúa' chunks: {len(cay_lua_results['documents'])}")
for doc in cay_lua_results["documents"]:
    if "Phù Nam" in doc and any(kw in doc for kw in ["kê", "đậu", "lương thực"]):
        p("[✓ FIXED - cấy lúa + Phù Nam + kê/đậu in SAME chunk]")
        p(doc[:600])
        p("---")

p("\n\n=== VECTOR SEARCH for query ===")
q_text = "ngoai trong lua thi nguoi Phu Nam con trong cay gi khong"
q_vec = embed.embed(q_text)
try:
    results = col.query(
        query_embeddings=[q_vec],
        n_results=10,
        include=["documents", "metadatas", "distances"],
    )
    for i, (doc, dist) in enumerate(zip(results["documents"][0], results["distances"][0])):
        p(f"[{i+1}] dist={dist:.4f} | {doc[:350]}")
        p()
except Exception as e:
    p(f"VECTOR SEARCH ERROR: {e}")

OUT.close()
print("Done. See scripts/debug_output.txt")
