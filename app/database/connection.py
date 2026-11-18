import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

DATABASE_CONFIG = {
    "host": os.getenv("DATABASE_HOST", "localhost"),
    "port": int(os.getenv("DATABASE_PORT", "5432")),
    "dbname": os.getenv("DATABASE_NAME", "sicae"),
    "user": os.getenv("DATABASE_USER", "postgres"),
    "password": os.getenv("DATABASE_PASSWORD", ""),
    "options": "-c timezone=America/Mexico_City",
}


def probar_conexion():
    try:
        with psycopg.connect(**DATABASE_CONFIG) as conexion:
            print("=================================")
            print("CONEXIÓN A POSTGRESQL EXITOSA")
            print(f"Base de datos: {DATABASE_CONFIG['dbname']}")
            print("=================================")
            return True

    except Exception as error:
        print("=================================")
        print("ERROR DE CONEXIÓN A POSTGRESQL")
        print(error)
        print("=================================")
        return False
