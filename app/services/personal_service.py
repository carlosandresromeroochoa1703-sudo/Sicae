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
# OBTENER TODO EL PERSONAL
# ============================================================

def obtener_personal():

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT

                    id,
                    numero_empleado,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    tipo_personal,
                    cargo,
                    area,
                    correo,
                    telefono,
                    foto,
                    qr,
                    activo,
                    fecha_registro

                FROM personal

                WHERE activo = TRUE

                ORDER BY
                    apellido_paterno,
                    apellido_materno,
                    nombre;
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
# OBTENER PERSONAL POR ID
# ============================================================

def obtener_personal_por_id(
    personal_id
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT

                    id,
                    numero_empleado,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    tipo_personal,
                    cargo,
                    area,
                    correo,
                    telefono,
                    foto,
                    qr,
                    activo,
                    fecha_registro

                FROM personal

                WHERE id = %s;
            """, (
                personal_id,
            ))

            fila = cursor.fetchone()

            return fila_a_dict(
                cursor,
                fila
            )


# ============================================================
# OBTENER PERSONAL POR TIPO
# ============================================================

def obtener_personal_por_tipo(
    tipo_personal
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT

                    id,
                    numero_empleado,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    tipo_personal,
                    cargo,
                    area,
                    correo,
                    telefono,
                    foto,
                    qr,
                    activo,
                    fecha_registro

                FROM personal

                WHERE
                    LOWER(TRIM(tipo_personal)) = LOWER(TRIM(%s))
                    AND activo = TRUE

                ORDER BY
                    apellido_paterno,
                    apellido_materno,
                    nombre;
            """, (
                tipo_personal,
            ))

            resultados = cursor.fetchall()

            return [

                fila_a_dict(
                    cursor,
                    fila
                )

                for fila in resultados

            ]


# ============================================================
# CREAR PERSONAL
# ============================================================

def crear_personal(

    numero_empleado,

    nombre,

    apellido_paterno,

    apellido_materno,

    tipo_personal,

    cargo,

    area,

    correo,

    telefono,

    foto=None,

    qr=None

):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                INSERT INTO personal (

                    numero_empleado,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    tipo_personal,
                    cargo,
                    area,
                    correo,
                    telefono,
                    foto,
                    qr,
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
                    TRUE

                );
            """, (

                numero_empleado,
                nombre,
                apellido_paterno,
                apellido_materno,
                tipo_personal,
                cargo,
                area,
                correo,
                telefono,
                foto,
                qr

            ))

        conexion.commit()


# ============================================================
# ACTUALIZAR PERSONAL
# ============================================================

def actualizar_personal(

    personal_id,

    numero_empleado,

    nombre,

    apellido_paterno,

    apellido_materno,

    tipo_personal,

    cargo,

    area,

    correo,

    telefono,

    foto=None,

    qr=None

):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            # ------------------------------------------------
            # SI SE RECIBIÓ UNA NUEVA FOTO
            # ------------------------------------------------

            if foto:

                cursor.execute("""
                    UPDATE personal

                    SET
                        numero_empleado = %s,
                        nombre = %s,
                        apellido_paterno = %s,
                        apellido_materno = %s,
                        tipo_personal = %s,
                        cargo = %s,
                        area = %s,
                        correo = %s,
                        telefono = %s,
                        foto = %s

                    WHERE id = %s;
                """, (

                    numero_empleado,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    tipo_personal,
                    cargo,
                    area,
                    correo,
                    telefono,
                    foto,
                    personal_id

                ))

            # ------------------------------------------------
            # SI NO SE RECIBIÓ UNA NUEVA FOTO
            # ------------------------------------------------

            else:

                cursor.execute("""
                    UPDATE personal

                    SET
                        numero_empleado = %s,
                        nombre = %s,
                        apellido_paterno = %s,
                        apellido_materno = %s,
                        tipo_personal = %s,
                        cargo = %s,
                        area = %s,
                        correo = %s,
                        telefono = %s

                    WHERE id = %s;
                """, (

                    numero_empleado,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    tipo_personal,
                    cargo,
                    area,
                    correo,
                    telefono,
                    personal_id

                ))

        conexion.commit()

# ============================================================
# ELIMINAR PERSONAL
# ============================================================

def eliminar_personal(
    personal_id
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE usuarios
                ADD COLUMN IF NOT EXISTS personal_id INTEGER
                REFERENCES personal(id) ON DELETE SET NULL;
            """)
            cursor.execute("""
                UPDATE usuarios
                SET activo = FALSE
                WHERE personal_id = %s AND rol = 'docente';
            """, (personal_id,))
            cursor.execute("""
                UPDATE personal
                SET activo = FALSE
                WHERE id = %s AND activo = TRUE
                RETURNING id;
            """, (personal_id,))
            eliminado = cursor.fetchone() is not None
        return eliminado
