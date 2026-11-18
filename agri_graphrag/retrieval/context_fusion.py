def fuse_context(graph_result,vector_hits):
    facts=[]; seen=set()
    for f in graph_result.get("facts",[]):
        key=(f.get("subject"),f.get("predicate"),f.get("object"),f.get("evidence"))
        if key not in seen: seen.add(key); facts.append(f)
    docs=[]
    for d in vector_hits:
        key=d.get("text","").strip()
        if key and key not in seen: seen.add(key); docs.append(d)
    return {"graph_facts":facts,"vector_documents":docs}
