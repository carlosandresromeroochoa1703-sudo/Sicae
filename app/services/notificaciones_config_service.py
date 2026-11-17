import psycopg

from app.database.connection import DATABASE_CONFIG


def obtener_configuracion_notificaciones():
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    correo_remitente,
                    asunto,
                    mensaje,
                    notificaciones_activas,
                    enviar_entrada,
                    enviar_salida,
                    fecha_actualizacion
                FROM configuracion_notificaciones
                ORDER BY id
                LIMIT 1
            """)

            fila = cursor.fetchone()

            if fila:
                return {
                    "id": fila[0],
                    "correo_remitente": fila[1],
                    "asunto": fila[2],
                    "mensaje": fila[3],
                    "notificaciones_activas": fila[4],
                    "enviar_entrada": fila[5],
                    "enviar_salida": fila[6],
                    "fecha_actualizacion": fila[7],
                }

            return None


def guardar_configuracion_notificaciones(
    correo_remitente,
    asunto,
    mensaje,
    notificaciones_activas,
    enviar_entrada,
    enviar_salida
):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT id
                FROM configuracion_notificaciones
                ORDER BY id
                LIMIT 1
            """)

            fila = cursor.fetchone()

            if fila:

                cursor.execute("""
                    UPDATE configuracion_notificaciones
                    SET
                        correo_remitente = %s,
                        asunto = %s,
                        mensaje = %s,
                        notificaciones_activas = %s,
                        enviar_entrada = %s,
                        enviar_salida = %s,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    correo_remitente,
                    asunto,
                    mensaje,
                    notificaciones_activas,
                    enviar_entrada,
                    enviar_salida,
                    fila[0]
                ))

            else:

                cursor.execute("""
                    INSERT INTO configuracion_notificaciones (
                        correo_remitente,
                        asunto,
                        mensaje,
                        notificaciones_activas,
                        enviar_entrada,
                        enviar_salida
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    correo_remitente,
                    asunto,
                    mensaje,
                    notificaciones_activas,
                    enviar_entrada,
                    enviar_salida
                ))

        conexion.commit()
