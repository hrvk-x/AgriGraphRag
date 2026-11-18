
from graph.neo4j_connection import Neo4jConnection

db = Neo4jConnection()

try:
    print("\n--- ENTITIES MATCHING TRY 3 ---")

    rows = db.run("""
        MATCH (n:Entity)
        WHERE toLower(n.name) CONTAINS 'try 3'
        RETURN n.name AS name, n.entity_id AS id
        LIMIT 20
    """)

    for row in rows:
        print(dict(row))

    print("\n--- RELATIONSHIPS CONNECTED TO TRY 3 ---")

    rows = db.run("""
        MATCH (s:Entity)-[r:FACT]->(o:Entity)
        WHERE toLower(s.name) CONTAINS 'try 3'
        RETURN s.name AS subject,
               r.predicate AS predicate,
               o.name AS object,
               r.evidence AS evidence
        LIMIT 20
    """)

    for row in rows:
        print(dict(row))

finally:
    db.close()
