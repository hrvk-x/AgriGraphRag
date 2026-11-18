from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
class Neo4jConnection:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    def verify(self):
        self.driver.verify_connectivity()
    def close(self):
        self.driver.close()
    def run(self, query, parameters=None):
        with self.driver.session(database=NEO4J_DATABASE) as session:
            return list(session.run(query, parameters or {}))
