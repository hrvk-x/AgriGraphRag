# AgriGraphRAG — Agricultural Knowledge Graph + Hybrid RAG System

An end-to-end system that **extracts** structured knowledge-graph triples from agricultural text using LLMs (via OpenRouter) and **answers questions** using a hybrid Graph + Vector retrieval-augmented generation pipeline.

> **Note:** All bundled sample data is illustrative software-test data only. It is not verified agricultural knowledge or farming advice.

---

## Architecture Overview

```
┌──────────────────────────────────┐       ┌──────────────────────────────────────┐
│     agri_kg_production/          │       │         agri_graphrag/               │
│                                  │       │                                      │
│  Crop Guide JSON                 │       │  ┌─────────────┐  ┌──────────────┐  │
│       │                          │       │  │   Neo4j      │  │  ChromaDB    │  │
│       ▼                          │       │  │  (Graph DB)  │  │ (Vector DB)  │  │
│  LLM Extraction (OpenRouter)     │       │  └──────┬───────┘  └──────┬───────┘  │
│       │                          │       │         │                 │          │
│       ▼                          │       │         ▼                 ▼          │
│  Validation & Evidence Check     │       │     Graph Retriever  Vector Search   │
│       │                          │       │         │                 │          │
│       ▼                          │       │         └────────┬────────┘          │
│  triples.json  ─────────────────────────►│          Context Fusion              │
│  (output/)                       │       │              │                       │
│                                  │       │              ▼                       │
│                                  │       │    Answer Generator (Gemini)         │
└──────────────────────────────────┘       └──────────────────────────────────────┘
```

| Sub-project | Purpose |
|---|---|
| `agri_kg_production/` | Extracts knowledge-graph triples from agricultural text chunks using an LLM via the OpenRouter API |
| `agri_graphrag/` | Hybrid GraphRAG system — loads triples into Neo4j, indexes passages in ChromaDB, answers questions via combined graph + vector retrieval |

---

## Prerequisites

- **Python 3.10 or 3.11** (Windows/Linux/macOS)
- **Neo4j Desktop** (or any Neo4j 5.x instance) with a local database started
- **Internet access** for installing packages, downloading the embedding model, and calling APIs

### API Keys (at least one)

| Key | Required for | Get it at |
|---|---|---|
| `OPENROUTER_API_KEY` | KG extraction (`agri_kg_production`) | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `GEMINI_API_KEY` | LLM-generated answers (optional in `agri_graphrag`) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/agri-graphrag.git
cd agri-graphrag
```

### 2. Set up Neo4j

1. Open **Neo4j Desktop**, create a local DBMS, set a password, and start it.
2. Use the default Bolt address: `bolt://localhost:7687`.
3. Use a dedicated empty database for this project.

---

## Part A — Knowledge Graph Extraction (`agri_kg_production/`)

Extracts structured triples (subject → predicate → object) from raw agricultural text using an LLM.

### Setup

```bash
cd agri_kg_production
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env and set your OPENROUTER_API_KEY
```

Place your input JSON file (a list of text chunks with `page_content` fields) in the `data/` directory, or set `AGRI_INPUT_JSON` in `.env` to its path.

### Run

```bash
# 1. Preflight check (zero API calls — verifies input file)
python preflight.py

# 2. Start extraction (resumable — safe to Ctrl+C)
python extractor.py

# 3. Re-export outputs without making API calls
python export_data.py
```

### Outputs

All outputs are written to the `output/` directory:

| File | Description |
|---|---|
| `triples.json` | Accepted triples (JSON array) |
| `triples.jsonl` | One triple per line |
| `triples.csv` | CSV format |
| `rejected_triples.json` | Triples that failed validation |
| `chunk_status.json` | Per-chunk processing status |
| `extraction_stats.json` | Summary statistics |
| `extraction.log` | Detailed log |
| `kg_extraction_openrouter_final.db` | SQLite checkpoint database |

### Key design features

- **Resumable:** SQLite checkpoints track chunk status; Ctrl+C is safe; re-run `extractor.py` to continue.
- **Adaptive splitting:** If LLM output is truncated, the passage is recursively bisected and re-extracted.
- **Evidence validation:** Every triple's evidence must be a verbatim continuous substring of the source text.
- **Daily budget:** Configurable limit (default 850) of API attempts per UTC day.
- **Ontology:** 31 entity types and 42 predicates defined in `config.py`.

---

## Part B — Hybrid GraphRAG (`agri_graphrag/`)

Loads triples into Neo4j and answers questions via combined graph + vector retrieval.

### Setup

```bash
cd agri_graphrag
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env — set at minimum your NEO4J_PASSWORD
```

### Build the demo graph (sample data)

```bash
python -m graph.graph_builder
```

Expected output: `Imported 17 illustrative facts into Neo4j.`

Verify in Neo4j Browser:
```cypher
MATCH (n:Entity)-[r:FACT]->(m:Entity) RETURN n, r, m LIMIT 50;
```

### (Optional) Import your extracted production triples

If you ran the extraction pipeline and have `triples.json`:

```bash
python import_real_triples.py
```

By default it looks for `../agri_kg_production/output/triples.json`. Override with:
```bash
# Windows PowerShell
$env:TRIPLES_JSON="path\to\your\triples.json"

# Linux / macOS
export TRIPLES_JSON="path/to/your/triples.json"
```

### Build the vector index

```bash
python main.py index
```

The first run downloads the `BAAI/bge-large-en-v1.5` embedding model (~1.3 GB); allow a few minutes.

### Ask questions (CLI)

```bash
python main.py chat
```

Example queries:
- `What is ADT 36 linked to in the sample data?`
- `What pests are connected to Rice?`
- `Tell me about Rice and its seasons.`

Type `exit` to quit. Without a Gemini key, the program prints retrieved evidence directly.

### Ask questions (API)

```bash
uvicorn api.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and test `POST /ask`:
```json
{"question": "What is ADT 36 linked to?"}
```

### (Optional) Enable Gemini generation

Add your key to `.env`:
```
GEMINI_API_KEY=your_key_here
```

Restart the CLI or API. The generator will produce natural-language answers citing the retrieved evidence.

---

## Project Structure

```
agri-graphrag/
├── .gitignore
├── README.md                          ← You are here
│
├── agri_kg_production/                ← KG extraction pipeline
│   ├── .env.example
│   ├── requirements.txt
│   ├── config.py                      # Model, chunking, budget, ontology settings
│   ├── extractor.py                   # Main extraction loop (OpenRouter API)
│   ├── prompts.py                     # LLM system prompt and JSON schema
│   ├── validators.py                  # Triple validation and evidence checking
│   ├── storage.py                     # SQLite-backed checkpoint store
│   ├── export_data.py                 # Export from SQLite to JSON/CSV
│   ├── preflight.py                   # Zero-cost dry run
│   ├── test.py                        # Quick output inspection
│   └── data/                          # Place your input JSON here
│
├── agri_graphrag/                     ← Hybrid GraphRAG system
│   ├── .env.example
│   ├── requirements.txt
│   ├── config.py                      # Neo4j, ChromaDB, model settings
│   ├── main.py                        # CLI entry point (index / chat)
│   ├── query_graph.py                 # Standalone graph query tool
│   ├── import_real_triples.py         # Batch-import production triples into Neo4j
│   ├── test.py                        # Neo4j connection test
│   ├── test_graph.py                  # Graph query test
│   ├── test_vector_connection.py      # Vector retrieval test
│   │
│   ├── api/
│   │   └── main.py                    # FastAPI wrapper (GET /health, POST /ask)
│   │
│   ├── data/
│   │   ├── sample_triples.json        # 17 illustrative demo triples
│   │   └── sample_documents.json      # 6 illustrative passages
│   │
│   ├── evaluation/
│   │   └── evaluate_retrieval.py      # Entity-link smoke test (3 questions)
│   │
│   ├── generation/
│   │   └── answer_generator.py        # Gemini generation or evidence-only output
│   │
│   ├── graph/
│   │   ├── neo4j_connection.py        # Neo4j driver wrapper
│   │   ├── graph_builder.py           # Import sample triples into Neo4j
│   │   ├── graph_queries.py           # Neighborhood retrieval (1-2 hop Cypher)
│   │   ├── entity_resolution.py       # Deterministic entity ID generation
│   │   └── schema.py                  # Neo4j constraint creation
│   │
│   └── retrieval/
│       ├── entity_extractor.py        # Entity linking (exact substring match)
│       ├── graph_retriever.py         # Graph search orchestrator
│       ├── vector_retriever.py        # ChromaDB + BGE-large-en-v1.5
│       ├── context_fusion.py          # Merge graph facts + vector passages
│       └── hybrid_graphrag.py         # Main retrieval orchestrator
```

---

## How It Works

### Extraction Pipeline (agri_kg_production)

1. **Chunking:** Input text is split into ~4,000-character work items at paragraph/sentence boundaries. Tables are split preserving header rows.
2. **LLM Extraction:** Each chunk is sent to the LLM (via OpenRouter) with a structured JSON schema enforcing allowed entity types and predicates.
3. **Adaptive Splitting:** If the LLM output is truncated, the chunk is recursively bisected and each half is re-extracted.
4. **Validation:** Each extracted triple is checked — entity types must be from the allowed set, predicates must match, and the evidence string must be a verbatim continuous substring of the source text.
5. **Checkpointing:** All progress is saved in SQLite. The process is fully resumable.

### Hybrid GraphRAG (agri_graphrag)

1. **Entity Linking:** Entity names from Neo4j are matched as substrings in the user's question.
2. **Graph Retrieval:** Matched entities are expanded via 1–2 hop Cypher traversal, returning connected FACT relationships.
3. **Vector Retrieval:** The question is embedded and searched against ChromaDB for semantically similar text passages.
4. **Context Fusion:** Graph facts and vector passages are deduplicated and merged.
5. **Answer Generation:** Combined context is either printed directly or sent to Gemini for a natural-language answer.

---

## Known Limitations

- Entity linking uses exact substring matching — no synonyms, fuzzy matching, or abbreviation handling.
- Graph retrieval is limited to a local 2-hop neighborhood — no multi-hop reasoning or query planning.
- All graph relationships use a generic `:FACT` edge type with a `predicate` property (not typed Neo4j relationship types).
- The evaluation script is a basic smoke test (3 questions), not a research-grade precision/recall evaluation.
- Sample facts are fictional/illustrative.

---

## License

This project is provided for educational and research purposes.
