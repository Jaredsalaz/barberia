from sqlmodel import SQLModel, Field
from datetime import datetime
import uuid

class ClientBase(SQLModel):
    name: str
    phone: str = Field(index=True)

class ClientCreate(ClientBase):
    tenant_id: uuid.UUID

class Client(ClientBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
