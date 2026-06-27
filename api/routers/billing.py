from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import json
from datetime import datetime
from api.db.postgres import get_pg_pool
from api.db.redis import get_redis

router = APIRouter(
    prefix="/billing",
    tags=["Billing & Consumer Accounts (PostgreSQL)"]
)

class ConsumerCreate(BaseModel):
    consumer_name: str
    email: EmailStr
    billing_address: str
    tariff_plan: str
    meta_data: Optional[Dict[str, Any]] = None

@router.post("/consumers")
async def create_consumer(consumer: ConsumerCreate):
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        try:
            account_id = await conn.fetchval(
                """
                INSERT INTO consumer_billing (consumer_name, email, billing_address, tariff_plan, meta_data)
                VALUES ($1, $2, $3, $4, $5) RETURNING account_id;
                """,
                consumer.consumer_name, consumer.email, consumer.billing_address, consumer.tariff_plan, consumer.meta_data
            )
            return {"message": "Consumer account created successfully", "account_id": account_id}
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise HTTPException(status_code=400, detail="Email already exists")
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/consumers/{account_id}")
async def get_consumer(account_id: int):
    redis_client = get_redis()
    cache_key = f"consumer:{account_id}"

    if redis_client:
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                print(f"==> Cache HIT for {cache_key}")
                return json.loads(cached_data)
        except Exception as e:
            print(f"Redis cache read error: {e}")

    print(f"==> Cache MISS for {cache_key}. Querying PostgreSQL...")
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM consumer_billing WHERE account_id = $1;", account_id)
        if not row:
            raise HTTPException(status_code=404, detail="Consumer not found")
        
        res = dict(row)
        
        if isinstance(res.get("created_at"), datetime):
            res["created_at"] = res["created_at"].isoformat()

        if redis_client:
            try:
                await redis_client.setex(cache_key, 3600, json.dumps(res))
                print(f"==> Data cached in Redis for key {cache_key}")
            except Exception as e:
                print(f"Redis cache write error: {e}")

        return res