from graph.neo4j_connection import Neo4jConnection
from retrieval.graph_retriever import graph_search
from retrieval.vector_retriever import VectorRetriever
from retrieval.context_fusion import fuse_context
class HybridGraphRAG:
    def __init__(self):
        self.graph=Neo4jConnection()
        self.vector=VectorRetriever()
    def close(self): self.graph.close()
    def ask(self,question):
        graph_result=graph_search(question,self.graph)
        vector_hits=self.vector.search(question)
        context=fuse_context(graph_result,vector_hits)
        return {"question":question,"matched_entities":graph_result["matched_entities"],**context}
