from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class EquipmentBase(BaseModel):
    asset_id: str = Field(..., description="Unique identifier matching the graph node")
    equipment_type: str = Field(..., description="e.g., Transformer, Switchgear, Meter")
    manufacturer: str
    generation: str
    specs: Dict[str, Any] = Field(default_factory=dict, description="Flexible heterogeneous metadata fields")

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentResponse(EquipmentBase):
    id: str = Field(..., alias="_id")