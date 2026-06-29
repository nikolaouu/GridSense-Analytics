#!/usr/bin/env python3
import asyncio
import sys
import os
import json
from datetime import datetime, timezone

# Εξασφάλιση ότι το root directory βρίσκεται στο path για τα imports της api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cassandra.util import uuid_from_time

# Εισαγωγή των αρχικοποιήσεων και των getters των DBs
from api.db.postgres import init_postgres_db, get_pg_pool
from api.db.mongo import init_mongo_db, get_mongo_db
from api.db.redis import init_redis_db, get_redis
from api.db.neo4j import init_neo4j_db, get_neo4j_driver
from api.db.cassandra import init_cassandra_db, get_cassandra_session


async def seed_postgres(pool):
    print(" seeding PostgreSQL (Consumers & Bills)...")
    async with pool.acquire() as conn:
        # 1. Εισαγωγή Καναλωτή με ON CONFLICT
        consumer_query = """
            INSERT INTO consumer_billing (consumer_name, email, billing_address, tariff_plan, meta_data)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (email) DO NOTHING;
        """
        await conn.execute(
            consumer_query,
            "Γιάννης Παπαδόπουλος",
            "giannis@gridsense.gr",
            "Δημοκρατίας 45, Λάρισα",
            "RESIDENTIAL",
            json.dumps({"phase_type": "three", "peak_kw_limit": 25.0, "tax_exempt": False})
        )

        # Ανάκτηση του account_id για συσχέτιση (αφού το serial ID μπορεί να διαφέρει)
        account_id = await conn.fetchval("SELECT account_id FROM consumer_billing WHERE email = $1", "giannis@gridsense.gr")
        
        # 2. Εισαγωγή Λογαριασμού με έλεγχο ύπαρξης (Idempotent Check)
        fixed_billing_date = datetime(2026, 6, 1, 10, 0, 0)
        bill_exists = await conn.fetchval(
            "SELECT 1 FROM bills WHERE customer_id = $1 AND billing_date = $2", 
            str(account_id), fixed_billing_date
        )
        
        if not bill_exists:
            bill_query = """
                INSERT INTO bills (customer_id, meter_id, total_kwh, amount_due, billing_date, status)
                VALUES ($1, $2, $3, $4, $5, $6);
            """
            await conn.execute(
                bill_query,
                str(account_id),
                "meter_larissa_101",
                420.5,
                84.10,
                fixed_billing_date,
                "PAID"
            )
            print("  Created missing seed bill record.")
        else:
            print("  Bill record already exists. Skipping insertion.")


async def seed_mongodb(db):
    print(" seeding MongoDB (Equipment Catalog)...")
    # Χρήση update_one με upsert=True για πλήρη ιδεμποτεντικότητα
    await db.catalog.update_one(
        {"asset_id": "meter_larissa_101"},
        {"$set": {
            "asset_id": "meter_larissa_101",
            "equipment_type": "Smart Meter",
            "manufacturer": "Schneider Electric",
            "generation": "Gen3-Smart",
            "specs": {"accuracy_class": "0.5S", "communication_module": "5G-NB-IoT", "firmware": "v3.2.1"}
        }},
        upsert=True
    )
    await db.catalog.update_one(
        {"asset_id": "trans_sub_01"},
        {"$set": {
            "asset_id": "trans_sub_01",
            "equipment_type": "Transformer",
            "manufacturer": "Siemens Energy",
            "generation": "EcoDesign II",
            "specs": {"kva_rating": 400, "cooling_type": "ONAN", "oil_volume_liters": 850}
        }},
        upsert=True
    )


def seed_cassandra(session):
    print(" seeding Cassandra (Time-Series Sensor Readings & Relay Events)...")
    
    # 1. Sensor Readings (Idempotent καθώς το PRIMARY KEY είναι ((sensor_id), reading_time))
    reading_query = """
        INSERT INTO sensor_readings (sensor_id, reading_time, metric_type, value, unit, quality_flag)
        VALUES (?, ?, ?, ?, ?, ?);
    """
    prepared_reading = session.prepare(reading_query)
    
    fixed_timestamps = [
        datetime(2026, 6, 29, 12, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 29, 13, 0, 0, tzinfo=timezone.utc),
    ]
    
    for ts in fixed_timestamps:
        session.execute(prepared_reading, ("meter_larissa_101", ts, "energy_kwh", 12.4, "kWh", 0))
        session.execute(prepared_reading, ("meter_larissa_101", ts, "voltage", 230.1, "V", 0))

    # 2. Relay Events (Χρήση σταθερού TimeUUID βασισμένο σε συγκεκριμένο timestamp)
    event_query = """
        INSERT INTO relay_events (feeder_id, event_time, relay_id, event_type, fault_type, current_kA)
        VALUES (?, ?, ?, ?, ?, ?);
    """
    prepared_event = session.prepare(event_query)
    
    fixed_epoch_time = 1782730000  # Σταθερό χρονικό σημείο μέσα στο 2026
    fixed_timeuuid = uuid_from_time(fixed_epoch_time)
    
    session.execute(prepared_event, ("feeder_larissa_1", fixed_timeuuid, "relay_lrs_04", "TRIP", "Line-to-Ground", 1.85))


async def seed_neo4j(driver):
    print(" seeding Neo4j (Grid Topology & Graphs)...")
    
    async def _tx_operations(tx):
        # 1. Δημιουργία / Ενημέρωση Κόμβων (MERGE)
        nodes = [
            {"node_id": "sub_larissa_main", "name": "Κεντρικός Υποσταθμός Λάρισας", "node_type": "Substation", "props": {"kv_level": 110.0}},
            {"node_id": "trans_sub_01", "name": "Μετασχηματιστής Διανομής 01", "node_type": "Transformer", "props": {"kva_capacity": 400}},
            {"node_id": "meter_larissa_101", "name": "Έξυπνος Μετρητής Καταναλωτή 101", "node_type": "Meter", "props": {"phase": "Three-Phase"}}
        ]
        
        node_cypher = """
            MERGE (n:GridNode {node_id: $node_id})
            ON CREATE SET n.name = $name, n.node_type = $node_type, n += $props
            ON MATCH SET n.name = $name, n.node_type = $node_type, n += $props
        """
        for node in nodes:
            await tx.run(node_cypher, node_id=node["node_id"], name=node["name"], node_type=node["node_type"], props=node["props"])

        # 2. Δημιουργία / Ενημέρωση Σχέσεων (MERGE)
        relationships = [
            {"source": "sub_larissa_main", "target": "trans_sub_01", "type": "SUPPLIES", "props": {"line_impedance": 0.12}},
            {"source": "trans_sub_01", "target": "meter_larissa_101", "type": "FEEDS", "props": {"cable_type": "Underground-Copper"}}
        ]
        
        for rel in relationships:
            rel_cypher = f"""
                MATCH (a:GridNode {{node_id: $source}}), (b:GridNode {{node_id: $target}})
                MERGE (a)-[r:{rel["type"]}]->(b)
                ON CREATE SET r += $props
                ON MATCH SET r += $props
            """
            await tx.run(rel_cypher, source=rel["source"], target=rel["target"], props=rel["props"])

    async with driver.session() as session:
        await session.execute_write(_tx_operations)


async def seed_redis(redis_client):
    print(" seeding Redis (Real-Time Caching)...")
    # Το SET αντικαθιστά άμεσα το κλειδί (Idempotent)
    redis_key = "latest:telemetry:meter_larissa_101"
    telemetry_payload = {
        "timestamp": "2026-06-29T13:00:00Z",
        "power_kw": 3.85,
        "voltage_v": 230.2,
        "current_a": 16.7
    }
    await redis_client.set(redis_key, json.dumps(telemetry_payload), ex=86400)


async def main():
    print("=== Starting Idempotent Data Seeding Engine for GridSense ===")
    
    try:
        # 1. Σύνδεση σε όλες τις βάσεις
        await init_postgres_db()
        await init_mongo_db()
        await init_redis_db()
        await init_neo4j_db()
        init_cassandra_db()
        
        # 2. Ανάκτηση clients/sessions
        pg_pool = get_pg_pool()
        mongo_db = get_mongo_db()
        redis_client = get_redis()
        neo4j_driver = get_neo4j_driver()
        cassandra_session = get_cassandra_session()
        
        await seed_postgres(pg_pool)
        await seed_mongodb(mongo_db)
        seed_cassandra(cassandra_session)
        await seed_neo4j(neo4j_driver)
        await seed_redis(redis_client)
        
        print("\n=== Seeding completed successfully and safely! (Idempotent) ===")
        
    except Exception as e:
        print(f"\nCRITICAL ERROR DURING SEEDING: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())