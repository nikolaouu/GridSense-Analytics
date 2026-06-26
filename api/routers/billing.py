from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import json
from api.db.postgres import get_pg_pool

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
            
            meta_data_json = json.dumps(consumer.meta_data) if consumer.meta_data else None
            account_id = await conn.fetchval(
                """
                INSERT INTO consumer_billing (consumer_name, email, billing_address, tariff_plan, meta_data)
                VALUES ($1, $2, $3, $4, $5) RETURNING account_id;
                """,
                consumer.consumer_name, consumer.email, consumer.billing_address, consumer.tariff_plan, meta_data_json
            
            )
            
            return {"message": "Consumer account created successfully", "account_id": account_id}
        
        except Exception as e:
            
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise HTTPException(status_code=400, detail="Email already exists")
            
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/consumers/{account_id}")
async def get_consumer(account_id: int):

    pool = get_pg_pool()

    async with pool.acquire() as conn:
        
        row = await conn.fetchrow("SELECT * FROM consumer_billing WHERE account_id = $1;", account_id)
        if not row:
            raise HTTPException(status_code=404, detail="Consumer not found")
        
        res = dict(row)
        
        if res.get("meta_data") and isinstance(res["meta_data"], str):
            res["meta_data"] = json.loads(res["meta_data"])
            
        return res