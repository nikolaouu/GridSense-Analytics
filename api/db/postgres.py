# api/db/postgres.py
import asyncpg
import asyncio
from api.config import settings

_pool = None

async def init_postgres_db():
    global _pool
    retries = 5
    while retries > 0:
        try:
            _pool = await asyncpg.create_pool(
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                min_size=2,
                max_size=10
            )
            
            async with _pool.acquire() as connection:
                await connection.execute("""
                    CREATE TABLE IF NOT EXISTS consumer_billing (
                        account_id SERIAL PRIMARY KEY,
                        consumer_name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        billing_address TEXT NOT NULL,
                        tariff_plan VARCHAR(50) NOT NULL,
                        meta_data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            print("PostgreSQL Database initialized with asyncpg pool.")
            return
        except Exception as e:
            print(f"PostgreSQL not ready, retrying... ({retries} left). Error: {e}")
            await asyncio.sleep(2)
            retries -= 1
            
    raise Exception("Could not connect to PostgreSQL")

def get_pg_pool():
    global _pool
    return _pool