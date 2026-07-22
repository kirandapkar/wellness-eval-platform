"""vector search over the 9 kb docs. mock mode: keyword match, no embeddings."""
import os
import glob
from agent.config import MOCK_MODE

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assignment_kb")

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_kb",
        "description": "Search the wellness knowledge base for grounded info on diet, exercise, sleep, meditation etc.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}

_docs_cache = None


def _load_docs():
    global _docs_cache
    if _docs_cache is None:
        _docs_cache = []
        for path in sorted(glob.glob(os.path.join(KB_DIR, "*.md"))):
            with open(path) as f:
                _docs_cache.append({"source_doc": os.path.basename(path), "text": f.read()})
    return _docs_cache


def _mock_search(query, k=3):
    docs = _load_docs()
    q = query.lower()
    scored = []
    for d in docs:
        score = sum(1 for w in q.split() if w in d["text"].lower())
        scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    results = []
    for score, d in scored[:k]:
        results.append({
            "title": d["source_doc"],
            "snippet": d["text"][:300],
            "source_doc": d["source_doc"],
        })
    return results


def _real_search(query, k=3):
    # real impl: chroma similarity search over embedded chunks
    import chromadb
    client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "..", "kb", "index"))
    coll = client.get_collection("wellness_kb")
    res = coll.query(query_texts=[query], n_results=k)
    out = []
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        out.append({"title": meta["source_doc"], "snippet": doc[:300], "source_doc": meta["source_doc"]})
    return out


def lookup_kb(query: str, k: int = 3):
    return _mock_search(query, k) if MOCK_MODE else _real_search(query, k)
