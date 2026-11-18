def identify_entities(question, db):
    """Beginner version: link entities by exact name occurrence in the question."""
    rows=db.run("MATCH (e:Entity) RETURN e.entity_id AS id,e.name AS name,e.entity_type AS entity_type")
    q=question.casefold()
    found=[dict(r) for r in rows if r["name"].casefold() in q]
    return sorted(found,key=lambda x:len(x["name"]),reverse=True)
