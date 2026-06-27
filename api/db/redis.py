import redis.asyncio as aioredis
import asyncio
from api.config import settings

_redis_client = None

async def init_redis_db():
    global _redis_client
    retries = 5
    while retries > 0:
        try:
            _redis_client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            
            await _redis_client.ping()
            print("Redis connection initialized successfully (redis.asyncio).")
            return
        except Exception as e:
            print(f"Redis not ready, retrying... ({retries} left). Error: {e}")
            await asyncio.sleep(2)
            retries -= 1
            
    raise Exception("Could not connect to Redis")

def get_redis():
    global _redis_client
    return _redis_client