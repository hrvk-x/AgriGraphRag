def retrieve_neighborhood(db, entity_ids, max_hops=2, limit=15):
    if not entity_ids: return []
    hops=max(1,min(int(max_hops),2))
    query=f"""
    MATCH p=(start:Entity)-[:FACT*1..{hops}]-(other:Entity)
    WHERE start.entity_id IN $entity_ids
    UNWIND relationships(p) AS rel
    WITH DISTINCT rel
    MATCH (s:Entity)-[rel]->(o:Entity)
    RETURN s.name AS subject,s.entity_type AS subject_type,
           rel.predicate AS predicate,o.name AS object,o.entity_type AS object_type,
           rel.evidence AS evidence,rel.confidence AS confidence,
           rel.qualifiers_json AS qualifiers,rel.source AS source
    LIMIT $limit
    """
    return [dict(r) for r in db.run(query,{"entity_ids":entity_ids,"limit":limit})]
