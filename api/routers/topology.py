import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.db.neo4j import get_neo4j_driver
from api.db.redis import get_redis  # <-- Εισαγωγή του Redis client

router = APIRouter(prefix="/topology", tags=["Network Topology (Neo4j)"])

class NodeCreate(BaseModel):
    asset_id: str
    asset_type: str
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
        
        redis_client = get_redis()

        if redis_client:
            await redis_client.delete(f"topology:trace:{node.asset_id}")
            
        return {"status": "success", "message": f"Asset {node.asset_id} created/updated."}

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
            raise HTTPException(status_code=404, detail="Source or Target node not found.")
        
        redis_client = get_redis()
        
        if redis_client:
            await redis_client.delete(f"topology:trace:{rel.source_id}")
            
        return {"status": "success", "message": f"Line created: {rel.source_id} -> FEEDS -> {rel.target_id}"}

@router.get("/trace-downstream/{asset_id}")
async def trace_downstream(asset_id: str):
    
    redis_client = get_redis()
    cache_key = f"topology:trace:{asset_id}"
    
    if redis_client:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            print(f"CACHE HIT: Returning topology trace for {asset_id} from Redis.")
            return json.loads(cached_data)
    
    print(f"CACHE MISS: Querying Neo4j for topology trace of {asset_id}.")
    driver = get_neo4j_driver()
    query = """
    MATCH (start:GridAsset {id: $asset_id})-[r:FEEDS*]->(downstream:GridAsset)
    RETURN downstream.id AS id, downstream.type AS type, downstream.location AS location
    """
    
    async with driver.session() as session:
        result = await session.run(query, asset_id=asset_id)
        records = await result.data()
        
        affected_meters = [r["id"] for r in records if r["type"] == "SmartMeter"]
        
        response_data = {
            "asset_id": asset_id,
            "affected_nodes_count": len(records),
            "affected_meters_count": len(affected_meters),
            "affected_meters": affected_meters,
            "all_affected_nodes": records,
            "cached": True
        }
        
        if redis_client and records:
            await redis_client.setex(cache_key, 300, json.dumps(response_data))
            
        response_data["cached"] = False
        return response_data