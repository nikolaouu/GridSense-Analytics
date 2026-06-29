from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class SensorReadingCreate(BaseModel):
    sensor_id: str = Field(..., description="The unique identifier of the sensor/meter")
    reading_time: datetime = Field(..., description="The UTC timestamp of the measurement")
    metric_type: str = Field(..., description="e.g., 'voltage', 'current', 'power_factor', 'temp', 'power_kw'")
    value: float
    unit: str
    quality_flag: int = Field(0, ge=0, le=2, description="0=good, 1=suspect, 2=bad")

class SensorReadingResponse(BaseModel):
    sensor_id: str
    reading_time: datetime
    metric_type: str
    value: float
    unit: str
    quality_flag: int

class SensorSummaryResponse(BaseModel):
    sensor_id: str
    latest_reading: Optional[SensorReadingResponse] = None
    stats_1h: Dict[str, Any] = Field(..., description="Aggregated metrics for the last 1 hour")
    cached_at: datetime