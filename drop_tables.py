from sqlmodel import SQLModel
from api.core.db import engine
# Importar todos los modelos para que SQLModel los conozca
from api.schemas.tenant import Tenant
from api.schemas.barber import Barber
from api.schemas.service import Service
from api.schemas.client import Client
from api.schemas.booking import Booking

print("Eliminando tablas existentes...")
SQLModel.metadata.drop_all(engine)
print("Tablas eliminadas.")
