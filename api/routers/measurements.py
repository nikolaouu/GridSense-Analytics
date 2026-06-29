from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import List
from api.db.cassandra import get_cassandra_session

router = APIRouter(prefix="/measurements", tags=["Smart Meter Measurements (Cassandra)"])

class MeasurementInput(BaseModel):
    meter_id: str
    timestamp: datetime
    energy_kwh: float
    voltage: float
    frequency: float

class MeasurementResponse(BaseModel):
    meter_id: str
    timestamp: datetime
    energy_kwh: float
    voltage: float
    frequency: float

@router.post("", status_code=201)
async def log_measurement(data: MeasurementInput):
    session = get_cassandra_session()
    if not session:
        raise HTTPException(status_code=500, detail="Cassandra session is unavailable.")
    
    query = """
        INSERT INTO sensor_readings (sensor_id, reading_time, metric_type, value, unit, quality_flag)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    try:

        session.execute(query, (data.meter_id, data.timestamp, "energy_kwh", data.energy_kwh, "kWh", "GOOD"))
        return {"status": "success", "message": f"Measurement recorded for meter {data.meter_id}."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra write error: {str(e)}")

@router.get("/{meter_id}", response_model=List[MeasurementResponse])
async def get_meter_history(meter_id: str, limit: int = Query(50, le=1000)):
    session = get_cassandra_session()
    if not session:
        raise HTTPException(status_code=500, detail="Cassandra session is unavailable.")
    
    query = """
        SELECT sensor_id, reading_time, value 
        FROM sensor_readings 
        WHERE sensor_id = %s AND metric_type = 'energy_kwh'
        LIMIT %s
    """
    
    try:
        rows = session.execute(query, (meter_id, limit))
        results = []
        for row in rows:

            results.append(MeasurementResponse(
                meter_id=row.sensor_id,
                timestamp=row.reading_time,
                energy_kwh=row.value,
                voltage=230.0,
                frequency=50.0
            ))
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cassandra read error: {str(e)}")