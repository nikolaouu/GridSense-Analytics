from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class RelayEventCreate(BaseModel):
    feeder_id: str = Field(..., description="The ID of the feeder zone where fault happened (Partition Key)")
    relay_id: str = Field(..., description="The ID of the reporting protective relay")
    event_type: str = Field(..., description="e.g., 'TRIP', 'CLOSE', 'WARN'")
    fault_type: Optional[str] = Field("NONE", description="e.g., 'Line-to-Ground', 'Three-Phase', 'NONE'")
    current_kA: float = Field(0.0, description="The measured fault current in kilo-Amperes")

class RelayEventResponse(BaseModel):
    feeder_id: str
    event_time: str = Field(..., description="TimeUUID string representation")
    relay_id: str
    event_type: str
    fault_type: str
    current_kA: float