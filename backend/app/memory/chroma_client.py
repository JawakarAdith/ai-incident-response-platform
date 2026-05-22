import chromadb
import os

# Path where ChromaDB stores data on disk
CHROMA_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../chroma_db"
)

def get_chroma_client():
    """Get ChromaDB client."""
    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )
    return client

def get_incidents_collection():
    """Get or create incidents collection."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name="incidents",
        metadata={"hnsw:space": "cosine"}
    )
    return collection