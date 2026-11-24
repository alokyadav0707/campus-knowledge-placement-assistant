import json

from src.index import build_index, make_metadata
from src.search import search


class FakeModel:
    def encode(self, texts, **kwargs):
        class Vectors(list):
            def tolist(self):
                return list(self)
        return Vectors([[float(len(text)), 1.0] for text in texts])


class FakeCollection:
    def __init__(self):
        self.items = []

    def add(self, ids, embeddings, documents, metadatas):
        self.items.extend(zip(ids, embeddings, documents, metadatas))

    def count(self):
        return len(self.items)

    def query(self, query_embeddings, n_results, include):
        items = self.items[:n_results]
        return {
            "ids": [[item[0] for item in items]],
            "documents": [[item[2] for item in items]],
            "metadatas": [[item[3] for item in items]],
            "distances": [[0.1 for item in items]],
        }


class FakeClient:
    def __init__(self):
        self.collections = {}

    def list_collections(self):
        from types import SimpleNamespace
        return [SimpleNamespace(name=name) for name in self.collections]

    def delete_collection(self, name):
        if name not in self.collections:
            raise ValueError("missing")
        del self.collections[name]

    def create_collection(self, name, metadata):
        self.collections[name] = FakeCollection()
        return self.collections[name]

    def get_collection(self, name):
        if name not in self.collections:
            raise ValueError("missing")
        return self.collections[name]


def test_metadata_and_dual_index(tmp_path):
    chunks = tmp_path / "chunks.jsonl"
    cells = tmp_path / "cells.jsonl"
    chunks.write_text(json.dumps({"chunk_id": "a", "filename": "demo.pdf",
                                   "page_number": 1, "text": "Placement deadline"}) + "\n")
    cells.write_text(json.dumps({"cell_id": "b", "filename": "demo.pdf",
                                  "page_number": 2, "value": "42", "text": "CS offers 42"}) + "\n")
    model = FakeModel()
    client = FakeClient()
    assert build_index(chunks, cells, tmp_path / "db", model, client) == (1, 1)
    results = search("CS offers?", tmp_path / "db", 5, model, client)
    assert {item["kind"] for item in results} == {"text", "cell"}
    assert {item["metadata"]["page_number"] for item in results} == {1, 2}
    assert "value" not in make_metadata({"value": "42", "page_number": 2})
    assert build_index(chunks, cells, tmp_path / "db", model, client) == (1, 1)
    assert len(client.collections["table_cells"].items) == 1
