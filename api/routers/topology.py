from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from api.db.neo4j import get_neo4j_driver

router = APIRouter(prefix="/topology", tags=["Network Topology (Neo4j)"])

class NodeCreate(BaseModel):
    asset_id: str
    asset_type: str  # Substation, Transformer, SmartMeter
    location: str

class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    rel_type: str = "FEEDS"

@router.post("/nodes", status_code=201)
async def create_grid_node(node: NodeCreate):
    
    driver = get_neo4j_driver()
    query = """
    MERGE (n:GridAsset {id: $asset_id})
    SET n.type = $asset_type, n.location = $location
    RETURN n
    """
    async with driver.session() as session:
        await session.run(query, asset_id=node.asset_id, asset_type=node.asset_type, location=node.location)
        return {"status": "success", "message": f"Asset {node.asset_id} ({node.asset_type}) created/updated successfully."}

@router.post("/relationships", status_code=201)
async def create_grid_relationship(rel: RelationshipCreate):

    driver = get_neo4j_driver()

    query = """
    MATCH (source:GridAsset {id: $source_id})
    MATCH (target:GridAsset {id: $target_id})
    MERGE (source)-[r:FEEDS]->(target)
    RETURN r
    """
    async with driver.session() as session:
        
        result = await session.run(query, source_id=rel.source_id, target_id=rel.target_id)
        info = await result.consume()
        
        if info.counters.relationships_created == 0:

            
            raise HTTPException(status_code=404, detail="Source or Target node not found, or relationship already exists.")
        return {"status": "success", "message": f"Line created: {rel.source_id} -> FEEDS -> {rel.target_id}"}

@router.get("/trace-downstream/{asset_id}")
async def trace_downstream(asset_id: str):

    driver = get_neo4j_driver()
    query = """
    MATCH (start:GridAsset {id: $asset_id})-[r:FEEDS*]->(downstream:GridAsset)
    RETURN downstream.id AS id, downstream.type AS type, downstream.location AS location
    """
    
    async with driver.session() as session:
        result = await session.run(query, asset_id=asset_id)
        records = await result.data()
        
        if not records:

            return {
                "asset_id": asset_id,
                "affected_nodes_count": 0,
                "affected_meters": [],
                "all_affected_nodes": []
            }
            
        affected_meters = [r["id"] for r in records if r["type"] == "SmartMeter"]
        
        return {
            "asset_id": asset_id,
            "affected_nodes_count": len(records),
            "affected_meters_count": len(affected_meters),
            "affected_meters": affected_meters,
            "all_affected_nodes": records
        }