import json

import psycopg

from app.database.connection import DATABASE_CONFIG


def _asegurar_tabla(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plantillas_credencial (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR(30) NOT NULL CHECK (tipo IN ('alumno', 'personal', 'direccion', 'prefectura', 'conferencias', 'proveedores')),
            nombre VARCHAR(100) NOT NULL,
            diseno JSONB NOT NULL,
            fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT plantillas_credencial_tipo_nombre_unico UNIQUE (tipo, nombre)
        );
    """)


def listar_plantillas_credencial(tipo):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tabla(cursor)
            if tipo == "todas":
                cursor.execute("SELECT id, tipo, nombre, diseno FROM plantillas_credencial ORDER BY tipo, nombre;")
            else:
                cursor.execute(
                    "SELECT id, tipo, nombre, diseno FROM plantillas_credencial WHERE tipo = %s ORDER BY nombre;",
                    (tipo,),
                )
            return [
                {"id": row[0], "tipo": row[1], "nombre": row[2], "diseño": row[3]}
                for row in cursor.fetchall()
            ]


def guardar_plantilla_credencial(tipo, nombre, diseño):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tabla(cursor)
            cursor.execute(
                """
                INSERT INTO plantillas_credencial (tipo, nombre, diseno)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (tipo, nombre) DO UPDATE
                SET diseno = EXCLUDED.diseno, fecha_actualizacion = CURRENT_TIMESTAMP
                RETURNING id, nombre, diseno;
                """,
                (tipo, nombre, json.dumps(diseño, ensure_ascii=False)),
            )
            row = cursor.fetchone()
            return {"id": row[0], "nombre": row[1], "diseño": row[2]}


def eliminar_plantilla_credencial(tipo, plantilla_id):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tabla(cursor)
            cursor.execute(
                "DELETE FROM plantillas_credencial WHERE tipo = %s AND id = %s RETURNING id;",
                (tipo, plantilla_id),
            )
            return cursor.fetchone() is not None
