from api.core.db import get_engine
from sqlalchemy import text

def migrate():
    engine = get_engine()
    with engine.connect() as conn:
        print("Añadiendo columna is_whatsapp_verified...")
        conn.execute(text("ALTER TABLE booking ADD COLUMN IF NOT EXISTS is_whatsapp_verified BOOLEAN DEFAULT FALSE"))
        print("Añadiendo columna fcm_token...")
        conn.execute(text("ALTER TABLE barber ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(255) DEFAULT NULL"))
        print("Añadiendo columnas de geolocalización y anuncios a tenant...")
        conn.execute(text("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS address VARCHAR(500) DEFAULT NULL"))
        conn.execute(text("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION DEFAULT NULL"))
        conn.execute(text("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION DEFAULT NULL"))
        conn.execute(text("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS image_url VARCHAR(1000) DEFAULT NULL"))
        conn.execute(text("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS description VARCHAR(1000) DEFAULT NULL"))
        conn.execute(text("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP DEFAULT NULL"))
        conn.commit()
        print("¡Migración completada con éxito!")

if __name__ == "__main__":
    migrate()
