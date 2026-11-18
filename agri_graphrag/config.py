import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_TRIPLES_PATH = DATA_DIR / "sample_triples.json"
SAMPLE_DOCUMENTS_PATH = DATA_DIR / "sample_documents.json"
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", str(BASE_DIR / "chroma_db")))
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "change_this_password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "triples")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
VECTOR_TOP_K = 4
GRAPH_MAX_HOPS = 2
GRAPH_TOP_K = 15
CHROMA_COLLECTION = "langchain"
