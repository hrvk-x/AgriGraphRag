# AgriGraphRAG — runnable learning prototype

This is a separate prototype. It does not change your existing RAG project.

**Important:** Every bundled fact and passage is illustrative software-test data only. It is not verified agricultural knowledge or farming advice.

## What happens when you ask a question?

1. The entity linker looks for known entity names in your question.
2. The graph retriever asks Neo4j for facts connected to those entities (up to two hops).
3. The vector retriever embeds your question and searches passages in ChromaDB.
4. Context fusion combines the two evidence sources.
5. The answer layer prints the evidence. Gemini generation is optional.

This is an entity-centric hybrid GraphRAG prototype, not Microsoft's full GraphRAG community-summary/global-search architecture.

## Requirements

- Windows, Python 3.10 or 3.11
- Neo4j Desktop with a local database started
- Internet for installing Python packages and downloading the embedding model

## Step 1 — Neo4j

In Neo4j Desktop, create a local DBMS, set a password, start it, and open its Query/Browser view. Use the default Bolt address `bolt://localhost:7687`.

Use a dedicated empty database for this demo. The importer clears `:Entity` nodes before re-importing.

## Step 2 — Python setup (PowerShell)

Open PowerShell in this folder:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If activation is blocked in that terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Step 3 — Configure credentials

```powershell
Copy-Item .env.example .env
notepad .env
```

Put your Neo4j password in `NEO4J_PASSWORD`. Do not share `.env`.

## Step 4 — Build the graph

```powershell
python -m graph.graph_builder
```

Expected: `Imported 17 illustrative facts into Neo4j.`

In Neo4j Browser, run:

```cypher
MATCH (n:Entity)-[r:FACT]->(m:Entity)
RETURN n,r,m
LIMIT 50;
```

## Step 5 — Build the vector index

```powershell
python main.py index
```

The first run downloads `all-MiniLM-L6-v2`; allow a few minutes.

## Step 6 — Ask questions

```powershell
python main.py chat
```

Try:
- `What is ADT 36 linked to in the sample data?`
- `What pests are connected to Rice?`
- `What is connected to Maize?`
- `Tell me about Rice and its seasons.`

Type `exit` to quit. Without a Gemini key, the program prints retrieved evidence, which lets us inspect retrieval before generation.

## Optional — Gemini

Add your key to `.env` as `GEMINI_API_KEY=...`, restart the CLI, and ask a question. The generator is instructed to describe only demo relationships.

## Optional — API

```powershell
uvicorn api.main:app --reload
```

Open `http://127.0.0.1:8000/docs`, then test `POST /ask` with:

```json
{"question":"What is ADT 36 linked to?"}
```

## Inspect Neo4j

```cypher
MATCH (n:Entity) RETURN count(n) AS entities;
MATCH ()-[r:FACT]->() RETURN count(r) AS facts;
MATCH (s:Entity)-[r:FACT]->(o:Entity)
RETURN s.name,r.predicate,o.name,r.evidence;
```

## Later: use your extracted agricultural triples

Export your real triples with `subject`, `subject_type`, `predicate`, `object`, `object_type`, `evidence`, and optional `confidence`, `qualifiers`, `source`. Adapt the importer to your extraction output format and review the destructive clear step before loading. Do not run this demo importer on a shared or production database.

## Current limitations (we will improve these together)

- Entity linking is exact substring matching; it does not understand synonyms or misspellings.
- The graph query retrieves a local neighborhood; it does not yet plan complex multi-hop questions.
- All predicates are stored as a generic `FACT` relationship with a `predicate` property.
- The evaluation script is only a smoke test, not a research-grade precision/recall evaluation.
- Sample facts are fictional/illustrative.
