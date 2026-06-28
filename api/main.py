from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.db.postgres import init_postgres_db
from api.db.mongo import init_mongo_db
from api.db.redis import init_redis_db
from api.db.neo4j import init_neo4j_db

from api.routers.billing import router as billing_router
from api.routers.equipment import router as equipment_router
from api.routers.topology import router as topology_router
from api.db.cassandra import init_cassandra_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing distributed database connections...")
    try:
        await init_postgres_db()
        await init_mongo_db()
        await init_redis_db()
        await init_neo4j_db()
        init_cassandra_db()
        
    except Exception as e:
        print(f"CRITICAL ERROR DURING LIFESPAN STARTUP: {e}")
        raise e
    yield
    print("Shutting down GridSense API...")

app = FastAPI(
    title="GridSense API",
    description="Advanced Data Management - Smart Power Grid Analytics Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(billing_router)
app.include_router(equipment_router)
app.include_router(topology_router)

@app.get("/")
def read_root():

    return {
        "status": "online",
        "message": "Welcome to GridSense Smart Grid Analytics Platform API"
    }