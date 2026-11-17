import psycopg

from app.database.connection import DATABASE_CONFIG
from app.database.schema import (
    TABLAS,
    CONFIGURACION_CREDENCIAL,
    CONFIGURACION_CREDENCIAL_PERSONAL,
    CONFIGURACION_SISTEMA,
    CONFIGURACION_NOTIFICACIONES
)

def crear_tablas():

    try:

        with psycopg.connect(
            **DATABASE_CONFIG
        ) as conexion:

            with conexion.cursor() as cursor:

                # ====================================================
                # TABLAS PRINCIPALES
                # ====================================================

                for nombre, sql in TABLAS.items():

                    print(
                        f"Creando tabla: {nombre}"
                    )

                    cursor.execute(
                        sql
                    )

                # Añade el operador responsable a las bases instaladas previamente.
                cursor.execute("ALTER TABLE accesos ADD COLUMN IF NOT EXISTS registrado_por VARCHAR(120);")
                cursor.execute("ALTER TABLE accesos_personal ADD COLUMN IF NOT EXISTS registrado_por VARCHAR(120);")


                # ====================================================
                # CONFIGURACIÓN DE CREDENCIAL
                # ====================================================

                print(
                    "Creando tabla: configuracion_credencial"
                )

                cursor.execute(
                    CONFIGURACION_CREDENCIAL
                )

                # ====================================================
                # CONFIGURACIÓN DE CREDENCIAL DEL PERSONAL
                # ====================================================

                print(
                    "Creando tabla: configuracion_credencial_personal"
                )

                cursor.execute(
                    CONFIGURACION_CREDENCIAL_PERSONAL
                )

                # Mantener instaladas las opciones de tamaño del QR en
                # bases que ya existían antes de agregar esta configuración.
                cursor.execute("""
                    ALTER TABLE configuracion_credencial
                    ADD COLUMN IF NOT EXISTS tamano_qr INTEGER NOT NULL DEFAULT 100;
                """)
                cursor.execute("""
                    ALTER TABLE configuracion_credencial_personal
                    ADD COLUMN IF NOT EXISTS tamano_qr INTEGER NOT NULL DEFAULT 300;
                """)
                cursor.execute("ALTER TABLE configuracion_credencial ADD COLUMN IF NOT EXISTS layout JSONB NOT NULL DEFAULT '{}'::jsonb;")
                cursor.execute("ALTER TABLE configuracion_credencial_personal ADD COLUMN IF NOT EXISTS layout JSONB NOT NULL DEFAULT '{}'::jsonb;")

                # ====================================================
                # CONFIGURACIÓN DEL SISTEMA
                # ====================================================

                print(
                    "Creando tabla: configuracion_sistema"
                )

                cursor.execute(
                    CONFIGURACION_SISTEMA
                )
                cursor.execute("ALTER TABLE configuracion_sistema ADD COLUMN IF NOT EXISTS logo_tamano INTEGER NOT NULL DEFAULT 120;")


                # ====================================================
                # CONFIGURACION DE NOTIFICACIONES POR CORREO
                # ====================================================

                print(
                    "Creando tabla: configuracion_notificaciones"
                )

                cursor.execute(
                    CONFIGURACION_NOTIFICACIONES
                )


            conexion.commit()


        print()
        print("========================================")
        print("BASE DE DATOS SICAE INICIALIZADA")
        print("Todas las tablas fueron creadas.")
        print("========================================")
        return True


    except Exception as error:

        print()
        print("========================================")
        print("ERROR AL CREAR LAS TABLAS")
        print(error)
        print("========================================")
        return False


if __name__ == "__main__":
    raise SystemExit(0 if crear_tablas() else 1)
