"""Embed text chunks and table cells into two local Chroma collections."""

import argparse
import json
from pathlib import Path

from src.ingest import ROOT

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run ingestion and table extraction first.")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def make_metadata(record):
    """Chroma metadata values must be basic scalar types, not nested objects."""
    return {key: value for key, value in record.items()
            if key not in {"text", "value"} and isinstance(value, (str, int, float, bool))}


def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME, device="cpu")


def index_records(client, model, collection_name, records, id_key, batch_size=32):
    # Rebuild so rerunning removes stale records, even if a collection is now empty.
    names = {item.name for item in client.list_collections()}
    if collection_name in names:
        client.delete_collection(collection_name)
    if not records:
        print(f"{collection_name}: 0 records")
        return 0
    collection = client.create_collection(collection_name, metadata={"hnsw:space": "cosine"})
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        texts = [record["text"] for record in batch]
        vectors = model.encode(texts, batch_size=batch_size, show_progress_bar=False).tolist()
        collection.add(
            ids=[record[id_key] for record in batch],
            embeddings=vectors,
            documents=texts,
            metadatas=[make_metadata(record) for record in batch],
        )
    print(f"{collection_name}: indexed {len(records)} records")
    return len(records)


def build_index(chunks_file, cells_file, db_path, model=None, client=None):
    chunks = read_jsonl(chunks_file)
    cells = read_jsonl(cells_file)
    if not chunks:
        raise ValueError("Text chunk file is empty")
    if model is None:
        model = get_model()
    if client is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_path))
    text_count = index_records(client, model, "text_chunks", chunks, "chunk_id")
    cell_count = index_records(client, model, "table_cells", cells, "cell_id")
    return text_count, cell_count


def main():
    parser = argparse.ArgumentParser(description="Build Chroma text and cell indexes")
    parser.add_argument("--chunks", type=Path, default=ROOT / "data/processed/chunks.jsonl")
    parser.add_argument("--cells", type=Path, default=ROOT / "data/processed/cells.jsonl")
    parser.add_argument("--db", type=Path, default=ROOT / "data/chroma")
    args = parser.parse_args()
    build_index(args.chunks, args.cells, args.db)


if __name__ == "__main__":
    main()
