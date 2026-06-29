# create_tables.py
from api.core.db import init_db

if __name__ == "__main__":
    print("Creando tablas en la base de datos...")
    init_db()
    print("¡Tablas creadas con éxito!")
