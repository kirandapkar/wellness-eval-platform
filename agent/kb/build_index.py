"""chunk the 9 kb docs and load into a local chroma collection. run once before real mode."""
import glob
import os

import chromadb

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assignment_kb")
INDEX_DIR = os.path.join(os.path.dirname(__file__), "index")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + size]))
        i += size - overlap
    return chunks


def build():
    client = chromadb.PersistentClient(path=INDEX_DIR)
    client.delete_collection("wellness_kb") if "wellness_kb" in [c.name for c in client.list_collections()] else None
    coll = client.create_collection("wellness_kb")

    ids, docs, metas = [], [], []
    for path in sorted(glob.glob(os.path.join(KB_DIR, "*.md"))):
        name = os.path.basename(path)
        text = open(path).read()
        for i, chunk in enumerate(chunk_text(text)):
            ids.append(f"{name}-{i}")
            docs.append(chunk)
            metas.append({"source_doc": name})

    coll.add(ids=ids, documents=docs, metadatas=metas)
    print(f"indexed {len(ids)} chunks from {len(glob.glob(os.path.join(KB_DIR, '*.md')))} docs into {INDEX_DIR}")


if __name__ == "__main__":
    build()
