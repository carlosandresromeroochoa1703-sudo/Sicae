import bcrypt
import psycopg

from app.database.connection import DATABASE_CONFIG


ROLES_PERMITIDOS = {"administrador", "operador", "docente"}


def _validar_rol(rol):
    if rol not in ROLES_PERMITIDOS:
        raise ValueError("Selecciona un rol válido para el usuario.")


def _asegurar_vinculo_docente(cursor):
    cursor.execute("""
        ALTER TABLE usuarios
        ADD COLUMN IF NOT EXISTS personal_id INTEGER
        REFERENCES personal(id) ON DELETE SET NULL;
    """)


def _validar_docente(cursor, personal_id, usuario_id=None):
    cursor.execute("""
        SELECT 1
        FROM personal p
        WHERE p.id = %s AND p.activo = TRUE
          AND LOWER(TRIM(p.tipo_personal)) = 'docente'
          AND NOT EXISTS (
              SELECT 1 FROM usuarios u
              WHERE u.personal_id = p.id AND u.rol = 'docente'
                AND u.activo = TRUE AND u.id <> COALESCE(%s, -1)
          );
    """, (personal_id, usuario_id))
    if cursor.fetchone() is None:
        raise ValueError("El docente no está activo, no es de tipo Docente o ya tiene una cuenta vinculada.")


def obtener_usuarios():
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_vinculo_docente(cursor)
            cursor.execute("""
                SELECT u.id, u.usuario, u.nombre, u.rol, u.activo, u.fecha_creacion,
                       u.personal_id,
                       concat_ws(' ', p.nombre, p.apellido_paterno, p.apellido_materno)
                FROM usuarios u
                LEFT JOIN personal p ON p.id = u.personal_id
                ORDER BY u.id ASC;
            """)
            return [
                {"id": r[0], "usuario": r[1], "nombre": r[2], "rol": r[3],
                 "activo": r[4], "fecha_creacion": r[5], "personal_id": r[6], "maestro": r[7]}
                for r in cursor.fetchall()
            ]


def crear_usuario(usuario, password, nombre, rol, personal_id=None):
    _validar_rol(rol)
    if rol == "docente" and not personal_id:
        raise ValueError("Selecciona el registro de personal correspondiente al maestro.")
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_vinculo_docente(cursor)
            if rol == "docente":
                _validar_docente(cursor, personal_id)
            cursor.execute("""
                INSERT INTO usuarios (usuario, password, nombre, rol, activo, personal_id)
                VALUES (%s, %s, %s, %s, TRUE, %s);
            """, (usuario.strip(), password_hash, nombre.strip(), rol,
                  personal_id if rol == "docente" else None))


def obtener_usuario_por_id(usuario_id):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_vinculo_docente(cursor)
            cursor.execute("""
                SELECT id, usuario, nombre, rol, activo, fecha_creacion, personal_id
                FROM usuarios WHERE id = %s;
            """, (usuario_id,))
            fila = cursor.fetchone()
    if not fila:
        return None
    return {"id": fila[0], "usuario": fila[1], "nombre": fila[2], "rol": fila[3],
            "activo": fila[4], "fecha_creacion": fila[5], "personal_id": fila[6]}


def actualizar_usuario(usuario_id, usuario, nombre, rol, password=None, personal_id=None):
    _validar_rol(rol)
    if rol == "docente" and not personal_id:
        raise ValueError("Selecciona el registro de personal correspondiente al maestro.")
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_vinculo_docente(cursor)
            if rol == "docente":
                _validar_docente(cursor, personal_id, usuario_id)
            valores = [usuario.strip(), nombre.strip(), rol,
                       personal_id if rol == "docente" else None]
            consulta = """
                UPDATE usuarios SET usuario = %s, nombre = %s, rol = %s, personal_id = %s
            """
            if password:
                password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                consulta += ", password = %s"
                valores.append(password_hash)
            consulta += " WHERE id = %s;"
            valores.append(usuario_id)
            cursor.execute(consulta, valores)


def cambiar_estado_usuario(usuario_id):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE usuarios SET activo = NOT activo WHERE id = %s;", (usuario_id,))


def autenticar_usuario(usuario, password):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_vinculo_docente(cursor)
            cursor.execute("""
                SELECT id, usuario, password, nombre, rol, activo, personal_id
                FROM usuarios WHERE usuario = %s;
            """, (usuario.strip(),))
            fila = cursor.fetchone()
    if not fila or not fila[5] or fila[4] not in ROLES_PERMITIDOS:
        return None
    try:
        password_correcta = bcrypt.checkpw(password.encode("utf-8"), fila[2].encode("utf-8"))
    except (ValueError, TypeError):
        return None
    if not password_correcta:
        return None
    return {"id": fila[0], "usuario": fila[1], "nombre": fila[3], "rol": fila[4],
            "activo": fila[5], "personal_id": fila[6]}
