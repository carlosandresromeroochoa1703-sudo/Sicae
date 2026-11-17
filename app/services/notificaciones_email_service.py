import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv, set_key

from app.services.notificaciones_config_service import obtener_configuracion_notificaciones


load_dotenv()
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


MENSAJE_PREDETERMINADO = """Estimado padre, madre o tutor:

Le informamos que se ha registrado un movimiento de asistencia en SICAE WEB.

Alumno: {nombre}
Matrícula: {matricula}
Movimiento: {movimiento}
Fecha: {fecha}
Hora: {hora}
Grado: {grado}
Grupo: {grupo}
Turno: {turno}

Este mensaje fue generado automáticamente por SICAE WEB.

Saludos."""


def obtener_configuracion_smtp():
    try:
        puerto = int(os.getenv("SMTP_PORT", "587"))
    except (TypeError, ValueError):
        puerto = 587
    return {
        "smtp_host": os.getenv("SMTP_HOST", ""),
        "smtp_port": puerto,
        "smtp_user": os.getenv("SMTP_USER", ""),
        "smtp_security": os.getenv("SMTP_SECURITY", "starttls"),
        "smtp_password_configurada": bool(os.getenv("SMTP_PASSWORD")),
    }


def guardar_configuracion_smtp(
    smtp_host, smtp_port, smtp_user, smtp_password, smtp_security, correo_remitente
):
    valores = {
        "SMTP_HOST": smtp_host.strip(),
        "SMTP_PORT": str(int(smtp_port)),
        "SMTP_USER": smtp_user.strip(),
        "SMTP_SECURITY": smtp_security,
        "SMTP_FROM": correo_remitente.strip(),
    }
    if smtp_password:
        valores["SMTP_PASSWORD"] = smtp_password
    for clave, valor in valores.items():
        set_key(str(ENV_PATH), clave, valor, quote_mode="always")
        os.environ[clave] = valor


def _enviar_correo_smtp(destino, asunto, cuerpo, remitente=None):
    host = os.getenv("SMTP_HOST")
    usuario = os.getenv("SMTP_USER")
    contrasena = os.getenv("SMTP_PASSWORD")
    remitente = remitente or os.getenv("SMTP_FROM") or usuario
    try:
        puerto = int(os.getenv("SMTP_PORT", "587"))
    except (TypeError, ValueError) as error:
        raise ValueError("El puerto SMTP debe ser un número válido.") from error
    if not host or not usuario or not contrasena or not remitente:
        raise ValueError("Completa servidor, usuario, remitente y contraseña SMTP.")

    mensaje = MIMEMultipart()
    mensaje["From"] = remitente
    mensaje["To"] = destino
    mensaje["Subject"] = asunto
    mensaje.attach(MIMEText(cuerpo, "plain", "utf-8"))

    seguridad = os.getenv("SMTP_SECURITY", "starttls").lower()
    contexto = ssl.create_default_context()
    if seguridad == "ssl":
        servidor = smtplib.SMTP_SSL(host, puerto, timeout=20, context=contexto)
    elif seguridad == "starttls":
        servidor = smtplib.SMTP(host, puerto, timeout=20)
    else:
        raise ValueError("Selecciona una conexión STARTTLS o SSL.")

    with servidor:
        if seguridad == "starttls":
            servidor.ehlo()
            servidor.starttls(context=contexto)
            servidor.ehlo()
        servidor.login(usuario, contrasena)
        servidor.sendmail(remitente, destino, mensaje.as_string())


def enviar_correo_prueba(destino):
    configuracion = obtener_configuracion_notificaciones() or {}
    remitente = configuracion.get("correo_remitente") or os.getenv("SMTP_FROM")
    _enviar_correo_smtp(
        destino,
        "Prueba de correo - SICAE WEB",
        "Este es un mensaje de prueba de SICAE WEB.\n\nLa configuración de correo se conectó correctamente.",
        remitente,
    )


def enviar_notificacion_acceso(
    correo_destino,
    nombre_completo,
    movimiento,
    fecha,
    hora,
    matricula="",
    grado="",
    grupo="",
    turno="",
):
    if not correo_destino:
        print("NOTIFICACION EMAIL: alumno sin correo.")
        return False

    configuracion = obtener_configuracion_notificaciones()
    if not configuracion:
        print("NOTIFICACION EMAIL: no existe configuración.")
        return False
    if not configuracion.get("notificaciones_activas", True):
        print("NOTIFICACION EMAIL: notificaciones desactivadas.")
        return False
    if movimiento == "ENTRADA" and not configuracion.get("enviar_entrada", True):
        return False
    if movimiento == "SALIDA" and not configuracion.get("enviar_salida", True):
        return False

    valores = {
        "nombre": nombre_completo or "",
        "matricula": matricula or "",
        "movimiento": movimiento or "",
        "fecha": fecha or "",
        "hora": hora or "",
        "grado": grado or "",
        "grupo": grupo or "",
        "turno": turno or "",
    }
    asunto = configuracion.get("asunto") or f"SICAE WEB - {movimiento} registrada"
    plantilla = configuracion.get("mensaje") or MENSAJE_PREDETERMINADO
    try:
        asunto_final = asunto.format(**valores)
        cuerpo = plantilla.format(**valores)
        remitente = configuracion.get("correo_remitente") or os.getenv("SMTP_FROM")
        _enviar_correo_smtp(correo_destino, asunto_final, cuerpo, remitente)
        print(f"NOTIFICACION EMAIL: enviada a {correo_destino}")
        return True
    except KeyError as error:
        print(f"NOTIFICACION EMAIL: variable no reconocida en la plantilla: {error}")
        return False
    except Exception as error:
        print("NOTIFICACION EMAIL: error al enviar:", error)
        return False


def enviar_notificacion_credencial_especial(
    correo_destino, nombre_completo, tipo_credencial, codigo, movimiento, fecha, hora,
    cargo="", organizacion="",
):
    if not correo_destino:
        return False
    valores = {
        "nombre": nombre_completo or "",
        "tipo": tipo_credencial or "Credencial",
        "codigo": codigo or "",
        "movimiento": movimiento or "",
        "fecha": fecha or "",
        "hora": hora or "",
        "cargo": cargo or "",
        "organizacion": organizacion or "",
    }
    asunto = f"SICAE WEB - {valores['movimiento']} de {valores['tipo']}"
    cuerpo = (
        "Se registró un movimiento de acceso en SICAE WEB.\n\n"
        "Tipo de credencial: {tipo}\nNombre: {nombre}\nCódigo: {codigo}\n"
        "Movimiento: {movimiento}\nFecha: {fecha}\nHora: {hora}\n"
        "Cargo: {cargo}\nOrganización: {organizacion}\n"
    ).format(**valores)
    configuracion = obtener_configuracion_notificaciones() or {}
    remitente = configuracion.get("correo_remitente") or os.getenv("SMTP_FROM")
    try:
        _enviar_correo_smtp(correo_destino, asunto, cuerpo, remitente)
        print(f"NOTIFICACION CREDENCIAL ESPECIAL: enviada a {correo_destino}")
        return True
    except Exception as error:
        print("NOTIFICACION CREDENCIAL ESPECIAL: error al enviar:", error)
        return False
