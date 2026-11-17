import os
import subprocess
from pathlib import Path
from datetime import datetime

from app.database.connection import DATABASE_CONFIG


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RESPALDOS_DIR = (
    BASE_DIR /
    "backups"
)

RESPALDOS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CREAR RESPALDO
# ============================================================

def crear_respaldo():

    nombre_base = DATABASE_CONFIG.get(
        "dbname"
    ) or DATABASE_CONFIG.get(
        "database"
    )

    usuario = DATABASE_CONFIG.get(
        "user"
    )

    host = DATABASE_CONFIG.get(
        "host",
        "localhost"
    )

    port = str(
        DATABASE_CONFIG.get(
            "port",
            5432
        )
    )

    password = DATABASE_CONFIG.get(
        "password"
    )


    if not nombre_base:

        raise Exception(
            "No se encontró el nombre de la base de datos."
        )


    fecha = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


    nombre_archivo = (
        f"SICAE_respaldo_{fecha}.backup"
    )


    ruta_backup = (
        RESPALDOS_DIR /
        nombre_archivo
    )


    # ========================================================
    # VARIABLE DE CONTRASEÑA
    # ========================================================

    entorno = os.environ.copy()

    if password:

        entorno[
            "PGPASSWORD"
        ] = str(password)


    # ========================================================
    # EJECUTAR PG_DUMP
    # ========================================================

    comando = [

        "pg_dump",

        "-h",
        host,

        "-p",
        port,

        "-U",
        usuario,

        "-F",
        "c",

        "-f",
        str(ruta_backup),

        nombre_base

    ]


    try:

        resultado = subprocess.run(

            comando,

            env=entorno,

            capture_output=True,

            text=True,

            timeout=300

        )


    except FileNotFoundError:

        raise Exception(
            "No se encontró pg_dump. "
            "Verifica que PostgreSQL esté instalado "
            "y que su carpeta bin esté en PATH."
        )


    if resultado.returncode != 0:

        if ruta_backup.exists():

            ruta_backup.unlink()

        raise Exception(
            resultado.stderr.strip()
            or "No se pudo crear el respaldo."
        )


    if not ruta_backup.exists():

        raise Exception(
            "El respaldo no fue generado."
        )


    return ruta_backup


# ============================================================
# OBTENER RESPALDOS
# ============================================================

def obtener_respaldos():

    respaldos = []


    for archivo in RESPALDOS_DIR.glob(
        "*.backup"
    ):

        try:

            tamaño = archivo.stat().st_size

            tamaño_mb = round(
                tamaño / (1024 * 1024),
                2
            )


            respaldos.append({

                "nombre":
                    archivo.name,

                "tamaño":
                    tamaño_mb,

                "fecha":
                    datetime.fromtimestamp(
                        archivo.stat().st_mtime
                    ).strftime(
                        "%d/%m/%Y %H:%M:%S"
                    ),

                "ruta":
                    archivo

            })


        except Exception:

            continue


    respaldos.sort(

        key=lambda x: x["ruta"].stat().st_mtime,

        reverse=True

    )


    return respaldos


# ============================================================
# ELIMINAR RESPALDO
# ============================================================

def eliminar_respaldo(
    nombre_archivo
):

    nombre = Path(
        nombre_archivo
    ).name


    if not nombre.endswith(
        ".backup"
    ):

        return False


    ruta = (
        RESPALDOS_DIR /
        nombre
    )


    if not ruta.exists():

        return False


    ruta.unlink()

    return True