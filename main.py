from fastapi import (
    FastAPI,
    Request,
    Form,
    File,
    UploadFile,
    BackgroundTasks
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    FileResponse,
    JSONResponse
)
from fastapi.encoders import jsonable_encoder

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.concurrency import run_in_threadpool

from dotenv import load_dotenv
import os
import io
import json
import secrets
import tempfile
import zipfile
from threading import Lock, Thread
from email.utils import parseaddr

from pathlib import Path
from datetime import date, time, datetime, timedelta
from urllib.parse import quote

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils import get_column_letter

import psycopg
from psycopg.errors import UniqueViolation

from app.database.connection import DATABASE_CONFIG
from app.database.init_db import crear_tablas

from app.services.notificaciones_email_service import (
    enviar_notificacion_acceso,
    enviar_notificacion_credencial_especial,
    obtener_configuracion_smtp,
    guardar_configuracion_smtp,
    enviar_correo_prueba
)
from app.services.notificaciones_config_service import (
    obtener_configuracion_notificaciones,
    guardar_configuracion_notificaciones
)

from app.services.alumnos_service import (
    obtener_alumno_detalle,
    obtener_alumnos_por_grupo,
    obtener_grupos,
    eliminar_alumno,
    eliminar_alumnos,
    crear_alumno,
    actualizar_alumno,
    importar_alumno_excel
)

from app.services.actividad_alumnos_service import (
    buscar_alumnos_por_nombre_o_matricula,
    obtener_actividad_alumno
)
from app.services.eventos_fuera_service import (
    listar_eventos_fuera,
    crear_evento_fuera,
    obtener_evento_fuera,
    cambiar_estado_evento_fuera,
    eliminar_evento_fuera,
    finalizar_evento_fuera,
    listar_asistencias_evento_fuera,
    registrar_asistencia_evento_fuera,
)
from app.services.notificaciones_eventos_service import (
    obtener_configuracion_notificaciones_eventos,
    guardar_configuracion_notificaciones_eventos,
    enviar_notificacion_asistencia_evento,
    enviar_notificacion_finalizacion_evento,
)
from app.services.horario_clases_service import (
    DIAS_SEMANA,
    listar_clases_horario,
    crear_clase_horario,
    crear_clases_horario,
    crear_clases_en_celdas,
    eliminar_clase_horario,
    obtener_configuracion_tablas,
    guardar_configuracion_tabla,
)
from app.services.asistencia_clases_service import (
    listar_clases_docente,
    listar_resumen_asistencia_clases,
    iniciar_sesion_asistencia,
    obtener_sesion_asistencia,
    listar_registros_sesion,
    registrar_asistencia_clase,
    cerrar_sesion_asistencia,
)

from app.services.usuarios_service import (
    obtener_usuarios,
    crear_usuario,
    obtener_usuario_por_id,
    actualizar_usuario,
    cambiar_estado_usuario,
    autenticar_usuario
)

from app.services.personal_service import (
    obtener_personal,
    obtener_personal_por_id,
    obtener_personal_por_tipo,
    crear_personal,
    actualizar_personal,
    eliminar_personal
)

from app.services.configuracion_credencial_service import (
    obtener_configuracion_credencial,
    actualizar_configuracion_credencial
   
)

from app.services.configuracion_credencial_personal_service import (
    obtener_configuracion_credencial_personal,
    actualizar_configuracion_credencial_personal

)
from app.services.plantillas_credencial_service import (
    listar_plantillas_credencial,
    guardar_plantilla_credencial,
    eliminar_plantilla_credencial,
)
from app.services.configuracion_sistema_service import (
    obtener_configuracion_sistema,
    actualizar_configuracion_sistema
)

from app.services.qr_service import (
    generar_qr_alumno,
    generar_qr_personal,
    generar_qr_credencial_especial,
)

from app.services.credenciales_especiales_service import (
    TIPOS_CREDENCIAL_ESPECIAL,
    listar_credenciales_especiales,
    obtener_credencial_especial,
    crear_credencial_especial,
    cambiar_estado_credencial_especial,
    obtener_configuracion_credencial_especial,
    guardar_configuracion_credencial_especial,
    registrar_acceso_credencial_especial,
    entidad_especial_para_pdf,
)
from app.services.powerpoint_service import convertir_pptx_a_dos_png

from app.services.credencial_pdf_service import (
    generar_pdf_credenciales,
    generar_pdf_credencial_personal
)

from app.services.reportes_service import (
    obtener_reporte_asistencias,
    obtener_reporte_credenciales_especiales,
)
from app.services.estadisticas_service import (
    obtener_resumen_estadisticas,
    obtener_estadisticas_por_grado,
    obtener_estadisticas_por_grupo,
    obtener_asistencia_por_fecha,
    obtener_grados_estadisticas,
    obtener_grupos_estadisticas
)
from app.services.respaldos_service import (
    crear_respaldo,
    obtener_respaldos,
    eliminar_respaldo
)
from app.services.backup_service import (
    generar_respaldo,
    obtener_respaldos,
    obtener_respaldo,
    eliminar_respaldo
)
from app.services.importar_respaldo_alumnos_service import (
    MAX_RESPALDO_BYTES,
    importar_alumnos_de_respaldo,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)
APP_ENV = os.getenv("APP_ENV", "development").lower()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if APP_ENV == "production":
        raise RuntimeError("Define una SECRET_KEY estable en el entorno de producción.")
    SECRET_KEY = secrets.token_urlsafe(32)

# ============================================================
# CONFIGURACIÓN
# ============================================================

TEMPLATES_DIR = (
    BASE_DIR /
    "app" /
    "templates"
)


STATIC_DIR = (
    BASE_DIR /
    "app" /
    "static"
)


UPLOADS_DIR = (
    STATIC_DIR /
    "uploads"
)


REPORTES_DIR = (
    STATIC_DIR /
    "reportes"
)


# ============================================================
# CREAR CARPETAS
# ============================================================

STATIC_DIR.mkdir(
    parents=True,
    exist_ok=True
)

UPLOADS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

REPORTES_DIR.mkdir(
    parents=True,
    exist_ok=True
)

_credenciales_jobs = {}
_credenciales_jobs_lock = Lock()


def _generar_credenciales_en_segundo_plano(job_id, alumnos, configuracion, ruta_pdf, cantidad_por_hoja, solo_qr):
    try:
        generar_pdf_credenciales(
            alumnos=alumnos,
            configuracion=configuracion,
            ruta_pdf=ruta_pdf,
            cantidad_por_hoja=cantidad_por_hoja,
            solo_qr=solo_qr,
        )
        if not ruta_pdf.exists() or ruta_pdf.stat().st_size == 0:
            raise RuntimeError("La generación terminó sin producir un PDF válido.")
        with _credenciales_jobs_lock:
            _credenciales_jobs[job_id]["estado"] = "listo"
    except Exception as error:
        print("Error generando credenciales:", error)
        with _credenciales_jobs_lock:
            _credenciales_jobs[job_id]["estado"] = "error"
            _credenciales_jobs[job_id]["mensaje"] = str(error)[:300]


def _encolar_generacion_credenciales(background_tasks, alumnos, configuracion, nombre_base, cantidad_por_hoja=8, solo_qr=False):
    job_id = secrets.token_urlsafe(18)
    nombre_archivo = f"{Path(nombre_base).stem}_{job_id[:8]}.pdf"
    ruta_pdf = REPORTES_DIR / nombre_archivo
    with _credenciales_jobs_lock:
        _credenciales_jobs[job_id] = {
            "estado": "generando",
            "ruta": str(ruta_pdf),
            "nombre": nombre_archivo,
            "mensaje": "",
        }
    background_tasks.add_task(
        _generar_credenciales_en_segundo_plano,
        job_id,
        alumnos,
        configuracion,
        ruta_pdf,
        cantidad_por_hoja,
        solo_qr,
    )
    return job_id


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(

    title="SICAE WEB",

    description=(
        "Sistema de Registro "
        "BGM José María Chávez"
    ),

    version="1.0.0"

)


# ============================================================
# SESIONES DE USUARIO
# ============================================================

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    https_only=APP_ENV == "production",
    same_site="lax",
)


@app.on_event("startup")
def iniciar_inicializacion_de_base_de_datos():
    """Inicializa/migra PostgreSQL sin retrasar la apertura del puerto HTTP."""
    app.state.database_initialization = "pending"

    def inicializar():
        app.state.database_initialization = "running"
        try:
            if not crear_tablas():
                raise RuntimeError("No se pudieron completar las migraciones de la base de datos.")
            app.state.database_initialization = "ready"
        except Exception as error:
            app.state.database_initialization = "failed"
            print(f"Error inicializando la base de datos: {error}")

    Thread(target=inicializar, name="sicae-db-init", daemon=True).start()


@app.middleware("http")
async def esperar_inicializacion_de_base_de_datos(request: Request, call_next):
    if request.url.path.startswith("/static/"):
        return await call_next(request)
    estado = getattr(app.state, "database_initialization", "pending")
    if estado != "ready":
        mensaje = (
            "La base de datos aún se está inicializando. Recarga en unos segundos."
            if estado in {"pending", "running"}
            else "La inicialización de la base de datos falló. Revisa los logs del servicio."
        )
        return JSONResponse({"ok": False, "mensaje": mensaje}, status_code=503)
    return await call_next(request)


# ============================================================
# ARCHIVOS ESTÁTICOS
# ============================================================

app.mount(

    "/static",

    StaticFiles(
        directory=str(STATIC_DIR)
    ),

    name="static"

)


# ============================================================
# PLANTILLAS
# ============================================================

templates = Jinja2Templates(

    directory=str(
        TEMPLATES_DIR
    )

)
def contexto_global(request: Request):

    configuracion = (
        obtener_configuracion_sistema()
    )

    return {
        "configuracion": configuracion
    }

templates.context_processors.append(
    contexto_global
)


# ============================================================
# INICIO DE SESIÓN
# ============================================================


# ============================================================
# CONFIGURACION DE NOTIFICACIONES POR CORREO
# ============================================================

# ============================================================
# CONFIGURACION DE NOTIFICACIONES POR CORREO
# ============================================================

@app.get("/notificaciones/configuracion")
async def mostrar_configuracion_notificaciones(request: Request):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )
    configuracion = obtener_configuracion_notificaciones()
    if request.session.get("rol") == "docente":
        return RedirectResponse(url="/asistencia-maestro", status_code=303)
    if request.session.get("rol") == "operador":
        return RedirectResponse(url="/inicio-plantel", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="configuracion_notificaciones.html",
        context={
            "configuracion_notificaciones": configuracion,
            "configuracion_smtp": obtener_configuracion_smtp()
        }
    )


@app.post("/notificaciones/configuracion")
async def guardar_configuracion_notificaciones_ruta(
    request: Request,
    correo_remitente: str = Form(""),
    asunto: str = Form("SICAE WEB - Notificación de asistencia"),
    mensaje: str = Form(""),
    notificaciones_activas: bool = Form(False),
    enviar_entrada: bool = Form(False),
    enviar_salida: bool = Form(False),
    smtp_host: str = Form(""),
    smtp_port: str = Form("587"),
    smtp_user: str = Form(""),
    smtp_password: str = Form(""),
    smtp_security: str = Form("starttls"),
    correo_prueba: str = Form(""),
    accion: str = Form("guardar")
):
    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    resultado = None
    error_configuracion = None
    try:
        puerto = int(smtp_port)
        if not 1 <= puerto <= 65535:
            raise ValueError("El puerto debe estar entre 1 y 65535.")
        if not correo_remitente.strip() or not smtp_host.strip() or not smtp_user.strip():
            raise ValueError("Completa el correo remitente, el servidor SMTP y el usuario SMTP.")
        if smtp_security not in {"starttls", "ssl"}:
            raise ValueError("Selecciona una conexión STARTTLS o SSL.")
        if accion == "probar":
            destino_prueba = parseaddr(correo_prueba.strip())[1]
            if not destino_prueba or "@" not in destino_prueba:
                raise ValueError("Escribe una dirección válida para recibir la prueba.")

        guardar_configuracion_smtp(
            smtp_host=smtp_host,
            smtp_port=puerto,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_security=smtp_security,
            correo_remitente=correo_remitente
        )
        guardar_configuracion_notificaciones(
            correo_remitente=correo_remitente,
            asunto=asunto,
            mensaje=mensaje,
            notificaciones_activas=notificaciones_activas,
            enviar_entrada=enviar_entrada,
            enviar_salida=enviar_salida
        )

        if accion == "probar":
            enviar_correo_prueba(destino_prueba)
            resultado = f"Correo de prueba enviado a {destino_prueba}."
        else:
            resultado = "Configuración guardada correctamente."
    except Exception as error:
        error_configuracion = str(error)

    configuracion = obtener_configuracion_notificaciones()
    return templates.TemplateResponse(
        request=request,
        name="configuracion_notificaciones.html",
        context={
            "configuracion_notificaciones": configuracion,
            "configuracion_smtp": obtener_configuracion_smtp(),
            "mensaje_guardado": resultado,
            "error_configuracion": error_configuracion
        }
    )


# ============================================================
# INICIO DE SESIÓN
# ============================================================

@app.get("/login")
async def mostrar_login(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": None
        }
    )


@app.post("/login")
async def iniciar_sesion(
    request: Request,
    usuario: str = Form(""),
    password: str = Form("")
):

    usuario_autenticado_resultado = autenticar_usuario(
        usuario,
        password
    )

    if not usuario_autenticado_resultado:

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Usuario o contraseña incorrectos."
            },
            status_code=401
        )

    request.session["usuario_id"] = usuario_autenticado_resultado["id"]
    request.session["usuario"] = usuario_autenticado_resultado["usuario"]
    request.session["nombre"] = usuario_autenticado_resultado["nombre"]
    request.session["rol"] = usuario_autenticado_resultado["rol"]
    request.session["personal_id"] = usuario_autenticado_resultado.get("personal_id")

    return RedirectResponse(
        url="/",
        status_code=303
    )
# ============================================================
# CERRAR SESIÓN
# ============================================================

@app.get(
    "/logout"
)
def cerrar_sesion(
    request: Request
):

    request.session.clear()


    return RedirectResponse(

        url="/login",

        status_code=303

    )

# ============================================================
# COMPROBAR SESIÓN
# ============================================================

def usuario_autenticado(
    request: Request
):

    return request.session.get(
        "usuario_id"
    )

# ============================================================
# COMPROBAR SI EL USUARIO ES ADMINISTRADOR
# ============================================================
def usuario_es_administrador(
    request: Request
):

    return request.session.get(
        "rol"
    ) == "administrador"


def usuario_puede_operar(request: Request):
    return request.session.get("rol") in {"administrador", "operador"}

# ============================================================
# ESTADÍSTICAS
# ============================================================

def obtener_estadisticas():
	
    estadisticas = {

        "alumnos": 0,

        "grupos": 0,

        "entradas": 0,

        "salidas": 0

    }


    try:

        with psycopg.connect(
            **DATABASE_CONFIG
        ) as conexion:

            with conexion.cursor() as cursor:

                # ====================================================
                # ALUMNOS
                # ====================================================

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM alumnos
                    WHERE activo = TRUE;
                """)

                resultado = cursor.fetchone()

                if resultado:

                    estadisticas[
                        "alumnos"
                    ] = resultado[0]


                # ====================================================
                
# GRUPOS
                # ====================================================

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM grupos
                    WHERE activo = TRUE;
                """)

                resultado = cursor.fetchone()

                if resultado:

                    estadisticas[
                        "grupos"
                    ] = resultado[0]


                # ====================================================
                # ENTRADAS
                # ====================================================

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM accesos
                    WHERE fecha = CURRENT_DATE
                    AND movimiento = 'ENTRADA';
                """)

                resultado = cursor.fetchone()

                if resultado:

                    estadisticas[
                        "entradas"
                    ] = resultado[0]


                # ====================================================
                # SALIDAS
                # ====================================================

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM accesos
                    WHERE fecha = CURRENT_DATE
                    AND movimiento = 'SALIDA';
                """)

                resultado = cursor.fetchone()

                if resultado:

                    estadisticas[
                        "salidas"
                    ] = resultado[0]


    except Exception as error:

        print()
        print("==========================================")
        print("ERROR OBTENIENDO ESTADÍSTICAS")
        print(error)
        print("==========================================")
        print()


    return estadisticas

# ============================================================
# INFORMACIÓN COMPLETA DEL DASHBOARD
# ============================================================

def obtener_dashboard():

    datos = {

        "alumnos": 0,

        "grupos": 0,

        "entradas": 0,

        "salidas": 0,

        "ausentes": 0,

        "total_asistencia": 0,

        "porcentaje_asistencia": 0,

        "ultimos_accesos": [],

        "asistencia_diaria": []

    }


    try:

        with psycopg.connect(
            **DATABASE_CONFIG
        ) as conexion:

            with conexion.cursor() as cursor:

                # ====================================================
                # ALUMNOS
                # ====================================================

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM alumnos
                    WHERE activo = TRUE;
                """)

                datos["alumnos"] = (
                    cursor.fetchone()[0]
                )


                # ====================================================
                # GRUPOS
                # ====================================================

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM grupos
                    WHERE activo = TRUE;
                """)

                datos["grupos"] = (
                    cursor.fetchone()[0]
                )


                # ====================================================
                # ENTRADAS DE HOY
                # ====================================================

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM accesos
                    WHERE fecha = CURRENT_DATE
                    AND movimiento = 'ENTRADA';
                """)

                datos["entradas"] = (
                    cursor.fetchone()[0]
                )


                # ====================================================
                # SALIDAS DE HOY
                # ====================================================

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM accesos
                    WHERE fecha = CURRENT_DATE
                    AND movimiento = 'SALIDA';
                """)

                datos["salidas"] = (
                    cursor.fetchone()[0]
                )


                # ====================================================
                # ALUMNOS QUE ENTRARON HOY
                # ====================================================

                cursor.execute("""
                    SELECT COUNT(DISTINCT alumno_id)
                    FROM accesos
                    WHERE fecha = CURRENT_DATE
                    AND movimiento = 'ENTRADA';
                """)

                presentes = (
                    cursor.fetchone()[0]
                )


                datos["total_asistencia"] = (
                    presentes
                )


                # ====================================================
                # AUSENTES
                # ====================================================

                datos["ausentes"] = max(

                    datos["alumnos"]
                    -
                    presentes,

                    0

                )


                # ====================================================
                # PORCENTAJE
                # ====================================================

                if datos["alumnos"] > 0:

                    datos["porcentaje_asistencia"] = round(

                        (
                            presentes /
                            datos["alumnos"]
                        ) * 100,

                        1

                    )


                # ====================================================
                # ÚLTIMOS ACCESOS
                # ====================================================

                cursor.execute("""
                    SELECT

                        a.nombre,
                        a.apellido_paterno,
                        a.apellido_materno,
                        a.matricula,
                        g.nombre_grupo,
                        g.grado,
                        g.turno,
                        ac.movimiento,
                        ac.fecha,
                        TO_CHAR(ac.hora, 'HH24:MI:SS') AS hora,
                        ac.registrado_por,
                        'alumno' AS tipo

                    FROM accesos ac

                    INNER JOIN alumnos a
                        ON a.id = ac.alumno_id

                    LEFT JOIN grupos g
                        ON g.id = a.grupo_id


                    UNION ALL


                    SELECT

                        p.nombre,
                        p.apellido_paterno,
                        p.apellido_materno,
                        p.numero_empleado,
                        p.area,
                        NULL AS grado,
                        NULL AS turno,
                        ap.movimiento,
                        ap.fecha,
                        TO_CHAR(ap.hora, 'HH24:MI:SS') AS hora,
                        ap.registrado_por,
                        'personal' AS tipo

                    FROM accesos_personal ap

                    INNER JOIN personal p
                        ON p.id = ap.personal_id

                    UNION ALL

                    SELECT
                        ce.nombre,
                        ce.apellido_paterno,
                        ce.apellido_materno,
                        ce.codigo,
                        CASE ce.tipo
                            WHEN 'direccion' THEN 'Dirección'
                            WHEN 'prefectura' THEN 'Prefectura'
                            WHEN 'conferencias' THEN 'Conferencias'
                            ELSE 'Proveedores'
                        END || CASE WHEN ce.organizacion IS NOT NULL AND ce.organizacion <> ''
                            THEN ' · ' || ce.organizacion ELSE '' END,
                        NULL::INTEGER AS grado,
                        ce.tipo AS turno,
                        ace.movimiento,
                        ace.fecha,
                        TO_CHAR(ace.hora, 'HH24:MI:SS') AS hora,
                        ace.registrado_por,
                        'especial' AS tipo
                    FROM accesos_credenciales_especiales ace
                    INNER JOIN credenciales_especiales ce ON ce.id = ace.credencial_id


                    ORDER BY

                        fecha DESC,
                        hora DESC

                    LIMIT 10;
                """)


                filas = cursor.fetchall()


                for fila in filas:

                    datos[
                        "ultimos_accesos"
                    ].append({

                        "nombre":
                            fila[0],

                        "apellido_paterno":
                            fila[1],

                        "apellido_materno":
                            fila[2],

                        "matricula":
                            fila[3],

                        "nombre_grupo":
                            fila[4],

                        "grado":
                            fila[5],

                        "turno":
                            fila[6],

                        "movimiento":
                            fila[7],

                        "fecha":
                            fila[8],

                        "hora":
                            fila[9],

                        "registrado_por":
                            fila[10],

                        "tipo":
                            fila[11]

                    })


                # ====================================================
                # ASISTENCIA ÚLTIMOS 7 DÍAS
                # ====================================================

                cursor.execute("""
                    SELECT

                        fecha,

                        COUNT(
                            DISTINCT alumno_id
                        )

                    FROM accesos

                    WHERE

                        fecha >= CURRENT_DATE - INTERVAL '6 days'

                        AND movimiento = 'ENTRADA'

                    GROUP BY fecha

                    ORDER BY fecha;
                """)


                filas = cursor.fetchall()


                for fila in filas:

                    datos[
                        "asistencia_diaria"
                    ].append({

                        "fecha":
                            str(fila[0]),

                        "cantidad":
                            fila[1]

                    })


    except Exception as error:

        print()
        print("==========================================")
        print("ERROR OBTENIENDO DASHBOARD")
        print(error)
        print("==========================================")
        print()


    return datos


# ============================================================
# INICIO
# ============================================================
@app.get("/")
def inicio(
    request: Request
):

    if not usuario_autenticado(request):

        return RedirectResponse(

            url="/login",

            status_code=303

        )


    if request.session.get("rol") == "docente":
        return RedirectResponse(url="/asistencia-maestro", status_code=303)
    if request.session.get("rol") == "operador":
        return RedirectResponse(url="/inicio-plantel", status_code=303)

    return templates.TemplateResponse(

        request=request,

        name="dashboard.html",

        context={}

    )


@app.get("/horarios")
def pagina_horarios(request: Request):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    materias = {}
    for clase in listar_resumen_asistencia_clases():
        materia = materias.setdefault(clase["materia"], {"nombre": clase["materia"], "grupos": {}})
        grupo = materia["grupos"].setdefault(
            clase["grupo_id"],
            {"id": clase["grupo_id"], "nombre": clase["grupo"], "clases": []},
        )
        grupo["clases"].append(clase)
    materias_asistencia = [
        {"nombre": materia["nombre"], "grupos": list(materia["grupos"].values())}
        for materia in sorted(materias.values(), key=lambda item: item["nombre"].casefold())
    ]
    return templates.TemplateResponse(
        request=request,
        name="horarios.html",
        context={
            "configuracion": obtener_configuracion_sistema(),
            "materias_asistencia": materias_asistencia,
            "dias": DIAS_SEMANA,
        },
    )


@app.get("/inicio-plantel")
def inicio_plantel(request: Request):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_puede_operar(request):
        return RedirectResponse(url="/asistencia-maestro", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="dashboard_plantel.html",
        context={
            "estadisticas": obtener_dashboard(),
            "configuracion": obtener_configuracion_sistema(),
        },
    )


@app.get("/api/inicio-plantel")
def api_inicio_plantel(request: Request):
    if not usuario_puede_operar(request):
        return JSONResponse({"ok": False, "mensaje": "No tienes permiso."}, status_code=403)
    return JSONResponse(jsonable_encoder(obtener_dashboard()))

# ============================================================
# ESTADÍSTICAS
# ============================================================

@app.get("/estadisticas")
def estadisticas(
    request: Request,
    periodo: str = "dia",
    fecha: str = "",
    grado: str = "",
    grupo_id: str = ""
):

    if not usuario_autenticado(request):

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    from datetime import date, timedelta
    import calendar

    hoy = date.today()

    # --------------------------------------------------------
    # FECHA BASE
    # --------------------------------------------------------

    if fecha:

        try:
            fecha_base = date.fromisoformat(fecha)

        except ValueError:

            fecha_base = hoy

    else:

        fecha_base = hoy


    # --------------------------------------------------------
    # CALCULAR PERIODO
    # --------------------------------------------------------

    if periodo == "semana":

        fecha_inicio = (
            fecha_base
            - timedelta(
                days=fecha_base.weekday()
            )
        )

        fecha_fin = (
            fecha_inicio
            + timedelta(days=6)
        )

    elif periodo == "mes":

        fecha_inicio = fecha_base.replace(
            day=1
        )

        ultimo_dia = calendar.monthrange(
            fecha_base.year,
            fecha_base.month
        )[1]

        fecha_fin = fecha_base.replace(
            day=ultimo_dia
        )

    elif periodo == "anio":

        fecha_inicio = date(
            fecha_base.year,
            1,
            1
        )

        fecha_fin = date(
            fecha_base.year,
            12,
            31
        )

    else:

        periodo = "dia"

        fecha_inicio = fecha_base
        fecha_fin = fecha_base


    # --------------------------------------------------------
    # CONVERTIR FILTROS VACÍOS
    # --------------------------------------------------------

    grado = int(grado) if grado.strip() else None
    grupo_id = int(grupo_id) if grupo_id.strip() else None


    # --------------------------------------------------------
    # DATOS
    # --------------------------------------------------------

    resumen = obtener_resumen_estadisticas(
        fecha_inicio,
        fecha_fin,
        grado,
        grupo_id
    )

    estadisticas_grado = (
        obtener_estadisticas_por_grado(
            fecha_inicio,
            fecha_fin
        )
    )

    estadisticas_grupo = (
        obtener_estadisticas_por_grupo(
            fecha_inicio,
            fecha_fin,
            grado
        )
    )

    asistencia_fecha = (
        obtener_asistencia_por_fecha(
            fecha_inicio,
            fecha_fin,
            grado,
            grupo_id
        )
    )

    grados = obtener_grados_estadisticas()

    grupos = obtener_grupos_estadisticas(
        grado
    )


    return templates.TemplateResponse(

        request=request,

        name="estadisticas.html",

        context={

            "resumen":
                resumen,

            "estadisticas_grado":
                estadisticas_grado,

            "estadisticas_grupo":
                estadisticas_grupo,

            "asistencia_fecha":
                asistencia_fecha,

            "grados":
                grados,

            "grupos":
                grupos,

            "periodo":
                periodo,

            "fecha":
                fecha_base.isoformat(),

            "grado":
                grado,

            "grupo_id":
                grupo_id,

            "fecha_inicio":
                fecha_inicio,

            "fecha_fin":
                fecha_fin

        }

    )


# ============================================================
# ALUMNOS
# ============================================================

# ============================================================
# ADMINISTRACION DE CORREOS DE ALUMNOS
# ============================================================

@app.get("/correos-alumnos")
def mostrar_correos_alumnos(request: Request):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)

    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    busqueda = request.query_params.get("buscar", "").strip()
    grupo_param = request.query_params.get("grupo_id", "").strip()
    grupo_seleccionado = (
        int(grupo_param)
        if grupo_param.isdigit()
        else None
    )

    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre_grupo, nombre, grado, turno
                FROM grupos
                WHERE activo = TRUE
                ORDER BY grado, nombre;
            """)
            grupos = cursor.fetchall()

            ids_grupos = {grupo[0] for grupo in grupos}
            if grupo_seleccionado not in ids_grupos:
                grupo_seleccionado = None

            cursor.execute("""
                SELECT
                    id,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    correo
                FROM alumnos
                WHERE activo = TRUE
                  AND (
                    %s = ''
                    OR CONCAT_WS(
                        ' ',
                        apellido_paterno,
                        apellido_materno,
                        nombre
                    ) ILIKE %s
                  )
                  AND (%s::integer IS NULL OR grupo_id = %s::integer)
                ORDER BY apellido_paterno, apellido_materno, nombre
                LIMIT 1000;
            """, (
                busqueda,
                f"%{busqueda}%",
                grupo_seleccionado,
                grupo_seleccionado
            ))

            filas = cursor.fetchall()

    alumnos_correo = [
        {
            "id": fila[0],
            "nombre": fila[1],
            "apellido_paterno": fila[2],
            "apellido_materno": fila[3],
            "correo": fila[4]
        }
        for fila in filas
    ]

    return templates.TemplateResponse(
        request=request,
        name="correos_alumnos.html",
        context={
            "alumnos": alumnos_correo,
            "grupos": grupos,
            "grupo_seleccionado": grupo_seleccionado,
            "busqueda": busqueda
        }
    )


@app.post("/correos-alumnos")
async def guardar_correos_alumnos(request: Request):
    from urllib.parse import urlencode

    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)

    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    formulario = await request.form()
    grupo_param = str(formulario.get("grupo_id", "")).strip()
    busqueda = str(formulario.get("buscar", "")).strip()

    def redireccion(**extra):
        parametros = {}
        if grupo_param.isdigit():
            parametros["grupo_id"] = grupo_param
        if busqueda:
            parametros["buscar"] = busqueda
        parametros.update(extra)
        return RedirectResponse(
            url="/correos-alumnos?" + urlencode(parametros),
            status_code=303
        )

    cambios = []

    for campo, valor in formulario.multi_items():
        if not campo.startswith("correo_"):
            continue

        try:
            alumno_id = int(campo.removeprefix("correo_"))
        except ValueError:
            continue

        correo = str(valor).strip()

        if correo and (
            correo.count("@") != 1
            or correo.startswith("@")
            or correo.endswith("@")
            or "." not in correo.rsplit("@", 1)[1]
            or " " in correo
        ):
            return redireccion(error="correo_invalido")

        cambios.append((correo or None, alumno_id))

    actualizados = 0

    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            for correo, alumno_id in cambios:
                cursor.execute("""
                    UPDATE alumnos
                    SET correo = %s
                    WHERE id = %s AND activo = TRUE
                """, (correo, alumno_id))
                actualizados += cursor.rowcount
        conexion.commit()

    return redireccion(guardado=str(actualizados))


@app.get("/alumnos")
def alumnos(
    request: Request
):
    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    grupos = obtener_grupos()

    return templates.TemplateResponse(

        request=request,

        name="alumnos.html",

        context={

            "grupos":
                grupos

        }

    )


@app.get("/actividad-alumnos")
def actividad_alumnos(
    request: Request,
    q: str = "",
    alumno_id: int | None = None,
    page: int = 1
):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    termino = (q or "").strip()
    resultados = buscar_alumnos_por_nombre_o_matricula(termino)
    alumno_seleccionado = None
    actividad = []
    total_actividad = 0
    total_paginas = 1
    pagina_actual = max(1, page)

    if alumno_id is not None:
        alumno_seleccionado = obtener_alumno_detalle(alumno_id)
        if alumno_seleccionado is not None:
            actividad, total_actividad, total_paginas = obtener_actividad_alumno(
                alumno_id,
                pagina=pagina_actual
            )
            pagina_actual = min(pagina_actual, total_paginas)
            if page > total_paginas:
                actividad, total_actividad, total_paginas = obtener_actividad_alumno(
                    alumno_id,
                    pagina=pagina_actual
                )

    return templates.TemplateResponse(
        request=request,
        name="actividad_alumnos.html",
        context={
            "q": termino,
            "resultados": resultados,
            "alumno_id": alumno_id,
            "alumno": alumno_seleccionado,
            "actividad": actividad,
            "total_actividad": total_actividad,
            "pagina_actual": pagina_actual,
            "total_paginas": total_paginas
        }
    )



# ============================================================
# ESTADÍSTICAS
# ============================================================
# ALUMNOS POR GRUPO
# ============================================================

@app.get(
    "/alumnos/grupo/{grupo_id}"
)
def alumnos_grupo(

    request: Request,

    grupo_id: int

):

    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    alumnos = (
        obtener_alumnos_por_grupo(
            grupo_id
        )
    )

    grupos = obtener_grupos()

    grupo = None


    for item in grupos:

        if item["id"] == grupo_id:

            grupo = item

            break


    if grupo is None:

        return RedirectResponse(

            url="/alumnos",

            status_code=303

        )


    return templates.TemplateResponse(

        request=request,

        name="alumnos_grupo.html",

        context={

            "alumnos":
                alumnos,

            "grupo":
                grupo

        }

    )


# ============================================================
# IMPRESIÓN DE CREDENCIALES
# ============================================================

@app.get(
    "/credencial/imprimir"
)
def imprimir_credenciales(
    request: Request
):

    
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )
    grupos = obtener_grupos()

    return templates.TemplateResponse(

        request=request,

        name="imprimir_credenciales.html",

        context={

            "grupos":
                grupos

        }

    )


# ============================================================
# SELECCIONAR ALUMNOS PARA IMPRESIÓN
# ============================================================

@app.get(
    "/credencial/imprimir/grupo/{grupo_id}"
)
def seleccionar_alumnos_impresion(

    request: Request,

    grupo_id: int

):

    
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )
    alumnos = (
        obtener_alumnos_por_grupo(
            grupo_id
        )
    )

    grupos = obtener_grupos()

    grupo = None


    for item in grupos:

        if item["id"] == grupo_id:

            grupo = item

            break


    if grupo is None:

        return RedirectResponse(

            url="/credencial/imprimir",

            status_code=303

        )


    return templates.TemplateResponse(

        request=request,

        name="seleccionar_credenciales.html",

        context={

            "alumnos":
                alumnos,

            "grupo":
                grupo

        }

    )


# ============================================================
# GENERAR CREDENCIALES SELECCIONADAS
# ============================================================

@app.post(
    "/alumnos/grupo/{grupo_id}/credenciales/seleccionar"
)
def generar_credenciales_seleccionadas(

        request: Request,

    background_tasks: BackgroundTasks,

    grupo_id: int,

    alumnos_ids: list[int] = Form([]),

    tipo_generacion: str = Form("completas"),

    cantidad_por_hoja: int = Form(8)

):

    
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )
# ========================================================
    # VERIFICAR SELECCIÓN
    # ========================================================

    if not alumnos_ids:

        return RedirectResponse(

            url=(
                f"/credencial/imprimir/"
                f"grupo/{grupo_id}"
            ),

            status_code=303

        )


    # ========================================================
    # OBTENER ALUMNOS DEL GRUPO
    # ========================================================

    alumnos_grupo = (
        obtener_alumnos_por_grupo(
            grupo_id
        )
    )


    if not alumnos_grupo:

        return RedirectResponse(

            url=f"/alumnos/grupo/{grupo_id}",

            status_code=303

        )


    # ========================================================
    # FILTRAR ALUMNOS SELECCIONADOS
    # ========================================================

    alumnos_seleccionados = []


    for alumno in alumnos_grupo:

        alumno_id = alumno.get(
            "id"
        )

        if alumno_id in alumnos_ids:

            alumnos_seleccionados.append(
                alumno
            )


    # ========================================================
    # VERIFICAR RESULTADO
    # ========================================================

    if not alumnos_seleccionados:

        return RedirectResponse(

            url=(
                f"/credencial/imprimir/"
                f"grupo/{grupo_id}"
            ),

            status_code=303

        )


    # ========================================================
    # CONFIGURACIÓN DE CREDENCIAL
    # ========================================================

    configuracion = (
        obtener_configuracion_credencial()
    )


    # ========================================================
    # OBTENER GRUPO
    # ========================================================

    grupos = obtener_grupos()

    grupo = None


    for item in grupos:

        if item["id"] == grupo_id:

            grupo = item

            break


    if grupo is None:

        return RedirectResponse(

            url="/credencial/imprimir",

            status_code=303

        )


    # ========================================================
    # NOMBRE DEL GRUPO
    # ========================================================

    nombre_grupo = str(

        grupo.get(
            "nombre_grupo",
            f"grupo_{grupo_id}"
        )

    ).strip()


    # ========================================================
    # LIMPIAR NOMBRE
    # ========================================================

    caracteres_no_validos = [

        "\\",
        "/",
        ":",
        "*",
        "?",
        "\"",
        "<",
        ">",
        "|"

    ]


    for caracter in caracteres_no_validos:

        nombre_grupo = (
            nombre_grupo.replace(
                caracter,
                "_"
            )
        )


    # ========================================================
    # NOMBRE DEL ARCHIVO
    # ========================================================

    solo_qr = tipo_generacion == "qr"
    prefijo_archivo = "codigos_qr_seleccionados" if solo_qr else "credenciales_seleccionadas"
    nombre_archivo = f"{prefijo_archivo}_{nombre_grupo}.pdf"


    # ========================================================
    # RUTA DEL PDF
    # ========================================================

    job_id = _encolar_generacion_credenciales(
        background_tasks,
        alumnos_seleccionados,
        configuracion,
        nombre_archivo,
        cantidad_por_hoja,
        solo_qr,
    )
    return templates.TemplateResponse(
        request=request,
        name="generando_credenciales.html",
        context={"job_id": job_id},
    )


@app.get("/credenciales/generacion/{job_id}/estado")
def estado_generacion_credenciales(request: Request, job_id: str):
    if not usuario_autenticado(request) or not usuario_es_administrador(request):
        return JSONResponse({"estado": "error", "mensaje": "Tu sesión expiró. Inicia sesión de nuevo."}, status_code=403)
    with _credenciales_jobs_lock:
        job = _credenciales_jobs.get(job_id)
        if not job:
            return JSONResponse({"estado": "error", "mensaje": "No se encontró esta generación. Vuelve a iniciar la descarga."}, status_code=404)
        respuesta = {"estado": job["estado"], "mensaje": job["mensaje"]}
        if job["estado"] == "listo":
            respuesta["descarga"] = f"/credenciales/generacion/{job_id}/pdf"
    return respuesta


@app.get("/credenciales/generacion/{job_id}/pdf")
def descargar_credenciales_generadas(request: Request, job_id: str):
    if not usuario_autenticado(request) or not usuario_es_administrador(request):
        return RedirectResponse(url="/login", status_code=303)
    with _credenciales_jobs_lock:
        job = _credenciales_jobs.get(job_id)
        if not job or job["estado"] != "listo":
            return RedirectResponse(url="/credencial/imprimir", status_code=303)
        ruta_pdf, nombre_archivo = job["ruta"], job["nombre"]
    return FileResponse(
        path=ruta_pdf,
        media_type="application/pdf",
        filename=nombre_archivo,
        content_disposition_type="inline",
    )


# ============================================================
# GENERAR CREDENCIALES PDF DEL GRUPO COMPLETO
# ============================================================

@app.get(
    "/alumnos/grupo/{grupo_id}/credenciales/pdf"
)
def credenciales_grupo_pdf(

    request: Request,

    background_tasks: BackgroundTasks,

    grupo_id: int

):

    
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )
# ========================================================
    # OBTENER ALUMNOS
    # ========================================================

    alumnos = (
        obtener_alumnos_por_grupo(
            grupo_id
        )
    )


    # ========================================================
    # VERIFICAR ALUMNOS
    # ========================================================

    if not alumnos:

        return RedirectResponse(

            url=f"/alumnos/grupo/{grupo_id}",

            status_code=303

        )


    # ========================================================
    # CONFIGURACIÓN
    # ========================================================

    configuracion = (
        obtener_configuracion_credencial()
    )


    # ========================================================
    # OBTENER GRUPO
    # ========================================================

    grupos = obtener_grupos()

    grupo = None


    for item in grupos:

        if item["id"] == grupo_id:

            grupo = item

            break


    if grupo is None:

        return RedirectResponse(

            url="/alumnos",

            status_code=303

        )


    # ========================================================
    # NOMBRE DEL GRUPO
    # ========================================================

    nombre_grupo = str(

        grupo.get(
            "nombre_grupo",
            f"grupo_{grupo_id}"
        )

    ).strip()


    # ========================================================
    # LIMPIAR NOMBRE
    # ========================================================

    caracteres_no_validos = [

        "\\",
        "/",
        ":",
        "*",
        "?",
        "\"",
        "<",
        ">",
        "|"

    ]


    for caracter in caracteres_no_validos:

        nombre_grupo = (
            nombre_grupo.replace(
                caracter,
                "_"
            )
        )


    nombre_archivo = f"credenciales_{nombre_grupo}.pdf"
    job_id = _encolar_generacion_credenciales(
        background_tasks,
        alumnos,
        configuracion,
        nombre_archivo,
    )
    return templates.TemplateResponse(
        request=request,
        name="generando_credenciales.html",
        context={"job_id": job_id},
    )

# ============================================================
# RESPALDOS
# ============================================================

@app.get(
    "/administracion/respaldos"
)
def respaldos(
    request: Request
):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    lista_respaldos = (
        obtener_respaldos()
    )


    return templates.TemplateResponse(

        request=request,

        name="respaldos.html",

        context={

            "respaldos":
                lista_respaldos

        }

    )


# ============================================================
# GENERAR RESPALDO
# ============================================================

@app.post(
    "/administracion/respaldos/generar"
)
def generar_respaldo_ruta(
    request: Request
):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    try:

        resultado = (
            generar_respaldo()
        )


        return RedirectResponse(

            url=(
                "/administracion/"
                "respaldos"
                "?exito=1"
            ),

            status_code=303

        )


    except Exception as error:

        print()
        print("==========================================")
        print("ERROR GENERANDO RESPALDO")
        print(error)
        print("==========================================")
        print()


        return RedirectResponse(

            url=(
                "/administracion/"
                "respaldos"
                "?error=1"
            ),

            status_code=303

        )


# ============================================================
# DESCARGAR RESPALDO
# ============================================================

@app.get(
    "/administracion/respaldos/descargar/{nombre_archivo}"
)
def descargar_respaldo(

    request: Request,

    nombre_archivo: str

):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    ruta = obtener_respaldo(
        nombre_archivo
    )


    if ruta is None:

        return RedirectResponse(

            url="/administracion/respaldos",

            status_code=303

        )


    return FileResponse(

        path=str(ruta),

        media_type="application/sql",

        filename=ruta.name

    )


# ============================================================
# ELIMINAR RESPALDO
# ============================================================

@app.post(
    "/administracion/respaldos/eliminar/{nombre_archivo}"
)
def eliminar_respaldo_ruta(

    request: Request,

    nombre_archivo: str

):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    eliminar_respaldo(
        nombre_archivo
    )


    return RedirectResponse(

        url="/administracion/respaldos",

        status_code=303

    )


# ============================================================
# ADMINISTRACIÓN
# ============================================================

@app.get(
    "/administracion"
)
def administracion(
    request: Request
):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )

    return templates.TemplateResponse(

        request=request,

        name="administracion.html",

        context={"maestros": obtener_personal_por_tipo("Docente")}

    )


# ============================================================
# RESPALDOS
# ============================================================

@app.get(
    "/administracion/respaldos"
)
def respaldos(
    request: Request
):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )


    lista_respaldos = (
        obtener_respaldos()
    )


    return templates.TemplateResponse(

        request=request,

        name="respaldos.html",

        context={

            "respaldos":
                lista_respaldos,

            "mensaje":
                None,

            "error":
                None

        }

    )


# ============================================================
# CREAR RESPALDO
# ============================================================

@app.post(
    "/administracion/respaldos/crear"
)
def crear_respaldo_ruta(
    request: Request
):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )


    try:

        crear_respaldo()


        return RedirectResponse(

            url=(
                "/administracion/respaldos"
                "?mensaje=creado"
            ),

            status_code=303

        )


    except Exception as error:

        print(
            "ERROR CREANDO RESPALDO:",
            error
        )


        return RedirectResponse(

            url=(
                "/administracion/respaldos"
                "?error=respaldo"
            ),

            status_code=303

        )


# ============================================================
# DESCARGAR RESPALDO
# ============================================================

@app.get(
    "/administracion/respaldos/descargar/{nombre_archivo}"
)
def descargar_respaldo(

    request: Request,

    nombre_archivo: str

):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )


    from pathlib import Path


    base_dir = (
        Path(__file__).resolve().parent
        / "backups"
    )


    nombre_seguro = Path(
        nombre_archivo
    ).name


    ruta = (
        base_dir /
        nombre_seguro
    )


    if not ruta.exists():

        return RedirectResponse(

            url="/administracion/respaldos",

            status_code=303

        )


    return FileResponse(

        path=str(ruta),

        media_type=(
            "application/octet-stream"
        ),

        filename=nombre_seguro

    )


# ============================================================
# ELIMINAR RESPALDO
# ============================================================

@app.get(
    "/administracion/respaldos/eliminar/{nombre_archivo}"
)
def eliminar_respaldo_ruta(

    request: Request,

    nombre_archivo: str

):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )


    eliminar_respaldo(
        nombre_archivo
    )


    return RedirectResponse(

        url="/administracion/respaldos",

        status_code=303

    )


# ============================================================
# INFORMACIÓN DEL SISTEMA
# ============================================================

@app.get(
    "/informacion"
)
def informacion(
    request: Request
):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )

    return templates.TemplateResponse(

        request=request,

        name="informacion.html",

        context={}

    )

# ============================================================
# USUARIOS
# ============================================================

@app.get(
    "/administracion/usuarios"
)
def usuarios(
    request: Request
):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )

    lista_usuarios = (
        obtener_usuarios()
    )
    personal_docentes = obtener_personal_por_tipo("Docente")
    docentes_vinculados = {
        usuario["personal_id"] for usuario in lista_usuarios
        if usuario.get("rol") == "docente" and usuario.get("activo") and usuario.get("personal_id")
    }

    return templates.TemplateResponse(

        request=request,

        name="usuarios.html",

        context={

            "usuarios":
                lista_usuarios,
            "docentes_sin_usuario": [
                maestro for maestro in personal_docentes
                if maestro["id"] not in docentes_vinculados
            ],

        }

    )

# ============================================================
# NUEVO USUARIO - FORMULARIO
# ============================================================

@app.get(
    "/administracion/usuarios/nuevo"
)
def nuevo_usuario(
    request: Request,
    personal_id: int = 0,
):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )

    return templates.TemplateResponse(

        request=request,

        name="nuevo_usuario.html",

        context={
            "maestros": obtener_personal_por_tipo("Docente"),
            "personal_id_seleccionado": personal_id,
            "rol_seleccionado": "docente" if personal_id else "operador",
            "error": request.query_params.get("error", ""),
        }

    )

# ============================================================
# EDITAR USUARIO - FORMULARIO
# ============================================================

@app.get(
    "/administracion/usuarios/{usuario_id}/editar"
)
def editar_usuario(

    usuario_id: int,

    request: Request

):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )

    usuario = obtener_usuario_por_id(

        usuario_id

    )

    if usuario is None:

        return RedirectResponse(

            url="/administracion/usuarios",

            status_code=303

        )

    return templates.TemplateResponse(

        request=request,

        name="editar_usuario.html",

        context={

            "usuario":
                usuario,
            "maestros": obtener_personal_por_tipo("Docente"),
            "error": request.query_params.get("error", ""),

        }

    )
# ============================================================
# CAMBIAR ESTADO DEL USUARIO
# ============================================================
@app.post(
    "/administracion/usuarios/{usuario_id}/estado"
)
def cambiar_estado(

    usuario_id: int,

    request: Request

):

    if not usuario_es_administrador(request):

        return RedirectResponse(

            url="/",

            status_code=303

        )

    cambiar_estado_usuario(

        usuario_id

    )

    return RedirectResponse(

        url="/administracion/usuarios",

        status_code=303

    )
# ============================================================
# GUARDAR CAMBIOS DEL USUARIO
# ============================================================

@app.post(
    "/administracion/usuarios/{usuario_id}/editar"
)
def guardar_edicion_usuario(

    usuario_id: int,

    request: Request,

    usuario: str = Form(...),

    nombre: str = Form(...),

    rol: str = Form(...),

    personal_id: int | None = Form(None),

    password: str = Form("")

):

    

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/",
            status_code=303
        )

    try:

        actualizar_usuario(

            usuario_id=usuario_id,

            usuario=usuario,

            nombre=nombre,

            rol=rol,

            personal_id=personal_id,

            password=password.strip() or None

        )

    except psycopg.errors.UniqueViolation:

        return RedirectResponse(

            url=(
                f"/administracion/usuarios/"
                f"{usuario_id}/editar?error=usuario"
            ),

            status_code=303

        )

    except ValueError:
        return RedirectResponse(
            url=f"/administracion/usuarios/{usuario_id}/editar?error=docente",
            status_code=303,
        )


    return RedirectResponse(

        url="/administracion/usuarios",

        status_code=303

    )


# ============================================================
# GUARDAR NUEVO USUARIO
# ============================================================

@app.post(
    "/administracion/usuarios/nuevo"
)
def guardar_nuevo_usuario(

    request: Request,

    usuario: str = Form(...),

    password: str = Form(...),

    nombre: str = Form(...),

    rol: str = Form(...),

    personal_id: int | None = Form(None)

):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/",
            status_code=303
        )

    try:

        crear_usuario(

            usuario=usuario,

            password=password,

            nombre=nombre,

            rol=rol,

            personal_id=personal_id

        )

    except psycopg.errors.UniqueViolation:

        return RedirectResponse(

            url="/administracion/usuarios/nuevo?error=usuario",

            status_code=303

        )

    except ValueError:
        return RedirectResponse(
            url="/administracion/usuarios/nuevo?error=docente",
            status_code=303,
        )


    return RedirectResponse(

        url="/administracion/usuarios",

        status_code=303

    )

# ============================================================
# PERSONAL
# ============================================================

@app.get(
    "/administracion/personal"
)
def personal(
    request: Request
):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    lista_personal = (
        obtener_personal()
    )


    return templates.TemplateResponse(

    	request=request,

    	name="personal.html",

    	context={

        	"personal":
            	    lista_personal,
                "personal_desactivado": request.query_params.get("desactivado") == "1",
                "personal_error": request.query_params.get("error") == "1",

    }

)

# ============================================================
# NUEVO PERSONAL - FORMULARIO
# ============================================================

@app.get(
    "/administracion/personal/nuevo"
)
def nuevo_personal(
    request: Request
):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    return templates.TemplateResponse(

    	request=request,

    	name="nuevo_personal.html",

        context={"error": "", "valores": {}}

)

# ============================================================
# EDITAR PERSONAL - FORMULARIO
# ============================================================

@app.get(
    "/administracion/personal/{personal_id}/editar"
)
def editar_personal(
    request: Request,
    personal_id: int
):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )

    persona = obtener_personal_por_id(
        personal_id
    )

    if persona is None:

        return RedirectResponse(
            url="/administracion/personal",
            status_code=303
        )

    nombre_qr = persona.get("qr")
    ruta_qr = UPLOADS_DIR / Path(str(nombre_qr or "")).name
    if not nombre_qr or not ruta_qr.is_file():
        try:
            persona["qr"] = generar_qr_personal(persona.get("numero_empleado"))
        except Exception as error:
            print("ERROR GENERANDO QR DEL PERSONAL:", error)

    return templates.TemplateResponse(
        request=request,
        name="editar_personal.html",
        context={
            "request": request,
            "persona": persona
        }
    )

# ============================================================
# GUARDAR CAMBIOS DEL PERSONAL
# ============================================================

@app.post(
    "/administracion/personal/{personal_id}/editar"
)
def guardar_edicion_personal(

    request: Request,

    personal_id: int,

    numero_empleado: str = Form(...),

    nombre: str = Form(...),

    apellido_paterno: str = Form(...),

    apellido_materno: str = Form(...),

    tipo_personal: str = Form(...),

    cargo: str = Form(""),

    area: str = Form(""),

    correo: str = Form(""),

    telefono: str = Form(""),

    foto: UploadFile = File(None)

):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    persona = obtener_personal_por_id(
        personal_id
    )


    if persona is None:

        return RedirectResponse(
            url="/administracion/personal",
            status_code=303
        )


    # --------------------------------------------------------
    # DATOS BÁSICOS
    # --------------------------------------------------------

    numero_empleado_limpio = (
        numero_empleado.strip()
    )


    # --------------------------------------------------------
    # GUARDAR NUEVA FOTO SI SE SELECCIONÓ
    # --------------------------------------------------------

    nombre_foto = None


    if foto is not None and foto.filename:

        extension = Path(
            foto.filename
        ).suffix.lower()


        nombre_foto = (
            f"personal_{numero_empleado_limpio}{extension}"
        )


        ruta_foto = (
            UPLOADS_DIR /
            nombre_foto
        )


        with open(
            ruta_foto,
            "wb"
        ) as archivo:

            archivo.write(
                foto.file.read()
            )


    # --------------------------------------------------------
    # ACTUALIZAR DATOS EN LA BASE DE DATOS
    # --------------------------------------------------------

    actualizar_personal(

        personal_id,

        numero_empleado_limpio,

        nombre.strip(),

        apellido_paterno.strip(),

        apellido_materno.strip(),

        tipo_personal.strip(),

        cargo.strip(),

        area.strip(),

        correo.strip(),

        telefono.strip(),

        foto=nombre_foto

    )


    return RedirectResponse(

        url="/administracion/personal",

        status_code=303

    )

#===============================================

@app.get("/administracion/credenciales-personal")
def credenciales_personal(request: Request):

    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="credenciales_personal.html",
        context={
            "request": request,
            "personal": obtener_personal()
        }
    )


@app.get("/credenciales-especiales")
def pagina_credenciales_especiales(
    request: Request,
    tipo: str = "direccion",
    guardado: int = 0,
    actualizado: int = 0,
    error: str = "",
):
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    if tipo not in TIPOS_CREDENCIAL_ESPECIAL:
        tipo = "direccion"
    configuracion = obtener_configuracion_credencial_especial(tipo)
    qr_preview = generar_qr_credencial_especial(f"PREVIEW-{tipo}")
    return templates.TemplateResponse(
        request=request,
        name="credenciales_especiales.html",
        context={
            "tipos": TIPOS_CREDENCIAL_ESPECIAL,
            "tipo": tipo,
            "tipo_label": TIPOS_CREDENCIAL_ESPECIAL[tipo],
            "credenciales": listar_credenciales_especiales(tipo),
            "configuracion": configuracion,
            "qr_preview": qr_preview,
            "guardado": bool(guardado),
            "actualizado": bool(actualizado),
            "error": error,
        },
    )


@app.post("/credenciales-especiales/crear")
async def crear_credencial_especial_ruta(
    request: Request,
    tipo: str = Form(...),
    nombre: str = Form(...),
    apellido_paterno: str = Form(""),
    apellido_materno: str = Form(""),
    cargo: str = Form(""),
    organizacion: str = Form(""),
    telefono: str = Form(""),
    correo_1: str = Form(""),
    correo_2: str = Form(""),
    correo_3: str = Form(""),
    correo_4: str = Form(""),
    foto: UploadFile | None = File(None),
):
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    if tipo not in TIPOS_CREDENCIAL_ESPECIAL:
        return RedirectResponse(url="/credenciales-especiales?error=tipo", status_code=303)
    nombre = nombre.strip()
    if not nombre:
        return RedirectResponse(url=f"/credenciales-especiales?tipo={tipo}&error=nombre", status_code=303)

    correos = []
    for valor in (correo_1, correo_2, correo_3, correo_4):
        direccion = valor.strip()
        if direccion and (parseaddr(direccion)[1] != direccion or "@" not in direccion):
            return RedirectResponse(url=f"/credenciales-especiales?tipo={tipo}&error=correo", status_code=303)
        correos.append(direccion or None)

    nombre_foto = None
    if foto is not None and foto.filename:
        extension = Path(foto.filename).suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            return RedirectResponse(url=f"/credenciales-especiales?tipo={tipo}&error=foto", status_code=303)
        contenido = await foto.read(8 * 1024 * 1024 + 1)
        valido = (
            extension == ".png" and contenido.startswith(b"\x89PNG\r\n\x1a\n")
            or extension in {".jpg", ".jpeg"} and contenido.startswith(b"\xff\xd8\xff")
            or extension == ".webp" and contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP"
        )
        if not contenido or len(contenido) > 8 * 1024 * 1024 or not valido:
            return RedirectResponse(url=f"/credenciales-especiales?tipo={tipo}&error=foto", status_code=303)
        nombre_foto = f"credencial_especial_{secrets.token_hex(8)}{extension}"
        with open(UPLOADS_DIR / nombre_foto, "wb") as archivo:
            archivo.write(contenido)

    try:
        crear_credencial_especial({
            "tipo": tipo,
            "nombre": nombre,
            "apellido_paterno": apellido_paterno.strip(),
            "apellido_materno": apellido_materno.strip(),
            "cargo": cargo.strip(),
            "organizacion": organizacion.strip(),
            "telefono": telefono.strip(),
            "foto": nombre_foto,
            "correo_1": correos[0], "correo_2": correos[1],
            "correo_3": correos[2], "correo_4": correos[3],
        })
        return RedirectResponse(url=f"/credenciales-especiales?tipo={tipo}&guardado=1", status_code=303)
    except Exception as error:
        print("Error al crear credencial especial:", error)
        return RedirectResponse(url=f"/credenciales-especiales?tipo={tipo}&error=guardar", status_code=303)


@app.post("/credenciales-especiales/{credencial_id}/estado")
def cambiar_estado_credencial_especial_ruta(
    request: Request, credencial_id: int, activo: bool = Form(...), tipo: str = Form("direccion")
):
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    cambiar_estado_credencial_especial(credencial_id, activo)
    return RedirectResponse(url=f"/credenciales-especiales?tipo={tipo}&actualizado=1", status_code=303)


@app.get("/credenciales-especiales/pdf")
def pdf_credenciales_especiales(request: Request, tipo: str = "direccion"):
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    if tipo not in TIPOS_CREDENCIAL_ESPECIAL:
        return RedirectResponse(url="/credenciales-especiales", status_code=303)
    credenciales = [c for c in listar_credenciales_especiales(tipo) if c.get("activo")]
    if not credenciales:
        return RedirectResponse(url=f"/credenciales-especiales?tipo={tipo}&error=sin-registros", status_code=303)
    configuracion = obtener_configuracion_credencial_especial(tipo)
    ruta = REPORTES_DIR / f"credenciales_especiales_{tipo}.pdf"
    generar_pdf_credenciales(
        [entidad_especial_para_pdf(c) for c in credenciales],
        configuracion,
        ruta,
        cantidad_por_hoja=8,
    )
    return FileResponse(path=str(ruta), media_type="application/pdf", filename=f"Credenciales_{tipo}.pdf")


@app.get("/credenciales-especiales/{credencial_id}/pdf")
def pdf_credencial_especial(request: Request, credencial_id: int):
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    credencial = obtener_credencial_especial(credencial_id)
    if not credencial:
        return RedirectResponse(url="/credenciales-especiales?error=no-encontrada", status_code=303)
    configuracion = obtener_configuracion_credencial_especial(credencial["tipo"])
    ruta = REPORTES_DIR / f"credencial_especial_{credencial_id}.pdf"
    generar_pdf_credenciales(
        [entidad_especial_para_pdf(credencial)], configuracion, ruta, cantidad_por_hoja=1
    )
    return FileResponse(path=str(ruta), media_type="application/pdf", filename=f"Credencial_{credencial['codigo']}.pdf")


@app.get("/credenciales-especiales/diseno")
def diseno_credencial_especial(request: Request, tipo: str = "direccion", guardado: int = 0):
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    if tipo not in TIPOS_CREDENCIAL_ESPECIAL:
        tipo = "direccion"
    configuracion_especial = obtener_configuracion_credencial_especial(tipo)
    return templates.TemplateResponse(
        request=request,
        name="configuracion_credencial.html",
        context={
            "tipo": tipo,
            "tipo_label": TIPOS_CREDENCIAL_ESPECIAL[tipo],
            "tipos_especiales": TIPOS_CREDENCIAL_ESPECIAL,
            "configuracion_credencial": configuracion_especial,
            "configuracion": obtener_configuracion_sistema(),
            "qr_preview": generar_qr_credencial_especial(f"PREVIEW-{tipo}"),
            "special_mode": True,
            "guardado": bool(guardado),
        },
    )


@app.post("/credenciales-especiales/diseno")
async def guardar_diseno_credencial_especial(
    request: Request,
    tipo: str = Form(...),
    nombre_institucion: str = Form(...),
    subtitulo: str = Form(""),
    texto_pie: str = Form(""),
    color_principal: str = Form("#1e3a8a"),
    color_secundario: str = Form("#2563eb"),
    color_texto: str = Form("#111827"),
    fuente: str = Form("Arial"),
    tamano_nombre: int = Form(20),
    tamano_qr: int = Form(300),
    mostrar_foto: str | None = Form(None),
    mostrar_qr: str | None = Form(None),
    mostrar_codigo: str | None = Form(None),
    mostrar_cargo: str | None = Form(None),
    mostrar_organizacion: str | None = Form(None),
    layout_json: str = Form("{}"),
    logo: UploadFile | None = File(None),
):
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    if tipo not in TIPOS_CREDENCIAL_ESPECIAL:
        return RedirectResponse(url="/credenciales-especiales", status_code=303)
    configuracion_actual = obtener_configuracion_credencial_especial(tipo)
    nombre_logo = configuracion_actual.get("logo")
    if logo is not None and logo.filename:
        extension = Path(logo.filename).suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            return RedirectResponse(url=f"/credenciales-especiales/diseno?tipo={tipo}", status_code=303)
        contenido = await logo.read(8 * 1024 * 1024 + 1)
        valido = (
            extension == ".png" and contenido.startswith(b"\x89PNG\r\n\x1a\n")
            or extension in {".jpg", ".jpeg"} and contenido.startswith(b"\xff\xd8\xff")
            or extension == ".webp" and contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP"
        )
        if not contenido or len(contenido) > 8 * 1024 * 1024 or not valido:
            return RedirectResponse(url=f"/credenciales-especiales/diseno?tipo={tipo}", status_code=303)
        nombre_logo = f"logo_credencial_especial_{tipo}{extension}"
        with open(UPLOADS_DIR / nombre_logo, "wb") as archivo:
            archivo.write(contenido)

    colores = (color_principal, color_secundario, color_texto)
    if any(len(color) != 7 or not color.startswith("#") for color in colores):
        return RedirectResponse(url=f"/credenciales-especiales/diseno?tipo={tipo}", status_code=303)
    try:
        distribucion = _validar_layout_credencial(layout_json)
    except (TypeError, ValueError):
        distribucion = {}
    diseño_libre = distribucion.get("_free") or {"enabled": False, "background": "#ffffff", "elements": []}
    guardar_configuracion_credencial_especial(tipo, {
        "nombre_institucion": nombre_institucion.strip() or "SICAE WEB",
        "subtitulo": subtitulo.strip(), "texto_pie": texto_pie.strip(), "logo": nombre_logo,
        "color_principal": color_principal, "color_secundario": color_secundario,
        "color_texto": color_texto, "color_fondo": diseño_libre.get("background", "#ffffff"),
        "fuente": fuente if fuente in {"Arial", "Helvetica", "Times", "Courier"} else "Arial",
        "tamano_nombre": max(12, min(tamano_nombre, 30)),
        "mostrar_foto": mostrar_foto is not None, "mostrar_qr": mostrar_qr is not None,
        "mostrar_codigo": mostrar_codigo is not None, "mostrar_cargo": mostrar_cargo is not None,
        "mostrar_organizacion": mostrar_organizacion is not None,
        "layout": {"_free": diseño_libre},
    })
    return RedirectResponse(url=f"/credenciales-especiales/diseno?tipo={tipo}&guardado=1", status_code=303)

# ============================================================
# CREDENCIAL DEL PERSONAL
# ============================================================

@app.get(
    "/administracion/personal/{personal_id}/credencial"
)
def credencial_personal(
    request: Request,
    personal_id: int
):

    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    personal = obtener_personal_por_id(
        personal_id
    )


    if personal is None:

        return RedirectResponse(
            url="/administracion/personal",
            status_code=303
        )

    nombre_qr = personal.get("qr")
    ruta_qr = UPLOADS_DIR / Path(str(nombre_qr or "")).name
    if not nombre_qr or not ruta_qr.is_file():
        try:
            personal["qr"] = generar_qr_personal(personal.get("numero_empleado"))
        except Exception as error:
            print("ERROR GENERANDO QR DEL PERSONAL:", error)


    configuracion = (
        obtener_configuracion_credencial_personal()
    )


    return templates.TemplateResponse(

        request=request,

        name="credencial_personal.html",

        context={

            "request": request,

            "personal": personal,

            "configuracion_personal": configuracion

        }

    )

# ============================================================
# GENERAR CREDENCIAL DEL PERSONAL PDF
# ============================================================

@app.get(
    "/administracion/personal/{personal_id}/credencial/pdf"
)
def credencial_personal_pdf(
    request: Request,
    personal_id: int
):

    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/",
            status_code=303
        )

    personal = obtener_personal_por_id(
        personal_id
    )

    if personal is None:

        return RedirectResponse(
            url="/administracion/personal",
            status_code=303
        )


    configuracion = (
        obtener_configuracion_credencial_personal()
    )


    nombre = (
        personal.get("nombre", "personal")
    ).strip()


    nombre_archivo = (
        f"credencial_personal_{personal_id}.pdf"
    )


    ruta_pdf = (
        REPORTES_DIR /
        nombre_archivo
    )


    try:

        generar_pdf_credencial_personal(

            personal=
                personal,

            configuracion=
                configuracion,

            ruta_pdf=
                ruta_pdf

        )

    except Exception as error:

        print()
        print("==========================================")
        print("ERROR GENERANDO PDF DEL PERSONAL")
        print(error)
        print("==========================================")
        print()

        return RedirectResponse(
            url=(
                f"/administracion/personal/"
                f"{personal_id}/credencial"
            ),
            status_code=303
        )


    if not ruta_pdf.exists():

        return RedirectResponse(
            url=(
                f"/administracion/personal/"
                f"{personal_id}/credencial"
            ),
            status_code=303
        )


    return FileResponse(

        path=str(
            ruta_pdf
        ),

        media_type="application/pdf",

        filename=nombre_archivo,

        content_disposition_type="inline"

    )


# ============================================================
# GUARDAR NUEVO PERSONAL
# ============================================================

@app.post(
    "/administracion/personal/nuevo"
)
def guardar_nuevo_personal(

    request: Request,

    numero_empleado: str = Form(...),

    nombre: str = Form(...),

    apellido_paterno: str = Form(...),

    apellido_materno: str = Form(""),

    tipo_personal: str = Form(...),

    cargo: str = Form(""),

    area: str = Form(""),

    correo: str = Form(""),

    telefono: str = Form(""),
    
    foto: UploadFile = File(None)

):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    valores = {
        "numero_empleado": numero_empleado.strip(),
        "nombre": nombre.strip(),
        "apellido_paterno": apellido_paterno.strip(),
        "apellido_materno": apellido_materno.strip(),
        "tipo_personal": tipo_personal.strip(),
        "cargo": cargo.strip(),
        "area": area.strip(),
        "correo": correo.strip(),
        "telefono": telefono.strip(),
    }
    nombre_qr = None
    nombre_foto = None
    ruta_qr = None
    ruta_foto = None
    qr_preexistente = False

    def volver_con_error(mensaje, status_code=400):
        if ruta_foto and ruta_foto.exists():
            ruta_foto.unlink(missing_ok=True)
        if ruta_qr and not qr_preexistente and ruta_qr.exists():
            ruta_qr.unlink(missing_ok=True)
        return templates.TemplateResponse(
            request=request,
            name="nuevo_personal.html",
            context={"error": mensaje, "valores": valores},
            status_code=status_code,
        )

    try:
        numero_limpio = valores["numero_empleado"]
        ruta_qr = UPLOADS_DIR / f"qr_personal_{numero_limpio}.png"
        qr_preexistente = ruta_qr.exists()
        nombre_qr = generar_qr_personal(numero_limpio)

        if foto is not None and foto.filename:
            extension = Path(foto.filename).suffix.lower()
            if extension not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                raise ValueError("La foto debe ser JPG, PNG, WEBP o GIF.")
            nombre_foto = f"personal_{secrets.token_hex(12)}{extension}"
            ruta_foto = UPLOADS_DIR / nombre_foto
            ruta_foto.write_bytes(foto.file.read())

        crear_personal(
            numero_empleado=numero_limpio,
            nombre=valores["nombre"],
            apellido_paterno=valores["apellido_paterno"],
            apellido_materno=valores["apellido_materno"] or None,
            tipo_personal=valores["tipo_personal"],
            cargo=valores["cargo"],
            area=valores["area"],
            correo=valores["correo"],
            telefono=valores["telefono"],
            foto=nombre_foto,
            qr=nombre_qr,
        )
    except psycopg.errors.UniqueViolation:
        return volver_con_error("Ese número de empleado ya está registrado.")
    except ValueError as error:
        return volver_con_error(str(error))
    except Exception as error:
        print("Error al guardar personal:", error)
        return volver_con_error("No se pudo guardar el personal. Revisa los datos e inténtalo de nuevo.", 500)

    return RedirectResponse(url="/administracion/personal?guardado=1", status_code=303)

# ============================================================
# ELIMINAR / DESACTIVAR PERSONAL
# ============================================================

@app.get(
    "/administracion/personal/{personal_id}/eliminar"
)
def eliminar_personal_ruta(

    request: Request,

    personal_id: int

):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    persona = obtener_personal_por_id(
        personal_id
    )


    if persona is None:

        return RedirectResponse(

            url="/administracion/personal",

            status_code=303

        )


    try:
        desactivado = eliminar_personal(personal_id)
    except Exception as error:
        print("Error al desactivar personal:", error)
        return RedirectResponse(url="/administracion/personal?error=1", status_code=303)


    return RedirectResponse(

        url="/administracion/personal?desactivado=1" if desactivado else "/administracion/personal?error=1",

        status_code=303

    )

# ============================================================
# REPORTES DE ASISTENCIA
# ============================================================

@app.get(
    "/reportes"
)
def reportes(

    request: Request,

    fecha_inicio: str | None = None,

    fecha_fin: str | None = None,

    grupo_id: int | None = None

):

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    accesos = obtener_reporte_asistencias(

        fecha_inicio=fecha_inicio,

        fecha_fin=fecha_fin,

        grupo_id=grupo_id

    )

    accesos_especiales = obtener_reporte_credenciales_especiales(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    grupos = obtener_grupos()


    return templates.TemplateResponse(

        request=request,

        name="reportes.html",

        context={

            "accesos":
                accesos,

            "accesos_especiales":
                accesos_especiales,

            "grupos":
                grupos,

            "fecha_inicio":
                fecha_inicio,

            "fecha_fin":
                fecha_fin,

            "grupo_id":
                grupo_id

        }

    )


@app.get(
    "/reportes/exportar/excel"
)
def exportar_reportes_excel(

    request: Request,

    fecha_inicio: str | None = None,

    fecha_fin: str | None = None,

    grupo_id: int | None = None

):

    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    # ========================================================
    # OBTENER DATOS
    # ========================================================

    accesos = obtener_reporte_asistencias(

        fecha_inicio=fecha_inicio,

        fecha_fin=fecha_fin,

        grupo_id=grupo_id

    )

    accesos_especiales = obtener_reporte_credenciales_especiales(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )


    # ========================================================
    # CREAR LIBRO
    # ========================================================

    libro = Workbook()

    hoja = libro.active

    hoja.title = "Asistencias"


    # ========================================================
    # CONFIGURACIÓN GENERAL
    # ========================================================

    hoja.sheet_view.showGridLines = False

    hoja.freeze_panes = "A8"


    # ========================================================
    # COLORES
    # ========================================================

    azul_oscuro = "1F4E78"

    azul_medio = "5B9BD5"

    azul_claro = "D9EAF7"

    gris_claro = "F3F6F9"

    blanco = "FFFFFF"

    verde = "E2F0D9"

    rojo = "FCE4D6"


    # ========================================================
    # BORDES
    # ========================================================

    borde_delgado = Side(
        style="thin",
        color="D9E1F2"
    )

    borde = Border(

        left=borde_delgado,

        right=borde_delgado,

        top=borde_delgado,

        bottom=borde_delgado

    )


    # ========================================================
    # CONFIGURACIÓN DEL SISTEMA
    # ========================================================

    configuracion_sistema = (
        obtener_configuracion_sistema()
    )

    # ========================================================
    # LOGO PARA EXCEL
    # ========================================================
    nombre_logo = (
        configuracion_sistema.get("logo_excel")
        if configuracion_sistema
        else None
    )

    nombre_logo_login = (
        configuracion_sistema.get("logo_login")
        if configuracion_sistema
        else None
    )

    if nombre_logo:

        ruta_logo = UPLOADS_DIR / nombre_logo

        if ruta_logo.exists():

            logo = ExcelImage(
                str(ruta_logo)
            )

            logo.width = 110
            logo.height = 110

            hoja.add_image(
                logo,
                "A1"
            )


    # ========================================================
    # NOMBRE DEL SISTEMA
    # ========================================================

    nombre_institucion = (
        configuracion_sistema.get(
            "titulo_excel"
        )
        if configuracion_sistema
        else "Reporte de Asistencias"
    )


    subtitulo = (
        configuracion_sistema.get(
            "subtitulo_excel"
        )
        if configuracion_sistema
        else "Sistema de Registro de Asistencias"
    )


    # ========================================================
    # ENCABEZADO INSTITUCIONAL
    # ========================================================

    hoja.merge_cells(
        "B1:H2"
    )


    celda_titulo = hoja["B1"]

    celda_titulo.value = (
        nombre_institucion
    )


    celda_titulo.font = Font(

        name="Calibri",

        size=20,

        bold=True,

        color=blanco

    )


    celda_titulo.alignment = Alignment(

        horizontal="center",

        vertical="center"

    )


    celda_titulo.fill = PatternFill(

        "solid",

        fgColor=azul_oscuro

    )


    # ========================================================
    # SUBTÍTULO
    # ========================================================

    hoja.merge_cells(
        "B3:H3"
    )


    celda_subtitulo = hoja["B3"]


    celda_subtitulo.value = (
        subtitulo
    )


    celda_subtitulo.font = Font(

        name="Calibri",

        size=12,

        italic=True,

        color="404040"

    )


    celda_subtitulo.alignment = Alignment(

        horizontal="center",

        vertical="center"

    )


    # ========================================================
    # TÍTULO DEL REPORTE
    # ========================================================

    hoja.merge_cells(
        "A4:I4"
    )


    celda_reporte = hoja["A4"]


    celda_reporte.value = (
        nombre_institucion
    )


    celda_reporte.font = Font(

        name="Calibri",

        size=16,

        bold=True,

        color=azul_oscuro

    )


    celda_reporte.alignment = Alignment(

        horizontal="center",

        vertical="center"

    )


    # ========================================================
    # INFORMACIÓN DEL REPORTE
    # ========================================================

    if fecha_inicio:

        periodo_inicio = fecha_inicio

    else:

        periodo_inicio = "Todos"


    if fecha_fin:

        periodo_fin = fecha_fin

    else:

        periodo_fin = "Todos"


    # Obtener nombre del grupo

    nombre_grupo = "Todos los grupos"


    if grupo_id:

        try:

            grupos = obtener_grupos()


            for grupo in grupos:

                if (
                    grupo.get("id")
                    == grupo_id
                ):

                    nombre_grupo = (

                        f'{grupo.get("grado", "")}{chr(176)} '

                        f'{grupo.get("nombre_grupo", "")} - '

                        

                        f'{grupo.get("turno", "")}'

                    ).strip()

                    break

        except Exception:

            nombre_grupo = (
                f"Grupo {grupo_id}"
            )


    hoja["A5"] = "Periodo:"

    hoja["B5"] = (
        f"{periodo_inicio}  -  "
        f"{periodo_fin}"
    )


    hoja["A6"] = "Grupo:"

    hoja["B6"] = nombre_grupo


    hoja["F5"] = "Registros:"

    hoja["G5"] = len(accesos)


    hoja["F6"] = "Generado:"

    from datetime import datetime

    hoja["G6"] = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )


    for celda in [

        hoja["A5"],

        hoja["A6"],

        hoja["F5"],

        hoja["F6"]

    ]:

        celda.font = Font(
            bold=True,
            color=azul_oscuro
        )


    for celda in [

        hoja["B5"],

        hoja["B6"],

        hoja["G5"],

        hoja["G6"]

    ]:

        celda.font = Font(
            color="404040"
        )


    # ========================================================
    # ENCABEZADOS DE LA TABLA
    # ========================================================

    fila_encabezado = 8


    encabezados = [

        "Fecha",

        "Hora",

        "Matricula",

        "Alumno",

        "Grupo",

        "Grado",

        "Turno",

        "Movimiento",

        "Registrado por"

    ]


    for columna, encabezado in enumerate(
        encabezados,
        start=1
    ):

        celda = hoja.cell(

            row=fila_encabezado,

            column=columna

        )


        celda.value = encabezado


        celda.font = Font(

            bold=True,

            color=blanco,

            size=11

        )


        celda.fill = PatternFill(

            "solid",

            fgColor=azul_oscuro

        )


        celda.alignment = Alignment(

            horizontal="center",

            vertical="center"

        )


        celda.border = borde


    hoja.row_dimensions[
        fila_encabezado
    ].height = 25


    # ========================================================
    # DATOS
    # ========================================================

    fila_actual = fila_encabezado + 1


    for indice, acceso in enumerate(
        accesos
    ):

        nombre_completo = " ".join(

            parte

            for parte in [

                acceso.get(
                    "nombre"
                ),

                acceso.get(
                    "apellido_paterno"
                ),

                acceso.get(
                    "apellido_materno"
                )

            ]

            if parte

        )


        grado = ""


        if acceso.get("grado"):

            grado = (

                f'{acceso["grado"]}\u00b0 '

                f'{acceso.get("grupo_nombre") or ""}'

            ).strip()


        datos_fila = [

            str(
                acceso.get("fecha")
                or ""
            ),

            str(
                acceso.get("hora")
                or ""
            )[:8],

            acceso.get(
                "matricula"
            ) or "",

            nombre_completo,

            acceso.get(
                "nombre_grupo"
            ) or "",

            grado,

            acceso.get(
                "turno"
            ) or "",

            acceso.get(
                "movimiento"
            ) or "",

            acceso.get("registrado_por") or "No disponible"

        ]


        for columna, valor in enumerate(
            datos_fila,
            start=1
        ):

            celda = hoja.cell(

                row=fila_actual,

                column=columna

            )


            celda.value = valor


            celda.border = borde


            celda.alignment = Alignment(

                vertical="center",

                horizontal=(
                    "center"
                    if columna in [
                        1,
                        2,
                        3,
                        5,
                        6,
                        7,
                        8,
                        9
                    ]
                    else "left"
                )

            )


            # Filas alternadas

            if indice % 2 == 1:

                celda.fill = PatternFill(

                    "solid",

                    fgColor=gris_claro

                )


        # ====================================================
        # COLOR DEL MOVIMIENTO
        # ====================================================

        celda_movimiento = hoja.cell(

            row=fila_actual,

            column=8

        )


        movimiento = str(
            acceso.get(
                "movimiento"
            ) or ""
        ).upper()


        if movimiento == "ENTRADA":

            celda_movimiento.fill = PatternFill(

                "solid",

                fgColor=verde

            )

            celda_movimiento.font = Font(

                bold=True,

                color="548235"

            )

        elif movimiento == "SALIDA":

            celda_movimiento.fill = PatternFill(

                "solid",

                fgColor=rojo

            )

            celda_movimiento.font = Font(

                bold=True,

                color="C00000"

            )


        fila_actual += 1


    # ========================================================
    # AJUSTAR COLUMNAS
    # ========================================================

    anchos = {

        "A": 14,

        "B": 12,

        "C": 18,

        "D": 38,

        "E": 22,

        "F": 16,

        "G": 16,

        "H": 18,

        "I": 24

    }


    for columna, ancho in anchos.items():

        hoja.column_dimensions[
            columna
        ].width = ancho


    # ========================================================
    # ALTURA DE FILAS
    # ========================================================

    for fila in range(
        fila_encabezado + 1,
        fila_actual
    ):

        hoja.row_dimensions[
            fila
        ].height = 22


    # ========================================================
    # FILTROS AUTOMÁTICOS
    # ========================================================

    if accesos:

        hoja.auto_filter.ref = (

            f"A{fila_encabezado}:"
            f"I{fila_actual - 1}"

        )


    # ========================================================
    # CONFIGURACIÓN DE IMPRESIÓN
    # ========================================================

    hoja.page_setup.orientation = (
        "landscape"
    )

    hoja.page_setup.paperSize = (
        hoja.PAPERSIZE_LETTER
    )

    hoja.page_setup.fitToWidth = 1

    hoja.page_setup.fitToHeight = 0

    hoja.sheet_properties.pageSetUpPr.fitToPage = True


    hoja.print_title_rows = (
        "1:8"
    )


    hoja.page_margins.left = 0.25

    hoja.page_margins.right = 0.25

    hoja.page_margins.top = 0.5

    hoja.page_margins.bottom = 0.5


    # ========================================================
    # CENTRAR HORIZONTALMENTE AL IMPRIMIR
    # ========================================================

    hoja.print_options.horizontalCentered = True


    # ========================================================
    # ARCHIVO
    # ========================================================

    ruta_excel = (

        REPORTES_DIR /
        "reporte_asistencias.xlsx"

    )
    

    hoja_especiales = libro.create_sheet("Credenciales especiales")
    hoja_especiales.append([
        "Fecha", "Hora", "Tipo", "Código", "Persona", "Cargo",
        "Organización", "Movimiento", "Registrado por",
    ])
    for celda in hoja_especiales[1]:
        celda.font = Font(bold=True, color="FFFFFF", size=11)
        celda.fill = PatternFill("solid", fgColor=azul_oscuro)
        celda.alignment = Alignment(horizontal="center", vertical="center")
        celda.border = borde
    for fila in accesos_especiales:
        hoja_especiales.append([
            str(fila.get("fecha") or ""),
            str(fila.get("hora") or "")[:8],
            fila.get("tipo_label") or "",
            fila.get("codigo") or "",
            fila.get("nombre_completo") or "",
            fila.get("cargo") or "",
            fila.get("organizacion") or "",
            fila.get("movimiento") or "",
            fila.get("registrado_por") or "No disponible",
        ])
        fila_excel = hoja_especiales.max_row
        for celda in hoja_especiales[fila_excel]:
            celda.border = borde
            celda.alignment = Alignment(vertical="center")
            if fila_excel % 2 == 1:
                celda.fill = PatternFill("solid", fgColor=gris_claro)
    hoja_especiales.freeze_panes = "A2"
    hoja_especiales.auto_filter.ref = hoja_especiales.dimensions
    for columna, ancho in {"A": 14, "B": 12, "C": 22, "D": 18, "E": 34, "F": 24, "G": 28, "H": 18, "I": 24}.items():
        hoja_especiales.column_dimensions[columna].width = ancho

    libro.save(
        ruta_excel
    )


    # ========================================================
    # DESCARGAR
    # ========================================================

    return FileResponse(

        path=str(
            ruta_excel
        ),

        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),

        filename=(
            "Reporte_Asistencias.xlsx"
        )

    )

# ============================================================
# DETALLE DEL ALUMNO
# ============================================================

# ============================================================
# DETALLE DEL ALUMNO
# ============================================================

@app.get(
    "/alumnos/detalle/{alumno_id}"
)
def detalle_alumno(

    request: Request,

    alumno_id: int

):
    
    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    alumno = (
        obtener_alumno_detalle(
            alumno_id
        )
    )


    if alumno is None:

        return RedirectResponse(

            url="/alumnos",

            status_code=303

        )


    return templates.TemplateResponse(

        request=request,

        name="alumno_detalle.html",

        context={

            "alumno":
                alumno

        }

    )


# ============================================================
# CREDENCIAL DEL ALUMNO
# ============================================================

@app.get(
    "/alumnos/{alumno_id}/credencial"
)
def credencial_alumno(

    request: Request,

    alumno_id: int

):

    
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )
    alumno = (
        obtener_alumno_detalle(
            alumno_id
        )
    )


    if alumno is None:

        return RedirectResponse(

            url="/alumnos",

            status_code=303

        )

    nombre_qr = alumno.get("qr")
    ruta_qr = UPLOADS_DIR / Path(str(nombre_qr or "")).name
    if not nombre_qr or not ruta_qr.is_file():
        try:
            alumno["qr"] = generar_qr_alumno(alumno.get("matricula"))
        except Exception as error:
            print("ERROR GENERANDO QR DEL ALUMNO:", error)


    configuracion = (
        obtener_configuracion_credencial()
    )


    return templates.TemplateResponse(

        request=request,

        name="credencial.html",

        context={

            "alumno":
                alumno,

            "configuracion_credencial": configuracion

        }

    )


# ============================================================
# GENERAR CREDENCIAL PDF
# ============================================================

@app.get(
    "/alumnos/{alumno_id}/credencial/pdf"
)
def credencial_pdf(

    request: Request,

    alumno_id: int

):
    
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    alumno = (
        obtener_alumno_detalle(
            alumno_id
        )
    )


    if alumno is None:

        return RedirectResponse(

            url="/alumnos",

            status_code=303

        )


    configuracion = (
        obtener_configuracion_credencial()
    )


    matricula = str(

        alumno.get(
            "matricula",
            alumno_id
        )

    ).strip()


    if not matricula:

        matricula = str(
            alumno_id
        )


    nombre_archivo = (
        f"credencial_{matricula}.pdf"
    )


    ruta_pdf = (
        REPORTES_DIR /
        nombre_archivo
    )


    try:

        generar_pdf_credenciales(

            alumnos=[
                alumno
            ],

            configuracion=
                configuracion,

            ruta_pdf=
                ruta_pdf

        )

    except Exception as error:

        print()
        print("==========================================")
        print("ERROR GENERANDO PDF")
        print(error)
        print("==========================================")
        print()


        return RedirectResponse(

            url=(
                f"/alumnos/detalle/"
                f"{alumno_id}"
            ),

            status_code=303

        )


    if not ruta_pdf.exists():

        return RedirectResponse(

            url=(
                f"/alumnos/detalle/"
                f"{alumno_id}"
            ),

            status_code=303

        )


    return FileResponse(

        path=str(
            ruta_pdf
        ),

        media_type=(
            "application/pdf"
        ),

        filename=nombre_archivo,

        content_disposition_type=
            "inline"

    )



# ============================================================
# PDF CREDENCIAL DEL PERSONAL
# ============================================================

@app.get(
    "/administracion/personal/{personal_id}/credencial/pdf"
)
def credencial_personal_pdf(
    request: Request,
    personal_id: int
):

    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/",
            status_code=303
        )

    personal = obtener_personal_por_id(
        personal_id
    )

    if personal is None:

        return RedirectResponse(
            url="/administracion/personal",
            status_code=303
        )


    configuracion = (
        obtener_configuracion_credencial_personal()
    )


    nombre_archivo = (
        f"credencial_personal_{personal_id}.pdf"
    )


    ruta_pdf = (
        REPORTES_DIR /
        nombre_archivo
    )


    try:

        generar_pdf_credencial_personal(
            personal=personal,
            configuracion=configuracion,
            ruta_pdf=ruta_pdf
        )

    except Exception as error:

        print()
        print("==========================================")
        print("ERROR GENERANDO PDF DEL PERSONAL")
        print(error)
        print("==========================================")
        print()

        return RedirectResponse(
            url=(
                f"/administracion/personal/"
                f"{personal_id}/credencial"
            ),
            status_code=303
        )


    if not ruta_pdf.exists():

        return RedirectResponse(
            url=(
                f"/administracion/personal/"
                f"{personal_id}/credencial"
            ),
            status_code=303
        )


    return FileResponse(
        path=str(ruta_pdf),
        media_type="application/pdf",
        filename=nombre_archivo,
        content_disposition_type="inline"
    )
# ============================================================
# EDITAR ALUMNO
# ============================================================

@app.get(
    "/alumnos/{alumno_id}/editar"
)
def editar_alumno(

    request: Request,

    alumno_id: int

):


    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/alumnos",
            status_code=303
        )
    alumno = (
        obtener_alumno_detalle(
            alumno_id
        )
    )


    if alumno is None:

        return RedirectResponse(

            url="/alumnos",

            status_code=303

        )

    nombre_qr = alumno.get("qr")
    ruta_qr = UPLOADS_DIR / Path(str(nombre_qr or "")).name
    if not nombre_qr or not ruta_qr.is_file():
        try:
            alumno["qr"] = generar_qr_alumno(alumno.get("matricula"))
        except Exception as error:
            print("ERROR GENERANDO QR DEL ALUMNO:", error)


    grupos = obtener_grupos()


    return templates.TemplateResponse(

        request=request,

        name="editar_alumno.html",

        context={

            "alumno":
                alumno,

            "grupos":
                grupos

        }

    )


# ============================================================
# GUARDAR EDICIÓN ALUMNO
# ============================================================

@app.post(
    "/alumnos/{alumno_id}/editar"
)
async def guardar_edicion_alumno(

    request: Request,

    alumno_id: int,

    matricula: str = Form(...),

    nombre: str = Form(...),

    apellido_paterno: str = Form(...),

    apellido_materno: str = Form(""),

    fecha_nacimiento: str = Form(""),

    correo: str = Form(""),

    telefono: str = Form(""),

    grupo_id: int = Form(...),

    foto: UploadFile | None =
        File(None)

):
    
    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/alumnos",
            status_code=303
        )

    alumno_actual = (
        obtener_alumno_detalle(
            alumno_id
        )
    )


    if alumno_actual is None:

        return RedirectResponse(

            url="/alumnos",

            status_code=303

        )


    nombre_foto = (
        alumno_actual.get(
            "foto"
        )
    )


    nombre_qr = (
        alumno_actual.get(
            "qr"
        )
    )


    matricula_anterior = str(

        alumno_actual.get(
            "matricula",
            ""
        )

    ).strip()


    matricula_nueva = str(
        matricula
    ).strip()


    matricula_cambio = (

        matricula_anterior !=
        matricula_nueva

    )


    # ========================================================
    # NUEVA FOTO
    # ========================================================

    if (
        foto is not None
        and foto.filename
    ):

        extension = Path(
            foto.filename
        ).suffix.lower()


        extensiones_permitidas = {

            ".jpg",
            ".jpeg",
            ".png",
            ".webp"

        }


        if extension in (
            extensiones_permitidas
        ):

            nombre_foto = (
                f"{matricula_nueva}"
                f"{extension}"
            )


            ruta_foto = (
                UPLOADS_DIR /
                nombre_foto
            )


            contenido = (
                await foto.read()
            )


            with open(
                ruta_foto,
                "wb"
            ) as archivo:

                archivo.write(
                    contenido
                )
    # ========================================================
    # NUEVO QR
    # ========================================================

    if matricula_cambio:

        nombre_qr = (
            generar_qr_alumno(
                matricula_nueva
            )
        )


    # ========================================================
    # ACTUALIZAR
    # ========================================================

    if not fecha_nacimiento:
        fecha_nacimiento = None

    try:

        actualizar_alumno(

            alumno_id=
                alumno_id,

            matricula=
                matricula_nueva,

            nombre=
                nombre,

            apellido_paterno=
                apellido_paterno,

            apellido_materno=
                apellido_materno,

            fecha_nacimiento=
                fecha_nacimiento,

            correo=
                correo,

            telefono=
                telefono,

            grupo_id=
                grupo_id,

            foto=
                nombre_foto,

            qr=
                nombre_qr

        )


    except UniqueViolation:

        return RedirectResponse(

            url=(
                f"/alumnos/"
                f"{alumno_id}/editar"
                f"?error=matricula"
            ),

            status_code=303

        )


    return RedirectResponse(

        url=(
            f"/alumnos/detalle/"
            f"{alumno_id}"
        ),

        status_code=303

    )


# ============================================================
# ELIMINAR ALUMNO
# ============================================================

@app.get(
    "/alumnos/{alumno_id}/eliminar"
)
def eliminar_alumno_ruta(

    request: Request,

    alumno_id: int

):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/alumnos",
            status_code=303
        )


    eliminar_alumno(
        alumno_id
    )


    return RedirectResponse(

        url="/alumnos",

        status_code=303

    )


# ============================================================
# ELIMINAR ALUMNOS SELECCIONADOS
# ============================================================

@app.post(
    "/alumnos/grupo/{grupo_id}/eliminar-seleccionados"
)
def eliminar_alumnos_seleccionados(

    request: Request,

    grupo_id: int,

    alumnos_ids: list[int] = Form([])

):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/alumnos",
            status_code=303
        )


    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/alumnos",
            status_code=303
        )


    if alumnos_ids:

        eliminar_alumnos(
            alumnos_ids
        )

    return RedirectResponse(

        url=f"/alumnos/grupo/{grupo_id}",

        status_code=303

    )


# ============================================================
# GRUPOS
# ============================================================

@app.get("/grupos")
def grupos(
    request: Request
):

    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    

    lista_grupos = (
        obtener_grupos()
    )


    return templates.TemplateResponse(

        request=request,

        name="grupos.html",

        context={

            "grupos":
                lista_grupos

        }

    )


# ============================================================
# NUEVO GRUPO
# ============================================================

@app.get(
    "/grupos/nuevo"
)
def nuevo_grupo(

    request: Request

):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/grupos",
            status_code=303
        )

    return templates.TemplateResponse(

        request=request,

        name="nuevo_grupo.html",

        context={}

    )


# ============================================================
# GUARDAR NUEVO GRUPO
# ============================================================

@app.post(
    "/grupos/nuevo"
)
def guardar_nuevo_grupo(

    request: Request,

    nombre_grupo: str =
        Form(...),

    grado: int =
        Form(...),

    nombre: str =
        Form(...),

    turno: str =
        Form(...)

):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/grupos",
            status_code=303
        )


    try:

        with psycopg.connect(
            **DATABASE_CONFIG
        ) as conexion:

            with conexion.cursor() as cursor:

                cursor.execute("""

                    INSERT INTO grupos (

                        nombre_grupo,
                        grado,
                        nombre,
                        turno,
                        activo

                    )

                    VALUES (

                        %s,
                        %s,
                        %s,
                        %s,
                        TRUE

                    );

                """, (

                    nombre_grupo.strip(),

                    grado,

                    nombre.strip().upper(),

                    turno

                ))

            conexion.commit()


    except Exception as error:

        print()
        print("==========================================")
        print("ERROR CREANDO GRUPO")
        print(error)
        print("==========================================")
        print()


    return RedirectResponse(

        url="/grupos",

        status_code=303

    )


# ============================================================
# EDITAR GRUPO
# ============================================================

@app.get(
    "/grupos/{grupo_id}/editar"
)
def editar_grupo(

    request: Request,

    grupo_id: int

):


    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/grupos",
            status_code=303
        )
    grupo = None


    try:

        with psycopg.connect(
            **DATABASE_CONFIG
        ) as conexion:

            with conexion.cursor() as cursor:

                cursor.execute("""

                    SELECT

                        id,
                        nombre_grupo,
                        grado,
                        nombre,
                        turno

                    FROM grupos

                    WHERE id = %s

                    AND activo = TRUE;

                """, (

                    grupo_id,

                ))


                fila = cursor.fetchone()


                if fila:

                    grupo = {

                        "id": fila[0],

                        "nombre_grupo":
                            fila[1],

                        "grado":
                            fila[2],

                        "nombre":
                            fila[3],

                        "turno":
                            fila[4]

                    }


    except Exception as error:

        print(
            "ERROR OBTENIENDO GRUPO:",
            error
        )


    if grupo is None:

        return RedirectResponse(

            url="/grupos",

            status_code=303

        )


    return templates.TemplateResponse(

        request=request,

        name="editar_grupo.html",

        context={

            "grupo":
                grupo

        }

    )


# ============================================================
# GUARDAR EDICIÓN GRUPO
# ============================================================

@app.post(
    "/grupos/{grupo_id}/editar"
)
def guardar_edicion_grupo(

    request: Request,

    grupo_id: int,

    nombre_grupo: str =
        Form(...),

    grado: int =
        Form(...),

    nombre: str =
        Form(...),

    turno: str =
        Form(...)

):

    if not usuario_es_administrador(request):
        return RedirectResponse(url="/grupos", status_code=303)

    try:

        with psycopg.connect(
            **DATABASE_CONFIG
        ) as conexion:

            with conexion.cursor() as cursor:

                cursor.execute("""

                    UPDATE grupos

                    SET

                        nombre_grupo = %s,

                        grado = %s,

                        nombre = %s,

                        turno = %s

                    WHERE id = %s

                    AND activo = TRUE;

                """, (

                    nombre_grupo.strip(),

                    grado,

                    nombre.strip().upper(),

                    turno,

                    grupo_id

                ))

            conexion.commit()


    except Exception as error:

        print()
        print("ERROR ACTUALIZANDO GRUPO:")
        print(error)


    return RedirectResponse(

        url="/grupos",

        status_code=303

    )


# ============================================================
# ELIMINAR GRUPO
# ============================================================

@app.get(
    "/grupos/{grupo_id}/eliminar"
)
def eliminar_grupo(

    request: Request,

    grupo_id: int

):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/grupos",
            status_code=303
        )


    try:

        with psycopg.connect(
            **DATABASE_CONFIG
        ) as conexion:

            with conexion.cursor() as cursor:

                cursor.execute("""

                    UPDATE grupos

                    SET activo = FALSE

                    WHERE id = %s;

                """, (

                    grupo_id,

                ))

            conexion.commit()


    except Exception as error:

        print(
            "ERROR ELIMINANDO GRUPO:",
            error
        )


    return RedirectResponse(

        url="/grupos",

        status_code=303

    )


# ============================================================
# NUEVO ALUMNO
# ============================================================

@app.get(
    "/alumnos/nuevo"
)
def nuevo_alumno(

    request: Request,

    grupo_id: int | None = None,

    error: str | None = None

):


    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/alumnos",
            status_code=303
        )
    grupos = obtener_grupos()


    return templates.TemplateResponse(

        request=request,

        name="nuevo_alumno.html",

        context={

            "grupos":
                grupos,

            "grupo_seleccionado":
                grupo_id,

            "error":
                error

        }

    )


# ============================================================
# GUARDAR NUEVO ALUMNO
# ============================================================

@app.post(
    "/alumnos/nuevo"
)
async def guardar_nuevo_alumno(
    request: Request,


    matricula: str =
        Form(...),

    nombre: str =
        Form(...),

    apellido_paterno: str =
        Form(...),

    apellido_materno: str =
        Form(""),

    fecha_nacimiento: str =
        Form(""),

    correo: str =
        Form(""),

    telefono: str =
        Form(""),

    grupo_id: int =
        Form(...),

    foto: UploadFile | None =
        File(None)

):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/alumnos",
            status_code=303
        )

    matricula = str(
        matricula
    ).strip()


    nombre_foto = None


    # ========================================================
    # FOTO
    # ========================================================

    if (
        foto is not None
        and foto.filename
    ):

        extension = Path(
            foto.filename
        ).suffix.lower()


        extensiones_permitidas = {

            ".jpg",
            ".jpeg",
            ".png",
            ".webp"

        }


        if extension in (
            extensiones_permitidas
        ):

            nombre_foto = (
                f"{matricula}"
                f"{extension}"
            )


            ruta_foto = (
                UPLOADS_DIR /
                nombre_foto
            )


            contenido = (
                await foto.read()
            )


            with open(
                ruta_foto,
                "wb"
            ) as archivo:

                archivo.write(
                    contenido
                )


    # ========================================================
    # CREAR ALUMNO
    # ========================================================

    if not fecha_nacimiento:
        fecha_nacimiento = None

    try:

        crear_alumno(

            matricula=
                matricula,

            nombre=
                nombre,

            apellido_paterno=
                apellido_paterno,

            apellido_materno=
                apellido_materno,

            fecha_nacimiento=
                fecha_nacimiento,

            correo=
                correo,

            telefono=
                telefono,

            grupo_id=
                grupo_id,

            foto=
                nombre_foto,

            qr=None

        )


    except UniqueViolation:

        if nombre_foto:

            ruta_foto = (
                UPLOADS_DIR /
                nombre_foto
            )


            if ruta_foto.exists():

                try:

                    ruta_foto.unlink()

                except Exception:

                    pass


        return RedirectResponse(

            url=(
                f"/alumnos/nuevo"
                f"?grupo_id={grupo_id}"
                f"&error=matricula"
            ),

            status_code=303

        )


    # ========================================================
    # GENERAR QR
    # ========================================================

    try:

        nombre_qr = (
            generar_qr_alumno(
                matricula
            )
        )


        with psycopg.connect(
            **DATABASE_CONFIG
        ) as conexion:

            with conexion.cursor() as cursor:

                cursor.execute("""

                    UPDATE alumnos

                    SET qr = %s

                    WHERE matricula = %s
                      AND activo = TRUE;

                """, (

                    nombre_qr,

                    matricula

                ))

            conexion.commit()


    except Exception as error:

        print()
        print("==========================================")
        print("ERROR GENERANDO QR")
        print(error)
        print("==========================================")
        print()


    return RedirectResponse(

        url="/alumnos",

        status_code=303

    )


# ============================================================
# CONFIGURACIÓN DEL SISTEMA
# ============================================================

# ============================================================
# IMPORTAR ALUMNOS DESDE EXCEL
# ============================================================

@app.post(
    "/alumnos/grupo/{grupo_id}/importar-excel"
)
async def importar_alumnos_excel(
    request: Request,



    grupo_id: int,

    archivo_excel: UploadFile =
        File(...)

):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/alumnos",
            status_code=303
        )


    # ========================================================
    # VERIFICAR ARCHIVO
    # ========================================================

    if (
        archivo_excel is None
        or not archivo_excel.filename
    ):

        return RedirectResponse(
            url=f"/alumnos/grupo/{grupo_id}",
            status_code=303
        )


    extension = Path(
        archivo_excel.filename
    ).suffix.lower()


    if extension != ".xlsx":

        return RedirectResponse(
            url=(
                f"/alumnos/grupo/"
                f"{grupo_id}"
                f"?error=excel"
            ),
            status_code=303
        )


    # ========================================================
    # GUARDAR TEMPORALMENTE EL EXCEL
    # ========================================================

    contenido_excel = (
        await archivo_excel.read()
    )


    ruta_temporal = (
        STATIC_DIR /
        "uploads" /
        "_importacion_alumnos.xlsx"
    )


    with open(
        ruta_temporal,
        "wb"
    ) as archivo:

        archivo.write(
            contenido_excel
        )


    # ========================================================
    # CONTADORES
    # ========================================================

    importados = 0
    duplicados = 0
    errores = 0


    # ========================================================
    # LEER EXCEL
    # ========================================================

    try:

        libro = load_workbook(
            ruta_temporal,
            data_only=True
        )

        hoja = libro.active


        # ====================================================
        # ENCABEZADOS
        # ====================================================

        encabezados = []

        for celda in hoja[1]:

            if celda.value is None:

                encabezados.append("")

            else:

                encabezados.append(
                    str(celda.value)
                    .strip()
                    .lower()
                )


        columnas = {

            encabezado: indice

            for indice, encabezado
            in enumerate(encabezados)

            if encabezado

        }


        # ====================================================
        # COLUMNAS OBLIGATORIAS
        # ====================================================

        columnas_requeridas = {

            "matricula",
            "nombre",
            "apellido_paterno"

        }


        if not columnas_requeridas.issubset(
            columnas.keys()
        ):

            libro.close()

            if ruta_temporal.exists():

                ruta_temporal.unlink()

            return RedirectResponse(

                url=(
                    f"/alumnos/grupo/"
                    f"{grupo_id}"
                    f"?error=columnas_excel"
                ),

                status_code=303

            )


        # ====================================================
        # PROCESAR FILAS
        # ====================================================

        for fila in hoja.iter_rows(
            min_row=2,
            values_only=True
        ):

            try:

                def obtener_valor(
                    nombre_columna
                ):

                    indice = columnas.get(
                        nombre_columna
                    )

                    if indice is None:
                        return ""

                    if indice >= len(fila):
                        return ""

                    valor = fila[indice]

                    if valor is None:
                        return ""

                    return valor


                matricula = obtener_valor(
                    "matricula"
                )

                nombre = obtener_valor(
                    "nombre"
                )

                apellido_paterno = (
                    obtener_valor(
                        "apellido_paterno"
                    )
                )

                apellido_materno = (
                    obtener_valor(
                        "apellido_materno"
                    )
                )

                fecha_nacimiento = (
                    obtener_valor(
                        "fecha_nacimiento"
                    )
                )

                correo = obtener_valor(
                    "correo"
                )

                telefono = obtener_valor(
                    "telefono"
                )


                # ============================================
                # LIMPIAR MATRÍCULA
                # ============================================

                matricula = str(
                    matricula
                ).strip()


                if not matricula:
                    continue


                # ============================================
                # VERIFICAR DUPLICADO
                # ============================================

                with psycopg.connect(
                    **DATABASE_CONFIG
                ) as conexion:

                    with conexion.cursor() as cursor:

                        cursor.execute(
                            """
                            SELECT id
                            FROM alumnos
                            WHERE matricula = %s
                              AND activo = TRUE
                            """,
                            (matricula,)
                        )

                        existente = (
                            cursor.fetchone()
                        )


                if existente:

                    duplicados += 1

                    continue


                # ============================================
                # FECHA DE NACIMIENTO
                # ============================================

                if hasattr(
                    fecha_nacimiento,
                    "date"
                ):

                    fecha_nacimiento = (
                        fecha_nacimiento.date()
                    )


                if fecha_nacimiento == "":
                    fecha_nacimiento = None


                # ============================================
                # CREAR ALUMNO
                # ============================================

                alumno_id = (
                    importar_alumno_excel(

                        matricula=matricula,

                        nombre=str(
                            nombre
                        ).strip(),

                        apellido_paterno=str(
                            apellido_paterno
                        ).strip(),

                        apellido_materno=str(
                            apellido_materno
                        ).strip(),

                        fecha_nacimiento=
                            fecha_nacimiento,

                        correo=str(
                            correo
                        ).strip(),

                        telefono=str(
                            telefono
                        ).strip(),

                        grupo_id=grupo_id

                    )
                )


                # ============================================
                # GENERAR QR
                # ============================================

                try:

                    nombre_qr = (
                        generar_qr_alumno(
                            matricula
                        )
                    )


                    with psycopg.connect(
                        **DATABASE_CONFIG
                    ) as conexion:

                        with conexion.cursor() as cursor:

                            cursor.execute(
                                """
                                UPDATE alumnos
                                SET qr = %s
                                WHERE id = %s
                                """,
                                (
                                    nombre_qr,
                                    alumno_id
                                )
                            )

                        conexion.commit()


                except Exception as error_qr:

                    print(
                        "ERROR GENERANDO QR:",
                        matricula,
                        error_qr
                    )


                importados += 1


            except Exception as error_fila:

                errores += 1

                print()
                print(
                    "ERROR IMPORTANDO FILA:"
                )
                print(
                    error_fila
                )
                print()


        libro.close()


    except Exception as error_excel:

        print()
        print(
            "ERROR LEYENDO EXCEL:"
        )
        print(
            error_excel
        )
        print()


        if ruta_temporal.exists():

            ruta_temporal.unlink()


        return RedirectResponse(

            url=(
                f"/alumnos/grupo/"
                f"{grupo_id}"
                f"?error=lectura_excel"
            ),

            status_code=303

        )


    # ========================================================
    # ELIMINAR ARCHIVO TEMPORAL
    # ========================================================

    if ruta_temporal.exists():

        ruta_temporal.unlink()


    # ========================================================
    # RESULTADO
    # ========================================================

    return RedirectResponse(

        url=(
            f"/alumnos/grupo/"
            f"{grupo_id}"
            f"?importados={importados}"
            f"&duplicados={duplicados}"
            f"&errores={errores}"
        ),

        status_code=303

    )



# ============================================================
# CONFIGURACION DE HORARIOS Y ASISTENCIA
# ============================================================

@app.get(
    "/configuracion/asistencia",
    response_class=HTMLResponse
)
def configuracion_asistencia(request: Request):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    hora_entrada,
                    tolerancia_minutos,
                    hora_cierre_entrada,
                    activo
                FROM configuracion_asistencia
                WHERE id = 1;
            """)

            fila = cursor.fetchone()

    if fila is None:

        configuracion = {
            "id": 1,
            "hora_entrada": "07:30",
            "tolerancia_minutos": 10,
            "hora_cierre_entrada": "08:30",
            "activo": True
        }

    else:

        configuracion = {
            "id": fila[0],
            "hora_entrada": str(fila[1])[:5],
            "tolerancia_minutos": fila[2],
            "hora_cierre_entrada": str(fila[3])[:5],
            "activo": fila[4]
        }

    return templates.TemplateResponse(
        request=request,
        name="configuracion_asistencia.html",
        context={
            "request": request,
            "configuracion_asistencia": configuracion
        }
    )


@app.post(
    "/configuracion/asistencia"
)
async def guardar_configuracion_asistencia(
    request: Request,
    hora_entrada: str = Form(...),
    tolerancia_minutos: int = Form(...),
    hora_cierre_entrada: str = Form(...),
    activo: str | None = Form(None)
):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if tolerancia_minutos < 0 or tolerancia_minutos > 180:
        return RedirectResponse(
            url="/configuracion/asistencia",
            status_code=303
        )

    if not hora_entrada or not hora_cierre_entrada:
        return RedirectResponse(
            url="/configuracion/asistencia",
            status_code=303
        )

    activo_valor = activo == "1"

    with psycopg.connect(**DATABASE_CONFIG) as conexion:
        with conexion.cursor() as cursor:

            cursor.execute("""
                UPDATE configuracion_asistencia
                SET
                    hora_entrada = %s,
                    tolerancia_minutos = %s,
                    hora_cierre_entrada = %s,
                    activo = %s,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = 1;
            """, (
                hora_entrada,
                tolerancia_minutos,
                hora_cierre_entrada,
                activo_valor
            ))

        conexion.commit()

    return RedirectResponse(
        url="/configuracion/asistencia",
        status_code=303
    )

@app.get(
    "/configuracion/sistema",
    response_class=HTMLResponse
)
def configuracion_sistema(
    request: Request,
    alumnos_importados: int = 0,
    alumnos_omitidos: int = 0,
    grupos_importados: int = 0,
    respaldo_error: int = 0,
):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    configuracion = (
        obtener_configuracion_sistema()
    )

    return templates.TemplateResponse(
    	request=request,
    	name="configuracion_sistema.html",
    	context={
            "request": request,
            "configuracion_credencial": configuracion,
            "alumnos_importados": alumnos_importados,
            "alumnos_omitidos": alumnos_omitidos,
            "grupos_importados": grupos_importados,
            "respaldo_error": bool(respaldo_error),
    }
)


@app.post("/configuracion/sistema/importar-respaldo-alumnos")
async def importar_respaldo_alumnos_ruta(
    request: Request,
    archivo: UploadFile = File(...),
):
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/login", status_code=303)
    try:
        nombre_archivo = archivo.filename or "respaldo.sql"
        extension = Path(nombre_archivo).suffix.lower()
        if extension not in {".sql", ".backup", ".dump"}:
            raise ValueError("Formato de respaldo no compatible.")
        with tempfile.TemporaryDirectory(prefix="sicae_subir_respaldo_") as temporal:
            ruta_temporal = Path(temporal) / f"respaldo{extension}"
            total = 0
            with ruta_temporal.open("wb") as destino:
                while bloque := await archivo.read(1024 * 1024):
                    total += len(bloque)
                    if total > MAX_RESPALDO_BYTES:
                        raise ValueError("El respaldo supera el límite de 1 GB.")
                    destino.write(bloque)
            resultado = await run_in_threadpool(
                importar_alumnos_de_respaldo, ruta_temporal, nombre_archivo
            )
        return RedirectResponse(
            url=(
                "/configuracion/sistema?alumnos_importados="
                f"{resultado['alumnos_insertados']}&alumnos_omitidos="
                f"{resultado['alumnos_omitidos']}&grupos_importados="
                f"{resultado['grupos_importados']}"
            ),
            status_code=303,
        )
    except Exception as error:
        print("Error al importar respaldo de alumnos:", error)
        return RedirectResponse(url="/configuracion/sistema?respaldo_error=1", status_code=303)

# ============================================================
# GUARDAR CONFIGURACIÓN DEL SISTEMA
# ============================================================

@app.post(
    "/configuracion/sistema"
)
async def guardar_configuracion_sistema(

    request: Request,

    nombre_sistema:
        str = Form(...),

    subtitulo:
        str = Form(...),

    titulo_excel:
        str = Form(...),

    subtitulo_excel:
        str = Form(...),

    texto_bienvenida:
        str = Form(...),

    logo_excel:
        UploadFile | None = File(None),

    logo_login:
        UploadFile | None = File(None),

    color_principal:
        str = Form("#2563EB"),

    color_secundario:
        str = Form("#1E40AF"),

    color_fondo_login:
        str = Form("#F3F4F6"),

    color_texto_login:
        str = Form("#111827"),

    logo_tamano:
        int = Form(120)

):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    configuracion_actual = (
        obtener_configuracion_sistema()
    )

    nombre_logo = (
        configuracion_actual.get("logo_excel")
        if configuracion_actual
        else None
    )

    nombre_logo_login = (
        configuracion_actual.get("logo_login")
        if configuracion_actual
        else None
    )

    # ========================================================
    # GUARDAR NUEVO LOGO EXCEL
    # ========================================================

    if logo_excel and logo_excel.filename:

        extension = Path(
            logo_excel.filename
        ).suffix.lower()

        extensiones_permitidas = [
            ".png",
            ".jpg",
            ".jpeg"
        ]

        if extension in extensiones_permitidas:

            nombre_logo = (
                "logo_excel" +
                extension
            )

            ruta_logo = (
                UPLOADS_DIR /
                nombre_logo
            )

            contenido = await logo_excel.read()

            with open(
                ruta_logo,
                "wb"
            ) as archivo:

                archivo.write(
                    contenido
                )

    # ========================================================
    # GUARDAR LOGO DEL LOGIN
    # ========================================================

    if logo_login and logo_login.filename:

        extension_login = Path(
            logo_login.filename
        ).suffix.lower()

        extensiones_permitidas_login = [
            ".png",
            ".jpg",
            ".jpeg"
        ]

        if extension_login in extensiones_permitidas_login:

            nombre_logo_login = (
                "logo_login" +
                extension_login
            )

            ruta_logo_login = (
                UPLOADS_DIR /
                nombre_logo_login
            )

            contenido_login = await logo_login.read()

            with open(
                ruta_logo_login,
                "wb"
            ) as archivo:

                archivo.write(
                    contenido_login
                )

    # ========================================================
    # GUARDAR CONFIGURACIÓN
    # ========================================================

    actualizar_configuracion_sistema(

        nombre_sistema=
            nombre_sistema,

        subtitulo=
            subtitulo,

        titulo_excel=
            titulo_excel,

        subtitulo_excel=
            subtitulo_excel,

        texto_bienvenida=
            texto_bienvenida,

        logo_excel=
            nombre_logo,

        color_principal=
            color_principal,

        color_secundario=
            color_secundario,

        color_fondo_login=
            color_fondo_login,

        color_texto_login=
            color_texto_login,

        logo_login=
            nombre_logo_login,

        logo_tamano=
            logo_tamano

    )

    return RedirectResponse(

        url="/configuracion/sistema",

        status_code=303

    )

@app.post("/credencial/configuracion/subir-imagen")
async def subir_imagen_diseno_credencial(request: Request, imagen: UploadFile = File(...)):
    if not usuario_es_administrador(request):
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    extension = Path(imagen.filename or "").suffix.lower()
    if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
        return JSONResponse({"error": "Formato no permitido"}, status_code=400)
    contenido = await imagen.read(8 * 1024 * 1024 + 1)
    if not contenido or len(contenido) > 8 * 1024 * 1024:
        return JSONResponse({"error": "La imagen debe pesar menos de 8 MB"}, status_code=400)
    valido = (
        extension == ".png" and contenido.startswith(b"\x89PNG\r\n\x1a\n")
        or extension in {".jpg", ".jpeg"} and contenido.startswith(b"\xff\xd8\xff")
        or extension == ".webp" and contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP"
    )
    if not valido:
        return JSONResponse({"error": "El archivo no parece ser una imagen válida"}, status_code=400)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    nombre = "diseno_credencial_" + secrets.token_hex(12) + extension
    (UPLOADS_DIR / nombre).write_bytes(contenido)
    return JSONResponse({"filename": nombre, "url": "/static/uploads/" + nombre})


@app.post("/credencial/configuracion/subir-powerpoint")
async def subir_powerpoint_diseno_credencial(request: Request, presentacion: UploadFile = File(...)):
    if not usuario_es_administrador(request):
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    if Path(presentacion.filename or "").suffix.lower() != ".pptx":
        return JSONResponse({"error": "Sube una presentación .pptx"}, status_code=400)
    contenido = await presentacion.read(25 * 1024 * 1024 + 1)
    if not contenido or len(contenido) > 25 * 1024 * 1024:
        return JSONResponse({"error": "La presentación debe pesar menos de 25 MB"}, status_code=400)
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
            nombres = set(paquete.namelist())
            if "[Content_Types].xml" not in nombres or "ppt/presentation.xml" not in nombres:
                raise ValueError("El archivo no contiene una presentación PowerPoint válida.")
            if sum(info.file_size for info in paquete.infolist()) > 300 * 1024 * 1024:
                raise ValueError("La presentación tiene contenido descomprimido demasiado grande.")
    except (zipfile.BadZipFile, ValueError) as error:
        return JSONResponse({"error": str(error) or "El archivo PowerPoint está dañado."}, status_code=400)

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    identificador = secrets.token_hex(12)
    nombre_frente = "diseno_powerpoint_frente_" + identificador + ".png"
    nombre_reverso = "diseno_powerpoint_reverso_" + identificador + ".png"
    try:
        with tempfile.TemporaryDirectory(prefix="sicae-pptx-import-") as directorio:
            ruta_origen = Path(directorio) / "presentacion.pptx"
            ruta_frente = Path(directorio) / nombre_frente
            ruta_reverso = Path(directorio) / nombre_reverso
            ruta_origen.write_bytes(contenido)
            await run_in_threadpool(convertir_pptx_a_dos_png, ruta_origen, ruta_frente, ruta_reverso)
            if any(ruta.stat().st_size > 15 * 1024 * 1024 for ruta in (ruta_frente, ruta_reverso)):
                return JSONResponse({"error": "Una imagen resultante supera el tamaño permitido."}, status_code=400)
            (UPLOADS_DIR / nombre_frente).write_bytes(ruta_frente.read_bytes())
            (UPLOADS_DIR / nombre_reverso).write_bytes(ruta_reverso.read_bytes())
    except Exception as error:
        print("Error al importar diseño PowerPoint:", error)
        detalle = " ".join(str(error).split())[:500]
        return JSONResponse({
            "error": "No se pudieron convertir las dos diapositivas. "
            "Verifica que el PowerPoint tenga frente y reverso y que sea compatible. "
            f"Detalle: {detalle}"
        }, status_code=422)
    return JSONResponse({
        "frontFilename": nombre_frente,
        "frontUrl": "/static/uploads/" + nombre_frente,
        "backFilename": nombre_reverso,
        "backUrl": "/static/uploads/" + nombre_reverso,
    })


def _validar_layout_credencial(raw):
    """Valida posiciones tradicionales y elementos del editor libre."""
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(value, dict):
        return {}
    result = {}
    allowed = {"institucion", "titulo", "foto", "datos", "qr", "pie"}
    for key, point in value.items():
        if key not in allowed or not isinstance(point, dict):
            continue
        try:
            result[key] = {"x": max(-700, min(700, float(point.get("x", 0)))),
                           "y": max(-400, min(400, float(point.get("y", 0))))}
        except (TypeError, ValueError):
            continue
    def validar_lado(free):
        if not isinstance(free, dict):
            return None
        allowed_types = {"rect", "text", "logo", "photo", "image", "qr"}
        raw_elements = free.get("elements", [])
        if not isinstance(raw_elements, list):
            raw_elements = []

        def color_safe(raw, default):
            candidate = str(raw or default)
            return candidate if len(candidate) == 7 and candidate.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in candidate[1:]) else default

        elements = []
        for item in raw_elements[:100]:
            if not isinstance(item, dict) or item.get("type") not in allowed_types:
                continue
            try:
                elements.append({
                    "id": str(item.get("id", ""))[:60],
                    "type": item["type"],
                    "x": max(0, min(700, float(item.get("x", 0)))),
                    "y": max(0, min(400, float(item.get("y", 0)))),
                    "w": max(12, min(700, float(item.get("w", 120)))),
                    "h": max(12, min(400, float(item.get("h", 48)))),
                    "fill": color_safe(item.get("fill"), "#2563eb"),
                    "color": color_safe(item.get("color"), "#111827"),
                    "fontSize": max(8, min(80, float(item.get("fontSize", 18)))),
                    "text": str(item.get("text", ""))[:500],
                    "field": str(item.get("field", ""))[:60],
                    "bold": bool(item.get("bold", False)),
                    "fontFamily": item.get("fontFamily") if item.get("fontFamily") in {"Arial", "Times", "Courier"} else "Arial",
                    "image": Path(str(item.get("image", ""))).name[:120],
                    "fit": item.get("fit") if item.get("fit") in {"cover", "stretch"} else "contain",
                })
            except (TypeError, ValueError):
                continue
        return {
            "enabled": bool(free.get("enabled", False)),
            "background": color_safe(free.get("background"), "#ffffff"),
            "elements": elements,
        }

    free = value.get("_free")
    if isinstance(free, dict):
        clean_free = validar_lado(free)
        clean_back = validar_lado(free.get("back"))
        if clean_back is not None:
            clean_free["back"] = clean_back
        result["_free"] = clean_free
    return result


@app.get("/credencial/plantillas")
def api_listar_plantillas_credencial(request: Request, tipo: str = "alumno"):
    if not usuario_es_administrador(request):
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    if tipo not in ({"alumno", "personal", "todas"} | set(TIPOS_CREDENCIAL_ESPECIAL)):
        return JSONResponse({"error": "Tipo de plantilla no válido"}, status_code=400)
    try:
        return JSONResponse(listar_plantillas_credencial(tipo))
    except Exception as error:
        print("Error al listar plantillas de credencial:", error)
        return JSONResponse({"error": "No se pudieron cargar las plantillas"}, status_code=500)


@app.post("/credencial/plantillas")
def api_guardar_plantilla_credencial(
    request: Request,
    tipo: str = Form(...),
    nombre: str = Form(...),
    diseño_json: str = Form(...),
):
    if not usuario_es_administrador(request):
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    nombre = nombre.strip()[:100]
    if tipo not in ({"alumno", "personal"} | set(TIPOS_CREDENCIAL_ESPECIAL)) or not nombre:
        return JSONResponse({"error": "Escribe un nombre válido para la plantilla"}, status_code=400)
    diseño = _validar_layout_credencial(diseño_json).get("_free")
    if not diseño or not diseño.get("enabled"):
        return JSONResponse({"error": "Activa o carga un diseño personalizado antes de guardarlo"}, status_code=400)
    try:
        return JSONResponse(guardar_plantilla_credencial(tipo, nombre, diseño))
    except Exception as error:
        print("Error al guardar plantilla de credencial:", error)
        return JSONResponse({"error": "No se pudo guardar la plantilla"}, status_code=500)


@app.delete("/credencial/plantillas/{plantilla_id}")
def api_eliminar_plantilla_credencial(
    request: Request,
    plantilla_id: int,
    tipo: str = "alumno",
):
    if not usuario_es_administrador(request):
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    if tipo not in ({"alumno", "personal"} | set(TIPOS_CREDENCIAL_ESPECIAL)):
        return JSONResponse({"error": "Tipo de plantilla no válido"}, status_code=400)
    try:
        if not eliminar_plantilla_credencial(tipo, plantilla_id):
            return JSONResponse({"error": "No se encontró la plantilla"}, status_code=404)
        return JSONResponse({"ok": True})
    except Exception as error:
        print("Error al eliminar plantilla de credencial:", error)
        return JSONResponse({"error": "No se pudo eliminar la plantilla"}, status_code=500)


# ============================================================
# CONFIGURACIÓN DE CREDENCIAL
# ============================================================

@app.get(
    "/credencial/configuracion"
)
def configuracion_credencial(

    request: Request

):

    if not usuario_es_administrador(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )
    configuracion = (
  	obtener_configuracion_credencial()
)
    qr_preview = generar_qr_alumno("22015021")
    return templates.TemplateResponse(

        request=request,

        name="configuracion_credencial.html",

        context={

            "configuracion_credencial": configuracion,
            "configuracion": obtener_configuracion_sistema(),
            "qr_preview": qr_preview,

        }

    )


# ============================================================
# GUARDAR CONFIGURACIÓN DE CREDENCIAL
# ============================================================

@app.post(
    "/credencial/configuracion"
)
async def guardar_configuracion_credencial(

    request: Request,

    nombre_institucion:
        str = Form(...),

    subtitulo:
        str = Form(""),

    logo:
        UploadFile | None = File(None),

    color_principal:
        str = Form("#1e3a8a"),

    color_secundario:
        str = Form("#2563eb"),

    color_texto:
        str = Form("#111827"),

    fuente:
        str = Form("Arial"),

    tamano_nombre:
        int = Form(30),

    tamano_qr:
        int = Form(300),

    mostrar_foto:
        str | None = Form(None),

    mostrar_qr:
        str | None = Form(None),

    mostrar_matricula:
        str | None = Form(None),

    mostrar_grupo:
        str | None = Form(None),

    mostrar_grado:
        str | None = Form(None),

    mostrar_turno:
        str | None = Form(None),

    texto_pie:
        str = Form(""),

    layout_json:
        str = Form("{}")

):
    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )

    print("======================================")
    print("POST CONFIGURACION CREDENCIAL RECIBIDO")
    print("INSTITUCION:", nombre_institucion)
    print("SUBTITULO:", subtitulo)
    print("COLOR PRINCIPAL:", color_principal)
    print("COLOR SECUNDARIO:", color_secundario)
    print("COLOR TEXTO:", color_texto)
    print("FUENTE:", fuente)
    print("TAMAÑO:", tamano_nombre)
    print("FOTO:", mostrar_foto)
    print("QR:", mostrar_qr)
    print("MATRICULA:", mostrar_matricula)
    print("GRUPO:", mostrar_grupo)
    print("GRADO:", mostrar_grado)
    print("TURNO:", mostrar_turno)
    print("PIE:", texto_pie)
    print("======================================")
    configuracion_actual = (
        obtener_configuracion_credencial()
    )


    nombre_logo = (

        configuracion_actual.get(
            "logo"
        )

        if configuracion_actual
        else None

    )


    # ========================================================
    # LOGO
    # ========================================================

    if (
        logo is not None
        and logo.filename
    ):

        extension = Path(
            logo.filename
        ).suffix.lower()


        extensiones_permitidas = {

            ".jpg",
            ".jpeg",
            ".png",
            ".webp"

        }


        if extension in (
            extensiones_permitidas
        ):

            nombre_logo = (
                "logo_credencial"
                + extension
            )


            ruta_logo = (
                UPLOADS_DIR /
                nombre_logo
            )


            contenido = (
                await logo.read()
            )


            with open(
                ruta_logo,
                "wb"
            ) as archivo:

                archivo.write(
                    contenido
                )


    # ========================================================
    # CHECKBOXES
    # ========================================================

    foto_activa = (
        mostrar_foto is not None
    )

    qr_activo = (
        mostrar_qr is not None
    )

    matricula_activa = (
        mostrar_matricula is not None
    )

    grupo_activo = (
        mostrar_grupo is not None
    )

    grado_activo = (
        mostrar_grado is not None
    )

    turno_activo = (
        mostrar_turno is not None
    )


    actualizar_configuracion_credencial(

        nombre_institucion=
            nombre_institucion,

        subtitulo=
            subtitulo,

        logo=
            nombre_logo,

        color_principal=
            color_principal,

        color_secundario=
            color_secundario,

        color_texto=
            color_texto,

        fuente=
            fuente,

        tamano_nombre=
            tamano_nombre,

        tamano_qr=
            tamano_qr,


        mostrar_foto=
            foto_activa,

        mostrar_qr=
            qr_activo,

        mostrar_matricula=
            matricula_activa,

        mostrar_grupo=
            grupo_activo,

        mostrar_grado=
            grado_activo,

        mostrar_turno=
            turno_activo,

        texto_pie=texto_pie,

        layout=
            _validar_layout_credencial(layout_json),
    )


    return RedirectResponse(

        url="/credencial/configuracion",

        status_code=303

    )


# ============================================================
# CONFIGURACIÓN DE CREDENCIAL DEL PERSONAL
# ============================================================

@app.get(
    "/credencial/configuracion-personal"
)
def configuracion_credencial_personal(

    request: Request

):

    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/login",
            status_code=303
        )


    configuracion = (
        obtener_configuracion_credencial_personal()
    )

    qr_preview = generar_qr_personal("03")


    html_prueba = templates.get_template(
        "configuracion_credencial_personal.html"
    ).render(
        request=request,
        configuracion=configuracion,
        qr_preview=qr_preview,
    )


    return HTMLResponse(content=html_prueba, status_code=200)




# ============================================================
# GUARDAR CONFIGURACIÓN DE CREDENCIAL DEL PERSONAL
# ============================================================

@app.post(
    "/credencial/configuracion-personal"
)
async def guardar_configuracion_credencial_personal(

    request: Request,

    nombre_institucion: str = Form(...),
    subtitulo: str = Form(""),
    logo: UploadFile | None = File(None),

    color_principal: str = Form("#166534"),
    color_secundario: str = Form("#22c55e"),
    color_texto: str = Form("#111827"),

    fuente: str = Form("Arial"),
    tamano_nombre: int = Form(30),
    tamano_qr: int = Form(300),

    mostrar_foto: str | None = Form(None),
    mostrar_qr: str | None = Form(None),
    mostrar_matricula: str | None = Form(None),
    mostrar_tipo_personal: str | None = Form(None),
    mostrar_cargo: str | None = Form(None),
    mostrar_area: str | None = Form(None),
    mostrar_correo: str | None = Form(None),
    mostrar_telefono: str | None = Form(None),

    texto_pie: str = Form(""),
    layout_json: str = Form("{}")
):
    if not usuario_es_administrador(request):

        return RedirectResponse(
            url="/",
            status_code=303
        )


    configuracion_actual = (
        obtener_configuracion_credencial_personal()
    )

    nombre_logo = (
        configuracion_actual.get("logo")
        if configuracion_actual
        else None
    )

    # ========================================================
    # LOGO
    # ========================================================

    if logo is not None and logo.filename:

        extension = Path(
            logo.filename
        ).suffix.lower()

        extensiones_permitidas = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        }

        if extension in extensiones_permitidas:

            nombre_logo = (
                "logo_credencial_personal"
                + extension
            )

            ruta_logo = (
                UPLOADS_DIR /
                nombre_logo
            )

            contenido = await logo.read()

            with open(
                ruta_logo,
                "wb"
            ) as archivo_logo:

                archivo_logo.write(
                    contenido
                )

    # ========================================================
    # CHECKBOXES
    # ========================================================

    foto_activa = mostrar_foto is not None
    qr_activo = mostrar_qr is not None
    matricula_activa = mostrar_matricula is not None
    tipo_personal_activo = mostrar_tipo_personal is not None
    cargo_activo = mostrar_cargo is not None
    area_activa = mostrar_area is not None
    correo_activo = mostrar_correo is not None
    telefono_activo = mostrar_telefono is not None

    actualizar_configuracion_credencial_personal(

        nombre_institucion=nombre_institucion,
        subtitulo=subtitulo,
        logo=nombre_logo,

        color_principal=color_principal,
        color_secundario=color_secundario,
        color_texto=color_texto,

        fuente=fuente,
        tamano_nombre=tamano_nombre,
        tamano_qr=tamano_qr,

        mostrar_foto=foto_activa,
        mostrar_qr=qr_activo,
        mostrar_matricula=matricula_activa,
        mostrar_tipo_personal=tipo_personal_activo,
        mostrar_cargo=cargo_activo,
        mostrar_area=area_activa,
        mostrar_correo=correo_activo,
        mostrar_telefono=telefono_activo,

        texto_pie=texto_pie,
        layout=_validar_layout_credencial(layout_json),
    )

    return RedirectResponse(
        url="/credencial/configuracion-personal",
        status_code=303
    )

@app.get("/escaner")
def escaner(
    request: Request
):

    if not usuario_autenticado(request):
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(

        request=request,

        name="escaner.html"

    )


@app.get("/eventos-fuera")
def pagina_eventos_fuera(request: Request, error: int = 0, correo_guardado: int = 0, correo_error: int = 0, finalizado: int = 0, correos_fallidos: int = 0, evento_eliminado: int = 0):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if request.session.get("rol") == "docente":
        return RedirectResponse(url="/asistencia-maestro", status_code=303)
    grupos = [
        {
            "id": fila["id"] if isinstance(fila, dict) else fila[0],
            "nombre_grupo": fila["nombre_grupo"] if isinstance(fila, dict) else fila[1],
            "nombre": fila["nombre"] if isinstance(fila, dict) else fila[2],
            "grado": fila["grado"] if isinstance(fila, dict) else fila[3],
            "turno": fila["turno"] if isinstance(fila, dict) else fila[4],
        }
        for fila in obtener_grupos()
    ]
    return templates.TemplateResponse(
        request=request,
        name="eventos_fuera.html",
        context={
            "configuracion": obtener_configuracion_sistema(),
            "grupos": grupos,
            "eventos": listar_eventos_fuera(),
            "error": bool(error),
            "correo_config": obtener_configuracion_notificaciones_eventos(),
            "correo_guardado": bool(correo_guardado),
            "correo_error": bool(correo_error),
            "evento_finalizado": bool(finalizado),
            "correos_fallidos": correos_fallidos,
            "evento_eliminado": bool(evento_eliminado),
        },
    )


@app.post("/eventos-fuera/notificaciones")
def guardar_notificaciones_eventos(
    request: Request,
    activa: bool = Form(False),
    asunto: str = Form(...),
    mensaje: str = Form(...),
):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    try:
        guardar_configuracion_notificaciones_eventos(activa, asunto, mensaje)
        return RedirectResponse(url="/eventos-fuera?correo_guardado=1", status_code=303)
    except Exception as error:
        print("Error al guardar notificaciones de eventos:", error)
        return RedirectResponse(url="/eventos-fuera?correo_error=1", status_code=303)


@app.post("/eventos-fuera/crear")
def crear_evento_fuera_plantel(
    request: Request,
    nombre: str = Form(...),
    fecha_evento: date = Form(...),
    lugar: str = Form(""),
    notas: str = Form(""),
    grupos_ids: list[int] = Form([]),
):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    try:
        evento_id = crear_evento_fuera(nombre, fecha_evento, lugar, notas, grupos_ids)
        return RedirectResponse(url=f"/eventos-fuera/{evento_id}/asistencia", status_code=303)
    except Exception as error:
        print("Error al crear evento fuera del plantel:", error)
        return RedirectResponse(url="/eventos-fuera?error=1", status_code=303)


@app.post("/eventos-fuera/{evento_id}/estado")
def actualizar_estado_evento_fuera(
    request: Request,
    evento_id: int,
    activo: bool = Form(...),
):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    cambiar_estado_evento_fuera(evento_id, activo)
    return RedirectResponse(url="/eventos-fuera", status_code=303)


@app.post("/eventos-fuera/{evento_id}/eliminar")
def eliminar_evento_fuera_plantel(request: Request, evento_id: int):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    eliminado = eliminar_evento_fuera(evento_id)
    return RedirectResponse(
        url=f"/eventos-fuera?evento_eliminado={1 if eliminado else 0}",
        status_code=303,
    )


@app.post("/eventos-fuera/{evento_id}/finalizar")
def finalizar_evento_fuera_plantel(request: Request, evento_id: int):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    datos, familias = finalizar_evento_fuera(evento_id)
    if datos is None:
        return RedirectResponse(url="/eventos-fuera", status_code=303)
    fallidos = sum(
        not enviar_notificacion_finalizacion_evento(familia["correo"], familia["nombre"], datos)[0]
        for familia in familias
    )
    return RedirectResponse(url=f"/eventos-fuera?finalizado=1&correos_fallidos={fallidos}", status_code=303)


@app.get("/eventos-fuera/{evento_id}/asistencia")
def pagina_asistencia_evento_fuera(request: Request, evento_id: int):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_puede_operar(request):
        return RedirectResponse(url="/", status_code=303)
    evento = obtener_evento_fuera(evento_id)
    if evento is None:
        return RedirectResponse(url="/eventos-fuera", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="asistencia_evento_fuera.html",
        context={
            "configuracion": obtener_configuracion_sistema(),
            "evento": evento,
            "asistencias": listar_asistencias_evento_fuera(evento_id),
        },
    )


@app.post("/api/eventos-fuera/{evento_id}/asistencia")
def api_registrar_asistencia_evento_fuera(request: Request, evento_id: int, payload: dict):
    if not usuario_autenticado(request):
        return JSONResponse({"ok": False, "mensaje": "La sesión expiró. Inicia sesión de nuevo."}, status_code=401)
    if not usuario_puede_operar(request):
        return JSONResponse({"ok": False, "mensaje": "No tienes permiso para registrar asistencia a eventos."}, status_code=403)
    try:
        matricula = str(payload.get("matricula") or "").strip()
        grupo_payload = payload.get("grupo_id")
        grupo_id = None if grupo_payload in (None, "", "todos") else int(grupo_payload)
        if not matricula:
            return JSONResponse({"ok": False, "mensaje": "No se recibió la matrícula."}, status_code=400)
        resultado = registrar_asistencia_evento_fuera(evento_id, grupo_id, matricula)
        if resultado.get("ok") and resultado.get("estado") == "registrado":
            correo_enviado, mensaje_correo = enviar_notificacion_asistencia_evento(
                resultado.get("correo"),
                {
                    "nombre": resultado.get("nombre", ""),
                    "matricula": resultado.get("matricula", ""),
                    "evento": resultado.get("evento", ""),
                    "fecha": resultado.get("fecha_evento", ""),
                    "hora": resultado.get("hora", ""),
                    "grupo": resultado.get("grupo", ""),
                    "lugar": resultado.get("lugar", ""),
                },
            )
            resultado["correo_enviado"] = correo_enviado
            if mensaje_correo:
                resultado["mensaje_correo"] = mensaje_correo
        return JSONResponse(resultado)
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "mensaje": "Selecciona un grupo válido y vuelve a escanear."}, status_code=400)
    except Exception as error:
        print("Error al registrar asistencia de evento:", error)
        return JSONResponse({"ok": False, "mensaje": "No se pudo registrar la asistencia."}, status_code=500)


@app.get("/clases")
def pagina_horario_clases(request: Request, guardado: int = 0, error: int = 0, grupo_id: int = 0, detalle: str = "", config_guardada: int = 0, config_error: int = 0):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="horario_clases.html",
        context={
            "configuracion": obtener_configuracion_sistema(),
            "grupos": obtener_grupos(),
            "maestros": obtener_personal_por_tipo("Docente"),
            "clases": listar_clases_horario(),
            "dias": DIAS_SEMANA,
            "grupo_seleccionado": grupo_id,
            "configuracion_tablas": obtener_configuracion_tablas(),
            "guardado": guardado,
            "error": bool(error),
            "detalle_error": detalle,
            "config_guardada": bool(config_guardada),
            "config_error": bool(config_error),
        },
    )


@app.get("/asistencia-maestro")
def pagina_asistencia_maestro(request: Request, mensaje: str = ""):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if request.session.get("rol") != "docente":
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="asistencia_maestro.html",
        context={
            "configuracion": obtener_configuracion_sistema(),
            "clases": listar_clases_docente(request.session["usuario_id"]),
            "hoy": date.today(),
            "dia_hoy": date.today().weekday(),
            "nombre": request.session.get("nombre", "Docente"),
            "mensaje": mensaje,
        },
    )


@app.post("/clases/{clase_id}/asistencia/iniciar")
def iniciar_asistencia_clase_ruta(request: Request, clase_id: int):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if request.session.get("rol") not in ("docente", "administrador"):
        return RedirectResponse(url="/", status_code=303)
    resultado = iniciar_sesion_asistencia(
        clase_id, request.session["usuario_id"], usuario_es_administrador(request)
    )
    if not resultado.get("ok"):
        destino = "/asistencia-maestro" if request.session.get("rol") == "docente" else "/clases"
        return RedirectResponse(url=f"{destino}?mensaje=sin_acceso", status_code=303)
    return RedirectResponse(url=f"/clases/asistencia/{resultado['sesion_id']}", status_code=303)


@app.get("/clases/asistencia/{sesion_id}")
def pagina_asistencia_clase(request: Request, sesion_id: int):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if request.session.get("rol") not in ("docente", "administrador"):
        return RedirectResponse(url="/", status_code=303)
    administrador = usuario_es_administrador(request)
    sesion = obtener_sesion_asistencia(sesion_id, request.session["usuario_id"], administrador)
    if not sesion:
        return RedirectResponse(url="/asistencia-maestro", status_code=303)
    registros = listar_registros_sesion(sesion_id)
    return templates.TemplateResponse(
        request=request,
        name="asistencia_clase.html",
        context={
            "configuracion": obtener_configuracion_sistema(),
            "sesion": sesion,
            "registros": registros,
            "presentes": sum(r["estado"] in ("presente", "retardo") for r in registros),
            "volver": "/" if administrador else "/asistencia-maestro",
        },
    )


@app.post("/clases/asistencia/{sesion_id}/cerrar")
def cerrar_asistencia_clase_ruta(request: Request, sesion_id: int):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if request.session.get("rol") not in ("docente", "administrador"):
        return RedirectResponse(url="/", status_code=303)
    cerrar_sesion_asistencia(sesion_id, request.session["usuario_id"], usuario_es_administrador(request))
    return RedirectResponse(url=f"/clases/asistencia/{sesion_id}", status_code=303)


@app.post("/api/clases/asistencia/{sesion_id}")
def api_registrar_asistencia_clase(request: Request, sesion_id: int, payload: dict):
    if not usuario_autenticado(request):
        return JSONResponse({"ok": False, "mensaje": "La sesión expiró. Inicia sesión de nuevo."}, status_code=401)
    if request.session.get("rol") not in ("docente", "administrador"):
        return JSONResponse({"ok": False, "mensaje": "No tienes acceso a esta función."}, status_code=403)
    try:
        resultado = registrar_asistencia_clase(
            sesion_id,
            request.session["usuario_id"],
            str(payload.get("matricula") or "").strip(),
            str(payload.get("estado") or "presente"),
            usuario_es_administrador(request),
        )
        return JSONResponse(resultado, status_code=200 if resultado.get("ok") else 400)
    except Exception as error:
        print("Error al registrar asistencia de clase:", error)
        return JSONResponse({"ok": False, "mensaje": "No se pudo registrar la asistencia."}, status_code=500)


@app.post("/clases/crear")
def crear_clase_horario_ruta(
    request: Request,
    grupo_id: int = Form(...),
    materia: str = Form(...),
    personal_id: int | None = Form(None),
    celdas_json: str = Form("[]"),
    aula: str = Form(""),
):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    try:
        celdas = json.loads(celdas_json)
        if not isinstance(celdas, list) or any(not isinstance(celda, dict) for celda in celdas):
            raise ValueError("La selección de celdas no es válida.")
        crear_clases_en_celdas(grupo_id, materia, personal_id, celdas, aula)
        return RedirectResponse(url=f"/clases?guardado={len(celdas)}&grupo_id={grupo_id}", status_code=303)
    except ValueError as error:
        detalle = quote(str(error))
        return RedirectResponse(url=f"/clases?error=1&grupo_id={grupo_id}&detalle={detalle}", status_code=303)
    except Exception as error:
        print("Error al guardar horario de clase:", error)
        return RedirectResponse(url=f"/clases?error=1&grupo_id={grupo_id}", status_code=303)


@app.post("/clases/configuracion-tabla")
def guardar_configuracion_tabla_ruta(
    request: Request,
    grupo_id: int = Form(...),
    hora_inicio: time = Form(...),
    minutos_por_celda: int = Form(...),
    cantidad_celdas: int = Form(...),
):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    try:
        guardar_configuracion_tabla(grupo_id, hora_inicio, minutos_por_celda, cantidad_celdas)
        return RedirectResponse(url=f"/clases?config_guardada=1&grupo_id={grupo_id}", status_code=303)
    except Exception as error:
        print("Error al guardar configuración de tabla:", error)
        return RedirectResponse(url=f"/clases?config_error=1&grupo_id={grupo_id}", status_code=303)


@app.post("/clases/{clase_id}/eliminar")
def eliminar_clase_horario_ruta(request: Request, clase_id: int, grupo_id: int = Form(0)):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    if not usuario_es_administrador(request):
        return RedirectResponse(url="/", status_code=303)
    eliminar_clase_horario(clase_id)
    return RedirectResponse(url=f"/clases?grupo_id={grupo_id}", status_code=303)


# ============================================================
# API DEL ESCÁNER
# ============================================================

@app.post("/api/escaner")
def registrar_escaneo(
    request: Request,
    payload: dict,
    background_tasks: BackgroundTasks,
):

    if not usuario_puede_operar(request):
        return JSONResponse({"ok": False, "mensaje": "No tienes permiso para registrar accesos."}, status_code=403)

    matricula = str(

        payload.get(
            "matricula",
            ""
        )

    ).strip()
    # Algunos lectores QR añaden caracteres de control al final; Excel también
    # puede importar una matrícula numérica como "12345.0". Conservamos el
    # valor original para la búsqueda exacta y limpiamos solo controles.
    matricula = "".join(caracter for caracter in matricula if caracter.isprintable()).strip()

    movimiento_solicitado = str(payload.get("movimiento") or "AUTO").strip().upper()
    if movimiento_solicitado not in {"AUTO", "ENTRADA", "SALIDA"}:
        return JSONResponse({"ok": False, "mensaje": "Selecciona entrada, salida o modo automático."}, status_code=400)
    registrado_por = request.session.get("nombre") or request.session.get("usuario") or "Operador"


    if not matricula:

        return {

            "ok": False,

            "mensaje":
                "No se recibió una matrícula."

        }

    if matricula.startswith("SICAE-ESPECIAL:"):
        referencia = matricula.split(":", 1)[1]
        try:
            resultado_especial = registrar_acceso_credencial_especial(
                referencia,
                movimiento_solicitado,
                registrado_por,
            )
            if not resultado_especial:
                return JSONResponse(
                    {"ok": False, "mensaje": "La credencial no existe o está inactiva."},
                    status_code=404,
                )
            credencial = resultado_especial["credencial"]
            nombre_especial = credencial["nombre_completo"]
            for destino in credencial["correos"]:
                background_tasks.add_task(
                    enviar_notificacion_credencial_especial,
                    destino,
                    nombre_especial,
                    credencial["etiqueta_tipo"],
                    credencial["codigo"],
                    resultado_especial["movimiento"],
                    resultado_especial["fecha"].strftime("%d/%m/%Y"),
                    resultado_especial["hora"].strftime("%H:%M:%S"),
                    credencial.get("cargo"),
                    credencial.get("organizacion"),
                )
            return {
                "ok": True,
                "mensaje": f"{resultado_especial['movimiento']} registrada correctamente.",
                "movimiento": resultado_especial["movimiento"],
                "fecha": str(resultado_especial["fecha"]),
                "hora": str(resultado_especial["hora"])[:8],
                "estado_asistencia": None,
                "alumno": {
                    "id": credencial["id"],
                    "matricula": credencial["codigo"],
                    "nombre": nombre_especial,
                    "foto": credencial.get("foto"),
                    "grupo": credencial["etiqueta_tipo"],
                    "turno": credencial.get("cargo") or credencial.get("organizacion") or "",
                },
            }
        except Exception as error:
            print("Error al registrar QR de credencial especial:", error)
            return JSONResponse(
                {"ok": False, "mensaje": "No se pudo registrar esta credencial."},
                status_code=500,
            )


    try:

        with psycopg.connect(
            **DATABASE_CONFIG
        ) as conexion:

            with conexion.cursor() as cursor:

                # ====================================================
                # BUSCAR ALUMNO
                # ====================================================

                cursor.execute("""

                    SELECT

                        a.id,

                        a.matricula,

                        a.nombre,

                        a.apellido_paterno,

                        a.apellido_materno,

                        a.correo,

                        a.foto,

                        g.nombre_grupo,

                        g.grado,

                        g.nombre AS grupo_nombre,

                        g.turno

                    FROM alumnos a

                    LEFT JOIN grupos g

                        ON a.grupo_id = g.id

                    WHERE
                        a.activo = TRUE
                        AND (
                            a.matricula = %s
                            OR upper(btrim(a.matricula)) = upper(btrim(%s))
                            OR regexp_replace(upper(btrim(a.matricula)), '\\.0+$', '') =
                               regexp_replace(upper(btrim(%s)), '\\.0+$', '')
                        )
                    ORDER BY CASE WHEN a.matricula = %s THEN 0 ELSE 1 END
                    LIMIT 1;

                """, (matricula, matricula, matricula, matricula))


                fila = cursor.fetchone()


                if fila is None:

                    return {

                        "ok": False,

                        "mensaje":
                            "Alumno no encontrado o inactivo.",

                        "matricula":
                            matricula

                    }


                alumno = {

                    "id":
                        fila[0],

                    "matricula":
                        fila[1],

                    "nombre":
                        fila[2],

                    "apellido_paterno":
                        fila[3],

                    "apellido_materno":
                        fila[4],

                    "correo":
                        fila[5],

                    "foto":
                        fila[6],

                    "nombre_grupo":
                        fila[7],

                    "grado":
                        fila[8],

                    "grupo_nombre":
                        fila[9],

                    "turno":
                        fila[10]

                }


                # ====================================================
                # ÚLTIMO MOVIMIENTO
                # ====================================================

                cursor.execute("""
                    SELECT
                        (SELECT movimiento
                         FROM accesos
                         WHERE alumno_id = %s AND fecha = CURRENT_DATE
                         ORDER BY hora DESC, id DESC
                         LIMIT 1),
                        EXISTS (
                            SELECT 1
                            FROM accesos
                            WHERE alumno_id = %s
                              AND fecha = CURRENT_DATE
                              AND movimiento = 'ENTRADA'
                        );
                """, (alumno["id"], alumno["id"]))
                ultimo_movimiento, tiene_entrada_hoy = cursor.fetchone()
                primera_entrada_hoy = not tiene_entrada_hoy


                # ====================================================
                # DETERMINAR MOVIMIENTO
                # ====================================================

                if movimiento_solicitado in {"ENTRADA", "SALIDA"}:
                    movimiento = movimiento_solicitado
                elif (

                    ultimo_movimiento is None
                    or ultimo_movimiento == "SALIDA"

                ):

                    movimiento = (
                        "ENTRADA"
                    )

                else:

                    movimiento = (
                        "SALIDA"
                    )


                # ====================================================
                # REGISTRAR ACCESO
                # ====================================================

                cursor.execute("""

                    INSERT INTO accesos (

                        alumno_id,
                        fecha,
                        hora,
                        movimiento,
                        registrado_por

                    )

                    VALUES (

                        %s,
                        CURRENT_DATE,
                        CURRENT_TIME,
                        %s,
                        %s

                    )

                    RETURNING

                        fecha,
                        hora;

                """, (

                    alumno["id"],
                    movimiento,
                    registrado_por

                ))


                fecha, hora = (
                    cursor.fetchone()
                )

                estado_asistencia = None

                if movimiento == "ENTRADA" and primera_entrada_hoy:
                    cursor.execute("""
                        SELECT
                            activo,
                            CASE
                                WHEN %s::time <= hora_entrada
                                    + (tolerancia_minutos * INTERVAL '1 minute')
                                THEN 'PUNTUAL'
                                ELSE 'RETARDO'
                            END
                        FROM configuracion_asistencia
                        WHERE id = 1;
                    """, (hora,))

                    configuracion_asistencia = cursor.fetchone()

                    if (
                        configuracion_asistencia
                        and configuracion_asistencia[0]
                    ):
                        estado_asistencia = configuracion_asistencia[1]


            conexion.commit()


        # ========================================================
        # NOTIFICACION POR CORREO
        # ========================================================

        background_tasks.add_task(
            enviar_notificacion_acceso,
            alumno.get("correo"),
            nombre_completo=" ".join(
                parte
                for parte in [
                    alumno.get("nombre"),
                    alumno.get("apellido_paterno"),
                    alumno.get("apellido_materno")
                ]
                if parte
            ),
            movimiento=movimiento,
            fecha=fecha,
            hora=hora,
            matricula=alumno.get("matricula"),
            grado=alumno.get("grado"),
            grupo=alumno.get("grupo_nombre"),
            turno=alumno.get("turno")
        )



        # ========================================================
        # NOMBRE COMPLETO
        # ========================================================

        nombre_completo = " ".join(

            parte

            for parte in [

                alumno.get(
                    "nombre"
                ),

                alumno.get(
                    "apellido_paterno"
                ),

                alumno.get(
                    "apellido_materno"
                )

            ]

            if parte

        )


        # ========================================================
        # GRUPO
        # ========================================================

        grado = alumno.get(
            "grado"
        )

        nombre_grupo = alumno.get(
            "grupo_nombre"
        )


        if grado and nombre_grupo:

            grupo = (
                f"{grado}° "
                f"{nombre_grupo}"
            )

        else:

            grupo = (
                alumno.get(
                    "nombre_grupo"
                )
                or ""
            )


        # ========================================================
        # RESPUESTA
        # ========================================================

        return {

            "ok":
                True,

            "mensaje":
                (
                    f"{movimiento} "
                    f"registrada correctamente."
                ),

            "movimiento":
                movimiento,

            "fecha":
                str(fecha),

            "hora":
                str(hora)[:8],

            "estado_asistencia":
                estado_asistencia,

            "alumno": {

                "id":
                    alumno["id"],

                "matricula":
                    alumno["matricula"],

                "nombre":
                    nombre_completo,

                "foto":
                    alumno.get(
                        "foto"
                    ),

                "grupo":
                    grupo,

                "turno":
                    alumno.get(
                        "turno"
                    ) or ""

            }

        }


    except Exception as error:

        print()
        print("==========================================")
        print("ERROR EN ESCÁNER")
        print(error)
        print("==========================================")
        print()


        return {

            "ok":
                False,

            "mensaje":
                (
                    "Ocurrió un error "
                    "al registrar la asistencia."
                )

        }


# ============================================================
# ESTADO DEL SISTEMA
# ============================================================

@app.get("/api/estado")
def estado():

    return {

        "sistema":
            "SICAE WEB",

        "estado":
            "funcionando"

    }


# ============================================================
# EJECUTAR SERVIDOR
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "main:app",

        host="127.0.0.1",

        port=8000,

        reload=True

    )


























































































