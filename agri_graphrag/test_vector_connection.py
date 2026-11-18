
from retrieval.vector_retriever import VectorRetriever

retriever = VectorRetriever()

print("\n" + "=" * 60)
print("TESTING AGRICULTURAL VECTOR RETRIEVAL")
print("=" * 60)

question = "Which rice varieties are suitable for Kuruvai season?"

results = retriever.search(question, top_k=5)

print(f"\nQuestion: {question}")
print(f"Retrieved chunks: {len(results)}")

for i, chunk in enumerate(results, start=1):

    print("\n" + "-" * 60)
    print(f"RESULT {i}")
    print("-" * 60)

    print("Chroma UUID:", chunk["id"])
    print("Chunk ID:", chunk["chunk_id"])
    print("Crop:", chunk["crop"])
    print("Category:", chunk["category"])
    print("Section:", chunk["section"])
    print("Source:", chunk["source"])
    print("Distance:", chunk["distance"])

    print("\nRetrieved text:")
    print(chunk["text"][:700])
