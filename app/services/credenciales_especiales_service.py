import psycopg
from psycopg.types.json import Jsonb

from app.database.connection import DATABASE_CONFIG
from app.services.qr_service import generar_qr_credencial_especial


TIPOS_CREDENCIAL_ESPECIAL = {
    "direccion": "Dirección",
    "prefectura": "Prefectura",
    "conferencias": "Conferencias",
    "proveedores": "Proveedores",
}

COLORES_CREDENCIAL_ESPECIAL = {
    "direccion": ("#312e81", "#6366f1"),
    "prefectura": ("#065f46", "#10b981"),
    "conferencias": ("#9a3412", "#f97316"),
    "proveedores": ("#1e40af", "#3b82f6"),
}


def _dict_rows(cursor):
    columnas = [columna.name for columna in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def listar_credenciales_especiales(tipo):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.*,
                       (SELECT COUNT(*) FROM accesos_credenciales_especiales a WHERE a.credencial_id = c.id) AS total_registros,
                       (SELECT MAX(fecha + hora) FROM accesos_credenciales_especiales a WHERE a.credencial_id = c.id) AS ultimo_registro
                FROM credenciales_especiales c
                WHERE c.tipo = %s
                ORDER BY c.activo DESC, c.nombre, c.apellido_paterno;
                """,
                (tipo,),
            )
            return _dict_rows(cursor)


def obtener_credencial_especial(credencial_id):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM credenciales_especiales WHERE id = %s",
                (credencial_id,),
            )
            fila = cursor.fetchone()
            if not fila:
                return None
            return dict(zip([columna.name for columna in cursor.description], fila))


def crear_credencial_especial(datos):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO credenciales_especiales (
                    tipo, nombre, apellido_paterno, apellido_materno, cargo,
                    organizacion, telefono, foto, correo_1, correo_2, correo_3, correo_4
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    datos["tipo"], datos["nombre"], datos.get("apellido_paterno"),
                    datos.get("apellido_materno"), datos.get("cargo"),
                    datos.get("organizacion"), datos.get("telefono"), datos.get("foto"),
                    datos.get("correo_1"), datos.get("correo_2"),
                    datos.get("correo_3"), datos.get("correo_4"),
                ),
            )
            credencial_id = cursor.fetchone()[0]
            codigo = f"ESP-{credencial_id:06d}"
            qr = generar_qr_credencial_especial(credencial_id)
            cursor.execute(
                "UPDATE credenciales_especiales SET codigo = %s, qr = %s WHERE id = %s",
                (codigo, qr, credencial_id),
            )
    return obtener_credencial_especial(credencial_id)


def cambiar_estado_credencial_especial(credencial_id, activo):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE credenciales_especiales SET activo = %s WHERE id = %s",
                (bool(activo), credencial_id),
            )
            return cursor.rowcount > 0


def obtener_configuracion_credencial_especial(tipo):
    principal, secundario = COLORES_CREDENCIAL_ESPECIAL[tipo]
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO configuracion_credencial_especial (tipo, color_principal, color_secundario)
                VALUES (%s, %s, %s)
                ON CONFLICT (tipo) DO NOTHING;
                """,
                (tipo, principal, secundario),
            )
            cursor.execute(
                "SELECT * FROM configuracion_credencial_especial WHERE tipo = %s",
                (tipo,),
            )
            fila = cursor.fetchone()
            return dict(zip([columna.name for columna in cursor.description], fila))


def guardar_configuracion_credencial_especial(tipo, datos):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO configuracion_credencial_especial (
                    tipo, nombre_institucion, subtitulo, texto_pie, logo,
                    color_principal, color_secundario, color_texto, color_fondo,
                    fuente, tamano_nombre, mostrar_foto, mostrar_qr, mostrar_codigo,
                    mostrar_cargo, mostrar_organizacion, layout, fecha_actualizacion
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                )
                ON CONFLICT (tipo) DO UPDATE SET
                    nombre_institucion = EXCLUDED.nombre_institucion,
                    subtitulo = EXCLUDED.subtitulo,
                    texto_pie = EXCLUDED.texto_pie,
                    logo = EXCLUDED.logo,
                    color_principal = EXCLUDED.color_principal,
                    color_secundario = EXCLUDED.color_secundario,
                    color_texto = EXCLUDED.color_texto,
                    color_fondo = EXCLUDED.color_fondo,
                    fuente = EXCLUDED.fuente,
                    tamano_nombre = EXCLUDED.tamano_nombre,
                    mostrar_foto = EXCLUDED.mostrar_foto,
                    mostrar_qr = EXCLUDED.mostrar_qr,
                    mostrar_codigo = EXCLUDED.mostrar_codigo,
                    mostrar_cargo = EXCLUDED.mostrar_cargo,
                    mostrar_organizacion = EXCLUDED.mostrar_organizacion,
                    layout = EXCLUDED.layout,
                    fecha_actualizacion = CURRENT_TIMESTAMP;
                """,
                (
                    tipo, datos["nombre_institucion"], datos.get("subtitulo", ""),
                    datos.get("texto_pie", ""), datos.get("logo"),
                    datos["color_principal"], datos["color_secundario"],
                    datos["color_texto"], datos["color_fondo"], datos["fuente"],
                    datos["tamano_nombre"], datos["mostrar_foto"], datos["mostrar_qr"],
                    datos["mostrar_codigo"], datos["mostrar_cargo"],
                    datos["mostrar_organizacion"],
                    Jsonb(datos.get("layout") or {}),
                ),
            )
    return obtener_configuracion_credencial_especial(tipo)


def registrar_acceso_credencial_especial(referencia, movimiento_solicitado, registrado_por):
    try:
        credencial_id = int(referencia)
    except (TypeError, ValueError):
        return None

    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM credenciales_especiales WHERE id = %s AND activo = TRUE",
                (credencial_id,),
            )
            fila = cursor.fetchone()
            if not fila:
                return None
            columnas = [columna.name for columna in cursor.description]
            credencial = dict(zip(columnas, fila))

            cursor.execute(
                """
                SELECT
                    (SELECT movimiento FROM accesos_credenciales_especiales
                     WHERE credencial_id = %s AND fecha = CURRENT_DATE
                     ORDER BY hora DESC, id DESC LIMIT 1),
                    EXISTS (SELECT 1 FROM accesos_credenciales_especiales
                            WHERE credencial_id = %s AND fecha = CURRENT_DATE AND movimiento = 'ENTRADA');
                """,
                (credencial_id, credencial_id),
            )
            ultimo_movimiento, tiene_entrada = cursor.fetchone()
            if movimiento_solicitado in {"ENTRADA", "SALIDA"}:
                movimiento = movimiento_solicitado
            else:
                movimiento = "ENTRADA" if ultimo_movimiento in (None, "SALIDA") else "SALIDA"

            cursor.execute(
                """
                INSERT INTO accesos_credenciales_especiales (credencial_id, movimiento, registrado_por)
                VALUES (%s, %s, %s)
                RETURNING fecha, hora;
                """,
                (credencial_id, movimiento, registrado_por),
            )
            fecha, hora = cursor.fetchone()

    nombre_completo = " ".join(
        parte for parte in (
            credencial.get("nombre"), credencial.get("apellido_paterno"),
            credencial.get("apellido_materno"),
        ) if parte
    )
    credencial["nombre_completo"] = nombre_completo
    credencial["correos"] = [credencial.get(f"correo_{indice}") for indice in range(1, 5) if credencial.get(f"correo_{indice}")]
    credencial["etiqueta_tipo"] = TIPOS_CREDENCIAL_ESPECIAL[credencial["tipo"]]
    return {
        "credencial": credencial,
        "movimiento": movimiento,
        "fecha": fecha,
        "hora": hora,
    }


def entidad_especial_para_pdf(credencial):
    return {
        "id": credencial["id"],
        "matricula": credencial.get("codigo") or f"ESP-{credencial['id']:06d}",
        "nombre": credencial.get("nombre") or "",
        "apellido_paterno": credencial.get("apellido_paterno") or "",
        "apellido_materno": credencial.get("apellido_materno") or "",
        "cargo": credencial.get("cargo") or "",
        "organizacion": credencial.get("organizacion") or "",
        "tipo_credencial": TIPOS_CREDENCIAL_ESPECIAL[credencial["tipo"]],
        "foto": credencial.get("foto"),
        "qr": credencial.get("qr"),
    }
