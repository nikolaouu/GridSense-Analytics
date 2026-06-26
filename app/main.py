from fastapi import FastAPI
from app.database.postgres import init_postgres_db
from app.routers import billing
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    print("Starting up GridSense API...")
    init_postgres_db()

    yield

    print("Shutting down GridSense API...")

app = FastAPI(
    title="GridSense API",
    description="Advanced Data Management - Smart Power Grid Analytics Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(billing.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to GridSense Smart Grid Analytics Platform API"
    }