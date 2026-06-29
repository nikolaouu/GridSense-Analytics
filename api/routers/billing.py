from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
import json

from api.db.postgres import get_pg_pool
from api.db.cassandra import get_cassandra_session
from api.models.billing import ConsumerCreate, ConsumerResponse, BillCalculateRequest, BillResponse

router = APIRouter(prefix="/billing", tags=["Billing & Cross-DB Analytics (PostgreSQL & Cassandra)"])


@router.post("/consumers", response_model=ConsumerResponse, status_code=201)
async def create_consumer(consumer: ConsumerCreate):
    pool = get_pg_pool()
    if not pool:
        raise HTTPException(status_code=500, detail="PostgreSQL pool is offline")

    query = """
        INSERT INTO consumer_billing (consumer_name, email, billing_address, tariff_plan, meta_data)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING account_id, consumer_name, email, billing_address, tariff_plan, meta_data, created_at;
    """
    
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                query,
                consumer.consumer_name,
                consumer.email,
                consumer.billing_address,
                consumer.tariff_plan,
                consumer.meta_data
            )
            return ConsumerResponse(
                account_id=row["account_id"],
                consumer_name=row["consumer_name"],
                email=row["email"],
                billing_address=row["billing_address"],
                tariff_plan=row["tariff_plan"],
                meta_data=row["meta_data"],
                created_at=row["created_at"]
            )
        except Exception as e:
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                raise HTTPException(status_code=400, detail="A consumer account with this email already exists.")
            raise HTTPException(status_code=500, detail=f"PostgreSQL Write Error: {str(e)}")


@router.post("/bills/calculate", response_model=BillResponse, status_code=201)
async def calculate_consumer_bill(request: BillCalculateRequest):
    pg_pool = get_pg_pool()
    cassandra_session = get_cassandra_session()
    
    if not pg_pool or not cassandra_session:
        raise HTTPException(status_code=500, detail="Required database engines are unavailable")
        
    async with pg_pool.acquire() as conn:
        consumer_row = await conn.fetchrow(
            "SELECT tariff_plan, meta_data FROM consumer_billing WHERE account_id = $1", 
            request.account_id
        )
        if not consumer_row:
            raise HTTPException(status_code=404, detail=f"Consumer account with ID {request.account_id} not found in PostgreSQL")
            
    tariff = consumer_row["tariff_plan"].upper()
    
    cassandra_query = """
        SELECT value FROM sensor_readings 
        WHERE sensor_id = ? AND metric_type = 'energy_kwh'
    """
    try:
        rows = cassandra_session.execute(cassandra_query, (request.sensor_id,))
        readings = [row.value for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra timeseries fetch error: {str(e)}")
        
    if not readings:
        raise HTTPException(
            status_code=422, 
            detail=f"Cannot generate bill. No 'energy_kwh' metrics found in Cassandra for sensor/meter '{request.sensor_id}'."
        )
    
    total_kwh = max(readings) - min(readings)
    if total_kwh <= 0:
        total_kwh = sum(readings)
        
    if tariff == "RESIDENTIAL":
        rate = 0.18
    elif tariff == "COMMERCIAL":
        rate = 0.24
    elif tariff == "INDUSTRIAL":
        rate = 0.14
    else:
        rate = 0.20
        
    amount_due = round(total_kwh * rate, 2)
    billing_date = datetime.now()
    status = "UNPAID"
    
    pg_insert_query = """
        INSERT INTO bills (customer_id, meter_id, total_kwh, amount_due, billing_date, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING bill_id, customer_id, meter_id, total_kwh, amount_due, billing_date, status;
    """
    
    async with pg_pool.acquire() as conn:
        try:
            bill_row = await conn.fetchrow(
                pg_insert_query,
                str(request.account_id),
                request.sensor_id,
                float(total_kwh),
                float(amount_due),
                billing_date,
                status
            )
            
            return BillResponse(
                bill_id=bill_row["bill_id"],
                customer_id=bill_row["customer_id"],
                meter_id=bill_row["meter_id"],
                total_kwh=bill_row["total_kwh"],
                amount_due=bill_row["amount_due"],
                billing_date=bill_row["billing_date"],
                status=bill_row["status"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PostgreSQL bill storage failure: {str(e)}")


@router.get("/consumers/{account_id}/bills", response_model=List[BillResponse])
async def get_consumer_bill_history(account_id: int):
    pool = get_pg_pool()
    if not pool:
        raise HTTPException(status_code=500, detail="PostgreSQL pool is offline")
        
    query = """
        SELECT bill_id, customer_id, meter_id, total_kwh, amount_due, billing_date, status
        FROM bills
        WHERE customer_id = $1
        ORDER BY billing_date DESC;
    """
    
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch(query, str(account_id))
            return [
                BillResponse(
                    bill_id=row["bill_id"],
                    customer_id=row["customer_id"],
                    meter_id=row["meter_id"],
                    total_kwh=row["total_kwh"],
                    amount_due=row["amount_due"],
                    billing_date=row["billing_date"],
                    status=row["status"]
                ) for row in rows
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PostgreSQL read error: {str(e)}")
        
@router.post("/bills/calculate", response_model=BillResponse, status_code=201)
async def calculate_consumer_bill(request: BillCalculateRequest):
    pool = get_pg_pool()
    cassandra_session = get_cassandra_session()
    if not pool or not cassandra_session:
        raise HTTPException(status_code=500, detail="Required database connections are offline")
    
    # 1. Ανάκτηση των μετρήσεων kwh από την Cassandra για τον συγκεκριμένο μετρητή
    cassandra_query = """
        SELECT value FROM sensor_readings 
        WHERE sensor_id = ? AND metric_type = 'energy_kwh'
    """
    try:
        prepared = cassandra_session.prepare(cassandra_query)
        rows = cassandra_session.execute(prepared, (request.sensor_id,))
        values = [row.value for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra fetch failure: {str(e)}")
    
    if not values:
        raise HTTPException(status_code=404, detail="No energy measurements found for this meter in Cassandra")
    
    # Υπολογισμός συνολικής κατανάλωσης (π.χ. άθροισμα ή max-min ανάλογα με τη λογική καταγραφής)
    total_kwh = sum(values)
    tariff_rate = 0.20  # Σταθερή χρέωση ανά kWh
    amount_due = total_kwh * tariff_rate
    billing_date = datetime.now()
    status = "UNPAID"
    
    pg_query = """
        INSERT INTO bills (customer_id, meter_id, total_kwh, amount_due, billing_date, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING bill_id, customer_id, meter_id, total_kwh, amount_due, billing_date, status;
    """
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                pg_query,
                str(request.account_id),
                request.sensor_id,
                total_kwh,
                amount_due,
                billing_date,
                status
            )
            return BillResponse(
                bill_id=row["bill_id"],
                customer_id=row["customer_id"],
                meter_id=row["meter_id"],
                total_kwh=row["total_kwh"],
                amount_due=row["amount_due"],
                billing_date=row["billing_date"],
                status=row["status"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PostgreSQL bill storage failure: {str(e)}")