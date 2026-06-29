import uuid
from datetime import datetime, timedelta
from sqlmodel import Session
from sqlalchemy import text
from api.core.db import get_engine, init_db
from api.schemas.tenant import Tenant
from api.schemas.barber import Barber
from api.schemas.service import Service
from api.schemas.client import Client
from api.schemas.booking import Booking
from api.core.security import Security

engine = get_engine()

def seed_database():
    with Session(engine) as session:
        # Limpiar datos antiguos para evitar duplicados en el seed
        print("Limpiando base de datos...")
        session.exec(text("TRUNCATE TABLE booking CASCADE"))
        session.exec(text("TRUNCATE TABLE client CASCADE"))
        session.exec(text("TRUNCATE TABLE service CASCADE"))
        session.exec(text("TRUNCATE TABLE barber CASCADE"))
        session.exec(text("TRUNCATE TABLE tenant CASCADE"))
        session.commit()

        # 1. Crear Tenants (Barberías)
        print("Creando Tenants...")
        
        # Sucursal Centro - Destacada (is_featured = True)
        tenant_centro = Tenant(
            name="Balam Barber Centro",
            slug="balam-barber-centro",
            phone="+52 961 123 4561",
            address="Av. Central Poniente 345, Centro Histórico, Tuxtla Gutiérrez",
            latitude=16.7528,
            longitude=-93.1158,
            is_featured=True,
            image_url="https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=600&q=80",
            description="Nuestra sucursal insignia en el corazón de la ciudad. Experiencia de corte tradicional y tratamientos de toalla caliente premium.",
            business_hours={
                "monday": {"open": "09:00", "close": "18:00"},
                "tuesday": {"open": "09:00", "close": "18:00"},
                "wednesday": {"open": "09:00", "close": "18:00"},
                "thursday": {"open": "09:00", "close": "18:00"},
                "friday": {"open": "09:00", "close": "18:00"},
                "saturday": {"open": "09:00", "close": "16:00"},
                "sunday": None
            }
        )

        # Sucursal Norte - Estándar (is_featured = False)
        tenant_norte = Tenant(
            name="Balam Barber Norte",
            slug="balam-barber-norte",
            phone="+52 961 123 4562",
            address="Blvd. Belisario Domínguez 1240, Norte Poniente, Tuxtla Gutiérrez",
            latitude=16.7628,
            longitude=-93.1358,
            is_featured=False,
            image_url="https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=600&q=80",
            description="Espacio moderno y dinámico especializado en estilos urbanos, texturas y coloración capilar de vanguardia.",
            business_hours={
                "monday": {"open": "10:00", "close": "20:00"},
                "tuesday": {"open": "10:00", "close": "20:00"},
                "wednesday": {"open": "10:00", "close": "20:00"},
                "thursday": {"open": "10:00", "close": "20:00"},
                "friday": {"open": "10:00", "close": "20:00"},
                "saturday": {"open": "10:00", "close": "18:00"},
                "sunday": None
            }
        )

        # Shelby Grooming Co - Destacada (is_featured = True)
        tenant_shelby = Tenant(
            name="Shelby Grooming Co.",
            slug="shelby-grooming-co",
            phone="+52 961 123 4563",
            address="Plaza Las Américas Local 14, Tuxtla Gutiérrez",
            latitude=16.7428,
            longitude=-93.0958,
            is_featured=True,
            image_url="https://images.unsplash.com/photo-1585747860715-2ba37e788b70?auto=format&fit=crop&w=600&q=80",
            description="Cuidado clásico para caballeros exigentes. Inspirado en el estilo británico clásico con cortes de tijera impecables y perfilado de barba.",
            business_hours={
                "monday": {"open": "09:00", "close": "19:00"},
                "tuesday": {"open": "09:00", "close": "19:00"},
                "wednesday": {"open": "09:00", "close": "19:00"},
                "thursday": {"open": "09:00", "close": "19:00"},
                "friday": {"open": "09:00", "close": "19:00"},
                "saturday": {"open": "10:00", "close": "15:00"},
                "sunday": None
            }
        )

        session.add(tenant_centro)
        session.add(tenant_norte)
        session.add(tenant_shelby)
        session.commit()
        session.refresh(tenant_centro)
        session.refresh(tenant_norte)
        session.refresh(tenant_shelby)

        # 2. Crear Barberos
        print("Creando Barberos...")
        # Barberos Centro
        barber1 = Barber(
            name="Arthur Shelby",
            email="arthur@balam.com",
            password_hash=Security.hash_password("password123"),
            tenant_id=tenant_centro.id
        )
        barber2 = Barber(
            name="Thomas Shelby",
            email="thomas@balam.com",
            password_hash=Security.hash_password("password456"),
            tenant_id=tenant_centro.id
        )
        # Barbero Norte
        barber3 = Barber(
            name="Dante Salas",
            email="dante@balam.com",
            password_hash=Security.hash_password("password789"),
            tenant_id=tenant_norte.id
        )
        # Barbero Shelby
        barber4 = Barber(
            name="Marco Vidal",
            email="marco@shelby.com",
            password_hash=Security.hash_password("passwordabc"),
            tenant_id=tenant_shelby.id
        )

        session.add(barber1)
        session.add(barber2)
        session.add(barber3)
        session.add(barber4)
        session.commit()
        session.refresh(barber1)
        session.refresh(barber2)
        session.refresh(barber3)
        session.refresh(barber4)

        # 3. Crear Servicios
        print("Creando Servicios...")
        # Servicios Centro
        s_centro_1 = Service(name="Corte Clásico", price=350.0, duration_minutes=45, tenant_id=tenant_centro.id)
        s_centro_2 = Service(name="Corte y Barba", price=500.0, duration_minutes=60, tenant_id=tenant_centro.id)
        s_centro_3 = Service(name="Arreglo de Barba", price=200.0, duration_minutes=30, tenant_id=tenant_centro.id)
        
        # Servicios Norte
        s_norte_1 = Service(name="Fade Premium", price=240.0, duration_minutes=40, tenant_id=tenant_norte.id)
        s_norte_2 = Service(name="Barba + Perfilado", price=180.0, duration_minutes=30, tenant_id=tenant_norte.id)
        s_norte_3 = Service(name="Paquete Urbano", price=380.0, duration_minutes=60, tenant_id=tenant_norte.id)

        # Servicios Shelby
        s_shelby_1 = Service(name="Corte de Tijera Clásico", price=400.0, duration_minutes=50, tenant_id=tenant_shelby.id)
        s_shelby_2 = Service(name="Afeitado Tradicional Navaja", price=300.0, duration_minutes=40, tenant_id=tenant_shelby.id)
        s_shelby_3 = Service(name="Grooming Completo Shelby", price=650.0, duration_minutes=80, tenant_id=tenant_shelby.id)

        session.add(s_centro_1)
        session.add(s_centro_2)
        session.add(s_centro_3)
        session.add(s_norte_1)
        session.add(s_norte_2)
        session.add(s_norte_3)
        session.add(s_shelby_1)
        session.add(s_shelby_2)
        session.add(s_shelby_3)
        session.commit()

        # 4. Crear Clientes
        print("Creando Clientes...")
        client1 = Client(name="Bruce Wayne", phone="555-000-0001", tenant_id=tenant_centro.id)
        client2 = Client(name="Tony Stark", phone="555-000-0002", tenant_id=tenant_centro.id)
        client3 = Client(name="Clark Kent", phone="555-000-0003", tenant_id=tenant_centro.id)
        client4 = Client(name="Johan Ulloa", phone="966 593 8297", tenant_id=tenant_centro.id)
        session.add(client1)
        session.add(client2)
        session.add(client3)
        session.add(client4)
        session.commit()
        session.refresh(client1)
        session.refresh(client2)
        session.refresh(client3)
        session.refresh(client4)

        # 5. Crear Reservas (Bookings)
        print("Creando Reservas...")
        now = datetime.now()
        booking1 = Booking(
            appointment_date=now + timedelta(days=1, hours=2),
            status="confirmed",
            tenant_id=tenant_centro.id,
            client_id=client1.id,
            service_id=s_centro_2.id,
            barber_id=barber1.id
        )
        booking2 = Booking(
            appointment_date=now + timedelta(days=2, hours=4),
            status="pending",
            tenant_id=tenant_centro.id,
            client_id=client2.id,
            service_id=s_centro_1.id,
            barber_id=barber2.id
        )
        booking3 = Booking(
            appointment_date=now - timedelta(days=1), # Reserva pasada
            status="completed",
            tenant_id=tenant_centro.id,
            client_id=client3.id,
            service_id=s_centro_3.id,
            barber_id=barber1.id
        )
        booking4 = Booking(
            appointment_date=now + timedelta(days=1, hours=4),
            status="pending",
            tenant_id=tenant_centro.id,
            client_id=client4.id,
            service_id=s_centro_2.id,
            barber_id=barber1.id
        )
        session.add(booking1)
        session.add(booking2)
        session.add(booking3)
        session.add(booking4)
        session.commit()

        print("¡Base de datos poblada con éxito con múltiples sucursales y datos PRO!")

if __name__ == "__main__":
    from sqlalchemy import text
    seed_database()
