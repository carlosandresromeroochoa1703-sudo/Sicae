from datetime import date

import psycopg

from app.database.connection import DATABASE_CONFIG


def _asegurar_tablas(cursor):
    cursor.execute("""
        ALTER TABLE usuarios
        ADD COLUMN IF NOT EXISTS personal_id INTEGER
        REFERENCES personal(id) ON DELETE SET NULL;
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sesiones_asistencia_clase (
            id BIGSERIAL PRIMARY KEY,
            clase_id BIGINT NOT NULL REFERENCES clases_horario(id) ON DELETE CASCADE,
            fecha DATE NOT NULL,
            estado VARCHAR(12) NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta', 'cerrada')),
            iniciada_por INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
            iniciada_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            cerrada_en TIMESTAMPTZ,
            UNIQUE (clase_id, fecha)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros_asistencia_clase (
            id BIGSERIAL PRIMARY KEY,
            sesion_id BIGINT NOT NULL REFERENCES sesiones_asistencia_clase(id) ON DELETE CASCADE,
            alumno_id INTEGER NOT NULL REFERENCES alumnos(id) ON DELETE CASCADE,
            estado VARCHAR(12) NOT NULL CHECK (estado IN ('presente', 'retardo', 'ausente')),
            hora_registro TIME,
            registrado_por INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
            UNIQUE (sesion_id, alumno_id)
        );
    """)


def listar_resumen_asistencia_clases():
    """Resumen por clase del horario, con sesiones y estados registrados."""
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT ch.id, ch.materia, ch.grupo_id, g.nombre_grupo, g.grado, g.nombre,
                       COALESCE(NULLIF(concat_ws(' ', p.nombre, p.apellido_paterno, p.apellido_materno), ''), 'Sin asignar') AS maestro,
                       ch.dia_semana, ch.hora_inicio, ch.hora_fin, ch.aula,
                       s.id, s.fecha, s.estado,
                       COUNT(r.id) FILTER (WHERE r.estado = 'presente') AS presentes,
                       COUNT(r.id) FILTER (WHERE r.estado = 'retardo') AS retardos,
                       COUNT(r.id) FILTER (WHERE r.estado = 'ausente') AS faltas
                FROM clases_horario ch
                JOIN grupos g ON g.id = ch.grupo_id
                LEFT JOIN personal p ON p.id = ch.personal_id
                LEFT JOIN sesiones_asistencia_clase s ON s.clase_id = ch.id
                LEFT JOIN registros_asistencia_clase r ON r.sesion_id = s.id
                GROUP BY ch.id, g.id, p.id, s.id
                ORDER BY g.grado, g.nombre_grupo, ch.materia, ch.dia_semana, ch.hora_inicio, s.fecha DESC;
            """)
            clases = {}
            for row in cursor.fetchall():
                clase_id = row[0]
                if clase_id not in clases:
                    clases[clase_id] = {
                        "id": clase_id, "materia": row[1], "grupo_id": row[2],
                        "grupo": f"{row[4]}° {row[5]} · {row[3]}", "maestro": row[6],
                        "dia_semana": row[7], "hora_inicio": row[8].strftime("%H:%M"),
                        "hora_fin": row[9].strftime("%H:%M"), "aula": row[10],
                        "sesiones": [], "presentes": 0, "retardos": 0, "faltas": 0,
                    }
                if row[11] is not None:
                    sesion = {
                        "id": row[11], "fecha": row[12], "estado": row[13],
                        "presentes": row[14], "retardos": row[15], "faltas": row[16],
                    }
                    clases[clase_id]["sesiones"].append(sesion)
                    for estado in ("presentes", "retardos", "faltas"):
                        clases[clase_id][estado] += sesion[estado]
            return list(clases.values())


def listar_clases_docente(usuario_id):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT ch.id, ch.grupo_id, ch.materia, ch.dia_semana,
                       ch.hora_inicio, ch.hora_fin, ch.aula,
                       g.nombre_grupo, g.grado, g.nombre,
                       s.id, s.estado
                FROM usuarios u
                JOIN personal p ON p.id = u.personal_id
                JOIN clases_horario ch ON ch.personal_id = p.id
                JOIN grupos g ON g.id = ch.grupo_id
                LEFT JOIN sesiones_asistencia_clase s
                    ON s.clase_id = ch.id AND s.fecha = %s
                WHERE u.id = %s AND u.activo = TRUE AND p.activo = TRUE
                ORDER BY ch.dia_semana, ch.hora_inicio;
            """, (date.today(), usuario_id))
            return [
                {"id": r[0], "grupo_id": r[1], "materia": r[2], "dia_semana": r[3],
                 "hora_inicio": r[4].strftime("%H:%M"), "hora_fin": r[5].strftime("%H:%M"),
                 "aula": r[6], "grupo": f"{r[8]}° {r[9]} · {r[7]}",
                 "sesion_id": r[10], "sesion_estado": r[11]}
                for r in cursor.fetchall()
            ]


def _consultar_clase(cursor, clase_id, usuario_id, es_administrador):
    cursor.execute("""
        SELECT ch.id, ch.grupo_id, ch.materia, ch.dia_semana, ch.hora_inicio, ch.hora_fin,
               ch.aula, g.nombre_grupo, g.grado, g.nombre,
               COALESCE(NULLIF(concat_ws(' ', p.nombre, p.apellido_paterno, p.apellido_materno), ''), 'Sin asignar') AS maestro
        FROM clases_horario ch
        JOIN grupos g ON g.id = ch.grupo_id
        LEFT JOIN personal p ON p.id = ch.personal_id
        WHERE ch.id = %s
          AND (%s OR EXISTS (
              SELECT 1 FROM usuarios u
              WHERE u.id = %s AND u.personal_id = ch.personal_id AND u.activo = TRUE
          ));
    """, (clase_id, es_administrador, usuario_id))
    row = cursor.fetchone()
    if not row:
        return None
    return {"id": row[0], "grupo_id": row[1], "materia": row[2], "dia_semana": row[3],
            "hora_inicio": row[4].strftime("%H:%M"), "hora_fin": row[5].strftime("%H:%M"),
            "aula": row[6], "grupo": f"{row[8]}° {row[9]} · {row[7]}", "maestro": row[10]}


def iniciar_sesion_asistencia(clase_id, usuario_id, es_administrador=False):
    fecha_hoy = date.today()
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            clase = _consultar_clase(cursor, clase_id, usuario_id, es_administrador)
            if not clase:
                return {"ok": False, "mensaje": "No tienes acceso a esta clase."}
            if not es_administrador and clase["dia_semana"] != fecha_hoy.weekday():
                return {"ok": False, "mensaje": "Esta clase no está programada para hoy."}
            cursor.execute("""
                INSERT INTO sesiones_asistencia_clase (clase_id, fecha, iniciada_por)
                VALUES (%s, %s, %s)
                ON CONFLICT (clase_id, fecha) DO NOTHING
                RETURNING id, estado;
            """, (clase_id, fecha_hoy, usuario_id))
            sesion = cursor.fetchone()
            if not sesion:
                cursor.execute("""
                    SELECT id, estado FROM sesiones_asistencia_clase
                    WHERE clase_id = %s AND fecha = %s;
                """, (clase_id, fecha_hoy))
                sesion = cursor.fetchone()
            return {"ok": True, "sesion_id": sesion[0], "estado": sesion[1], "clase": clase}


def obtener_sesion_asistencia(sesion_id, usuario_id, es_administrador=False):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT s.id, s.fecha, s.estado, ch.id
                FROM sesiones_asistencia_clase s
                JOIN clases_horario ch ON ch.id = s.clase_id
                WHERE s.id = %s
                  AND (%s OR EXISTS (
                      SELECT 1 FROM usuarios u
                      WHERE u.id = %s AND u.personal_id = ch.personal_id AND u.activo = TRUE
                  ));
            """, (sesion_id, es_administrador, usuario_id))
            row = cursor.fetchone()
            if not row:
                return None
            clase = _consultar_clase(cursor, row[3], usuario_id, es_administrador)
            return {"id": row[0], "fecha": row[1], "estado": row[2], "clase": clase}


def listar_registros_sesion(sesion_id):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT r.alumno_id, a.nombre, a.apellido_paterno, a.apellido_materno,
                       a.matricula, r.estado, r.hora_registro
                FROM registros_asistencia_clase r
                JOIN alumnos a ON a.id = r.alumno_id
                WHERE r.sesion_id = %s
                ORDER BY CASE r.estado WHEN 'presente' THEN 1 WHEN 'retardo' THEN 2 ELSE 3 END,
                         a.apellido_paterno, a.apellido_materno, a.nombre;
            """, (sesion_id,))
            return [
                {"alumno_id": r[0], "nombre": " ".join(str(x or "").strip() for x in r[1:4]).strip(),
                 "matricula": r[4], "estado": r[5], "hora": r[6].strftime("%H:%M:%S") if r[6] else "—"}
                for r in cursor.fetchall()
            ]


def registrar_asistencia_clase(sesion_id, usuario_id, matricula, estado, es_administrador=False):
    if estado not in ("presente", "retardo"):
        return {"ok": False, "mensaje": "Selecciona presente o retardo."}
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT s.estado, ch.grupo_id
                FROM sesiones_asistencia_clase s
                JOIN clases_horario ch ON ch.id = s.clase_id
                WHERE s.id = %s
                  AND (%s OR EXISTS (
                      SELECT 1 FROM usuarios u
                      WHERE u.id = %s AND u.personal_id = ch.personal_id AND u.activo = TRUE
                  ));
            """, (sesion_id, es_administrador, usuario_id))
            sesion = cursor.fetchone()
            if not sesion:
                return {"ok": False, "mensaje": "No tienes acceso a esta asistencia."}
            if sesion[0] != "abierta":
                return {"ok": False, "mensaje": "La asistencia ya está cerrada."}
            cursor.execute("""
                SELECT id, matricula, nombre, apellido_paterno, apellido_materno
                FROM alumnos
                WHERE matricula = %s AND grupo_id = %s AND activo = TRUE;
            """, (matricula.strip(), sesion[1]))
            alumno = cursor.fetchone()
            if not alumno:
                return {"ok": False, "mensaje": "No se encontró un alumno activo de este grupo con esa matrícula."}
            cursor.execute("""
                INSERT INTO registros_asistencia_clase
                    (sesion_id, alumno_id, estado, hora_registro, registrado_por)
                VALUES (%s, %s, %s, CURRENT_TIME, %s)
                ON CONFLICT (sesion_id, alumno_id) DO NOTHING
                RETURNING estado, hora_registro;
            """, (sesion_id, alumno[0], estado, usuario_id))
            registro = cursor.fetchone()
            if not registro:
                cursor.execute("""
                    SELECT estado, hora_registro FROM registros_asistencia_clase
                    WHERE sesion_id = %s AND alumno_id = %s;
                """, (sesion_id, alumno[0]))
                existente = cursor.fetchone()
                return {"ok": True, "estado": "duplicado", "alumno_id": alumno[0],
                        "nombre": " ".join(str(x or "").strip() for x in alumno[2:5]).strip(),
                        "matricula": alumno[1], "estado_asistencia": existente[0],
                        "hora": existente[1].strftime("%H:%M:%S") if existente[1] else "—"}
            return {"ok": True, "estado": "registrado", "alumno_id": alumno[0],
                    "nombre": " ".join(str(x or "").strip() for x in alumno[2:5]).strip(),
                    "matricula": alumno[1], "estado_asistencia": registro[0],
                    "hora": registro[1].strftime("%H:%M:%S")}


def cerrar_sesion_asistencia(sesion_id, usuario_id, es_administrador=False):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT s.estado, s.fecha, ch.grupo_id
                FROM sesiones_asistencia_clase s
                JOIN clases_horario ch ON ch.id = s.clase_id
                WHERE s.id = %s
                  AND (%s OR EXISTS (
                      SELECT 1 FROM usuarios u
                      WHERE u.id = %s AND u.personal_id = ch.personal_id AND u.activo = TRUE
                  ));
            """, (sesion_id, es_administrador, usuario_id))
            sesion = cursor.fetchone()
            if not sesion:
                return False
            if sesion[0] == "cerrada":
                return True
            cursor.execute("""
                INSERT INTO registros_asistencia_clase
                    (sesion_id, alumno_id, estado, hora_registro, registrado_por)
                SELECT %s, a.id, 'ausente', NULL, %s
                FROM alumnos a
                WHERE a.grupo_id = %s AND a.activo = TRUE
                ON CONFLICT (sesion_id, alumno_id) DO NOTHING;
            """, (sesion_id, usuario_id, sesion[2]))
            cursor.execute("""
                UPDATE sesiones_asistencia_clase
                SET estado = 'cerrada', cerrada_en = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (sesion_id,))
            return True
