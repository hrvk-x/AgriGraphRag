from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from retrieval.hybrid_graphrag import HybridGraphRAG
from generation.answer_generator import generate_answer
app=FastAPI(title="AgriGraphRAG Demo API")
class AskRequest(BaseModel):
    question:str
@app.get("/health")
def health():
    rag=HybridGraphRAG()
    try:
        rag.graph.verify()
        return {"status":"ok","neo4j":"connected"}
    finally: rag.close()
@app.post("/ask")
def ask(req:AskRequest):
    if not req.question.strip(): raise HTTPException(400,"Question cannot be empty")
    rag=HybridGraphRAG()
    try:
        result=rag.ask(req.question)
        return {"answer":generate_answer(result),"retrieval":result}
    finally: rag.close()
