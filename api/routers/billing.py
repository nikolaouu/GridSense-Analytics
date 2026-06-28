from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from datetime import datetime
from api.db.cassandra import get_cassandra_session
import json
from typing import Optional, Dict, Any
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


class BillResponse(BaseModel):
    bill_id: int
    customer_id: str
    meter_id: str
    total_kwh: float
    amount_due: float
    billing_date: datetime
    status: str


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
    

@router.post("/generate/{customer_id}", response_model=BillResponse)
async def generate_bill(customer_id: str, meter_id: str = Query(..., description="The smart meter ID to calculate consumption from")):

    cassandra_session = get_cassandra_session()
    pg_conn = get_postgres_conn()
    
    if not cassandra_session or not pg_conn:
        raise HTTPException(status_code=500, detail="Database connections unavailable.")
        
    cassandra_query = """
        SELECT energy_kwh FROM meter_readings 
        WHERE meter_id = %s 
        LIMIT 1000
    """

    try:

        rows = cassandra_session.execute(cassandra_query, (meter_id,))
        readings = [row.energy_kwh for row in rows]
        
        if not readings:
            raise HTTPException(status_code=404, detail=f"No consumption measurements found in Cassandra for meter {meter_id}.")
        
        total_kwh = max(readings) - min(readings)
        if total_kwh <= 0:
            total_kwh = sum(readings)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra fetch error: {str(e)}")

    rate_per_kwh = 0.20
    amount_due = round(total_kwh * rate_per_kwh, 2)
    billing_date = datetime.now()
    status = "UNPAID"

    pg_query = """
        INSERT INTO bills (customer_id, meter_id, total_kwh, amount_due, billing_date, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id;
    """

    try:
        
        with pg_conn.cursor() as cursor:
            cursor.execute(pg_query, (customer_id, meter_id, total_kwh, amount_due, billing_date, status))
            bill_id = cursor.fetchone()[0]
            pg_conn.commit()

    except Exception as e:
        
        pg_conn.rollback()
        raise HTTPException(status_code=500, detail=f"PostgreSQL write error: {str(e)}")

    return BillResponse(
        bill_id=bill_id,
        customer_id=customer_id,
        meter_id=meter_id,
        total_kwh=total_kwh,
        amount_due=amount_due,
        billing_date=billing_date,
        status=status
    )
