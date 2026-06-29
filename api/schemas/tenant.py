from sqlmodel import SQLModel, Field, Column, JSON
from datetime import datetime
import uuid
from typing import Optional, Dict, Any

class TenantBase(SQLModel):
    name: str
    slug: str = Field(unique=True, index=True)
    phone: Optional[str] = None
    is_active: bool = True
    business_hours: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_featured: bool = False
    image_url: Optional[str] = None
    description: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None

class TenantCreate(TenantBase):
    pass

class Tenant(TenantBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
