from fastapi import APIRouter, HTTPException, Body
from api.models.mongo import EquipmentCreate, EquipmentBase
from api.db.mongo import get_mongo_db
from typing import List

router = APIRouter(
    prefix="/equipment",
    tags=["Equipment Metadata Catalog (MongoDB)"]
)

@router.post("/", response_model=dict)
async def add_equipment(equipment: EquipmentCreate):

    db = get_mongo_db()
    
    existing = await db.catalog.find_one({"asset_id": equipment.asset_id})
    
    if existing:
        raise HTTPException(status_code=400, detail="Equipment with this asset_id already exists")
    
    doc = equipment.model_dump()
    result = await db.catalog.insert_one(doc)
    return {"message": "Equipment profile added successfully", "inserted_id": str(result.inserted_id)}

@router.get("/{asset_id}", response_model=dict)
async def get_equipment_profile(asset_id: str):

    db = get_mongo_db()
    doc = await db.catalog.find_one({"asset_id": asset_id})
    
    if not doc:
        raise HTTPException(status_code=404, detail="Equipment profile not found")
    
    doc["_id"] = str(doc["_id"])
    return doc