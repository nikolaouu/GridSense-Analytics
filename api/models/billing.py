from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ConsumerCreate(BaseModel):
    consumer_name: str = Field(..., description="Full name of the grid consumer")
    email: EmailStr = Field(..., description="Unique contact email")
    billing_address: str = Field(..., description="Physical billing address")
    tariff_plan: str = Field(..., description="Pricing profile, e.g., 'RESIDENTIAL', 'COMMERCIAL', 'INDUSTRIAL'")
    meta_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Dynamic JSONB metadata: phase_type (single/three), peak_kw_limit, tax_exempt status"
    )

class ConsumerResponse(BaseModel):
    account_id: int
    consumer_name: str
    email: EmailStr
    billing_address: str
    tariff_plan: str
    meta_data: Optional[Dict[str, Any]]
    created_at: datetime

class BillCalculateRequest(BaseModel):
    account_id: int = Field(..., description="The relational PostgreSQL account ID")
    sensor_id: str = Field(..., description="The Cassandra smart meter ID associated with this user")

class BillResponse(BaseModel):
    bill_id: int
    customer_id: str
    meter_id: str
    total_kwh: float
    amount_due: float
    billing_date: datetime
    status: str