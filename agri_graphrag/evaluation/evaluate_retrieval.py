from retrieval.hybrid_graphrag import HybridGraphRAG
CASES=[
 ("What is ADT 36 linked to?",["ADT 36"]),
 ("Which pest is connected to Maize?",["Maize"]),
 ("Tell me about Rice and its seasons.",["Rice"])
]
def main():
    rag=HybridGraphRAG()
    try:
        passed=0
        for q,expected in CASES:
            result=rag.ask(q)
            found=[e["name"] for e in result["matched_entities"]]
            ok=all(x in found for x in expected); passed+=ok
            print(("PASS" if ok else "FAIL")+f" | {q} | {found}")
        print(f"Entity-link smoke test: {passed}/{len(CASES)}")
    finally: rag.close()
if __name__=="__main__": main()
