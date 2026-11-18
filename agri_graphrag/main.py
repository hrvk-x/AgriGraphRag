from retrieval.vector_retriever import VectorRetriever
from retrieval.hybrid_graphrag import HybridGraphRAG
from generation.answer_generator import generate_answer

def main():
    import argparse
    parser=argparse.ArgumentParser(description="AgriGraphRAG learning prototype")
    parser.add_argument("command",choices=["index","chat"])
    args=parser.parse_args()
    if args.command=="index":
        count=VectorRetriever().build_index(reset=True)
        print(f"Indexed {count} sample passages in ChromaDB.")
        return
    app=HybridGraphRAG()
    try:
        app.graph.verify()
        print("\\nAgriGraphRAG is ready. Ask a question; type exit to stop.")
        print("Example: What is ADT 36 linked to in the sample data?\\n")
        while True:
            q=input("You: ").strip()
            if q.casefold() in {"exit","quit"}: break
            if not q: continue
            result=app.ask(q)
            print("\\nMatched entities:")
            for e in result["matched_entities"]: print(f" - {e['name']} ({e['entity_type']})")
            print("\\n"+generate_answer(result)+"\\n")
    finally: app.close()
if __name__=="__main__": main()
