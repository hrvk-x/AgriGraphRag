from config import GEMINI_API_KEY,GEMINI_MODEL

def evidence_only(result):
    out=["Retrieved evidence from the illustrative demo dataset:"]
    if result["graph_facts"]:
        out.append("\\nGraph relationships:")
        for f in result["graph_facts"]:
            out.append(f"- {f['subject']} --{f['predicate']}--> {f['object']}. Evidence: {f['evidence']} [source: {f.get('source','unknown')}]")
    if result["vector_documents"]:
        out.append("\\nRelated passages:")
        for d in result["vector_documents"]:
            out.append(f"- {d['text']} [source: {d['source']}]")
    if not result["graph_facts"] and not result["vector_documents"]:
        out.append("No matching evidence was retrieved. Try a crop, variety, pest or season in the sample dataset.")
    out.append("\\nReminder: these are fictional software-test examples, not agricultural recommendations.")
    return "\\n".join(out)

def generate_answer(result):
    if not GEMINI_API_KEY: return evidence_only(result)
    from google import genai
    client=genai.Client(api_key=GEMINI_API_KEY)
    prompt=f"""Explain only the retrieved demo relationships. The records are illustrative software-test data,
NOT real agricultural recommendations. Do not turn them into farming advice. If evidence is insufficient,
say so. Cite the supplied evidence.
Question: {result['question']}
Graph facts: {result['graph_facts']}
Retrieved passages: {result['vector_documents']}"""
    response=client.models.generate_content(model=GEMINI_MODEL,contents=prompt)
    return response.text or evidence_only(result)
