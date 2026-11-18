def create_constraints(db):
    db.run("""
    CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
    FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE
    """)
