from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from app.database.postgres import get_postgres_conn

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
def create_consumer(consumer: ConsumerCreate):

    conn = get_postgres_conn()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO consumer_billing (consumer_name, email, billing_address, tariff_plan, meta_data)
            VALUES (%s, %s, %s, %s, %s) RETURNING account_id;
            """,
            (consumer.consumer_name, consumer.email, consumer.billing_address, consumer.tariff_plan, psycopg2.extras.Json(consumer.meta_data))
        )

        account_id = cursor.fetchone()['account_id']
        conn.commit()
        
        return {"message": "Consumer account created successfully", "account_id": account_id}
    
    except psycopg2.errors.UniqueViolation:

        conn.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")
    
    finally:
        cursor.close()
        conn.close()

@router.get("/consumers/{account_id}")
def get_consumer(account_id: int):

    conn = get_postgres_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM consumer_billing WHERE account_id = %s;", (account_id,))
    consumer = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not consumer:
        raise HTTPException(status_code=404, detail="Consumer not found")
    
    return consumer