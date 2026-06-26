from fastapi import FastAPI
from api.db.postgres import init_postgres_db
from api.db.mongo import init_mongo_db

from api.routers.billing import router as billing_router
from api.routers.equipment import router as equipment_router

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing distributed database connections...")
    try:
        await init_postgres_db()
        await init_mongo_db()
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

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to GridSense Smart Grid Analytics Platform API"
    }