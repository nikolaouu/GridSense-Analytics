from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import Dict, Any, Optional, Annotated


def convert_object_id(v: Any) -> str:
    if v is None:
        return v
    return str(v)


PyObjectId = Annotated[str, BeforeValidator(convert_object_id)]

class EquipmentBase(BaseModel):
    asset_id: str = Field(..., description="Unique identifier matching the graph node")
    equipment_type: str = Field(..., description="e.g., Transformer, Switchgear, Meter")
    manufacturer: str
    generation: str
    specs: Dict[str, Any] = Field(default_factory=dict, description="Flexible heterogeneous metadata fields")

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentResponse(EquipmentBase):

    id: PyObjectId = Field(..., alias="_id")


    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )