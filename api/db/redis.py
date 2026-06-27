import redis.asyncio as aioredis
import asyncio
from api.config import settings

_redis_client = None

async def init_redis_db():
    
    global _redis_client
    
    redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}"
    
    retries = 5
    while retries > 0:
        try:
            _redis_client = aioredis.from_url(redis_url, decode_responses=True)
            await _redis_client.ping()
            print("Redis Database initialized and authenticated successfully.")
            return
        except Exception as e:
            print(f"Redis not ready or auth failed, retrying... ({retries} left). Error: {e}")
            await asyncio.sleep(2)
            retries -= 1
            
    raise Exception("Could not connect to Redis")

def get_redis():
    global _redis_client
    return _redis_client