from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from api.db.neo4j import get_neo4j_driver

router = APIRouter(
    prefix="/topology",
    tags=["Grid Topology & Network (Neo4j Graph)"]
)

class NodeCreate(BaseModel):
    asset_id: str = Field(..., description="Unique ID for the grid asset")
    node_type: str = Field(..., description="Type of node: Substation, Transformer, or Meter")
    name: str

class EdgeCreate(BaseModel):
    source_id: str = Field(..., description="Asset ID of the source node")
    target_id: str = Field(..., description="Asset ID of the target node")
    rel_type: str = Field("FEEDS", description="Type of relationship, e.g., FEEDS, CONNECTED_TO")

@router.post("/nodes")
async def create_node(node: NodeCreate):

    driver = get_neo4j_driver()

    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j driver not initialized")

    label = node.node_type.strip().replace(" ", "_")
    if label not in ["Substation", "Transformer", "Meter"]:
        raise HTTPException(status_code=400, detail="Invalid node_type. Choose from Substation, Transformer, Meter.")

    query = f"""
    MERGE (n:{label} {{asset_id: $asset_id}})
    ON CREATE SET n.name = $name, n.created_at = timestamp()
    RETURN n.asset_id as asset_id, n.name as name;
    """

    async with driver.session() as session:
        try:
            result = await session.run(query, asset_id=node.asset_id, name=node.name)
            record = await result.single()
            if record:
                return {"message": "Grid node created or verified successfully", "node": dict(record)}
            raise HTTPException(status_code=400, detail="Could not create node")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/edges")
async def create_edge(edge: EdgeCreate):
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j driver not initialized")

    rel_type = edge.rel_type.strip().upper()

    query = f"""
    MATCH (a {{asset_id: $source_id}}), (b {{asset_id: $target_id}})
    MERGE (a)-[r:{rel_type}]->(b)
    RETURN a.asset_id as source, b.asset_id as target, type(r) as relationship;
    """

    async with driver.session() as session:

        try:
            
            result = await session.run(query, source_id=edge.source_id, target_id=edge.target_id)
            record = await result.single()
            
            if record:
                return {"message": "Topology relationship created successfully", "edge": dict(record)}
            
            raise HTTPException(status_code=404, detail="Source or Target node not found in the graph")
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))