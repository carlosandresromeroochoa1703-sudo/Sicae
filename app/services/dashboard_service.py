import psycopg

from app.database.connection import DATABASE_CONFIG


def obtener_estadisticas():

    with psycopg.connect(**DATABASE_CONFIG) as conexion:

        with conexion.cursor() as cursor:

            # ==================================================
            # TOTAL DE ALUMNOS ACTIVOS
            # ==================================================

            cursor.execute("""
                SELECT COUNT(*)
                FROM alumnos
                WHERE activo = TRUE;
            """)

            alumnos = cursor.fetchone()[0]


            # ==================================================
            # TOTAL DE GRUPOS ACTIVOS
            # ==================================================

            cursor.execute("""
                SELECT COUNT(*)
                FROM grupos
                WHERE activo = TRUE;
            """)

            grupos = cursor.fetchone()[0]


            # ==================================================
            # ENTRADAS DE HOY
            # ==================================================

            cursor.execute("""
                SELECT COUNT(*)
                FROM accesos
                WHERE fecha = CURRENT_DATE
                AND movimiento = 'ENTRADA';
            """)

            entradas = cursor.fetchone()[0]


            # ==================================================
            # SALIDAS DE HOY
            # ==================================================

            cursor.execute("""
                SELECT COUNT(*)
                FROM accesos
                WHERE fecha = CURRENT_DATE
                AND movimiento = 'SALIDA';
            """)

            salidas = cursor.fetchone()[0]


            # ==================================================
            # ALUMNOS QUE HAN REGISTRADO ENTRADA HOY
            #
            # DISTINCT evita contar dos veces al mismo alumno
            # si por alguna razón tiene más de una entrada.
            # ==================================================

            cursor.execute("""
                SELECT COUNT(DISTINCT alumno_id)
                FROM accesos
                WHERE fecha = CURRENT_DATE
                AND movimiento = 'ENTRADA';
            """)

            alumnos_presentes = cursor.fetchone()[0]


            # ==================================================
            # AUSENTES DE HOY
            # ==================================================

            ausentes = alumnos - alumnos_presentes


            # Evitar valores negativos por seguridad
            if ausentes < 0:
                ausentes = 0


            # ==================================================
            # PORCENTAJE DE ASISTENCIA
            # ==================================================

            if alumnos > 0:

                porcentaje_asistencia = (
                    alumnos_presentes / alumnos
                ) * 100

            else:

                porcentaje_asistencia = 0


            # ==================================================
            # ÚLTIMOS ACCESOS
            # ==================================================

            cursor.execute("""
                SELECT

                    accesos.fecha,

                    accesos.hora,

                    accesos.movimiento,

                    alumnos.matricula,

                    alumnos.nombre,

                    alumnos.apellido_paterno,

                    alumnos.apellido_materno,

                    grupos.nombre_grupo

                FROM accesos

                INNER JOIN alumnos
                    ON alumnos.id = accesos.alumno_id

                LEFT JOIN grupos
                    ON grupos.id = alumnos.grupo_id

                ORDER BY

                    accesos.fecha DESC,

                    accesos.hora DESC,

                    accesos.id DESC

                LIMIT 10;
            """)

            filas_accesos = cursor.fetchall()


    # ======================================================
    # CONVERTIR ÚLTIMOS ACCESOS
    # ======================================================

    ultimos_accesos = []


    for fila in filas_accesos:

        ultimos_accesos.append({

            "fecha":
                fila[0],

            "hora":
                fila[1],

            "movimiento":
                fila[2],

            "matricula":
                fila[3],

            "nombre":
                fila[4],

            "apellido_paterno":
                fila[5],

            "apellido_materno":
                fila[6],

            "grupo":
                fila[7]

        })


    # ======================================================
    # RESULTADO FINAL
    # ======================================================

    return {

        "alumnos":
            alumnos,

        "grupos":
            grupos,

        "entradas":
            entradas,

        "salidas":
            salidas,

        "alumnos_presentes":
            alumnos_presentes,

        "ausentes":
            ausentes,

        "porcentaje_asistencia":
            round(
                porcentaje_asistencia,
                1
            ),

        "ultimos_accesos":
            ultimos_accesos

    }