from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
from cassandra.util import uuid_from_time
from api.db.cassandra import get_cassandra_session
from api.db.redis import get_redis
from api.models.alerts import RelayEventCreate, RelayEventResponse
import json
import time

router = APIRouter(prefix="/alerts", tags=["Alerting & Real-Time Failure Tracking (Pub/Sub)"])


@router.post("/relay-events", status_code=201)
async def trigger_relay_event(event: RelayEventCreate):
    cassandra_session = get_cassandra_session()
    redis_client = get_redis()
    
    if not cassandra_session or not redis_client:
        raise HTTPException(status_code=500, detail="Database connections are offline")
        
    current_timeuuid = uuid_from_time(time.time())
    
    query = """
        INSERT INTO relay_events (feeder_id, event_time, relay_id, event_type, fault_type, current_kA)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        prepared = cassandra_session.prepare(query)
        cassandra_session.execute(prepared, (
            event.feeder_id,
            current_timeuuid,
            event.relay_id,
            event.event_type,
            event.fault_type,
            float(event.current_kA)
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra log failure: {str(e)}")
        
    alert_payload = {
        "feeder_id": event.feeder_id,
        "event_time": str(current_timeuuid),
        "relay_id": event.relay_id,
        "event_type": event.event_type,
        "fault_type": event.fault_type,
        "current_kA": event.current_kA,
        "severity": "CRITICAL" if event.event_type == "TRIP" and event.current_kA > 1.5 else "WARNING"
    }
    
    try:
        await redis_client.publish("grid:alerts", json.dumps(alert_payload))
    except Exception as e:
        print(f"Redis Pub/Sub broadcast warning: {e}")
        
    return {
        "status": "alert_triggered", 
        "event_timeuuid": str(current_timeuuid),
        "broadcast_channel": "grid:alerts"
    }


@router.get("/feeder/{feeder_id}", response_model=List[RelayEventResponse])
async def get_feeder_alerts(feeder_id: str, limit: int = Query(20, ge=1, le=100)):
    cassandra_session = get_cassandra_session()
    if not cassandra_session:
        raise HTTPException(status_code=500, detail="Cassandra session is unavailable")
        
    query = """
        SELECT feeder_id, event_time, relay_id, event_type, fault_type, current_kA 
        FROM relay_events 
        WHERE feeder_id = ? 
        LIMIT ?
    """
    try:
        rows = cassandra_session.execute(query, (feeder_id, limit))
        return [
            RelayEventResponse(
                feeder_id=row.feeder_id,
                event_time=str(row.event_time),
                relay_id=row.relay_id,
                event_type=row.event_type,
                fault_type=row.fault_type,
                current_kA=row.current_kA
            ) for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra retrieval error: {str(e)}")