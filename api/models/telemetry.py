from pydantic import BaseModel, Field
from datetime import datetime

class TelemetryCreate(BaseModel):
    asset_id: str = Field(..., description="The unique identifier of the sensor/asset")
    timestamp: datetime = Field(..., description="The UTC timestamp of the measurement")
    power_kw: float = Field(..., description="Active power consumption/generation in kW")
    voltage_v: float = Field(..., description="Line voltage in Volts")
    current_a: float = Field(..., description="Current in Amperes")