import psycopg

from app.database.connection import DATABASE_CONFIG


# ============================================================
# OBTENER REPORTE DE ASISTENCIAS
# ============================================================

def obtener_reporte_asistencias(
    fecha_inicio=None,
    fecha_fin=None,
    grupo_id=None
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            # ====================================================
            # OBTENER TODOS LOS ALUMNOS
            # ====================================================

            consulta_alumnos = """

                SELECT

                    a.id,

                    a.matricula,

                    a.nombre,

                    a.apellido_paterno,

                    a.apellido_materno,

                    a.grupo_id,

                    g.nombre_grupo,

                    g.grado,

                    g.nombre
                        AS grupo_nombre,

                    g.turno

                FROM alumnos a

                LEFT JOIN grupos g

                    ON g.id = a.grupo_id

                WHERE a.activo = TRUE

            """

            parametros_alumnos = []


            # ====================================================
            # FILTRO GRUPO
            # ====================================================

            if grupo_id:

                consulta_alumnos += """

                    AND a.grupo_id = %s

                """

                parametros_alumnos.append(
                    grupo_id
                )


            consulta_alumnos += """

                ORDER BY

                    a.apellido_paterno,

                    a.apellido_materno,

                    a.nombre;

            """


            cursor.execute(

                consulta_alumnos,

                parametros_alumnos

            )


            alumnos = cursor.fetchall()


            # ====================================================
            # OBTENER ACCESOS
            # ====================================================

            consulta_accesos = """

                SELECT

                    accesos.id,

                    accesos.fecha,

                    accesos.hora,

                    accesos.movimiento,

                    alumnos.id
                        AS alumno_id,

                    alumnos.matricula,

                    alumnos.nombre,

                    alumnos.apellido_paterno,

                    alumnos.apellido_materno,

                    grupos.id
                        AS grupo_id,

                    grupos.nombre_grupo,

                    grupos.grado,

                    grupos.nombre
                        AS grupo_nombre,

                    grupos.turno,

                    accesos.registrado_por

                FROM accesos

                INNER JOIN alumnos

                    ON alumnos.id =
                       accesos.alumno_id

                LEFT JOIN grupos

                    ON grupos.id =
                       alumnos.grupo_id

                WHERE alumnos.activo = TRUE

            """

            parametros_accesos = []


            # ====================================================
            # FILTRO FECHA INICIO
            # ====================================================

            if fecha_inicio:

                consulta_accesos += """

                    AND accesos.fecha >= %s

                """

                parametros_accesos.append(
                    fecha_inicio
                )


            # ====================================================
            # FILTRO FECHA FIN
            # ====================================================

            if fecha_fin:

                consulta_accesos += """

                    AND accesos.fecha <= %s

                """

                parametros_accesos.append(
                    fecha_fin
                )


            # ====================================================
            # FILTRO GRUPO
            # ====================================================

            if grupo_id:

                consulta_accesos += """

                    AND alumnos.grupo_id = %s

                """

                parametros_accesos.append(
                    grupo_id
                )


            consulta_accesos += """

                ORDER BY

                    accesos.fecha DESC,

                    accesos.hora DESC,

                    accesos.id DESC;

            """


            cursor.execute(

                consulta_accesos,

                parametros_accesos

            )


            accesos = cursor.fetchall()


    # ============================================================
    # CONVERTIR ACCESOS
    # ============================================================

    resultados = []


    alumnos_con_acceso = set()


    for fila in accesos:

        alumno_id = fila[4]


        alumnos_con_acceso.add(
            alumno_id
        )


        resultados.append({

            "id":
                fila[0],

            "fecha":
                fila[1],

            "hora":
                fila[2],

            "movimiento":
                fila[3],

            "alumno_id":
                fila[4],

            "matricula":
                fila[5],

            "nombre":
                fila[6],

            "apellido_paterno":
                fila[7],

            "apellido_materno":
                fila[8],

            "grupo_id":
                fila[9],

            "nombre_grupo":
                fila[10],

            "grado":
                fila[11],

            "grupo_nombre":
                fila[12],

            "turno":
                fila[13],

            "registrado_por":
                fila[14]

        })


    # ============================================================
    # AGREGAR ALUMNOS AUSENTES
    # ============================================================

    for alumno in alumnos:

        alumno_id = alumno[0]


        # --------------------------------------------------------
        # Si el alumno NO tiene ningún acceso en el periodo
        # --------------------------------------------------------

        if alumno_id not in alumnos_con_acceso:

            resultados.append({

                "id":
                    None,

                "fecha":
                    fecha_inicio
                    or fecha_fin
                    or "",

                "hora":
                    "",

                "movimiento":
                    "AUSENTE",

                "alumno_id":
                    alumno[0],

                "matricula":
                    alumno[1],

                "nombre":
                    alumno[2],

                "apellido_paterno":
                    alumno[3],

                "apellido_materno":
                    alumno[4],

                "grupo_id":
                    alumno[5],

                "nombre_grupo":
                    alumno[6],

                "grado":
                    alumno[7],

                "grupo_nombre":
                    alumno[8],

                "turno":
                    alumno[9]

            })


    # ============================================================
    # ORDENAR RESULTADOS
    # ============================================================

    resultados.sort(

        key=lambda registro: (

            str(
                registro.get("fecha")
                or ""
            ),

            str(
                registro.get("hora")
                or ""
            )

        ),

        reverse=True

    )


    return resultados


def obtener_reporte_credenciales_especiales(fecha_inicio=None, fecha_fin=None):
    consulta = """
        SELECT
            ace.fecha,
            ace.hora,
            ace.movimiento,
            ace.registrado_por,
            ce.codigo,
            ce.nombre,
            ce.apellido_paterno,
            ce.apellido_materno,
            ce.tipo,
            ce.cargo,
            ce.organizacion
        FROM accesos_credenciales_especiales ace
        JOIN credenciales_especiales ce ON ce.id = ace.credencial_id
        WHERE TRUE
    """
    parametros = []
    if fecha_inicio:
        consulta += " AND ace.fecha >= %s"
        parametros.append(fecha_inicio)
    if fecha_fin:
        consulta += " AND ace.fecha <= %s"
        parametros.append(fecha_fin)
    consulta += " ORDER BY ace.fecha DESC, ace.hora DESC, ace.id DESC"

    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(consulta, parametros)
            columnas = [columna.name for columna in cursor.description]
            filas = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

    from app.services.credenciales_especiales_service import TIPOS_CREDENCIAL_ESPECIAL
    for fila in filas:
        fila["tipo_label"] = TIPOS_CREDENCIAL_ESPECIAL.get(fila["tipo"], fila["tipo"])
        fila["nombre_completo"] = " ".join(
            parte for parte in (fila.get("nombre"), fila.get("apellido_paterno"), fila.get("apellido_materno")) if parte
        )
    return filas


# ============================================================
# OBTENER TODOS LOS ALUMNOS ACTIVOS PARA REPORTES
# ============================================================

def obtener_alumnos_para_reporte(
    grupo_id=None
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            consulta = """

                SELECT

                    a.id,

                    a.matricula,

                    a.nombre,

                    a.apellido_paterno,

                    a.apellido_materno,

                    a.grupo_id,

                    g.nombre_grupo,

                    g.grado,

                    g.nombre
                        AS grupo_nombre,

                    g.turno

                FROM alumnos a

                LEFT JOIN grupos g

                    ON g.id = a.grupo_id

                WHERE

                    a.activo = TRUE

            """

            parametros = []


            if grupo_id:

                consulta += """

                    AND a.grupo_id = %s

                """

                parametros.append(
                    grupo_id
                )


            consulta += """

                ORDER BY

                    a.apellido_paterno,

                    a.apellido_materno,

                    a.nombre;

            """


            cursor.execute(

                consulta,

                parametros

            )


            filas = cursor.fetchall()


    resultados = []


    for fila in filas:

        resultados.append({

            "alumno_id":
                fila[0],

            "matricula":
                fila[1],

            "nombre":
                fila[2],

            "apellido_paterno":
                fila[3],

            "apellido_materno":
                fila[4],

            "grupo_id":
                fila[5],

            "nombre_grupo":
                fila[6],

            "grado":
                fila[7],

            "grupo_nombre":
                fila[8],

            "turno":
                fila[9]

        })


    return resultados
