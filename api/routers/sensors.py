from fastapi import APIRouter, HTTPException, Query
from typing import List, Union, Optional
from datetime import datetime, timedelta, timezone
from api.db.cassandra import get_cassandra_session
from api.db.redis import get_redis
from api.models.cassandra import SensorReadingCreate, SensorReadingResponse, SensorSummaryResponse
import json

router = APIRouter(prefix="/sensors", tags=["Sensors & High-Rate Ingestion (Cassandra & Redis)"])

@router.post("/readings", status_code=201)
async def ingest_sensor_readings(payload: Union[SensorReadingCreate, List[SensorReadingCreate]]):
    session = get_cassandra_session()
    if not session:
        raise HTTPException(status_code=500, detail="Cassandra session is unavailable")
    
    readings = [payload] if isinstance(payload, SensorReadingCreate) else payload
    
    query = """
        INSERT INTO sensor_readings (sensor_id, reading_time, metric_type, value, unit, quality_flag)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        prepared = session.prepare(query)
        for r in readings:
            session.execute(prepared, (
                r.sensor_id,
                r.reading_time,
                r.metric_type,
                float(r.value),
                r.unit,
                int(r.quality_flag)
            ))
        return {"status": "success", "message": f"Successfully ingested {len(readings)} reading(s)."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra batch write error: {str(e)}")


@router.get("/{sensor_id}/readings", response_model=List[SensorReadingResponse])
async def get_sensor_readings(
    sensor_id: str,
    limit: int = Query(50, ge=1, le=1000),
    from_time: Optional[datetime] = None
):
    session = get_cassandra_session()
    if not session:
        raise HTTPException(status_code=500, detail="Cassandra session is unavailable")
    
    if from_time:
        query = """
            SELECT sensor_id, reading_time, metric_type, value, unit, quality_flag 
            FROM sensor_readings 
            WHERE sensor_id = ? AND reading_time >= ?
            LIMIT ?
        """
        params = (sensor_id, from_time, limit)
    else:
        query = """
            SELECT sensor_id, reading_time, metric_type, value, unit, quality_flag 
            FROM sensor_readings 
            WHERE sensor_id = ?
            LIMIT ?
        """
        params = (sensor_id, limit)
        
    try:
        rows = session.execute(query, params)
        return [
            SensorReadingResponse(
                sensor_id=row.sensor_id,
                reading_time=row.reading_time,
                metric_type=row.metric_type,
                value=row.value,
                unit=row.unit,
                quality_flag=row.quality_flag
            ) for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra read error: {str(e)}")


@router.get("/{sensor_id}/summary", response_model=SensorSummaryResponse)
async def get_sensor_summary(sensor_id: str):

    redis_client = get_redis()
    cassandra_session = get_cassandra_session()
    
    if not redis_client or not cassandra_session:
        raise HTTPException(status_code=500, detail="Database clients are unavailable")
        
    redis_key = f"cache:sensor:summary:{sensor_id}"
    
    try:
        cached_data = await redis_client.get(redis_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        print(f"Redis hit warning: {e}") 
        
    try:

        latest_query = """
            SELECT sensor_id, reading_time, metric_type, value, unit, quality_flag 
            FROM sensor_readings WHERE sensor_id = ? LIMIT 1
        """
        latest_row = cassandra_session.execute(latest_query, (sensor_id,)).one()
        
        latest_obj = None
        if latest_row:
            latest_obj = {
                "sensor_id": latest_row.sensor_id,
                "reading_time": latest_row.reading_time.isoformat(),
                "metric_type": latest_row.metric_type,
                "value": latest_row.value,
                "unit": latest_row.unit,
                "quality_flag": latest_row.quality_flag
            }
            
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        stats_query = """
            SELECT value FROM sensor_readings 
            WHERE sensor_id = ? AND reading_time >= ?
        """
        rows_1h = cassandra_session.execute(stats_query, (sensor_id, one_hour_ago))
        values = [row.value for row in rows_1h]
        
        if values:
            stats = {
                "avg_value": round(sum(values) / len(values), 3),
                "max_value": max(values),
                "min_value": min(values),
                "count": len(values)
            }
        else:
            stats = {"avg_value": 0.0, "max_value": 0.0, "min_value": 0.0, "count": 0}
            
        response_json = {
            "sensor_id": sensor_id,
            "latest_reading": latest_obj,
            "stats_1h": stats,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        
        await redis_client.set(redis_key, json.dumps(response_json), ex=30)
        
        return response_json
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database aggregation error: {str(e)}")
    
from datetime import timezone

@router.get("/summary/{sensor_id}", response_model=SensorSummaryResponse)
async def get_sensor_summary(sensor_id: str):
    redis_client = get_redis()
    cassandra_session = get_cassandra_session()
    
    if not redis_client or not cassandra_session:
        raise HTTPException(status_code=500, detail="Database/Cache systems are offline")
    
    redis_key = f"summary:sensor:{sensor_id}"
    
    try:
        cached_data = await redis_client.get(redis_key)
        if cached_data:
            return SensorSummaryResponse(**json.loads(cached_data))
    except Exception as e:
        print(f"Redis hit warning: {e}")
        
    latest_query = """
        SELECT sensor_id, reading_time, metric_type, value, unit, quality_flag 
        FROM sensor_readings 
        WHERE sensor_id = ? 
        LIMIT 1
    """
    try:
        prepared_latest = cassandra_session.prepare(latest_query)
        latest_rows = cassandra_session.execute(prepared_latest, (sensor_id,))
        latest_row = latest_rows.one()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra query failure: {str(e)}")
        
    latest_obj = None
    if latest_row:
        latest_obj = SensorReadingResponse(
            sensor_id=latest_row.sensor_id,
            reading_time=latest_row.reading_time,
            metric_type=latest_row.metric_type,
            value=latest_row.value,
            unit=latest_row.unit,
            quality_flag=latest_row.quality_flag
        )
        
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    stats_query = """
        SELECT value FROM sensor_readings 
        WHERE sensor_id = ? AND reading_time >= ?
    """
    try:
        prepared_stats = cassandra_session.prepare(stats_query)
        rows_1h = cassandra_session.execute(prepared_stats, (sensor_id, one_hour_ago))
        values = [row.value for row in rows_1h]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra stats aggregation failure: {str(e)}")
        
    if values:
        stats = {
            "avg_value": round(sum(values) / len(values), 3),
            "max_value": max(values),
            "min_value": min(values),
            "count": len(values)
        }
    else:
        stats = {"avg_value": 0.0, "max_value": 0.0, "min_value": 0.0, "count": 0}
        
    response_obj = SensorSummaryResponse(
        sensor_id=sensor_id,
        latest_reading=latest_obj,
        stats_1h=stats,
        cached_at=datetime.now(timezone.utc)
    )
    
    try:
        await redis_client.set(redis_key, response_obj.model_dump_json(), ex=60)
    except Exception as e:
        print(f"Redis write warning: {e}")
        
    return response_obj