import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import psycopg

from app.database.connection import DATABASE_CONFIG


MAX_RESPALDO_BYTES = 1024 * 1024 * 1024
_COPY_HEADER = re.compile(
    r'^COPY\s+(?:(?:"?[\w$]+"?)\.)?"?(grupos|alumnos)"?\s*\((.*?)\)\s+FROM\s+stdin;$',
    re.IGNORECASE,
)
_IDENTIFIER = re.compile(r'^"?([\w$]+)"?$')


def _decodificar_campo_copy(valor):
    if valor == r"\N":
        return None
    salida = []
    indice = 0
    escapes = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
    while indice < len(valor):
        caracter = valor[indice]
        indice += 1
        if caracter != "\\" or indice >= len(valor):
            salida.append(caracter)
            continue
        siguiente = valor[indice]
        indice += 1
        if siguiente in escapes:
            salida.append(escapes[siguiente])
        elif siguiente == "x" and indice < len(valor):
            digitos = valor[indice:indice + 2]
            if re.fullmatch(r"[0-9a-fA-F]{1,2}", digitos):
                salida.append(chr(int(digitos, 16)))
                indice += len(digitos)
            else:
                salida.append(siguiente)
        elif siguiente in "01234567":
            digitos = siguiente
            while indice < len(valor) and len(digitos) < 3 and valor[indice] in "01234567":
                digitos += valor[indice]
                indice += 1
            salida.append(chr(int(digitos, 8)))
        else:
            salida.append(siguiente)
    return "".join(salida)


def _iterar_copy(ruta_sql, solo_tabla=None):
    """Lee filas COPY una por una para no cargar respaldos grandes en memoria."""
    with open(ruta_sql, "r", encoding="utf-8", errors="replace", newline="") as archivo:
        for linea in archivo:
            coincidencia = _COPY_HEADER.match(linea.rstrip("\r\n"))
            if not coincidencia:
                continue
            tabla = coincidencia.group(1).lower()
            if solo_tabla and tabla != solo_tabla:
                for linea_datos in archivo:
                    if linea_datos.rstrip("\r\n") == r"\.":
                        break
                continue
            columnas = []
            for columna in coincidencia.group(2).split(","):
                identificador = _IDENTIFIER.match(columna.strip())
                if not identificador:
                    columnas = []
                    break
                columnas.append(identificador.group(1).lower())
            for linea_datos in archivo:
                linea_datos = linea_datos.rstrip("\r\n")
                if linea_datos == r"\.":
                    break
                valores = linea_datos.split("\t")
                if columnas and len(valores) == len(columnas):
                    yield tabla, {
                        columna: _decodificar_campo_copy(valor)
                        for columna, valor in zip(columnas, valores)
                    }


def _obtener_pg_restore():
    encontrado = shutil.which("pg_restore")
    if encontrado:
        return encontrado
    candidatos = [
        Path(r"C:\Program Files\PostgreSQL\18\bin\pg_restore.exe"),
        Path(r"C:\Program Files\PostgreSQL\17\bin\pg_restore.exe"),
        Path(r"C:\Program Files\PostgreSQL\16\bin\pg_restore.exe"),
    ]
    return next((str(ruta) for ruta in candidatos if ruta.is_file()), None)


def _obtener_sql_del_respaldo(archivo, carpeta_temporal):
    with open(archivo, "rb") as respaldo:
        firma = respaldo.read(5)
    if firma != b"PGDMP":
        return archivo
    ejecutable = _obtener_pg_restore()
    if not ejecutable:
        raise ValueError("No se encontró pg_restore para abrir este respaldo. Usa un respaldo .sql o instala PostgreSQL.")
    ruta_sql = Path(carpeta_temporal) / "datos.sql"
    resultado = subprocess.run(
        [ejecutable, "--data-only", "--no-owner", "--no-privileges", "--file", str(ruta_sql), str(archivo)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
    )
    if resultado.returncode != 0:
        raise ValueError("El archivo de respaldo no es válido o no se pudo leer con pg_restore.")
    return ruta_sql


def _valor_bool(valor, predeterminado=True):
    if valor is None:
        return predeterminado
    return str(valor).strip().lower() in {"t", "true", "1", "yes", "sí", "si"}


def _clave_grupo(grado, nombre, turno):
    return tuple(str(valor or "").strip().casefold() for valor in (grado, nombre, turno))


def importar_alumnos_de_respaldo(ruta_archivo, nombre_archivo):
    extension = Path(nombre_archivo or "").suffix.lower()
    if extension not in {".sql", ".backup", ".dump"}:
        raise ValueError("Formato no compatible. Selecciona un respaldo .sql, .backup o .dump de PostgreSQL.")
    ruta_archivo = Path(ruta_archivo)
    if not ruta_archivo.is_file() or ruta_archivo.stat().st_size == 0:
        raise ValueError("El respaldo está vacío.")
    if ruta_archivo.stat().st_size > MAX_RESPALDO_BYTES:
        raise ValueError("El respaldo supera el límite de 1 GB.")

    with tempfile.TemporaryDirectory(prefix="sicae_importar_respaldo_") as temporal:
        ruta_sql = _obtener_sql_del_respaldo(ruta_archivo, temporal)
        grupos_respaldo = [fila for _, fila in _iterar_copy(ruta_sql, solo_tabla="grupos")]

        with psycopg.connect(**DATABASE_CONFIG) as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT id, grado, nombre, turno FROM grupos ORDER BY id;")
                grupos_actuales = {}
                for grupo_id, grado, nombre, turno in cursor.fetchall():
                    grupos_actuales.setdefault(_clave_grupo(grado, nombre, turno), grupo_id)

                mapa_grupos = {}
                for grupo in grupos_respaldo:
                    grupo_anterior = grupo.get("id")
                    try:
                        grado = int(grupo.get("grado") or 0)
                    except (TypeError, ValueError):
                        continue
                    nombre = (grupo.get("nombre") or "").strip()
                    turno = (grupo.get("turno") or "").strip()
                    nombre_grupo = (grupo.get("nombre_grupo") or f"{grado}{nombre}").strip()
                    if grado < 1 or not nombre or not turno:
                        continue
                    clave = _clave_grupo(grado, nombre, turno)
                    grupo_actual = grupos_actuales.get(clave)
                    if grupo_actual is None:
                        cursor.execute("""
                            INSERT INTO grupos (nombre_grupo, grado, nombre, turno, activo)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING id;
                        """, (nombre_grupo[:100], grado, nombre[:20], turno[:20], True))
                        grupo_actual = cursor.fetchone()[0]
                        grupos_actuales[clave] = grupo_actual
                    else:
                        cursor.execute(
                            "UPDATE grupos SET activo = TRUE WHERE id = %s;",
                            (grupo_actual,),
                        )
                    if grupo_anterior is not None:
                        mapa_grupos[str(grupo_anterior)] = grupo_actual

                lote = []
                insertados = 0
                candidatos = 0
                omitidos = 0
                encontro_bloque_alumnos = False

                def insertar_lote():
                    nonlocal insertados, candidatos
                    if not lote:
                        return
                    candidatos += len(lote)
                    fila_sql = "(" + ", ".join(["%s"] * 9) + ")"
                    valores_sql = ", ".join([fila_sql] * len(lote))
                    parametros = tuple(valor for fila in lote for valor in fila)
                    cursor.execute(
                        f"INSERT INTO alumnos (matricula, nombre, apellido_paterno, apellido_materno, fecha_nacimiento, correo, telefono, grupo_id, activo) VALUES {valores_sql} ON CONFLICT DO NOTHING RETURNING id;",
                        parametros,
                    )
                    insertados += len(cursor.fetchall())
                    lote.clear()

                for _, alumno in _iterar_copy(ruta_sql, solo_tabla="alumnos"):
                    encontro_bloque_alumnos = True
                    matricula = (alumno.get("matricula") or "").strip()
                    nombre = (alumno.get("nombre") or "").strip()
                    apellido_paterno = (alumno.get("apellido_paterno") or "").strip()
                    if not matricula or not nombre or not apellido_paterno:
                        omitidos += 1
                        continue
                    grupo_anterior = alumno.get("grupo_id")
                    grupo_actual = mapa_grupos.get(str(grupo_anterior)) if grupo_anterior is not None else None
                    fecha_nacimiento = alumno.get("fecha_nacimiento")
                    if fecha_nacimiento in ("", "infinity", "-infinity"):
                        fecha_nacimiento = None
                    elif fecha_nacimiento:
                        try:
                            date.fromisoformat(fecha_nacimiento)
                        except ValueError:
                            fecha_nacimiento = None
                    lote.append((
                        matricula[:50], nombre[:100], apellido_paterno[:100],
                        (alumno.get("apellido_materno") or "")[:100] or None,
                        fecha_nacimiento, (alumno.get("correo") or "")[:150] or None,
                        (alumno.get("telefono") or "")[:30] or None, grupo_actual,
                        _valor_bool(alumno.get("activo")),
                    ))
                    if len(lote) >= 1000:
                        insertar_lote()

                insertar_lote()
                if not encontro_bloque_alumnos:
                    raise ValueError("No se encontraron datos de alumnos en el respaldo. Debe ser un volcado PostgreSQL con datos en formato COPY.")
                omitidos += candidatos - insertados

        return {"alumnos_insertados": insertados, "alumnos_omitidos": omitidos, "grupos_importados": len(mapa_grupos)}
