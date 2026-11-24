"""Search both indexes; answer generation will be added in Part 3."""

import argparse
from pathlib import Path

from src.index import get_model
from src.ingest import ROOT


def search(question, db_path, top_k=5, model=None, client=None, collection="both"):
    if model is None:
        model = get_model()
    if client is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_path))

    vector = model.encode([question], show_progress_bar=False).tolist()[0]
    results = []
    available = {item.name for item in client.list_collections()}
    collections = {"both": ("text_chunks", "table_cells"),
                   "text": ("text_chunks",), "cell": ("table_cells",)}
    for collection_name in collections[collection]:
        if collection_name not in available:
            continue
        collection = client.get_collection(collection_name)
        count = collection.count()
        if count == 0:
            continue
        found = collection.query(
            query_embeddings=[vector],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
        for item_id, document, metadata, distance in zip(
            found["ids"][0], found["documents"][0],
            found["metadatas"][0], found["distances"][0]
        ):
            results.append({
                "id": item_id,
                "kind": "text" if collection_name == "text_chunks" else "cell",
                "text": document,
                "metadata": metadata,
                "distance": distance,
            })
    # Both collections use identical embeddings and cosine distance.
    return sorted(results, key=lambda item: item["distance"])[:top_k]


def main():
    parser = argparse.ArgumentParser(description="Search local indexed PDFs")
    parser.add_argument("question", help="Question in quotation marks")
    parser.add_argument("--db", type=Path, default=ROOT / "data/chroma")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.top_k <= 0:
        parser.error("--top-k must be positive")
    matches = search(args.question, args.db, args.top_k)
    for rank, item in enumerate(matches, 1):
        source = item["metadata"]
        print(f"\n{rank}. [{item['kind']}] {source['filename']} page {source['page_number']} "
              f"(cosine distance {item['distance']:.3f})")
        print(item["text"][:400])
    if not matches:
        print("No results. Build the index first.")


if __name__ == "__main__":
    main()
