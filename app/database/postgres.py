import psycopg2
from psycopg2.extras import RealDictCursor
import time
from app.config import settings

def get_postgres_conn():

    retries = 5
    while retries > 0:
        try:
            conn = psycopg2.connect(
                host=settings.POSTGRES_HOST,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                port=settings.POSTGRES_PORT,
                cursor_factory=RealDictCursor
            )
            return conn
        except psycopg2.OperationalError as e:
            print(f"PostgreSQL not ready yet, retrying... ({retries} left)")
            time.sleep(2)
            retries -= 1
    raise Exception("Could not connect to PostgreSQL")

def init_postgres_db():

    conn = get_postgres_conn()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consumer_billing (
            account_id SERIAL PRIMARY KEY,
            consumer_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            billing_address TEXT NOT NULL,
            tariff_plan VARCHAR(50) NOT NULL,
            meta_data JSONB, -- Εδώ θα αποθηκεύονται extra εύflexible πληροφορίες
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("PostgreSQL database initialized successfully!")
