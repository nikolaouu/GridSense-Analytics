from fastapi import APIRouter, HTTPException, Query
from typing import List
from api.db.neo4j import get_neo4j_driver
from api.models.graph import NodeCreate, RelationshipCreate, FaultImpactResponse, AffectedNode, RestorePathResponse, GridPathStep

router = APIRouter(prefix="/grid", tags=["Grid Topology & Graph Queries (Neo4j)"])

async def _node_exists(tx, node_id: str) -> bool:
    query = "MATCH (n) WHERE n.node_id = $node_id RETURN count(n) > 0 AS exists"
    result = await tx.run(query, node_id=node_id)
    record = await result.single()
    return record["exists"] if record else False



async def _tx_create_node(tx, cypher, node_id, name, properties):
    res = await tx.run(cypher, node_id=node_id, name=name, properties=properties)
    await res.consume()
    return True

async def _tx_create_relationship(tx, cypher, source_id, target_id, properties):
    res = await tx.run(cypher, source_id=source_id, target_id=target_id, properties=properties)
    await res.consume()
    return True

async def _tx_get_fault_impact(tx, cypher, node_id, depth):
    res = await tx.run(cypher, node_id=node_id, depth=depth)
    return await res.data()

async def _tx_get_restore_path(tx, cypher, source_id, target_id):
    res = await tx.run(cypher, source_id=source_id, target_id=target_id)
    record = await res.single()
    if not record:
        return None
    
    path_steps = []
    for n in record["path_nodes"]:
        path_steps.append({
            "node_id": n.get("node_id"),
            "node_type": list(n.labels)[0] if n.labels else "Unknown",
            "name": n.get("name", "")
        })
    return path_steps


@router.post("/nodes", status_code=201)
async def create_grid_node(node: NodeCreate):
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j driver is unavailable")
    
    safe_label = "".join([c for c in node.node_type if c.isalnum()])
    cypher = f"""
        MERGE (n:{safe_label} {{node_id: $node_id}})
        SET n.name = $name
        SET n += $properties
        RETURN n.node_id AS node_id
    """
    
    async with driver.session() as session:
        try:
            await session.execute_write(_tx_create_node, cypher, node.node_id, node.name, node.properties)
            return {"status": "success", "message": f"Node '{node.node_id}' created/updated successfully with label :{safe_label}."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Neo4j write error: {str(e)}")

@router.post("/relationships", status_code=201)
async def create_grid_relationship(rel: RelationshipCreate):
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j driver is unavailable")
    
    safe_rel_type = "".join([c for c in rel.rel_type if c.isalnum() or c == '_']).upper()
    cypher = f"""
        MATCH (a) WHERE a.node_id = $source_id
        MATCH (b) WHERE b.node_id = $target_id
        MERGE (a)-[r:{safe_rel_type}]->(b)
        SET r += $properties
        RETURN type(r)
    """
    
    async with driver.session() as session:
        source_exists = await session.execute_read(_node_exists, rel.source_id)
        target_exists = await session.execute_read(_node_exists, rel.target_id)
        
        if not source_exists or not target_exists:
            raise HTTPException(status_code=404, detail="Source or target node not found in graph topology")
            
        try:
            await session.execute_write(_tx_create_relationship, cypher, rel.source_id, rel.target_id, rel.properties)
            return {"status": "success", "message": f"Relationship [{safe_rel_type}] established successfully."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Neo4j relationship error: {str(e)}")


@router.get("/fault-impact/{node_id}", response_model=FaultImpactResponse)
async def get_fault_impact(node_id: str, max_depth: int = Query(6, ge=1, le=15)):
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j driver is unavailable")
        
    cypher = """
        MATCH (origin {node_id: $node_id})
        MATCH (origin)-[:FEEDS|SUPPLIES|CONNECTS_TO*1..$depth]->(downstream)
        RETURN labels(downstream)[0] AS node_type,
               downstream.node_id AS node_id,
               downstream.name AS name,
               length(shortestPath((origin)-[:FEEDS|SUPPLIES|CONNECTS_TO*]-(downstream))) AS depth
        ORDER BY depth, node_id
    """
    
    async with driver.session() as session:
        node_exists = await session.execute_read(_node_exists, node_id)
        if not node_exists:
            raise HTTPException(status_code=404, detail=f"Origin node '{node_id}' not found in topology graph")
            
        try:
            records = await session.execute_read(_tx_get_fault_impact, cypher, node_id, max_depth)
            
            affected = [
                AffectedNode(
                    node_id=rec["node_id"],
                    node_type=rec["node_type"] or "Unknown",
                    name=rec["name"] or "",
                    depth=rec["depth"]
                ) for rec in records
            ]
            
            return FaultImpactResponse(
                origin_id=node_id,
                affected_nodes=affected,
                total_affected=len(affected)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Neo4j Graph Traversal error: {str(e)}")


@router.get("/restore-paths", response_model=RestorePathResponse)
async def get_restore_path(source_id: str, target_id: str):
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j driver is unavailable")
        
    cypher = """
        MATCH (start {node_id: $source_id}), (end {node_id: $target_id})
        MATCH p = shortestPath((start)-[:FEEDS|SUPPLIES|CONNECTS_TO*1..15]-(end))
        RETURN nodes(p) AS path_nodes
    """
    
    async with driver.session() as session:
        try:
            path_steps_data = await session.execute_read(_tx_get_restore_path, cypher, source_id, target_id)
            
            if not path_steps_data:
                return RestorePathResponse(source_id=source_id, target_id=target_id, path_found=False, path=[])
                
            path_steps = [
                GridPathStep(
                    node_id=item["node_id"],
                    node_type=item["node_type"],
                    name=item["name"]
                ) for item in path_steps_data
            ]
            
            return RestorePathResponse(
                source_id=source_id,
                target_id=target_id,
                path_found=True,
                path=path_steps
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Neo4j Pathfinding error: {str(e)}")
        
@router.post("/nodes", status_code=201)
async def create_grid_node(node: NodeCreate):
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j driver is unavailable")
    
    cypher = """
        MERGE (n:GridNode {node_id: $node_id})
        ON CREATE SET n.name = $name, n.node_type = $node_type, n += $properties
        ON MATCH SET n.name = $name, n.node_type = $node_type, n += $properties
        RETURN n
    """
    async with driver.session() as session:
        try:
            await session.execute_write(_tx_create_node, cypher, node.node_id, node.name, node.properties)
            return {"status": "success", "message": f"Node {node.node_id} integrated into topology successfully."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Neo4j node creation failure: {str(e)}")


@router.post("/relationships", status_code=201)
async def create_grid_relationship(rel: RelationshipCreate):
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j driver is unavailable")
    
    cypher = f"""
        MATCH (a {{node_id: $source_id}}), (b {{node_id: $target_id}})
        MERGE (a)-[r:{rel.rel_type}]->(b)
        SET r += $properties
        RETURN r
    """
    async with driver.session() as session:
        try:
            await session.execute_write(_tx_create_relationship, cypher, rel.source_id, rel.target_id, rel.properties)
            return {"status": "success", "message": f"Relationship {rel.rel_type} established successfully."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Neo4j relationship failure: {str(e)}")


@router.get("/fault-impact", response_model=FaultImpactResponse)
async def get_fault_impact(node_id: str, depth: int = Query(3, ge=1, le=10)):
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j driver is unavailable")
    
    cypher = """
        MATCH (start {node_id: $node_id})
        MATCH p = (start)-[:FEEDS|SUPPLIES*1..10]->(downstream)
        WHERE length(p) <= $depth
        RETURN downstream.node_id AS node_id, downstream.node_type AS node_type, downstream.name AS name, length(p) AS depth
    """
    async with driver.session() as session:
        try:
            records = await session.execute_read(_tx_get_fault_impact, cypher, node_id, depth)
            affected = [
                AffectedNode(
                    node_id=r["node_id"],
                    node_type=r["node_type"],
                    name=r["name"],
                    depth=r["depth"]
                ) for r in records
            ]
            return FaultImpactResponse(
                origin_id=node_id,
                affected_nodes=affected,
                total_affected=len(affected)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Neo4j fault impact query failure: {str(e)}")