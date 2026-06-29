from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class NodeCreate(BaseModel):
    node_id: str = Field(..., description="Unique ID of the grid component")
    name: str = Field(..., description="Human readable name (e.g., Substation Alpha)")
    node_type: str = Field(..., description="Type: Substation, Transformer, Feeder, Relay, Meter")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata properties")

class RelationshipCreate(BaseModel):
    source_id: str = Field(..., description="The ID of the source node")
    target_id: str = Field(..., description="The ID of the target/downstream node")
    rel_type: str = Field(..., description="Type of edge: FEEDS, SUPPLIES, CONNECTS_TO")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Properties of the line/connection")

class AffectedNode(BaseModel):
    node_id: str
    node_type: str
    name: str
    depth: int

class FaultImpactResponse(BaseModel):
    origin_id: str
    affected_nodes: List[AffectedNode]
    total_affected: int

class GridPathStep(BaseModel):
    node_id: str
    node_type: str
    name: str

class RestorePathResponse(BaseModel):
    source_id: str
    target_id: str
    path_found: bool
    path: List[GridPathStep]