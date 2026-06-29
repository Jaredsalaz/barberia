from sqlmodel import create_engine, SQLModel, Session, select
from .config import settings
from ..schemas import * # Importar todos los modelos para SQLModel
import uuid
from datetime import datetime

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        try:
            db_url = settings.DATABASE_URL
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            
            connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
            _engine = create_engine(db_url, echo=True, connect_args=connect_args)
        except Exception as e:
            print(f"[DB] Warning: Could not create engine with {settings.DATABASE_URL} - {e}")
            # Fallback a SQLite con archivo en /tmp
            print("[DB] Using SQLite file-based database at /tmp/balam.db")
            _engine = create_engine("sqlite:////tmp/balam.db", echo=True, connect_args={"check_same_thread": False})
    return _engine

def init_db():
    try:
        engine = get_engine()
        print("[DB] Creating tables...")
        SQLModel.metadata.create_all(engine)
        print("[DB] Tables created successfully")

        # Crear datos de prueba
        _create_test_data(engine)
    except Exception as e:
        print(f"[DB] Warning: Could not initialize database - {e}")
        import traceback
        traceback.print_exc()

def _create_test_data(engine):
    """Crear datos de prueba si no existen"""
    try:
        with Session(engine) as session:
            # Verificar si ya existe un tenant
            tenant = session.exec(select(Tenant)).first()
            if tenant:
                print("[DB] Test data already exists")
                return

            print("[DB] Creating test data...")

            # Usar ID fijo para el tenant principal
            TENANT_ID = uuid.UUID("1b4f6113-8bef-42d4-9409-0c143c8379a1")
            business_hours = {
                "monday": {"open": "09:00", "close": "17:00"},
                "tuesday": {"open": "09:00", "close": "17:00"},
                "wednesday": {"open": "09:00", "close": "17:00"},
                "thursday": {"open": "09:00", "close": "17:00"},
                "friday": {"open": "09:00", "close": "17:00"},
                "saturday": {"open": "10:00", "close": "13:00"},
                "sunday": None
            }
            tenant = Tenant(
                id=TENANT_ID,
                name="Balam Barber",
                slug="balam-barber",
                phone="1234567890",
                is_active=True,
                business_hours=business_hours,
                created_at=datetime.now()
            )
            session.add(tenant)
            session.flush() # Asegurar que el Tenant se cree antes que el barbero
            
            # Crear servicios por defecto vinculados al ID fijo
            services = [
                Service(id=uuid.uuid4(), tenant_id=TENANT_ID, name="Corte Clásico", price=350, duration_minutes=30),
                Service(id=uuid.uuid4(), tenant_id=TENANT_ID, name="Corte y Barba", price=500, duration_minutes=50),
                Service(id=uuid.uuid4(), tenant_id=TENANT_ID, name="Arreglo de Barba", price=200, duration_minutes=20)
            ]
            for s in services: session.add(s)

            # Crear barbero
            try:
                from .security import Security
                password_hash = Security.hash_password("123456")
            except:
                password_hash = "123456"

            # Usar un ID fijo para el barbero para que la App de Flutter no pierda la sesión
            BARBER_ID = uuid.UUID("e796b2ae-8bf7-4308-8264-1e0eebaacd15")
            barber = Barber(
                id=BARBER_ID,
                tenant_id=TENANT_ID,
                name="Paulo Londra",
                email="paulo@balambarber.com",
                password_hash=password_hash,
                is_active=True
            )
            session.add(barber)
            session.commit()
            print("[DB] Production-ready data created successfully")

    except Exception as e:
        print(f"[DB] Warning: Could not create test data - {e}")
        import traceback
        traceback.print_exc()

def get_session():
    engine = get_engine()
    with Session(engine) as session:
        yield session
