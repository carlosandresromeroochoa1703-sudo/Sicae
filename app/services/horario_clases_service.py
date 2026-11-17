import psycopg

from app.database.connection import DATABASE_CONFIG


DIAS_SEMANA = [
    (0, "Lunes"),
    (1, "Martes"),
    (2, "Miércoles"),
    (3, "Jueves"),
    (4, "Viernes"),
    (5, "Sábado"),
    (6, "Domingo"),
]


def _asegurar_tabla(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clases_horario (
            id BIGSERIAL PRIMARY KEY,
            grupo_id INTEGER NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
            materia VARCHAR(150) NOT NULL,
            personal_id INTEGER REFERENCES personal(id) ON DELETE RESTRICT,
            dia_semana SMALLINT NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
            hora_inicio TIME NOT NULL,
            hora_fin TIME NOT NULL,
            aula VARCHAR(100) NOT NULL DEFAULT '',
            creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (hora_fin > hora_inicio)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion_tabla_horario (
            grupo_id INTEGER PRIMARY KEY REFERENCES grupos(id) ON DELETE CASCADE,
            hora_inicio TIME NOT NULL DEFAULT '07:00',
            minutos_por_celda SMALLINT NOT NULL DEFAULT 30 CHECK (minutos_por_celda BETWEEN 5 AND 180),
            cantidad_celdas SMALLINT NOT NULL DEFAULT 20 CHECK (cantidad_celdas BETWEEN 2 AND 48),
            actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        ALTER TABLE clases_horario
        ALTER COLUMN personal_id DROP NOT NULL;
    """)


def obtener_configuracion_tablas():
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tabla(cursor)
            cursor.execute("""
                SELECT grupo_id, hora_inicio, minutos_por_celda, cantidad_celdas
                FROM configuracion_tabla_horario;
            """)
            return {
                row[0]: {
                    "hora_inicio": row[1].strftime("%H:%M"),
                    "minutos_por_celda": row[2],
                    "cantidad_celdas": row[3],
                }
                for row in cursor.fetchall()
            }


def guardar_configuracion_tabla(grupo_id, hora_inicio, minutos_por_celda, cantidad_celdas):
    if minutos_por_celda < 5 or minutos_por_celda > 180:
        raise ValueError("La duración de cada celda debe ser de 5 a 180 minutos.")
    if cantidad_celdas < 2 or cantidad_celdas > 48:
        raise ValueError("La tabla debe tener entre 2 y 48 celdas.")
    inicio_minutos = hora_inicio.hour * 60 + hora_inicio.minute
    if inicio_minutos + minutos_por_celda * cantidad_celdas > 24 * 60:
        raise ValueError("El horario de la tabla no puede pasar de medianoche.")
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tabla(cursor)
            cursor.execute("""
                INSERT INTO configuracion_tabla_horario
                    (grupo_id, hora_inicio, minutos_por_celda, cantidad_celdas)
                SELECT id, %s, %s, %s FROM grupos WHERE id = %s AND activo = TRUE
                ON CONFLICT (grupo_id) DO UPDATE SET
                    hora_inicio = EXCLUDED.hora_inicio,
                    minutos_por_celda = EXCLUDED.minutos_por_celda,
                    cantidad_celdas = EXCLUDED.cantidad_celdas,
                    actualizado_en = CURRENT_TIMESTAMP
                RETURNING grupo_id;
            """, (hora_inicio, minutos_por_celda, cantidad_celdas, grupo_id))
            if cursor.fetchone() is None:
                raise ValueError("El grupo seleccionado ya no está activo.")


def listar_clases_horario():
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tabla(cursor)
            cursor.execute("""
                SELECT ch.id, ch.grupo_id, g.nombre_grupo, g.grado, g.nombre,
                       ch.materia, ch.personal_id,
                       COALESCE(NULLIF(concat_ws(' ', p.nombre, p.apellido_paterno, p.apellido_materno), ''), 'Sin asignar') AS maestro,
                       ch.dia_semana, ch.hora_inicio, ch.hora_fin, ch.aula
                FROM clases_horario ch
                JOIN grupos g ON g.id = ch.grupo_id
                LEFT JOIN personal p ON p.id = ch.personal_id
                ORDER BY ch.dia_semana, ch.hora_inicio, g.grado, g.nombre_grupo;
            """)
            return [
                {
                    "id": row[0], "grupo_id": row[1], "grupo": f"{row[3]}° {row[4]} · {row[2]}",
                    "materia": row[5], "personal_id": row[6], "maestro": row[7],
                    "dia_semana": row[8], "dia": DIAS_SEMANA[row[8]][1],
                    "hora_inicio": row[9].strftime("%H:%M"), "hora_fin": row[10].strftime("%H:%M"),
                    "aula": row[11],
                }
                for row in cursor.fetchall()
            ]


def crear_clases_horario(grupo_id, materia, personal_id, dias_semana, hora_inicio, hora_fin, aula=""):
    materia = (materia or "").strip()
    aula = (aula or "").strip()
    dias_semana = sorted(set(dias_semana or []))
    if not materia:
        raise ValueError("Escribe el nombre de la materia o clase.")
    if hora_fin <= hora_inicio:
        raise ValueError("La hora de fin debe ser posterior a la hora de inicio.")
    if not dias_semana or any(dia not in range(7) for dia in dias_semana):
        raise ValueError("Selecciona al menos un día válido.")
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tabla(cursor)
            cursor.execute("SELECT 1 FROM grupos WHERE id = %s AND activo = TRUE;", (grupo_id,))
            if not cursor.fetchone():
                raise ValueError("El grupo seleccionado ya no está activo.")
            if personal_id is not None:
                cursor.execute("""
                    SELECT 1 FROM personal
                    WHERE id = %s AND activo = TRUE
                      AND LOWER(TRIM(tipo_personal)) = 'docente';
                """, (personal_id,))
                if not cursor.fetchone():
                    raise ValueError("El maestro seleccionado ya no está activo.")
            for dia_semana in dias_semana:
                cursor.execute("""
                    SELECT 1
                    FROM clases_horario
                    WHERE dia_semana = %s
                      AND hora_inicio < %s AND hora_fin > %s
                      AND (grupo_id = %s OR personal_id = %s)
                    LIMIT 1;
                """, (dia_semana, hora_fin, hora_inicio, grupo_id, personal_id))
                if cursor.fetchone():
                    nombre_dia = DIAS_SEMANA[dia_semana][1]
                    raise ValueError(f"El grupo o el maestro ya tiene una clase en ese horario el {nombre_dia}.")
            cursor.executemany("""
                INSERT INTO clases_horario
                    (grupo_id, materia, personal_id, dia_semana, hora_inicio, hora_fin, aula)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, [
                (grupo_id, materia[:150], personal_id, dia, hora_inicio, hora_fin, aula[:100])
                for dia in dias_semana
            ])


def crear_clases_en_celdas(grupo_id, materia, personal_id, celdas, aula=""):
    """Guarda las clases en los días y bloques exactos elegidos en la cuadrícula."""
    materia = (materia or "").strip()
    aula = (aula or "").strip()
    if not materia:
        raise ValueError("Escribe el nombre de la materia o clase.")
    if not celdas:
        raise ValueError("Selecciona al menos una celda del horario.")
    if len(celdas) > 70:
        raise ValueError("Selecciona como máximo 70 celdas a la vez.")
    normalizadas = []
    for celda in celdas:
        dia, inicio, fin = int(celda["dia"]), celda["inicio"], celda["fin"]
        if dia not in range(7) or inicio not in range(24 * 60) or fin not in range(1, 24 * 60 + 1) or fin <= inicio:
            raise ValueError("Una de las celdas seleccionadas tiene un horario inválido.")
        normalizadas.append((dia, inicio, fin))
    normalizadas = sorted(set(normalizadas))
    for index, (dia, inicio, fin) in enumerate(normalizadas):
        if any(otro_dia == dia and otro_inicio < fin and otro_fin > inicio
               for otro_dia, otro_inicio, otro_fin in normalizadas[index + 1:]):
            raise ValueError("Hay celdas seleccionadas que se traslapan entre sí.")
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tabla(cursor)
            cursor.execute("SELECT 1 FROM grupos WHERE id = %s AND activo = TRUE;", (grupo_id,))
            if not cursor.fetchone():
                raise ValueError("El grupo seleccionado ya no está activo.")
            if personal_id is not None:
                cursor.execute("""
                    SELECT 1 FROM personal
                    WHERE id = %s AND activo = TRUE
                      AND LOWER(TRIM(tipo_personal)) = 'docente';
                """, (personal_id,))
                if not cursor.fetchone():
                    raise ValueError("El maestro seleccionado ya no está activo.")
            for dia, inicio, fin in normalizadas:
                hora_inicio = f"{inicio // 60:02d}:{inicio % 60:02d}"
                hora_fin = f"{fin // 60:02d}:{fin % 60:02d}"
                cursor.execute("""
                    SELECT 1 FROM clases_horario
                    WHERE dia_semana = %s AND hora_inicio < %s AND hora_fin > %s
                      AND (grupo_id = %s OR personal_id = %s)
                    LIMIT 1;
                """, (dia, hora_fin, hora_inicio, grupo_id, personal_id))
                if cursor.fetchone():
                    raise ValueError(f"El grupo o el maestro ya tiene una clase en ese horario el {DIAS_SEMANA[dia][1]}.")
            cursor.executemany("""
                INSERT INTO clases_horario
                    (grupo_id, materia, personal_id, dia_semana, hora_inicio, hora_fin, aula)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, [
                (grupo_id, materia[:150], personal_id, dia,
                 f"{inicio // 60:02d}:{inicio % 60:02d}",
                 f"{fin // 60:02d}:{fin % 60:02d}", aula[:100])
                for dia, inicio, fin in normalizadas
            ])


def crear_clase_horario(grupo_id, materia, personal_id, dia_semana, hora_inicio, hora_fin, aula=""):
    return crear_clases_horario(
        grupo_id, materia, personal_id, [dia_semana], hora_inicio, hora_fin, aula
    )


def eliminar_clase_horario(clase_id):
    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            _asegurar_tabla(cursor)
            cursor.execute("DELETE FROM clases_horario WHERE id = %s;", (clase_id,))
            return cursor.rowcount > 0
