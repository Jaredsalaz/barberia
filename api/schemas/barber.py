from sqlmodel import SQLModel, Field
import uuid
from typing import Optional

class BarberBase(SQLModel):
    name: str
    is_active: bool = True
    email: Optional[str] = None
    password_hash: Optional[str] = None
    fcm_token: Optional[str] = Field(default=None, nullable=True)

class BarberCreate(BarberBase):
    tenant_id: uuid.UUID

class Barber(BarberBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
