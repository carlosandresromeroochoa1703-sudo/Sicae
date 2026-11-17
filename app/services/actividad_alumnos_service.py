import psycopg

from app.database.connection import DATABASE_CONFIG


def buscar_alumnos_por_nombre_o_matricula(termino, limite=50):
    termino = (termino or "").strip()
    if len(termino) < 2:
        return []

    patron = f"%{termino}%"
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.matricula,
                    a.nombre,
                    a.apellido_paterno,
                    a.apellido_materno,
                    g.nombre_grupo,
                    g.grado,
                    g.nombre AS grupo_nombre
                FROM alumnos a
                LEFT JOIN grupos g ON g.id = a.grupo_id
                WHERE a.activo = TRUE
                  AND (
                    a.matricula ILIKE %s
                    OR CONCAT_WS(' ', a.nombre, a.apellido_paterno, a.apellido_materno) ILIKE %s
                  )
                ORDER BY a.apellido_paterno, a.apellido_materno, a.nombre
                LIMIT %s
                """,
                (patron, patron, limite),
            )
            columnas = [columna.name for columna in cursor.description]
            return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def obtener_actividad_alumno(alumno_id, pagina=1, por_pagina=50):
    pagina = max(1, int(pagina or 1))
    desplazamiento = (pagina - 1) * por_pagina

    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM accesos WHERE alumno_id = %s",
                (alumno_id,),
            )
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT id, fecha, hora, movimiento, registrado_por
                FROM accesos
                WHERE alumno_id = %s
                ORDER BY fecha DESC, hora DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (alumno_id, por_pagina, desplazamiento),
            )
            columnas = [columna.name for columna in cursor.description]
            actividad = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    return actividad, total, total_paginas
