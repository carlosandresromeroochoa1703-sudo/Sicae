import os
import shutil
import subprocess

from pathlib import Path
from datetime import datetime

from app.database.connection import DATABASE_CONFIG


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parents[2]


BACKUPS_DIR = (
    BASE_DIR /
    "backups"
)


# ============================================================
# CREAR CARPETA DE RESPALDOS
# ============================================================

BACKUPS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# RUTA DE PG_DUMP
# ============================================================

PG_DUMP = (
    os.getenv("PG_DUMP_PATH")
    or shutil.which("pg_dump")
    or r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
)


# ============================================================
# GENERAR RESPALDO
# ============================================================

def generar_respaldo():

    fecha = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )


    nombre_archivo = (
        f"sicae_backup_{fecha}.sql"
    )


    ruta_respaldo = (
        BACKUPS_DIR /
        nombre_archivo
    )


    # ========================================================
    # CONFIGURACIÓN POSTGRESQL
    # ========================================================

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


    dbname = DATABASE_CONFIG.get(
        "dbname",
        "sicae"
    )


    user = DATABASE_CONFIG.get(
        "user",
        "postgres"
    )


    password = DATABASE_CONFIG.get(
        "password",
        ""
    )


    # ========================================================
    # VARIABLES DE ENTORNO
    # ========================================================

    entorno = os.environ.copy()


    entorno["PGPASSWORD"] = (
        password
    )


    # ========================================================
    # COMANDO PG_DUMP
    # ========================================================

    comando = [

        PG_DUMP,

        "-h",
        host,

        "-p",
        port,

        "-U",
        user,

        "-d",
        dbname,

        "-F",
        "p",

        "-f",
        str(ruta_respaldo)

    ]


    # ========================================================
    # EJECUTAR RESPALDO
    # ========================================================

    try:

        resultado = subprocess.run(

            comando,

            env=entorno,

            capture_output=True,

            text=True,

            encoding="utf-8",

            errors="replace"

        )


        # ====================================================
        # VERIFICAR ERROR
        # ====================================================

        if resultado.returncode != 0:

            if ruta_respaldo.exists():

                ruta_respaldo.unlink()


            raise Exception(

                resultado.stderr.strip()

                or

                "No se pudo generar el respaldo."

            )


        # ====================================================
        # VERIFICAR ARCHIVO
        # ====================================================

        if not ruta_respaldo.exists():

            raise Exception(

                "PostgreSQL no generó "
                "el archivo de respaldo."

            )


        # ====================================================
        # RESULTADO
        # ====================================================

        return {

            "ok":
                True,

            "archivo":
                nombre_archivo,

            "ruta":
                ruta_respaldo,

            "mensaje":
                "Respaldo generado correctamente."

        }


    except FileNotFoundError:

        if ruta_respaldo.exists():

            ruta_respaldo.unlink()


        raise Exception(

            "No se encontró pg_dump en: "

            f"{PG_DUMP}"

        )


# ============================================================
# LISTAR RESPALDOS
# ============================================================

def obtener_respaldos():

    respaldos = []


    if not BACKUPS_DIR.exists():

        return respaldos


    for archivo in BACKUPS_DIR.glob(
        "sicae_backup_*.sql"
    ):

        try:

            estadisticas = (
                archivo.stat()
            )


            respaldos.append({

                "nombre":
                    archivo.name,

                "ruta":
                    archivo,

                "tamano":
                    estadisticas.st_size,

                "fecha":
                    datetime.fromtimestamp(
                        estadisticas.st_mtime
                    )

            })


        except Exception:

            continue


    # ========================================================
    # ORDENAR DEL MÁS RECIENTE AL MÁS ANTIGUO
    # ========================================================

    respaldos.sort(

        key=lambda respaldo:
            respaldo["fecha"],

        reverse=True

    )


    return respaldos


# ============================================================
# OBTENER RESPALDO
# ============================================================

def obtener_respaldo(
    nombre_archivo
):

    # ========================================================
    # EVITAR RUTAS EXTERNAS
    # ========================================================

    nombre_archivo = Path(
        nombre_archivo
    ).name


    ruta = (
        BACKUPS_DIR /
        nombre_archivo
    )


    # ========================================================
    # VERIFICACIONES
    # ========================================================

    if not ruta.exists():

        return None


    if not ruta.is_file():

        return None


    if not ruta.name.startswith(
        "sicae_backup_"
    ):

        return None


    if ruta.suffix.lower() != ".sql":

        return None


    return ruta


# ============================================================
# ELIMINAR RESPALDO
# ============================================================

def eliminar_respaldo(
    nombre_archivo
):

    ruta = obtener_respaldo(
        nombre_archivo
    )


    if ruta is None:

        return False


    try:

        ruta.unlink()

        return True


    except Exception:

        return False