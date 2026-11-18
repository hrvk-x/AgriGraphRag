from config import GRAPH_MAX_HOPS, GRAPH_TOP_K
from retrieval.entity_extractor import identify_entities
from graph.graph_queries import retrieve_neighborhood
def graph_search(question,db):
    entities=identify_entities(question,db)
    facts=retrieve_neighborhood(db,[e["id"] for e in entities],GRAPH_MAX_HOPS,GRAPH_TOP_K)
    return {"matched_entities":entities,"facts":facts}
