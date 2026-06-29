from sqlmodel import SQLModel, Field
import uuid

class ServiceBase(SQLModel):
    name: str
    price: float
    duration_minutes: int
    is_active: bool = True

class ServiceCreate(ServiceBase):
    tenant_id: uuid.UUID

class Service(ServiceBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
