import os

import bcrypt
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

        configuracion_conexion = {
            **DATABASE_CONFIG,
            "connect_timeout": 10,
            "options": (
                "-c timezone=America/Mexico_City "
                "-c lock_timeout=30000 "
                "-c statement_timeout=120000"
            ),
        }
        with psycopg.connect(**configuracion_conexion) as conexion:

            with conexion.cursor() as cursor:

                # ====================================================
                # TABLAS PRINCIPALES
                # ====================================================

                # Evita que dos instancias durante un despliegue intenten
                # aplicar las mismas migraciones al mismo tiempo.
                cursor.execute("SELECT pg_advisory_xact_lock(731904221);")

                for nombre, sql in TABLAS.items():

                    print(
                        f"Creando tabla: {nombre}"
                    )

                    cursor.execute(
                        sql
                    )

                # Acelera la consulta del último movimiento durante escaneos
                # simultáneos. Los índices también se aplican a instalaciones
                # existentes porque IF NOT EXISTS hace segura la migración.
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_accesos_alumno_fecha_ultimo
                    ON accesos (alumno_id, fecha, hora DESC, id DESC);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_accesos_personal_fecha_ultimo
                    ON accesos_personal (personal_id, fecha, hora DESC, id DESC);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_accesos_especial_fecha_ultimo
                    ON accesos_credenciales_especiales (credencial_id, fecha, hora DESC, id DESC);
                """)

                cursor.execute("""
                    INSERT INTO configuracion_asistencia (
                        id, hora_entrada, tolerancia_minutos,
                        hora_cierre_entrada, activo
                    )
                    VALUES (1, '07:30', 10, '08:30', TRUE)
                    ON CONFLICT (id) DO NOTHING;
                """)

                # Añade el operador responsable a las bases instaladas previamente.
                cursor.execute("ALTER TABLE accesos ADD COLUMN IF NOT EXISTS registrado_por VARCHAR(120);")
                cursor.execute("ALTER TABLE accesos_personal ADD COLUMN IF NOT EXISTS registrado_por VARCHAR(120);")
                cursor.execute("ALTER TABLE accesos ALTER COLUMN hora TYPE TIME(0) USING hora::TIME(0);")
                cursor.execute("ALTER TABLE accesos ALTER COLUMN hora SET DEFAULT CURRENT_TIME(0);")
                cursor.execute("ALTER TABLE accesos_personal ALTER COLUMN hora TYPE TIME(0) USING hora::TIME(0);")
                cursor.execute("ALTER TABLE accesos_personal ALTER COLUMN hora SET DEFAULT CURRENT_TIME(0);")
                cursor.execute("ALTER TABLE accesos_credenciales_especiales ALTER COLUMN hora TYPE TIME(0) USING hora::TIME(0);")
                cursor.execute("ALTER TABLE accesos_credenciales_especiales ALTER COLUMN hora SET DEFAULT CURRENT_TIME(0);")
                cursor.execute("ALTER TABLE configuracion_credencial_especial ADD COLUMN IF NOT EXISTS layout JSONB NOT NULL DEFAULT '{}'::jsonb;")


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

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS plantillas_credencial (
                        id SERIAL PRIMARY KEY,
                        tipo VARCHAR(30) NOT NULL,
                        nombre VARCHAR(100) NOT NULL,
                        diseno JSONB NOT NULL,
                        fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT plantillas_credencial_tipo_nombre_unico UNIQUE (tipo, nombre)
                    );
                """)
                cursor.execute("ALTER TABLE plantillas_credencial DROP CONSTRAINT IF EXISTS plantillas_credencial_tipo_check;")
                cursor.execute("""
                    ALTER TABLE plantillas_credencial ADD CONSTRAINT plantillas_credencial_tipo_check
                    CHECK (tipo IN ('alumno', 'personal', 'direccion', 'prefectura', 'conferencias', 'proveedores'));
                """)

                # Crea el primer administrador solo cuando se configuran
                # credenciales de bootstrap y la tabla de usuarios está vacía.
                usuario_inicial = os.getenv("SICAE_INITIAL_ADMIN_USER", "").strip()
                password_inicial = os.getenv("SICAE_INITIAL_ADMIN_PASSWORD", "")
                if usuario_inicial and password_inicial:
                    cursor.execute("SELECT EXISTS (SELECT 1 FROM usuarios);")
                    if not cursor.fetchone()[0]:
                        if len(password_inicial.encode("utf-8")) > 72:
                            raise ValueError(
                                "SICAE_INITIAL_ADMIN_PASSWORD no puede exceder 72 bytes."
                            )
                        nombre_inicial = (
                            os.getenv("SICAE_INITIAL_ADMIN_NAME", "Administrador").strip()
                            or "Administrador"
                        )
                        password_hash = bcrypt.hashpw(
                            password_inicial.encode("utf-8"), bcrypt.gensalt()
                        ).decode("utf-8")
                        cursor.execute(
                            """
                            INSERT INTO usuarios (usuario, password, nombre, rol, activo)
                            VALUES (%s, %s, %s, 'administrador', TRUE);
                            """,
                            (usuario_inicial, password_hash, nombre_inicial),
                        )
                        print("Se creó el administrador inicial configurado en el entorno.")


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
