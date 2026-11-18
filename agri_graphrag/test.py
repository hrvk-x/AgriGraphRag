from dotenv import load_dotenv
import os
from pathlib import Path
from neo4j import GraphDatabase

# Always load the .env located beside this Python file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE")

print("Loaded .env:", env_path)
print("URI:", uri)
print("Username:", username)
print("Database:", database)
print("Password loaded:", bool(password))

driver = GraphDatabase.driver(uri, auth=(username, password))

try:
    driver.verify_connectivity()

    with driver.session(database=database) as session:
        result = session.run("RETURN 'GraphRAG connected!' AS message")
        print("\nSUCCESS:", result.single()["message"])

except Exception as e:
    print("\nCONNECTION FAILED:")
    print(e)

finally:
    driver.close()