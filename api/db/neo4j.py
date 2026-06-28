import asyncio
from neo4j import AsyncGraphDatabase
from api.config import settings

_driver = None

async def init_neo4j_db():
    global _driver
    
    _driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI, 
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    
    retries = 15
    while retries > 0:
        try:

            await _driver.verify_connectivity()
            print("Neo4j Database initialized and verified successfully.")
            return
        except Exception as e:

            print(f"Neo4j is not ready or DNS is resolving... ({retries} left). Error: {e}")
            await asyncio.sleep(4)
            retries -= 1
            
    raise Exception("Could not connect to Neo4j after multiple attempts.")

def get_neo4j_driver():
    global _driver
    return _driver