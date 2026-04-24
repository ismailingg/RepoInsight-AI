# verify_phase3.py
import chromadb
import hashlib

CHROMA_DB_PATH = "./data/chroma_db"
repo_url = "https://github.com/pallets/flask"

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:16]
collection = client.get_collection(f"repo_{repo_hash}")

print(f"Collection: {collection.name}")
print(f"Total chunks stored: {collection.count()}")

# Peek at first 3 chunks
results = collection.peek(limit=3)
print(f"\nSample chunks:")
for i in range(len(results['ids'])):
    print(f"\n  ID:    {results['ids'][i]}")
    print(f"  File:  {results['metadatas'][i]['file']}")
    print(f"  Lines: {results['metadatas'][i]['start_line']} → {results['metadatas'][i]['end_line']}")
    print(f"  Preview: {results['documents'][i][:80]}...")