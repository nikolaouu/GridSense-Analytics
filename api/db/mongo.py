from motor.motor_asyncio import AsyncIOMotorClient
from api.config import settings

MONGO_URL = f"mongodb://{settings.MONGO_INITDB_ROOT_USERNAME}:{settings.MONGO_INITDB_ROOT_PASSWORD}@{settings.MONGO_HOST}:{settings.MONGO_PORT}"

_mongo_client = None
_db = None

async def init_mongo_db():
    global _mongo_client, _db
    _mongo_client = AsyncIOMotorClient(MONGO_URL)
    _db = _mongo_client["gridsense_catalog"]
    print("MongoDB client initialized (Async Motor).")

def get_mongo_db():
    global _db
    return _db