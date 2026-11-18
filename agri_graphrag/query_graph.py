
import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load the project's environment variables
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

DATABASE = os.getenv("NEO4J_DATABASE", "triples")


def search_graph(question):
    # Extract searchable words from the user's question
    terms = [
        word.lower().strip(".,?!")
        for word in question.split()
        if len(word.strip(".,?!")) >= 2
    ]

    query = """
    MATCH (e:Entity)
    WHERE any(term IN $terms WHERE toLower(e.name) CONTAINS term)

    WITH e
    LIMIT 10

    OPTIONAL MATCH (e)-[r:FACT]-(other:Entity)

    RETURN e.name AS entity,
           e.entity_type AS entity_type,
           collect(DISTINCT {
               predicate: r.predicate,
               related_entity: other.name,
               related_type: other.entity_type,
               evidence: r.evidence
           }) AS facts
    """

    with driver.session(database=DATABASE) as session:
        results = session.run(query, terms=terms)

        found = False

        for record in results:
            found = True
            print("\nMATCHED ENTITY:", record["entity"])
            print("TYPE:", record["entity_type"])

            for fact in record["facts"]:
                if fact["related_entity"] is not None:
                    print(
                        f"  -- {fact['predicate']} --> "
                        f"{fact['related_entity']} "
                        f"({fact['related_type']})"
                    )
                    if fact["evidence"]:
                        print("     Evidence:", fact["evidence"][:300])

        if not found:
            print("\nNo matching entities found in the graph.")


if __name__ == "__main__":
    try:
        print("AGRICULTURAL GRAPH QUERY SYSTEM")
        print("Type 'exit' to quit.")

        while True:
            question = input("\nYou: ").strip()

            if question.lower() == "exit":
                break

            if question:
                search_graph(question)

    finally:
        driver.close()
