from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import uuid

class BookingBase(SQLModel):
    appointment_date: datetime
    status: str = Field(default="pending") # pending, confirmed, cancelled, completed
    is_whatsapp_verified: bool = Field(default=False)

class BookingCreate(BookingBase):
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    service_id: uuid.UUID
    barber_id: Optional[uuid.UUID] = None

class Booking(BookingBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    client_id: uuid.UUID = Field(foreign_key="client.id")
    service_id: uuid.UUID = Field(foreign_key="service.id")
    barber_id: Optional[uuid.UUID] = Field(default=None, foreign_key="barber.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
