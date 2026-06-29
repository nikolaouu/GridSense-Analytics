from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.db.mongo import init_mongo_db
from api.db.redis import init_redis_db
from api.db.neo4j import init_neo4j_db
from api.db.postgres import init_postgres_db
from api.db.cassandra import init_cassandra_db

from api.routers.billing import router as billing_router
from api.routers.equipment import router as equipment_router
from api.routers.grid import router as grid_router
from api.routers.sensors import router as sensors_router
from api.routers.alerts import router as alerts_router
from api.routers.measurements import router as measurements_router
from api.routers.telemetry import router as telemetry_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing distributed database connections based on assignment specs...")
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
    description="Advanced Data Management - Smart Power Grid Analytics Platform (Official Implementation)",
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(billing_router)
app.include_router(equipment_router)
app.include_router(grid_router)
app.include_router(sensors_router)
app.include_router(alerts_router)
app.include_router(measurements_router)
app.include_router(telemetry_router)

@app.get("/")
def read_root():
    return {
        "status": "running",
        "platform": "GridSense Smart Grid Analytics"
    }