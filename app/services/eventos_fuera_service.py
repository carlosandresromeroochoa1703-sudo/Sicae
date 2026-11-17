import psycopg
from zoneinfo import ZoneInfo

from app.database.connection import DATABASE_CONFIG


def _asegurar_tablas(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos_fuera_plantel (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(160) NOT NULL,
            fecha_evento DATE NOT NULL,
            lugar VARCHAR(200) NOT NULL DEFAULT '',
            notas TEXT NOT NULL DEFAULT '',
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finalizado_en TIMESTAMPTZ
        );
    """)
    cursor.execute("ALTER TABLE eventos_fuera_plantel ADD COLUMN IF NOT EXISTS finalizado_en TIMESTAMPTZ;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evento_fuera_grupos (
            evento_id INTEGER NOT NULL REFERENCES eventos_fuera_plantel(id) ON DELETE CASCADE,
            grupo_id INTEGER NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
            PRIMARY KEY (evento_id, grupo_id)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asistencia_eventos_fuera (
            id BIGSERIAL PRIMARY KEY,
            evento_id INTEGER NOT NULL REFERENCES eventos_fuera_plantel(id) ON DELETE CASCADE,
            alumno_id INTEGER NOT NULL REFERENCES alumnos(id) ON DELETE CASCADE,
            grupo_id INTEGER NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
            registrada_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT asistencia_evento_alumno_unica UNIQUE (evento_id, alumno_id)
        );
    """)


def listar_eventos_fuera():
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT e.id, e.nombre, e.fecha_evento, e.lugar, e.notas, e.activo, e.finalizado_en,
                       COALESCE((
                           SELECT string_agg(g.nombre_grupo || ' ' || g.grado::text || '° ' || g.nombre, ', ' ORDER BY g.grado, g.nombre)
                           FROM evento_fuera_grupos eg JOIN grupos g ON g.id = eg.grupo_id
                           WHERE eg.evento_id = e.id
                       ), '') AS grupos,
                       (SELECT COUNT(*) FROM asistencia_eventos_fuera a WHERE a.evento_id = e.id) AS presentes
                FROM eventos_fuera_plantel e
                ORDER BY e.fecha_evento DESC, e.id DESC;
            """)
            return [
                {"id": row[0], "nombre": row[1], "fecha_evento": row[2], "lugar": row[3],
                 "notas": row[4], "activo": row[5],
                 "finalizado_en": row[6].astimezone(ZoneInfo("America/Mexico_City")) if row[6] else None,
                 "grupos": row[7], "presentes": row[8]}
                for row in cursor.fetchall()
            ]


def crear_evento_fuera(nombre, fecha_evento, lugar, notas, grupos_ids):
    ids = sorted({int(value) for value in grupos_ids})
    if not nombre.strip() or not ids:
        raise ValueError("Indica el nombre del evento y al menos un grupo.")
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("SELECT id FROM grupos WHERE activo = TRUE AND id = ANY(%s);", (ids,))
            grupos_validos = {row[0] for row in cursor.fetchall()}
            if grupos_validos != set(ids):
                raise ValueError("Uno o más grupos seleccionados ya no están disponibles.")
            cursor.execute("""
                INSERT INTO eventos_fuera_plantel (nombre, fecha_evento, lugar, notas)
                VALUES (%s, %s, %s, %s) RETURNING id;
            """, (nombre.strip()[:160], fecha_evento, (lugar or "").strip()[:200], (notas or "").strip()))
            evento_id = cursor.fetchone()[0]
            cursor.executemany(
                "INSERT INTO evento_fuera_grupos (evento_id, grupo_id) VALUES (%s, %s);",
                [(evento_id, grupo_id) for grupo_id in ids],
            )
            return evento_id


def obtener_evento_fuera(evento_id):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT id, nombre, fecha_evento, lugar, notas, activo, finalizado_en
                FROM eventos_fuera_plantel WHERE id = %s;
            """, (evento_id,))
            row = cursor.fetchone()
            if not row:
                return None
            evento = {"id": row[0], "nombre": row[1], "fecha_evento": row[2], "lugar": row[3], "notas": row[4], "activo": row[5],
                      "finalizado_en": row[6].astimezone(ZoneInfo("America/Mexico_City")) if row[6] else None}
            cursor.execute("""
                SELECT g.id, g.nombre_grupo, g.grado, g.nombre, g.turno
                FROM evento_fuera_grupos eg JOIN grupos g ON g.id = eg.grupo_id
                WHERE eg.evento_id = %s ORDER BY g.grado, g.nombre;
            """, (evento_id,))
            evento["grupos"] = [
                {"id": r[0], "nombre_grupo": r[1], "grado": r[2], "nombre": r[3], "turno": r[4]}
                for r in cursor.fetchall()
            ]
            return evento


def cambiar_estado_evento_fuera(evento_id, activo):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute(
                "UPDATE eventos_fuera_plantel SET activo = %s WHERE id = %s RETURNING id;",
                (activo, evento_id),
            )
            return cursor.fetchone() is not None


def eliminar_evento_fuera(evento_id):
    """Elimina un evento y sus grupos/asistencias dependientes."""
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute(
                "DELETE FROM eventos_fuera_plantel WHERE id = %s RETURNING id;",
                (evento_id,),
            )
            return cursor.fetchone() is not None


def finalizar_evento_fuera(evento_id):
    """Finaliza el evento una sola vez y devuelve familias con asistencia registrada."""
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                UPDATE eventos_fuera_plantel
                SET activo = FALSE, finalizado_en = COALESCE(finalizado_en, CURRENT_TIMESTAMP)
                WHERE id = %s AND finalizado_en IS NULL
                RETURNING nombre, fecha_evento, lugar, finalizado_en;
            """, (evento_id,))
            evento = cursor.fetchone()
            if not evento:
                return None, []
            cursor.execute("""
                SELECT DISTINCT ON (al.id) al.id, al.nombre, al.apellido_paterno,
                       al.apellido_materno, al.correo
                FROM asistencia_eventos_fuera a
                JOIN alumnos al ON al.id = a.alumno_id
                WHERE a.evento_id = %s AND COALESCE(al.correo, '') <> ''
                ORDER BY al.id;
            """, (evento_id,))
            familias = [{"nombre": " ".join(str(v or "").strip() for v in r[1:4]).strip(), "correo": r[4]} for r in cursor.fetchall()]
            datos = {"evento": evento[0], "fecha": evento[1].strftime("%d/%m/%Y"), "lugar": evento[2] or "", "finalizado_en": evento[3]}
            return datos, familias


def listar_asistencias_evento_fuera(evento_id):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT a.id, a.alumno_id, al.matricula, al.nombre, al.apellido_paterno,
                       al.apellido_materno, g.nombre_grupo, g.grado, g.nombre, a.registrada_en
                FROM asistencia_eventos_fuera a
                JOIN alumnos al ON al.id = a.alumno_id
                JOIN grupos g ON g.id = a.grupo_id
                WHERE a.evento_id = %s
                ORDER BY a.registrada_en DESC;
            """, (evento_id,))
            return [
                {"id": r[0], "alumno_id": r[1], "matricula": r[2],
                 "nombre": " ".join(str(value or "").strip() for value in r[3:6]).strip(),
                 "grupo": f"{r[7]}° {r[8]} · {r[6]}",
                 "registrada_en": r[9].strftime("%H:%M:%S")}
                for r in cursor.fetchall()
            ]


def registrar_asistencia_evento_fuera(evento_id, grupo_id, matricula):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tablas(cursor)
            cursor.execute("""
                SELECT activo, nombre, fecha_evento, lugar
                FROM eventos_fuera_plantel WHERE id = %s;
            """, (evento_id,))
            evento = cursor.fetchone()
            if not evento:
                return {"ok": False, "estado": "no_encontrado", "mensaje": "Evento no encontrado."}
            if not evento[0]:
                return {"ok": False, "estado": "cerrado", "mensaje": "Este evento está cerrado."}
            consulta_alumno = """
                SELECT al.id, al.matricula, al.nombre, al.apellido_paterno, al.apellido_materno,
                       g.id, g.grado, g.nombre, g.nombre_grupo, al.correo
                FROM alumnos al
                JOIN grupos g ON g.id = al.grupo_id
                JOIN evento_fuera_grupos eg ON eg.grupo_id = g.id AND eg.evento_id = %s
                WHERE al.matricula = %s AND al.activo = TRUE AND g.activo = TRUE
            """
            parametros_alumno = [evento_id, matricula.strip()]
            if grupo_id is not None:
                consulta_alumno += " AND al.grupo_id = %s"
                parametros_alumno.append(grupo_id)
            consulta_alumno += ";"
            cursor.execute(consulta_alumno, tuple(parametros_alumno))
            alumno = cursor.fetchone()
            if not alumno:
                return {"ok": False, "estado": "grupo_incorrecto", "mensaje": "No se encontró un alumno activo con esa matrícula en el grupo seleccionado."}
            cursor.execute("""
                INSERT INTO asistencia_eventos_fuera (evento_id, alumno_id, grupo_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (evento_id, alumno_id) DO NOTHING
                RETURNING registrada_en;
            """, (evento_id, alumno[0], alumno[5]))
            registro = cursor.fetchone()
            if registro:
                return {"ok": True, "estado": "registrado", "alumno_id": alumno[0], "mensaje": "Asistencia registrada.",
                        "matricula": alumno[1], "nombre": " ".join(str(v or "").strip() for v in alumno[2:5]).strip(),
                        "grupo": f"{alumno[6]}° {alumno[7]} · {alumno[8]}", "hora": registro[0].strftime("%H:%M:%S"),
                        "correo": alumno[9], "evento": evento[1], "fecha_evento": evento[2].strftime("%d/%m/%Y"),
                        "lugar": evento[3] or ""}
            cursor.execute("SELECT registrada_en FROM asistencia_eventos_fuera WHERE evento_id = %s AND alumno_id = %s;", (evento_id, alumno[0]))
            existente = cursor.fetchone()
            return {"ok": True, "estado": "duplicado", "alumno_id": alumno[0], "mensaje": "Este alumno ya tiene asistencia en el evento.",
                    "matricula": alumno[1], "nombre": " ".join(str(v or "").strip() for v in alumno[2:5]).strip(),
                    "grupo": f"{alumno[6]}° {alumno[7]} · {alumno[8]}",
                    "hora": existente[0].strftime("%H:%M:%S") if existente else "",
                    "correo": alumno[9], "evento": evento[1], "fecha_evento": evento[2].strftime("%d/%m/%Y"),
                    "lugar": evento[3] or ""}
