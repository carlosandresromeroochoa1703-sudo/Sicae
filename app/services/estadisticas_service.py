import psycopg

from app.database.connection import DATABASE_CONFIG


# ============================================================
# RESUMEN GENERAL DE ASISTENCIA
# ============================================================

def obtener_resumen_estadisticas(
    fecha_inicio,
    fecha_fin,
    grado=None,
    grupo_id=None
):

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            filtros = [
                "a.activo = TRUE"
            ]

            parametros = []

            if grado is not None:
                filtros.append("g.grado = %s")
                parametros.append(grado)

            if grupo_id is not None:
                filtros.append("a.grupo_id = %s")
                parametros.append(grupo_id)

            condiciones = " AND ".join(filtros)

            cursor.execute(f"""
                SELECT
                    COUNT(DISTINCT a.id) AS total_alumnos,
                    COUNT(DISTINCT CASE
                        WHEN ac.fecha IS NOT NULL
                        THEN a.id
                    END) AS alumnos_con_asistencia
                FROM alumnos a
                LEFT JOIN grupos g
                    ON g.id = a.grupo_id
                LEFT JOIN accesos ac
                    ON ac.alumno_id = a.id
                    AND ac.fecha BETWEEN %s AND %s
                    AND ac.movimiento = 'ENTRADA'
                WHERE {condiciones};
            """, (
                fecha_inicio,
                fecha_fin,
                *parametros
            ))

            resultado = cursor.fetchone()

    total = resultado[0] or 0
    asistencia = resultado[1] or 0
    faltas = max(total - asistencia, 0)

    porcentaje = 0

    if total > 0:
        porcentaje = round(
            (asistencia / total) * 100,
            2
        )

    return {
        "total_alumnos": total,
        "asistencia": asistencia,
        "faltas": faltas,
        "porcentaje": porcentaje
    }


# ============================================================
# ESTADÍSTICAS POR GRADO
# ============================================================

def obtener_estadisticas_por_grado(
    fecha_inicio,
    fecha_fin
):

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT
                    g.grado,
                    COUNT(DISTINCT a.id) AS total_alumnos,
                    COUNT(DISTINCT CASE
                        WHEN ac.fecha IS NOT NULL
                        THEN a.id
                    END) AS alumnos_con_asistencia
                FROM grupos g
                LEFT JOIN alumnos a
                    ON a.grupo_id = g.id
                    AND a.activo = TRUE
                LEFT JOIN accesos ac
                    ON ac.alumno_id = a.id
                    AND ac.fecha BETWEEN %s AND %s
                    AND ac.movimiento = 'ENTRADA'
                WHERE g.activo = TRUE
                GROUP BY g.grado
                ORDER BY g.grado;
            """, (
                fecha_inicio,
                fecha_fin
            ))

            resultados = cursor.fetchall()

    estadisticas = []

    for fila in resultados:

        grado = fila[0]
        total = fila[1] or 0
        asistencia = fila[2] or 0
        faltas = max(total - asistencia, 0)

        porcentaje = 0

        if total > 0:
            porcentaje = round(
                (asistencia / total) * 100,
                2
            )

        estadisticas.append({
            "grado": grado,
            "total_alumnos": total,
            "asistencia": asistencia,
            "faltas": faltas,
            "porcentaje": porcentaje
        })

    return estadisticas


# ============================================================
# ESTADÍSTICAS POR GRUPO
# ============================================================

def obtener_estadisticas_por_grupo(
    fecha_inicio,
    fecha_fin,
    grado=None
):

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            if grado is None:

                cursor.execute("""
                    SELECT
                        g.id,
                        g.nombre_grupo,
                        g.nombre,
                        g.grado,
                        g.turno,
                        COUNT(DISTINCT a.id) AS total_alumnos,
                        COUNT(DISTINCT CASE
                            WHEN ac.fecha IS NOT NULL
                            THEN a.id
                        END) AS alumnos_con_asistencia
                    FROM grupos g
                    LEFT JOIN alumnos a
                        ON a.grupo_id = g.id
                        AND a.activo = TRUE
                    LEFT JOIN accesos ac
                        ON ac.alumno_id = a.id
                        AND ac.fecha BETWEEN %s AND %s
                        AND ac.movimiento = 'ENTRADA'
                    WHERE g.activo = TRUE
                    GROUP BY
                        g.id,
                        g.nombre_grupo,
                        g.nombre,
                        g.grado,
                        g.turno
                    ORDER BY
                        g.grado,
                        g.nombre;
                """, (
                    fecha_inicio,
                    fecha_fin
                ))

            else:

                cursor.execute("""
                    SELECT
                        g.id,
                        g.nombre_grupo,
                        g.nombre,
                        g.grado,
                        g.turno,
                        COUNT(DISTINCT a.id) AS total_alumnos,
                        COUNT(DISTINCT CASE
                            WHEN ac.fecha IS NOT NULL
                            THEN a.id
                        END) AS alumnos_con_asistencia
                    FROM grupos g
                    LEFT JOIN alumnos a
                        ON a.grupo_id = g.id
                        AND a.activo = TRUE
                    LEFT JOIN accesos ac
                        ON ac.alumno_id = a.id
                        AND ac.fecha BETWEEN %s AND %s
                        AND ac.movimiento = 'ENTRADA'
                    WHERE
                        g.activo = TRUE
                        AND g.grado = %s
                    GROUP BY
                        g.id,
                        g.nombre_grupo,
                        g.nombre,
                        g.grado,
                        g.turno
                    ORDER BY
                        g.nombre;
                """, (
                    fecha_inicio,
                    fecha_fin,
                    grado
                ))

            resultados = cursor.fetchall()

    estadisticas = []

    for fila in resultados:

        total = fila[5] or 0
        asistencia = fila[6] or 0
        faltas = max(total - asistencia, 0)

        porcentaje = 0

        if total > 0:
            porcentaje = round(
                (asistencia / total) * 100,
                2
            )

        estadisticas.append({
            "id": fila[0],
            "nombre_grupo": fila[1],
            "nombre": fila[2],
            "grado": fila[3],
            "turno": fila[4],
            "total_alumnos": total,
            "asistencia": asistencia,
            "faltas": faltas,
            "porcentaje": porcentaje
        })

    return estadisticas


# ============================================================
# ASISTENCIA POR FECHA
# ============================================================

def obtener_asistencia_por_fecha(
    fecha_inicio,
    fecha_fin,
    grado=None,
    grupo_id=None
):

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            filtros = [
                "a.activo = TRUE"
            ]

            parametros = []

            if grado is not None:
                filtros.append("g.grado = %s")
                parametros.append(grado)

            if grupo_id is not None:
                filtros.append("a.grupo_id = %s")
                parametros.append(grupo_id)

            condiciones = " AND ".join(filtros)

            cursor.execute(f"""
                SELECT
                    ac.fecha,
                    COUNT(DISTINCT ac.alumno_id)
                FROM accesos ac
                INNER JOIN alumnos a
                    ON a.id = ac.alumno_id
                LEFT JOIN grupos g
                    ON g.id = a.grupo_id
                WHERE
                    ac.fecha BETWEEN %s AND %s
                    AND ac.movimiento = 'ENTRADA'
                    AND {condiciones}
                GROUP BY ac.fecha
                ORDER BY ac.fecha;
            """, (
                fecha_inicio,
                fecha_fin,
                *parametros
            ))

            resultados = cursor.fetchall()

    return [
        {
            "fecha": fila[0],
            "asistencia": fila[1]
        }
        for fila in resultados
    ]


# ============================================================
# OBTENER GRADOS DISPONIBLES
# ============================================================

def obtener_grados_estadisticas():

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT DISTINCT grado
                FROM grupos
                WHERE activo = TRUE
                ORDER BY grado;
            """)

            resultados = cursor.fetchall()

    return [fila[0] for fila in resultados]


# ============================================================
# OBTENER GRUPOS POR GRADO
# ============================================================

def obtener_grupos_estadisticas(grado=None):

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            if grado is None:

                cursor.execute("""
                    SELECT
                        id,
                        nombre_grupo,
                        grado,
                        turno
                    FROM grupos
                    WHERE activo = TRUE
                    ORDER BY grado, nombre;
                """)

            else:

                cursor.execute("""
                    SELECT
                        id,
                        nombre_grupo,
                        grado,
                        turno
                    FROM grupos
                    WHERE
                        activo = TRUE
                        AND grado = %s
                    ORDER BY nombre;
                """, (grado,))

            resultados = cursor.fetchall()

    return [
        {
            "id": fila[0],
            "nombre_grupo": fila[1],
            "grado": fila[2],
            "turno": fila[3]
        }
        for fila in resultados
    ]
