import psycopg

from app.database.connection import DATABASE_CONFIG


# ============================================================
# OBTENER GRUPOS ACTIVOS
# ============================================================

def obtener_grupos():

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    nombre_grupo,
                    nombre,
                    grado,
                    turno
                FROM grupos
                WHERE activo = TRUE
                ORDER BY grado, nombre;
            """)

            grupos = cursor.fetchall()

    return grupos


# ============================================================
# OBTENER GRUPO POR ID
# ============================================================

def obtener_grupo(grupo_id):

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    nombre_grupo,
                    nombre,
                    grado,
                    turno,
                    activo
                FROM grupos
                WHERE id = %s;
            """, (grupo_id,))

            grupo = cursor.fetchone()

    if grupo is None:
        return None

    return {
        "id": grupo[0],
        "nombre_grupo": grupo[1],
        "nombre": grupo[2],
        "grado": grupo[3],
        "turno": grupo[4],
        "activo": grupo[5]
    }


# ============================================================
# CREAR GRUPO
# ============================================================

def crear_grupo(
    nombre_grupo,
    nombre,
    grado,
    turno
):

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                INSERT INTO grupos (
                    nombre_grupo,
                    nombre,
                    grado,
                    turno,
                    activo
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    TRUE
                );
            """, (
                nombre_grupo,
                nombre,
                grado,
                turno
            ))

        conexion.commit()


# ============================================================
# ACTUALIZAR GRUPO
# ============================================================

def actualizar_grupo(
    grupo_id,
    nombre_grupo,
    nombre,
    grado,
    turno
):

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                UPDATE grupos
                SET
                    nombre_grupo = %s,
                    nombre = %s,
                    grado = %s,
                    turno = %s
                WHERE id = %s;
            """, (
                nombre_grupo,
                nombre,
                grado,
                turno,
                grupo_id
            ))

        conexion.commit()


# ============================================================
# ELIMINAR / DESACTIVAR GRUPO
# ============================================================

def eliminar_grupo(grupo_id):

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                UPDATE grupos
                SET activo = FALSE
                WHERE id = %s;
            """, (grupo_id,))

        conexion.commit()