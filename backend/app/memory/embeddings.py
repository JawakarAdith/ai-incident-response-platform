from sentence_transformers import SentenceTransformer
from typing import List

# Load lazily — not on startup
_model = None

def get_model():
    """Load model only when first needed."""
    global _model
    if _model is None:
        print("Loading embedding model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded!")
    return _model

def get_embedding(text: str) -> List[float]:
    model = get_model()
    embedding = model.encode(text)
    return embedding.tolist()

def get_embeddings(texts) -> List[List[float]]:
    model = get_model()
    embeddings = model.encode(texts)
    return embeddings.tolist()