from fastapi import APIRouter, HTTPException
from api.models.telemetry import TelemetryCreate
from api.db.cassandra import get_cassandra_session
from api.db.redis import get_redis
import json
from datetime import datetime

router = APIRouter(
    prefix="/telemetry",
    tags=["Telemetry Ingestion (Cassandra & Redis)"]
)

@router.post("/")
async def ingest_telemetry(data: TelemetryCreate):
    
    cassandra_session = get_cassandra_session()
    redis_client = get_redis()
    
    if not cassandra_session:
        raise HTTPException(status_code=500, detail="Cassandra session is unavailable")
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis client is unavailable")

    try:
        
        query = """
            INSERT INTO gridsense_ts.telemetry (asset_id, timestamp, power_kw, voltage_v, current_a)
            VALUES (?, ?, ?, ?, ?)
        """
        prepared = cassandra_session.prepare(query)
        
        cassandra_session.execute(prepared, (
            data.asset_id,
            data.timestamp,
            data.power_kw,
            data.voltage_v,
            data.current_a
        ))

        redis_key = f"latest:telemetry:{data.asset_id}"
        payload = {
            "timestamp": data.timestamp.isoformat(),
            "power_kw": data.power_kw,
            "voltage_v": data.voltage_v,
            "current_a": data.current_a
        }
        
        await redis_client.set(redis_key, json.dumps(payload), ex=86400)

        return {"status": "success", "message": f"Telemetry ingested for asset {data.asset_id}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest telemetry: {str(e)}")


@router.get("/{asset_id}/latest")
async def get_latest_telemetry(asset_id: str):
    redis_client = get_redis_client()
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis client is unavailable")

    redis_key = f"latest:telemetry:{asset_id}"
    cached_data = await redis_client.get(redis_key)

    if not cached_data:
        raise HTTPException(
            status_code=404, 
            detail=f"No real-time telemetry found in cache for asset {asset_id}. Device might be offline."
        )

    return json.loads(cached_data)