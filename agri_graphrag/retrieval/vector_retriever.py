
import os
from sentence_transformers import SentenceTransformer
import chromadb

from config import (
    CHROMA_DIR,
    CHROMA_COLLECTION,
    EMBEDDING_MODEL,
    VECTOR_TOP_K,
)


class VectorRetriever:

    def __init__(self):
        print("Connecting to the existing agricultural ChromaDB...")

        # Connect to the existing persistent database.
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        # Get the existing collection.
        # get_collection() will fail if the name is incorrect.
        # It will NOT silently create an empty collection.
        self.collection = self.client.get_collection(
            name=CHROMA_COLLECTION
        )

        print(f"Collection: {CHROMA_COLLECTION}")
        print(f"Total chunks: {self.collection.count()}")

        # Load the same embedding model used during ingestion.
        # Downloads automatically on first run; set EMBEDDING_MODEL_PATH
        # to use a local snapshot instead.
        print(f"Loading embedding model: {EMBEDDING_MODEL}")

        model_path = os.environ.get("EMBEDDING_MODEL_PATH", EMBEDDING_MODEL)
        self.model = SentenceTransformer(model_path)

        print("Vector retriever initialized successfully.")

    def search(self, question, top_k=VECTOR_TOP_K):

        count = self.collection.count()

        if count == 0:
            return []

        # Convert the question into a 1024-dimensional vector.
        query_embedding = self.model.encode(
            [question],
            normalize_embeddings=True
        ).tolist()

        # Search the existing collection.
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, count),
            include=[
                "documents",
                "metadatas",
                "distances"
            ]
        )

        retrieved_chunks = []

        for i, document in enumerate(results["documents"][0]):

            metadata = results["metadatas"][0][i] or {}

            retrieved_chunks.append({
                "id": results["ids"][0][i],
                "chunk_id": metadata.get("chunk_id"),
                "text": document,
                "metadata": metadata,
                "source": metadata.get("source", "unknown"),
                "crop": metadata.get("crop", "unknown"),
                "category": metadata.get("category", "unknown"),
                "section": metadata.get("section", "unknown"),
                "distance": results["distances"][0][i]
            })

        return retrieved_chunks
