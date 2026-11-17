import os
from zoneinfo import ZoneInfo

import psycopg

from app.database.connection import DATABASE_CONFIG
from app.services.notificaciones_email_service import _enviar_correo_smtp


MENSAJE_EVENTO_PREDETERMINADO = """Estimado padre, madre o tutor:

Le informamos que se registró la asistencia de su hijo(a) a una actividad fuera del plantel.

Alumno: {nombre}
Matrícula: {matricula}
Evento: {evento}
Fecha del evento: {fecha}
Hora de registro: {hora}
Grupo: {grupo}
Lugar: {lugar}

Este mensaje corresponde a una actividad fuera del plantel y es independiente de los avisos de entrada y salida.

Saludos.
"""


def _asegurar_configuracion(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion_notificaciones_eventos (
            id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            activa BOOLEAN NOT NULL DEFAULT FALSE,
            asunto TEXT NOT NULL DEFAULT 'SICAE WEB - Asistencia a evento: {evento}',
            mensaje TEXT NOT NULL DEFAULT ''
        );
    """)
    cursor.execute("""
        INSERT INTO configuracion_notificaciones_eventos (id, activa, asunto, mensaje)
        VALUES (1, FALSE, 'SICAE WEB - Asistencia a evento: {evento}', %s)
        ON CONFLICT (id) DO NOTHING;
    """, (MENSAJE_EVENTO_PREDETERMINADO,))


def obtener_configuracion_notificaciones_eventos():
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_configuracion(cursor)
            cursor.execute("""
                SELECT activa, asunto, mensaje
                FROM configuracion_notificaciones_eventos
                WHERE id = 1;
            """)
            fila = cursor.fetchone()
            return {"activa": fila[0], "asunto": fila[1], "mensaje": fila[2]}


def guardar_configuracion_notificaciones_eventos(activa, asunto, mensaje):
    asunto = (asunto or "").strip()
    mensaje = (mensaje or "").strip()
    if not asunto or not mensaje:
        raise ValueError("El asunto y el mensaje del correo son obligatorios.")
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_configuracion(cursor)
            cursor.execute("""
                UPDATE configuracion_notificaciones_eventos
                SET activa = %s, asunto = %s, mensaje = %s
                WHERE id = 1;
            """, (bool(activa), asunto[:300], mensaje[:10000]))


def enviar_notificacion_asistencia_evento(correo_destino, datos):
    if not correo_destino:
        return False, "El alumno no tiene correo registrado."
    try:
        configuracion = obtener_configuracion_notificaciones_eventos()
        if not configuracion["activa"]:
            return False, ""
        asunto = configuracion["asunto"].format(**datos)
        cuerpo = configuracion["mensaje"].format(**datos)
        _enviar_correo_smtp(
            correo_destino,
            asunto,
            cuerpo,
            os.getenv("SMTP_FROM") or os.getenv("SMTP_USER"),
        )
        return True, "Aviso enviado al correo registrado."
    except KeyError as error:
        print("NOTIFICACION EVENTO: variable no reconocida en la plantilla:", error)
        return False, f"La plantilla contiene una variable no reconocida: {error}."
    except Exception as error:
        print("NOTIFICACION EVENTO: error al enviar:", error)
        return False, "La asistencia se registró, pero no se pudo enviar el correo."


def enviar_notificacion_finalizacion_evento(correo_destino, nombre_alumno, datos):
    """Notifica a la familia la hora local a la que terminó el evento."""
    if not correo_destino:
        return False, ""
    try:
        hora = datos["finalizado_en"].astimezone(ZoneInfo("America/Mexico_City")).strftime("%H:%M")
        cuerpo = (
            "Estimado padre, madre o tutor:\n\n"
            f"Le informamos que el evento fuera del plantel «{datos['evento']}» ha finalizado.\n\n"
            f"Alumno: {nombre_alumno}\n"
            f"Fecha: {datos['fecha']}\n"
            f"Hora de finalización: {hora}\n"
            f"Lugar: {datos['lugar']}\n\n"
            "Saludos.\nSICAE WEB"
        )
        _enviar_correo_smtp(
            correo_destino,
            f"SICAE WEB - Finalizó el evento: {datos['evento']}",
            cuerpo,
            os.getenv("SMTP_FROM") or os.getenv("SMTP_USER"),
        )
        return True, ""
    except Exception as error:
        print("NOTIFICACION FINALIZACION EVENTO: error al enviar:", error)
        return False, str(error)
