from neo4j import AsyncGraphDatabase
import asyncio
from api.config import settings

_neo4j_driver = None

async def init_neo4j_db():

    global _neo4j_driver
    
    auth_parts = settings.NEO4J_AUTH.split("/")
    username = auth_parts[0]
    password = auth_parts[1] if len(auth_parts) > 1 else ""

    uri = f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}"
    
    retries = 5
    while retries > 0:
        try:

            _neo4j_driver = AsyncGraphDatabase.driver(uri, auth=(username, password))

            await _neo4j_driver.verify_connectivity()
            print("Neo4j Graph Database connection initialized successfully.")
            return
        
        except Exception as e:

            print(f"Neo4j not ready, retrying... ({retries} left). Error: {e}")
            await asyncio.sleep(3)

            retries -= 1
            
    raise Exception("Could not connect to Neo4j")

def get_neo4j_driver():
    global _neo4j_driver
    return _neo4j_driver

async def close_neo4j_db():
    global _neo4j_driver
    if _neo4j_driver:
        await _neo4j_driver.close()
        print("Neo4j connection closed.")
        