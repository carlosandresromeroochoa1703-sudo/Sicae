import psycopg

from app.database.connection import DATABASE_CONFIG


def obtener_configuracion_credencial_personal():

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    nombre_institucion,
                    subtitulo,
                    logo,
                    color_principal,
                    color_secundario,
                    color_texto,
                    fuente,
                    tamano_nombre,
                    tamano_qr,
                    mostrar_foto,
                    mostrar_qr,
                    mostrar_matricula,
                    mostrar_tipo_personal,
                    mostrar_cargo,
                    mostrar_area,
                    mostrar_correo,
                    mostrar_telefono,
                    texto_pie,
                    layout,
                    fecha_actualizacion
                FROM configuracion_credencial_personal
                ORDER BY id
                LIMIT 1;
            """)

            resultado = cursor.fetchone()

            if resultado is None:
                return crear_configuracion_credencial_personal()

            columnas = [
                descripcion.name
                for descripcion in cursor.description
            ]

            return dict(
                zip(
                    columnas,
                    resultado
                )
            )


def crear_configuracion_credencial_personal():

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                INSERT INTO configuracion_credencial_personal (
                    nombre_institucion,
                    subtitulo,
                    color_principal,
                    color_secundario,
                    color_texto,
                    fuente,
                    tamano_nombre,
                    tamano_qr,
                    mostrar_foto,
                    mostrar_qr,
                    mostrar_matricula,
                    mostrar_tipo_personal,
                    mostrar_cargo,
                    mostrar_area,
                    mostrar_correo,
                    mostrar_telefono,
                    texto_pie
                )
                VALUES (
                    'SICAE WEB',
                    'Sistema de Registro BGM José María Chávez',
                    '#166534',
                    '#22c55e',
                    '#111827',
                    'Arial',
                    30,
                    300,
                    TRUE,
                    TRUE,
                    TRUE,
                    TRUE,
                    TRUE,
                    TRUE,
                    TRUE,
                    TRUE,
                    'Documento de identificación del personal'
                )
                RETURNING
                    id,
                    nombre_institucion,
                    subtitulo,
                    logo,
                    color_principal,
                    color_secundario,
                    color_texto,
                    fuente,
                    tamano_nombre,
                    tamano_qr,
                    mostrar_foto,
                    mostrar_qr,
                    mostrar_matricula,
                    mostrar_tipo_personal,
                    mostrar_cargo,
                    mostrar_area,
                    mostrar_correo,
                    mostrar_telefono,
                    texto_pie,
                    fecha_actualizacion;
            """)

            resultado = cursor.fetchone()

            conexion.commit()

            columnas = [
                descripcion.name
                for descripcion in cursor.description
            ]

            return dict(
                zip(
                    columnas,
                    resultado
                )
            )


def actualizar_configuracion_credencial_personal(

    nombre_institucion,
    subtitulo,
    logo,
    color_principal,
    color_secundario,
    color_texto,
    fuente,
    tamano_nombre,
    tamano_qr,
    mostrar_foto,
    mostrar_qr,
    mostrar_matricula,
    mostrar_tipo_personal,
    mostrar_cargo,
    mostrar_area,
    mostrar_correo,
    mostrar_telefono,
    texto_pie,
    layout=None,

):

    from psycopg.types.json import Jsonb
    layout = Jsonb(layout or {})

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                UPDATE configuracion_credencial_personal
                SET
                    nombre_institucion = %s,
                    subtitulo = %s,
                    logo = %s,
                    color_principal = %s,
                    color_secundario = %s,
                    color_texto = %s,
                    fuente = %s,
                    tamano_nombre = %s,
                    tamano_qr = %s,
                    mostrar_foto = %s,
                    mostrar_qr = %s,
                    mostrar_matricula = %s,
                    mostrar_tipo_personal = %s,
                    mostrar_cargo = %s,
                    mostrar_area = %s,
                    mostrar_correo = %s,
                    mostrar_telefono = %s,
                    texto_pie = %s,
                    layout = %s,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT id
                    FROM configuracion_credencial_personal
                    ORDER BY id
                    LIMIT 1
                );
            """, (

                nombre_institucion,
                subtitulo,
                logo,
                color_principal,
                color_secundario,
                color_texto,
                fuente,
                tamano_nombre,
                tamano_qr,
                mostrar_foto,
                mostrar_qr,
                mostrar_matricula,
                mostrar_tipo_personal,
                mostrar_cargo,
                mostrar_area,
                mostrar_correo,
                mostrar_telefono,
                texto_pie,
                layout,

            ))

        conexion.commit()



