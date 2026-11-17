import psycopg

from app.database.connection import DATABASE_CONFIG


# ============================================================
# OBTENER CONFIGURACIÓN DEL SISTEMA
# ============================================================

def obtener_configuracion_sistema():

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    nombre_sistema,
                    subtitulo,
                    titulo_excel,
                    subtitulo_excel,
                    texto_bienvenida,
                    logo_excel,
                    color_principal,
                    color_secundario,
                    color_fondo_login,
                    logo_login,
                    logo_tamano,
                    fecha_actualizacion
                FROM configuracion_sistema
                ORDER BY id
                LIMIT 1;
            """)

            resultado = cursor.fetchone()

            if resultado is None:
                return crear_configuracion_sistema()

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


# ============================================================
# CREAR CONFIGURACIÓN INICIAL
# ============================================================

def crear_configuracion_sistema():

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                INSERT INTO configuracion_sistema (
                    nombre_sistema,
                    subtitulo,
                    titulo_excel,
                    subtitulo_excel,
                    texto_bienvenida,
                    color_principal,
                    color_secundario,
                    color_fondo_login,
                    color_texto_login,
                logo_tamano,
                )
                VALUES (
                    'SICAE WEB',
                    'Sistema de Registro BGM José María Chávez',
                    'Reporte de Asistencias',
                    'Sistema de Registro de Asistencias',
                    'Sistema de control y registro de asistencias.',
                    '#2563EB',
                    '#1E40AF',
                    '#F3F4F6',
                    '#111827',
                    120
                )
                RETURNING
                    id,
                    nombre_sistema,
                    subtitulo,
                    titulo_excel,
                    subtitulo_excel,
                    texto_bienvenida,
                    logo_excel,
                    color_principal,
                    color_secundario,
                    color_fondo_login,
                    color_texto_login,
                    logo_login,
                    logo_tamano,
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


# ============================================================
# ACTUALIZAR CONFIGURACIÓN
# ============================================================

def actualizar_configuracion_sistema(
    nombre_sistema,
    subtitulo,
    texto_bienvenida,
    logo_excel,
    color_principal,
    color_secundario,
    color_fondo_login,
    color_texto_login,
    logo_login,
    logo_tamano,
    titulo_excel,
    subtitulo_excel
):

    with psycopg.connect(
        **DATABASE_CONFIG
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                UPDATE configuracion_sistema
                SET
                    nombre_sistema = %s,
                    subtitulo = %s,
                    texto_bienvenida = %s,
                    logo_excel = %s,
                    color_principal = %s,
                    color_secundario = %s,
                    color_fondo_login = %s,
                    color_texto_login = %s,
                    logo_login = %s,
                    logo_tamano = %s,
                    titulo_excel = %s,
                    subtitulo_excel = %s,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT id
                    FROM configuracion_sistema
                    ORDER BY id
                    LIMIT 1
                );
            """, (
                nombre_sistema,
                subtitulo,
                texto_bienvenida,
                logo_excel,
                color_principal,
                color_secundario,
                color_fondo_login,
                color_texto_login,
                logo_login,
                logo_tamano,
                titulo_excel,
                subtitulo_excel
            ))

        conexion.commit()







