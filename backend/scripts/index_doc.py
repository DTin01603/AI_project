#!/usr/bin/env python3
"""CLI utility to index documents into the RAG vector store.

Usage examples:
  python scripts/index_doc.py --file "D:/docs/guide.md"
  python scripts/index_doc.py --file "D:/docs/a.md" --file "D:/docs/b.pdf"
  python scripts/index_doc.py --file "D:/docs/guide.md" --db-path "./data/conversations.db"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap_import_path() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    src_path = backend_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Index documents for RAG retrieval")
    parser.add_argument(
        "--file",
        dest="files",
        action="append",
        required=True,
        help="Absolute or relative path to a document file. Repeat --file for multiple files.",
    )
    parser.add_argument(
        "--db-path",
        default="./data/conversations.db",
        help="SQLite DB path for document metadata (default: ./data/conversations.db)",
    )
    parser.add_argument(
        "--vector-store-path",
        default=None,
        help="Optional override for vector store path. Defaults to RAG config value.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Optional path to RAG YAML config file.",
    )
    return parser


def main() -> int:
    _bootstrap_import_path()

    from rag.config import load_config
    from rag.document_indexer import DocumentIndexer
    from rag.embedding import SentenceTransformerEmbedding
    from rag.vector_store import ChromaVectorStore

    parser = _build_parser()
    args = parser.parse_args()

    config = load_config(args.config) if args.config else load_config()
    vector_store_path = args.vector_store_path or config.vector_store_path

    embedding_model = SentenceTransformerEmbedding(
        model_name=config.embedding_model,
        dimension=config.embedding_dimension,
        batch_size=config.batch_size,
        cache_size=config.cache_size,
    )

    vector_store = ChromaVectorStore(
        persist_directory=vector_store_path,
        collection_name="indexed_documents",
    )

    indexer = DocumentIndexer(
        db_path=args.db_path,
        embedding_model=embedding_model,
        vector_store=vector_store,
        config=config,
    )

    paths = [Path(p).expanduser().resolve() for p in args.files]
    results, errors = indexer.index_files(paths)

    payload = {
        "indexed_count": len(results),
        "error_count": len(errors),
        "results": [
            {
                "document_id": r.document_id,
                "file_path": r.file_path,
                "source_type": r.source_type,
                "chunk_count": r.chunk_count,
            }
            for r in results
        ],
        "errors": [{"file_path": p, "error": err} for p, err in errors],
    }

    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
