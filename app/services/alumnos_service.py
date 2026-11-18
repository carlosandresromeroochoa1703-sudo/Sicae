import psycopg

from app.database.connection import DATABASE_CONFIG


# ============================================================
# CONVERTIR FILA A DICCIONARIO
# ============================================================

def fila_a_dict(cursor, fila):

    if fila is None:
        return None

    columnas = [
        columna.name
        for columna in cursor.description
    ]

    return dict(
        zip(
            columnas,
            fila
        )
    )


# ============================================================
# OBTENER TODOS LOS ALUMNOS
# ============================================================

def obtener_alumnos():

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT

                    a.id,
                    a.matricula,
                    a.nombre,
                    a.apellido_paterno,
                    a.apellido_materno,
                    a.fecha_nacimiento,
                    a.numero_seguro_social,
                    a.nombre_padre,
                    a.curp,
                    a.correo,
                    a.telefono,
                    a.foto,
                    a.qr,
                    a.grupo_id,
                    a.activo,
                    a.fecha_registro,

                    g.nombre_grupo,
                    g.grado,
                    g.nombre AS grupo_nombre,
                    g.turno

                FROM alumnos a

                LEFT JOIN grupos g
                    ON a.grupo_id = g.id

                WHERE a.activo = TRUE

                ORDER BY
                    a.apellido_paterno,
                    a.apellido_materno,
                    a.nombre;
            """)

            resultados = cursor.fetchall()

            return [

                fila_a_dict(
                    cursor,
                    fila
                )

                for fila in resultados

            ]


# ============================================================
# OBTENER ALUMNO POR ID
# ============================================================

def obtener_alumno(
    alumno_id
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT

                    id,
                    matricula,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    fecha_nacimiento,
                    numero_seguro_social,
                    nombre_padre,
                    curp,
                    correo,
                    telefono,
                    foto,
                    qr,
                    grupo_id,
                    activo,
                    fecha_registro

                FROM alumnos

                WHERE id = %s;
            """, (
                alumno_id,
            ))

            fila = cursor.fetchone()

            return fila_a_dict(
                cursor,
                fila
            )


# ============================================================
# OBTENER ALUMNOS POR GRUPO
# ============================================================

def obtener_alumnos_por_grupo(
    grupo_id
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT

                    a.id,
                    a.matricula,
                    a.nombre,
                    a.apellido_paterno,
                    a.apellido_materno,
                    a.fecha_nacimiento,
                    a.numero_seguro_social,
                    a.nombre_padre,
                    a.curp,
                    a.correo,
                    a.telefono,
                    a.foto,
                    a.qr,
                    a.grupo_id,
                    a.activo,
                    a.fecha_registro,

                    g.nombre_grupo,
                    g.grado,
                    g.nombre AS grupo_nombre,
                    g.turno

                FROM alumnos a

                LEFT JOIN grupos g
                    ON a.grupo_id = g.id

                WHERE
                    a.grupo_id = %s
                    AND a.activo = TRUE

                ORDER BY
                    a.apellido_paterno,
                    a.apellido_materno,
                    a.nombre;
            """, (
                grupo_id,
            ))

            resultados = cursor.fetchall()

            alumnos = [

                fila_a_dict(
                    cursor,
                    fila
                )

                for fila in resultados

            ]

            return alumnos


def obtener_lista_asistencia_manual(grupo_id):
    """Lista alumnos activos del grupo con su último movimiento de hoy."""
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT
                    a.id,
                    a.matricula,
                    a.nombre,
                    a.apellido_paterno,
                    a.apellido_materno,
                    a.foto,
                    g.nombre_grupo,
                    g.grado,
                    g.nombre AS grupo_nombre,
                    g.turno,
                    (
                        SELECT ac.movimiento
                        FROM accesos ac
                        WHERE ac.alumno_id = a.id
                          AND ac.fecha = CURRENT_DATE
                        ORDER BY ac.hora DESC, ac.id DESC
                        LIMIT 1
                    ) AS ultimo_movimiento,
                    (
                        SELECT ac.hora
                        FROM accesos ac
                        WHERE ac.alumno_id = a.id
                          AND ac.fecha = CURRENT_DATE
                        ORDER BY ac.hora DESC, ac.id DESC
                        LIMIT 1
                    ) AS ultima_hora
                FROM alumnos a
                LEFT JOIN grupos g ON g.id = a.grupo_id
                WHERE a.grupo_id = %s AND a.activo = TRUE
                ORDER BY a.apellido_paterno, a.apellido_materno, a.nombre;
            """, (grupo_id,))
            return [fila_a_dict(cursor, fila) for fila in cursor.fetchall()]


# ============================================================
# OBTENER ALUMNO DETALLADO
# ============================================================

def obtener_alumno_detalle(
    alumno_id
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT

                    a.id,
                    a.matricula,
                    a.nombre,
                    a.apellido_paterno,
                    a.apellido_materno,
                    a.fecha_nacimiento,
                    a.numero_seguro_social,
                    a.nombre_padre,
                    a.curp,
                    a.correo,
                    a.telefono,
                    a.foto,
                    a.qr,
                    a.grupo_id,
                    a.activo,
                    a.fecha_registro,

                    g.nombre_grupo,
                    g.grado,
                    g.nombre AS grupo_nombre,
                    g.turno

                FROM alumnos a

                LEFT JOIN grupos g
                    ON a.grupo_id = g.id

                WHERE a.id = %s;
            """, (
                alumno_id,
            ))

            fila = cursor.fetchone()

            return fila_a_dict(
                cursor,
                fila
            )


# ============================================================
# OBTENER GRUPOS
# ============================================================

def obtener_grupos():

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT

                    g.id,
                    g.nombre_grupo,
                    g.grado,
                    g.nombre,
                    g.turno,

                    COUNT(a.id) AS cantidad_alumnos

                FROM grupos g

                LEFT JOIN alumnos a
                    ON a.grupo_id = g.id
                    AND a.activo = TRUE

                WHERE g.activo = TRUE

                GROUP BY

                    g.id,
                    g.nombre_grupo,
                    g.grado,
                    g.nombre,
                    g.turno

                ORDER BY

                    g.grado,
                    g.nombre;
            """)

            resultados = cursor.fetchall()

            grupos = []

            for fila in resultados:

                grupos.append({

                    "id": fila[0],

                    "nombre_grupo": fila[1],

                    "grado": fila[2],

                    "nombre": fila[3],

                    "turno": fila[4],

                    "cantidad_alumnos": fila[5]

                })

            return grupos


# ============================================================
# CREAR ALUMNO
# ============================================================

def crear_alumno(

    matricula,

    nombre,

    apellido_paterno,

    apellido_materno,

    fecha_nacimiento,

    correo,

    telefono,

    grupo_id,

    foto=None,

    qr=None,

    numero_seguro_social=None,

    nombre_padre=None,

    curp=None

):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                INSERT INTO alumnos (

                    matricula,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    fecha_nacimiento,
                    numero_seguro_social,
                    nombre_padre,
                    curp,
                    correo,
                    telefono,
                    foto,
                    qr,
                    grupo_id,
                    activo

                )

                VALUES (

                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    TRUE

                );
            """, (

                matricula,

                nombre,

                apellido_paterno,

                apellido_materno,

                fecha_nacimiento,

                numero_seguro_social,

                nombre_padre,

                curp,

                correo,

                telefono,

                foto,

                qr,

                grupo_id

            ))

        conexion.commit()


# ============================================================
# ACTUALIZAR ALUMNO
# ============================================================

def actualizar_alumno(

    alumno_id,

    matricula,

    nombre,

    apellido_paterno,

    apellido_materno,

    fecha_nacimiento,

    correo,

    telefono,

    grupo_id,

    foto=None,

    qr=None,

    numero_seguro_social=None,

    nombre_padre=None,

    curp=None

):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                UPDATE alumnos

                SET

                    matricula = %s,
                    nombre = %s,
                    apellido_paterno = %s,
                    apellido_materno = %s,
                    fecha_nacimiento = %s,
                    numero_seguro_social = %s,
                    nombre_padre = %s,
                    curp = %s,
                    correo = %s,
                    telefono = %s,
                    grupo_id = %s,
                    foto = COALESCE(NULLIF(%s, ''), foto),
                    qr = COALESCE(NULLIF(%s, ''), qr)

                WHERE id = %s;
            """, (

                matricula,

                nombre,

                apellido_paterno,

                apellido_materno,

                fecha_nacimiento,

                numero_seguro_social,

                nombre_padre,

                curp,

                correo,

                telefono,

                grupo_id,

                foto,

                qr,

                alumno_id

            ))

        conexion.commit()


# ============================================================
# ELIMINAR / DESACTIVAR ALUMNO
# ============================================================

def eliminar_alumno(
    alumno_id
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                UPDATE alumnos

                SET activo = FALSE

                WHERE id = %s;
            """, (
                alumno_id,
            ))

        conexion.commit()

# ============================================================

def eliminar_alumnos(
    alumnos_ids
):
    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                UPDATE alumnos
                SET activo = FALSE
                WHERE id = ANY(%s);
            """, (
                alumnos_ids,
            ))

        conexion.commit()
# IMPORTAR ALUMNOS DESDE EXCEL
# ============================================================

def importar_alumno_excel(
    matricula,
    nombre,
    apellido_paterno,
    apellido_materno="",
    fecha_nacimiento=None,
    correo="",
    telefono="",
    grupo_id=None,
    numero_seguro_social="",
    nombre_padre="",
    curp=""
):

    matricula = str(
        matricula
    ).strip()

    nombre = str(
        nombre or ""
    ).strip()

    apellido_paterno = str(
        apellido_paterno or ""
    ).strip()

    apellido_materno = str(
        apellido_materno or ""
    ).strip()

    correo = str(
        correo or ""
    ).strip()

    telefono = str(
        telefono or ""
    ).strip()

    numero_seguro_social = str(numero_seguro_social or "").strip() or None
    nombre_padre = str(nombre_padre or "").strip() or None
    curp = str(curp or "").strip().upper() or None


    if not matricula:
        raise ValueError(
            "La matrícula está vacía."
        )


    if not nombre:
        raise ValueError(
            "El nombre está vacío."
        )


    if not apellido_paterno:
        raise ValueError(
            "El apellido paterno está vacío."
        )


    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO alumnos (
                    matricula,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    fecha_nacimiento,
                    numero_seguro_social,
                    nombre_padre,
                    curp,
                    correo,
                    telefono,
                    foto,
                    qr,
                    grupo_id,
                    activo
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NULL,
                    NULL,
                    %s,
                    TRUE
                )
                RETURNING id;
                """,
                (
                    matricula,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    fecha_nacimiento,
                    numero_seguro_social,
                    nombre_padre,
                    curp,
                    correo,
                    telefono,
                    grupo_id
                )
            )

            alumno_id = cursor.fetchone()[0]

        conexion.commit()


    return alumno_id



