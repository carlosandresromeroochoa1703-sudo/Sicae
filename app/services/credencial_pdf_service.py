from pathlib import Path
from contextlib import contextmanager

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.pagesizes import letter

from app.services.qr_service import generar_qr_alumno, generar_qr_personal




@contextmanager
def _mover_bloque_credencial(pdf, configuracion, clave, escala_x, escala_y):
    punto = (configuracion or {}).get("layout") or {}
    punto = punto.get(clave) or {}
    try:
        dx, dy = float(punto.get("x", 0)), float(punto.get("y", 0))
    except (TypeError, ValueError, AttributeError):
        dx = dy = 0
    pdf.saveState()
    pdf.translate(dx * escala_x, -dy * escala_y)
    try:
        yield
    finally:
        pdf.restoreState()


# ============================================================
# RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_DIR = BASE_DIR / "static"

UPLOADS_DIR = STATIC_DIR / "uploads"

REPORTES_DIR = STATIC_DIR / "reportes"


UPLOADS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

REPORTES_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# TAMAÑO FÍSICO DE LA CREDENCIAL
# ESTÁNDAR CR80 / ID-1
# ============================================================

CREDENCIAL_ANCHO = 85.60 / 25.4 * 72

CREDENCIAL_ALTO = 53.98 / 25.4 * 72

# ============================================================
# HOJA
# ============================================================

HOJA_ANCHO, HOJA_ALTO = letter


# ============================================================
# DISEÑO ORIGINAL DEL HTML
# ============================================================

HTML_ANCHO = 700

HTML_ALTO = 400


ESCALA_UNIFORME = min(
    CREDENCIAL_ANCHO / HTML_ANCHO,
    CREDENCIAL_ALTO / HTML_ALTO
)

ESCALA_X = ESCALA_UNIFORME

ESCALA_Y = ESCALA_UNIFORME


def sx(valor):
    return valor * ESCALA_X


def sy(valor):
    return valor * ESCALA_Y


# ============================================================
# FUENTES
# ============================================================

FUENTES_PERMITIDAS = {

    "Arial": "Helvetica",

    "Helvetica": "Helvetica",

    "Times": "Times-Roman",

    "Times-Roman": "Times-Roman",

    "Courier": "Courier",

}


FUENTES_NEGRITA = {

    "Arial": "Helvetica-Bold",

    "Helvetica": "Helvetica-Bold",

    "Times": "Times-Bold",

    "Times-Roman": "Times-Bold",

    "Courier": "Courier-Bold",

}


def obtener_fuente(nombre):

    if not nombre:
        return "Helvetica"

    return FUENTES_PERMITIDAS.get(
        nombre,
        "Helvetica"
    )


def obtener_fuente_negrita(nombre):

    if not nombre:
        return "Helvetica-Bold"

    return FUENTES_NEGRITA.get(
        nombre,
        "Helvetica-Bold"
    )


# ============================================================
# COLOR HEX
# ============================================================

def color_hex(
    valor,
    color_defecto="#1e3a8a"
):

    if not valor:
        valor = color_defecto

    try:

        valor = str(valor).replace(
            "#",
            ""
        )

        if len(valor) != 6:
            raise ValueError

        rojo = int(
            valor[0:2],
            16
        )

        verde = int(
            valor[2:4],
            16
        )

        azul = int(
            valor[4:6],
            16
        )

        return colors.Color(
            rojo / 255,
            verde / 255,
            azul / 255
        )

    except Exception:

        return colors.HexColor(
            color_defecto
        )


# ============================================================
# BUSCAR IMAGEN
# ============================================================

def buscar_imagen(nombre):

    if not nombre:
        return None

    ruta = UPLOADS_DIR / Path(str(nombre)).name

    if ruta.exists():
        return ruta

    return None


def buscar_o_generar_qr(entidad, personal=False):
    """Devuelve un QR existente o lo reconstruye desde su identificador."""
    ruta = buscar_imagen(entidad.get("qr"))
    if ruta:
        return ruta

    identificador = entidad.get("numero_empleado" if personal else "matricula")
    if not identificador:
        return None

    generador = generar_qr_personal if personal else generar_qr_alumno
    try:
        return buscar_imagen(generador(str(identificador)))
    except Exception as error:
        print("ERROR GENERANDO QR:", identificador, error)
        return None


# ============================================================
# IMAGEN CONTAIN
# ============================================================

def dibujar_contain(
    pdf,
    ruta,
    x,
    y,
    ancho,
    alto
):

    if not ruta:
        return False

    try:

        imagen = ImageReader(
            str(ruta)
        )

        ancho_original, alto_original = (
            imagen.getSize()
        )

        if (
            ancho_original <= 0
            or alto_original <= 0
        ):
            return False

        escala = min(
            ancho / ancho_original,
            alto / alto_original
        )

        nuevo_ancho = (
            ancho_original * escala
        )

        nuevo_alto = (
            alto_original * escala
        )

        nuevo_x = (
            x +
            (ancho - nuevo_ancho) / 2
        )

        nuevo_y = (
            y +
            (alto - nuevo_alto) / 2
        )

        pdf.drawImage(

            imagen,

            nuevo_x,
            nuevo_y,

            width=nuevo_ancho,
            height=nuevo_alto,

            preserveAspectRatio=True,

            mask="auto"

        )

        return True

    except Exception as error:

        print(
            "ERROR DIBUJANDO IMAGEN:",
            error
        )

        return False


# ============================================================
# IMAGEN COVER
# ============================================================

def dibujar_cover(
    pdf,
    ruta,
    x,
    y,
    ancho,
    alto
):

    if not ruta:
        return False



    try:

        imagen = ImageReader(
            str(ruta)
        )

        ancho_original, alto_original = (
            imagen.getSize()
        )

        if (
            ancho_original <= 0
            or alto_original <= 0
        ):
            return False

        escala = max(
            ancho / ancho_original,
            alto / alto_original
        )

        nuevo_ancho = (
            ancho_original * escala
        )

        nuevo_alto = (
            alto_original * escala
        )

        nuevo_x = (
            x +
            (ancho - nuevo_ancho) / 2
        )

        nuevo_y = (
            y +
            (alto - nuevo_alto) / 2
        )

        pdf.saveState()

        ruta_clip = pdf.beginPath()

        ruta_clip.rect(
            x,
            y,
            ancho,
            alto
        )

        pdf.clipPath(
            ruta_clip,
            stroke=0,
            fill=0
        )

        pdf.drawImage(

            imagen,

            nuevo_x,
            nuevo_y,

            width=nuevo_ancho,
            height=nuevo_alto,

            preserveAspectRatio=True,

            mask="auto"

        )

        pdf.restoreState()

        return True

    except Exception as error:

        print(
            "ERROR DIBUJANDO FOTO:",
            error
        )

        return False


def dibujar_silueta_foto(pdf, x, y, ancho, alto, borde=None):
    """Dibuja el mismo marcador neutro de fotografía que usa la vista previa."""
    pdf.saveState()
    pdf.setFillColor(colors.HexColor("#f1f5f9"))
    pdf.roundRect(x, y, ancho, alto, min(ancho, alto) * 0.08, fill=1, stroke=0)
    centro_x = x + ancho / 2
    color_silueta = colors.HexColor("#0f766e")
    pdf.setFillColor(color_silueta)
    pdf.circle(centro_x, y + alto * 0.68, min(ancho, alto) * 0.14, fill=1, stroke=0)
    figura = pdf.beginPath()
    figura.moveTo(x + ancho * 0.18, y + alto * 0.10)
    figura.curveTo(x + ancho * 0.20, y + alto * 0.36, x + ancho * 0.34, y + alto * 0.48, centro_x, y + alto * 0.48)
    figura.curveTo(x + ancho * 0.66, y + alto * 0.48, x + ancho * 0.80, y + alto * 0.36, x + ancho * 0.82, y + alto * 0.10)
    figura.close()
    pdf.drawPath(figura, fill=1, stroke=0)
    if borde:
        pdf.setStrokeColor(borde)
        pdf.setLineWidth(1)
        pdf.roundRect(x, y, ancho, alto, min(ancho, alto) * 0.08, fill=0, stroke=1)
    pdf.restoreState()


# ============================================================
# AJUSTAR TEXTO
# ============================================================

def ajustar_texto(
    texto,
    fuente,
    tamano,
    ancho_maximo
):

    texto = str(
        texto or ""
    ).strip()

    if not texto:
        return ""

    if stringWidth(
        texto,
        fuente,
        tamano
    ) <= ancho_maximo:

        return texto

    while (
        texto
        and
        stringWidth(
            texto + "...",
            fuente,
            tamano
        ) > ancho_maximo
    ):

        texto = texto[:-1]

    return texto.rstrip() + "..."


def dividir_texto(texto, fuente, tamano, ancho_maximo):
    """Envuelve el texto en líneas sin descartar palabras ni caracteres."""
    palabras = str(texto or "").split()
    if not palabras:
        return [""]
    lineas = []
    linea = ""
    for palabra in palabras:
        candidata = f"{linea} {palabra}".strip()
        if linea and stringWidth(candidata, fuente, tamano) <= ancho_maximo:
            linea = candidata
            continue
        if not linea and stringWidth(palabra, fuente, tamano) > ancho_maximo:
            fragmento = ""
            for caracter in palabra:
                if fragmento and stringWidth(fragmento + caracter, fuente, tamano) > ancho_maximo:
                    lineas.append(fragmento)
                    fragmento = caracter
                else:
                    fragmento += caracter
            linea = fragmento
            continue
        if linea:
            lineas.append(linea)
        linea = palabra
    if linea:
        lineas.append(linea)
    return lineas


# ============================================================
# DISTRIBUCIÓN
# ============================================================

def obtener_distribucion(cantidad):

    distribuciones = {

        1: (1, 1),

        2: (2, 1),

        4: (2, 2),

        8: (2, 4),

    }

    return distribuciones.get(
        cantidad,
        (2, 4)
    )


# ============================================================
# POSICIONES
# ============================================================

def calcular_posiciones(cantidad):

    columnas, filas = obtener_distribucion(cantidad)
    ancho_credencial, alto_credencial = CREDENCIAL_ANCHO, CREDENCIAL_ALTO

    espacio_horizontal = (
        HOJA_ANCHO -
        (
            columnas *
            ancho_credencial
        )
    ) / (
        columnas + 1
    )

    espacio_vertical = (
        HOJA_ALTO -
        (
            filas *
            alto_credencial
        )
    ) / (
        filas + 1
    )

    posiciones = []

    for fila in range(filas):

        for columna in range(columnas):

            x = (
                espacio_horizontal +
                columna *
                (
                    ancho_credencial +
                    espacio_horizontal
                )
            )

            y = (
                HOJA_ALTO -
                espacio_vertical -
                alto_credencial -
                fila *
                (
                    alto_credencial +
                    espacio_vertical
                )
            )

            posiciones.append(
                (
                    x,
                    y
                )
            )

    return posiciones


def _dibujar_diseno_libre(pdf, entidad, configuracion, x, y, personal=False, lado="frente"):
    """Dibuja en PDF el lienzo libre guardado desde la configuración."""
    layout = (configuracion or {}).get("layout") or {}
    diseño_base = layout.get("_free") or {}
    diseño = diseño_base.get("back") if lado == "reverso" else diseño_base
    diseño = diseño or {}
    if not diseño.get("enabled"):
        return False

    escala = ESCALA_UNIFORME
    ancho = CREDENCIAL_ANCHO
    alto = CREDENCIAL_ALTO
    lienzo_h = 400 * escala
    compensacion_y = max((alto - lienzo_h) / 2, 0)
    color_fondo = color_hex(diseño.get("background"), "#ffffff")
    pdf.saveState()
    clip = pdf.beginPath()
    clip.roundRect(x, y, ancho, alto, 18 * escala)
    pdf.clipPath(clip, stroke=0, fill=0)
    pdf.setFillColor(color_fondo)
    pdf.roundRect(x, y, ancho, alto, 18 * escala, fill=1, stroke=0)

    matricula = entidad.get("numero_empleado") if personal else entidad.get("matricula")
    campos = {
        "nombre": " ".join(str(entidad.get(k, "") or "").strip() for k in
                            ("nombre", "apellido_paterno", "apellido_materno") if str(entidad.get(k, "") or "").strip()),
        "matricula": str(matricula or ""),
        "grupo": str(entidad.get("nombre_grupo", entidad.get("grupo_nombre", "")) or ""),
        "grado": str(entidad.get("grado", "") or ""),
        "turno": str(entidad.get("turno", "") or ""),
        "tipo_personal": str(entidad.get("tipo_personal", "") or ""),
        "cargo": str(entidad.get("cargo", "") or ""),
        "area": str(entidad.get("area", "") or ""),
        "correo": str(entidad.get("correo", "") or ""),
        "telefono": str(entidad.get("telefono", "") or ""),
        "institucion": str(configuracion.get("nombre_institucion", "") or ""),
        "subtitulo": str(configuracion.get("subtitulo", "") or ""),
        "texto_pie": str(configuracion.get("texto_pie", "") or ""),
        "tipo_credencial": str(entidad.get("tipo_credencial", "") or ""),
        "organizacion": str(entidad.get("organizacion", "") or ""),
    }
    fuente = obtener_fuente(configuracion.get("fuente", "Arial"))
    fuente_negrita = obtener_fuente_negrita(configuracion.get("fuente", "Arial"))

    for item in diseño.get("elements", []):
        tipo = item.get("type")
        ex, ey = float(item.get("x", 0)), float(item.get("y", 0))
        ew, eh = float(item.get("w", 120)), float(item.get("h", 48))
        px = x + ex * escala
        py = y + alto - compensacion_y - (ey + eh) * escala
        pw, ph = ew * escala, eh * escala

        if tipo == "rect":
            pdf.setFillColor(color_hex(item.get("fill"), "#2563eb"))
            # Las formas que llegan al borde del lienzo deben sangrar hasta
            # el borde físico de la tarjeta, incluso con el ajuste vertical
            # que conserva la proporción del lienzo dentro del formato CR80.
            rect_izq = x if ex <= 0 else px
            rect_der = x + ancho if ex + ew >= 700 else px + pw
            rect_abajo = y if ey + eh >= 400 else py
            rect_arriba = y + alto if ey <= 0 else py + ph
            pdf.rect(
                rect_izq,
                rect_abajo,
                max(rect_der - rect_izq, 0),
                max(rect_arriba - rect_abajo, 0),
                fill=1,
                stroke=0,
            )
        elif tipo in {"logo", "photo", "image", "qr"}:
            if tipo == "logo":
                ruta = buscar_imagen(configuracion.get("logo"))
            elif tipo == "photo":
                ruta = buscar_imagen(entidad.get("foto"))
            elif tipo == "image":
                ruta = buscar_imagen(item.get("image"))
            else:
                ruta = buscar_o_generar_qr(entidad, personal=personal)
            if ruta:
                if tipo == "image" and item.get("fit") == "stretch":
                    if ex <= 0 and ey <= 0 and ex + ew >= 700 and ey + eh >= 400:
                        pdf.drawImage(str(ruta), x, y, ancho, alto, preserveAspectRatio=False, mask="auto")
                    else:
                        pdf.drawImage(str(ruta), px, py, pw, ph, preserveAspectRatio=False, mask="auto")
                elif tipo == "photo" or (tipo == "image" and item.get("fit") == "cover"):
                    dibujar_cover(pdf, ruta, px, py, pw, ph)
                else:
                    dibujar_contain(pdf, ruta, px, py, pw, ph)
            elif tipo == "photo":
                dibujar_silueta_foto(pdf, px, py, pw, ph)
        elif tipo == "text":
            texto = campos.get(item.get("field", ""), item.get("text", ""))
            if not item.get("field"):
                texto = item.get("text", "")
            if texto:
                size = float(item.get("fontSize", 18)) * escala
                fuente_item = obtener_fuente(item.get("fontFamily") or configuracion.get("fuente", "Arial"))
                fuente_item_negrita = obtener_fuente_negrita(item.get("fontFamily") or configuracion.get("fuente", "Arial"))
                fuente_texto = fuente_item_negrita if item.get("bold") else fuente_item
                pdf.setFillColor(color_hex(item.get("color"), "#111827"))
                pdf.setFont(fuente_texto, size)
                lineas = []
                for parrafo in str(texto).splitlines() or [""]:
                    lineas.extend(simpleSplit(parrafo, fuente_texto, size, max(pw, 1)))
                pdf.saveState()
                caja = pdf.beginPath()
                caja.rect(px, py, pw, ph)
                pdf.clipPath(caja, stroke=0, fill=0)
                for n, linea in enumerate(lineas):
                    pdf.drawString(px, y + alto - compensacion_y - ey * escala - size * (n + 1), linea)
                pdf.restoreState()

    pdf.setStrokeColor(color_hex(configuracion.get("color_principal"), "#1e3a8a"))
    pdf.setLineWidth(1)
    pdf.roundRect(x, y, ancho, alto, 18 * escala, fill=0, stroke=1)
    pdf.restoreState()
    return True


# ============================================================
# DIBUJAR CREDENCIAL
# ============================================================

def dibujar_credencial_especial(pdf, entidad, configuracion, x, y, lado="frente"):
    layout = configuracion.get("layout") or {}
    if _dibujar_diseno_libre(pdf, entidad, configuracion, x, y, personal=False, lado=lado):
        return
    if layout and "_free" not in layout:
        return _dibujar_credencial_especial_layout(pdf, entidad, configuracion, x, y, layout)
    ancho, alto = CREDENCIAL_ANCHO, CREDENCIAL_ALTO
    fondo = color_hex(configuracion.get("color_fondo"), "#ffffff")
    principal = color_hex(configuracion.get("color_principal"), "#1e3a8a")
    secundario = color_hex(configuracion.get("color_secundario"), "#2563eb")
    texto = color_hex(configuracion.get("color_texto"), "#111827")
    escala = ESCALA_UNIFORME
    pdf.saveState()
    borde = pdf.beginPath()
    borde.roundRect(x, y, ancho, alto, 17 * escala)
    pdf.clipPath(borde, stroke=0, fill=0)
    pdf.setFillColor(fondo)
    pdf.roundRect(x, y, ancho, alto, 17 * escala, fill=1, stroke=0)

    alto_encabezado = alto * 0.29
    pdf.setFillColor(principal)
    pdf.rect(x, y + alto - alto_encabezado, ancho, alto_encabezado, fill=1, stroke=0)
    pdf.setFillColor(secundario)
    pdf.rect(x, y, ancho, 15 * escala, fill=1, stroke=0)

    ruta_logo = buscar_imagen(configuracion.get("logo"))
    if ruta_logo:
        dibujar_contain(pdf, ruta_logo, x + 9 * escala, y + alto - 30 * escala, 28 * escala, 22 * escala)
    pdf.setFillColor(colors.white)
    fuente = obtener_fuente(configuracion.get("fuente", "Arial"))
    fuente_negrita = obtener_fuente_negrita(configuracion.get("fuente", "Arial"))
    pdf.setFont(fuente_negrita, 8 * escala)
    pdf.drawString(x + (42 if ruta_logo else 11) * escala, y + alto - 13 * escala, str(configuracion.get("nombre_institucion") or "SICAE WEB")[:48])
    pdf.setFont(fuente, 6.4 * escala)
    pdf.drawString(x + (42 if ruta_logo else 11) * escala, y + alto - 24 * escala, str(configuracion.get("subtitulo") or entidad.get("tipo_credencial") or "")[:56])

    mostrar_foto = configuracion.get("mostrar_foto", True)
    mostrar_qr = configuracion.get("mostrar_qr", True)
    mostrar_codigo = configuracion.get("mostrar_codigo", True)
    mostrar_cargo = configuracion.get("mostrar_cargo", True)
    mostrar_organizacion = configuracion.get("mostrar_organizacion", True)
    foto_x, foto_y, foto_lado = x + 10 * escala, y + 30 * escala, 42 * escala
    ruta_foto = buscar_imagen(entidad.get("foto")) if mostrar_foto else None
    if ruta_foto:
        dibujar_cover(pdf, ruta_foto, foto_x, foto_y, foto_lado, foto_lado)
    elif mostrar_foto:
        dibujar_silueta_foto(pdf, foto_x, foto_y, foto_lado, foto_lado)

    qr_lado = 48 * escala
    ruta_qr = buscar_imagen(entidad.get("qr")) if mostrar_qr else None
    if ruta_qr:
        dibujar_contain(pdf, ruta_qr, x + ancho - qr_lado - 9 * escala, y + 25 * escala, qr_lado, qr_lado)

    inicio_texto = x + (60 if mostrar_foto else 12) * escala
    fin_texto = x + ancho - (64 if mostrar_qr else 10) * escala
    ancho_texto = max(fin_texto - inicio_texto, 40 * escala)
    nombre = " ".join(str(entidad.get(campo) or "").strip() for campo in ("nombre", "apellido_paterno", "apellido_materno") if str(entidad.get(campo) or "").strip())
    try:
        tamano_nombre = max(9, min(int(configuracion.get("tamano_nombre", 20)), 30)) * escala
    except (TypeError, ValueError):
        tamano_nombre = 20 * escala
    pdf.setFillColor(texto)
    pdf.setFont(fuente_negrita, tamano_nombre)
    lineas_nombre = simpleSplit(nombre or "Nombre", fuente_negrita, tamano_nombre, ancho_texto)
    pdf.drawString(inicio_texto, y + alto - 52 * escala, lineas_nombre[0] if lineas_nombre else "")
    pdf.setFont(fuente_negrita, 7.5 * escala)
    pdf.setFillColor(principal)
    pdf.drawString(inicio_texto, y + alto - 66 * escala, str(entidad.get("tipo_credencial") or "Identificación")[:34])
    pdf.setFillColor(texto)
    pdf.setFont(fuente, 7 * escala)
    if mostrar_cargo and entidad.get("cargo"):
        pdf.drawString(inicio_texto, y + alto - 79 * escala, str(entidad["cargo"])[:42])
    if mostrar_organizacion and entidad.get("organizacion"):
        pdf.drawString(inicio_texto, y + alto - 91 * escala, str(entidad["organizacion"])[:42])
    if mostrar_codigo:
        pdf.setFont(fuente_negrita, 6.5 * escala)
        pdf.drawString(x + 10 * escala, y + 5 * escala, str(entidad.get("matricula") or "")[:32])
    texto_pie = str(configuracion.get("texto_pie") or "")
    if texto_pie:
        pdf.setFont(fuente, 5.5 * escala)
        pdf.drawRightString(x + ancho - 8 * escala, y + 5 * escala, texto_pie[:42])
    pdf.setStrokeColor(principal)
    pdf.setLineWidth(0.8)
    pdf.roundRect(x, y, ancho, alto, 17 * escala, fill=0, stroke=1)
    pdf.restoreState()


def _dibujar_credencial_especial_layout(pdf, entidad, configuracion, x, y, layout):
    """Render the administrator's draggable card layout on the printed card."""
    ancho, alto = CREDENCIAL_ANCHO, CREDENCIAL_ALTO
    principal = color_hex(configuracion.get("color_principal"), "#1e3a8a")
    secundario = color_hex(configuracion.get("color_secundario"), "#2563eb")
    color_texto = color_hex(configuracion.get("color_texto"), "#111827")
    fuente = obtener_fuente(configuracion.get("fuente", "Arial"))
    negrita = obtener_fuente_negrita(configuracion.get("fuente", "Arial"))
    foto_activa = configuracion.get("mostrar_foto", True)
    qr_activo = configuracion.get("mostrar_qr", True)

    def caja(nombre, alto_pct=10):
        item = layout.get(nombre) or {}
        try:
            px = x + ancho * max(0, min(100, float(item.get("x", 0)))) / 100
            py_top = alto * max(0, min(100, float(item.get("y", 0)))) / 100
            pw = ancho * max(5, min(100, float(item.get("w", 30)))) / 100
        except (TypeError, ValueError):
            return x, y, ancho * .3, alto * .1
        ph = alto * alto_pct / 100
        return px, y + alto - py_top - ph, pw, ph

    def texto_elemento(nombre, contenido, *, size=8, bold=False, fill=color_texto, alto_pct=10, fondo=None):
        if not contenido:
            return
        px, py, pw, ph = caja(nombre, alto_pct)
        pdf.saveState()
        if fondo:
            pdf.setFillColor(fondo)
            pdf.rect(px, py, pw, ph, fill=1, stroke=0)
        pdf.setFillColor(fill)
        pdf.setFont(negrita if bold else fuente, size * ESCALA_UNIFORME)
        pdf.beginPath()
        clip = pdf.beginPath()
        clip.rect(px, py, pw, ph)
        pdf.clipPath(clip, stroke=0, fill=0)
        pdf.drawString(px + 2, py + max(1, (ph - size * ESCALA_UNIFORME) / 2), str(contenido))
        pdf.restoreState()

    pdf.saveState()
    borde = pdf.beginPath()
    borde.roundRect(x, y, ancho, alto, 17 * ESCALA_UNIFORME)
    pdf.clipPath(borde, stroke=0, fill=0)
    pdf.setFillColor(color_hex(configuracion.get("color_fondo"), "#ffffff"))
    pdf.roundRect(x, y, ancho, alto, 17 * ESCALA_UNIFORME, fill=1, stroke=0)

    ruta_logo = buscar_imagen(configuracion.get("logo"))
    if ruta_logo:
        px, py, pw, ph = caja("logo", 24)
        dibujar_contain(pdf, ruta_logo, px, py, pw, ph)
    texto_elemento("institucion", configuracion.get("nombre_institucion") or "SICAE WEB", size=16, bold=True, fill=colors.white, alto_pct=15, fondo=principal)
    texto_elemento("subtitulo", configuracion.get("subtitulo") or entidad.get("tipo_credencial"), size=10, fill=colors.white, alto_pct=12, fondo=principal)

    if foto_activa:
        px, py, pw, ph = caja("foto", 39)
        foto = buscar_imagen(entidad.get("foto"))
        if foto:
            dibujar_cover(pdf, foto, px, py, min(pw, ph), min(pw, ph))
        else:
            dibujar_silueta_foto(pdf, px, py, min(pw, ph), min(pw, ph))
    if qr_activo:
        px, py, pw, ph = caja("qr", 39)
        qr = buscar_imagen(entidad.get("qr"))
        if qr:
            pdf.setFillColor(colors.white)
            pdf.rect(px, py, pw, ph, fill=1, stroke=0)
            dibujar_contain(pdf, qr, px, py, pw, ph)

    nombre = " ".join(str(entidad.get(campo) or "").strip() for campo in ("nombre", "apellido_paterno", "apellido_materno") if str(entidad.get(campo) or "").strip())
    try:
        tamano = max(9, min(int(configuracion.get("tamano_nombre", 20)), 30)) * .42
    except (TypeError, ValueError):
        tamano = 8.4
    texto_elemento("nombre", nombre or "Nombre", size=tamano, bold=True, alto_pct=16)
    texto_elemento("tipo", entidad.get("tipo_credencial") or "Identificación", size=10, bold=True, fill=principal, alto_pct=10)
    if configuracion.get("mostrar_cargo", True):
        texto_elemento("cargo", entidad.get("cargo"), size=9, alto_pct=9)
    if configuracion.get("mostrar_organizacion", True):
        texto_elemento("organizacion", entidad.get("organizacion"), size=9, alto_pct=9)
    if configuracion.get("mostrar_codigo", True):
        texto_elemento("codigo", entidad.get("matricula"), size=8, bold=True, alto_pct=9)
    texto_elemento("pie", configuracion.get("texto_pie"), size=7, fill=colors.white, alto_pct=10, fondo=secundario)
    pdf.setStrokeColor(principal)
    pdf.roundRect(x, y, ancho, alto, 17 * ESCALA_UNIFORME, fill=0, stroke=1)
    pdf.restoreState()
    return True


def dibujar_credencial(
    pdf,
    alumno,
    configuracion,
    x,
    y,
    lado="frente",
):

    configuracion = configuracion or {}

    if alumno.get("tipo_credencial"):
        dibujar_credencial_especial(pdf, alumno, configuracion, x, y, lado=lado)
        return

    if _dibujar_diseno_libre(pdf, alumno, configuracion, x, y, personal=False, lado=lado):
        return

    # ========================================================
    # COLORES
    # ========================================================

    color_principal = color_hex(
        configuracion.get(
            "color_principal"
        ),
        "#1e3a8a"
    )

    color_secundario = color_hex(
        configuracion.get(
            "color_secundario"
        ),
        "#2563eb"
    )

    color_texto = color_hex(
        configuracion.get(
            "color_texto"
        ),
        "#111827"
    )

    # ========================================================
    # FUENTES
    # ========================================================

    fuente_nombre = configuracion.get(
        "fuente",
        "Arial"
    )

    fuente = obtener_fuente(
        fuente_nombre
    )

    fuente_negrita = obtener_fuente_negrita(
        fuente_nombre
    )

    try:
        tamano_nombre = int(
            configuracion.get(
                "tamano_nombre",
                21
            )
        )
    except Exception:
        tamano_nombre = 21

    tamano_nombre = max(
        12,
        min(
            tamano_nombre,
            60
        )
    )

    # ========================================================
    # DATOS DEL ALUMNO
    # ========================================================

    nombre = (
        f"{alumno.get('nombre', '')} "
        f"{alumno.get('apellido_paterno', '')} "
        f"{alumno.get('apellido_materno', '') or ''}"
    ).strip()

    matricula = str(
        alumno.get(
            "matricula",
            ""
        )
    ).strip()

    nombre_grupo = str(
        alumno.get(
            "nombre_grupo",
            alumno.get(
                "grupo_nombre",
                ""
            )
        ) or ""
    )

    grado = str(
        alumno.get(
            "grado",
            ""
        ) or ""
    )

    turno = str(
        alumno.get(
            "turno",
            ""
        ) or ""
    )

    # ========================================================
    # IMAGENES
    # ========================================================

    ruta_foto = buscar_imagen(
        alumno.get(
            "foto"
        )
    )

    ruta_logo = buscar_imagen(
        configuracion.get(
            "logo"
        )
    )

    ruta_qr = buscar_o_generar_qr(alumno)

    # ========================================================
    # ELEMENTOS VISIBLES
    # ========================================================

    mostrar_foto = configuracion.get(
        "mostrar_foto",
        True
    )

    mostrar_qr = configuracion.get(
        "mostrar_qr",
        True
    )

    mostrar_matricula = configuracion.get(
        "mostrar_matricula",
        True
    )

    mostrar_grupo = configuracion.get(
        "mostrar_grupo",
        True
    )

    mostrar_grado = configuracion.get(
        "mostrar_grado",
        True
    )

    mostrar_turno = configuracion.get(
        "mostrar_turno",
        True
    )

    # ========================================================
    # SISTEMA DE ESCALA
    #
    # VISTA PREVIA:
    # 700 x 400 px
    #
    # PDF:
    # CREDENCIAL_ANCHO x CREDENCIAL_ALTO
    # ========================================================

    HTML_ANCHO = 700
    HTML_ALTO = 400

    ESCALA_X = min(
        CREDENCIAL_ANCHO / HTML_ANCHO,
        CREDENCIAL_ALTO / HTML_ALTO
    )

    ESCALA_Y = ESCALA_X

    def px(valor):
        return valor * ESCALA_X

    def py(valor):
        return valor * ESCALA_Y

    ancho = CREDENCIAL_ANCHO
    alto = CREDENCIAL_ALTO

    radio = px(22)

    pdf.saveState()
    clip_card = pdf.beginPath()
    clip_card.roundRect(x, y, ancho, alto, radio)
    pdf.clipPath(clip_card, stroke=0, fill=0)

    # ========================================================
    # FONDO
    # ========================================================

    pdf.saveState()

    pdf.setFillColor(
        colors.white
    )

    pdf.roundRect(
        x,
        y,
        ancho,
        alto,
        radio,
        fill=1,
        stroke=0
    )

    pdf.restoreState()

    # ========================================================
    # ENCABEZADO
    #
    # HTML:
    # min-height: 95px
    # padding: 18px 25px
    # ========================================================

    encabezado = py(95)

    pdf.saveState()

    ruta_clip = pdf.beginPath()

    ruta_clip.roundRect(
        x,
        y + alto - encabezado,
        ancho,
        encabezado,
        radio
    )

    pdf.clipPath(
        ruta_clip,
        stroke=0,
        fill=0
    )

    pdf.setFillColor(
        color_principal
    )

    pdf.rect(
        x,
        y + alto - encabezado,
        ancho,
        encabezado,
        fill=1,
        stroke=0
    )

    pdf.restoreState()

    # ========================================================
    # LOGO
    with _mover_bloque_credencial(pdf, configuracion, "institucion", ESCALA_X, ESCALA_Y):
        #
        # HTML:
        # 60 x 60
        # padding: 4
        # ========================================================

        logo_ancho = px(60)
        logo_alto = py(60)

        logo_x = x + px(25)

        logo_y = (
            y +
            alto -
            py(18) -
            logo_alto
        )

        if ruta_logo:

            pdf.setFillColor(
                colors.white
            )

            pdf.roundRect(
                logo_x,
                logo_y,
                logo_ancho,
                logo_alto,
                px(9),
                fill=1,
                stroke=0
            )

            dibujar_contain(
                pdf,
                ruta_logo,
                logo_x + px(4),
                logo_y + py(4),
                logo_ancho - px(8),
                logo_alto - py(8)
            )

        # ========================================================
        # TEXTO DE INSTITUCION
        # ========================================================

        if ruta_logo:

            texto_x = (
                x +
                px(25) +
                px(60) +
                px(15)
            )

        else:

            texto_x = (
                x +
                px(25)
            )

        ancho_texto = (
            x +
            ancho -
            texto_x -
            px(25)
        )

        institucion = str(
            configuracion.get(
                "nombre_institucion",
                "SICAE"
            ) or "SICAE"
        ).strip()

        pdf.setFillColor(
            colors.white
        )

        tamano_institucion = py(21)

        pdf.setFont(
            fuente_negrita,
            tamano_institucion
        )

        institucion = ajustar_texto(
            institucion,
            fuente_negrita,
            tamano_institucion,
            ancho_texto
        )

        pdf.drawString(
            texto_x,
            y +
            alto -
            py(18) -
            py(25),
            institucion
        )

        # ========================================================
        # SUBTITULO
        # ========================================================

        subtitulo = str(
            configuracion.get(
                "subtitulo",
                ""
            ) or ""
        ).strip()

        if subtitulo:

            tamano_subtitulo = py(12)

            pdf.setFont(
                fuente,
                tamano_subtitulo
            )

            subtitulo = ajustar_texto(
                subtitulo,
                fuente,
                tamano_subtitulo,
                ancho_texto
            )

            pdf.drawString(
                texto_x,
                y +
                alto -
                py(18) -
                py(48),
                subtitulo
            )

    pdf.setFont(fuente_negrita, py(12))
    with _mover_bloque_credencial(pdf, configuracion, "titulo", ESCALA_X, ESCALA_Y):
        pdf.drawRightString(
            x + ancho - px(25),
            y + alto - py(59),
            "CREDENCIAL ESCOLAR"
        )

        # ========================================================
    # CUERPO
    #
    # HTML:
    # padding: 22px 25px
    # gap: 22px
    # ========================================================

    cuerpo_y = (
        y +
        alto -
        encabezado
    )

    padding_x = px(25)
    padding_y = py(22)

    # ========================================================
    # FOTO
    with _mover_bloque_credencial(pdf, configuracion, "foto", ESCALA_X, ESCALA_Y):
        #
        # HTML:
        # 120 x 145
        # ========================================================

        foto_ancho = px(120)
        foto_alto = py(145)

        foto_x = (
            x +
            padding_x
        )

        foto_y = (
            cuerpo_y -
            padding_y -
            foto_alto
        )

        if mostrar_foto:

            if ruta_foto:

                dibujar_cover(
                    pdf,
                    ruta_foto,
                    foto_x,
                    foto_y,
                    foto_ancho,
                    foto_alto
                )

            else:
                dibujar_silueta_foto(
                    pdf,
                    foto_x,
                    foto_y,
                    foto_ancho,
                    foto_alto
                )

            pdf.setStrokeColor(
                colors.HexColor(
                    "#e5e7eb"
                )
            )

            pdf.setLineWidth(
                px(3)
            )

            pdf.roundRect(
                foto_x,
                foto_y,
                foto_ancho,
                foto_alto,
                px(10),
                fill=0,
                stroke=1
            )

        # ========================================================
    # QR
    with _mover_bloque_credencial(pdf, configuracion, "qr", ESCALA_X, ESCALA_Y):
        #
        # HTML:
        # contenedor 105
        # imagen 90 x 90
        # ========================================================

        try:
            tamano_qr = int(
                configuracion.get(
                    "tamano_qr",
                    300
                )
            )
        except Exception:
            tamano_qr = 300

        tamano_qr = max(
            100,
            min(
                tamano_qr,
                500
            )
        )

        qr_contenedor = px(tamano_qr)
        qr_tamano = px(tamano_qr)

        qr_x = (
            x +
            ancho -
            padding_x -
            qr_contenedor
        )

        qr_imagen_x = (
            qr_x +
            (
                qr_contenedor -
                qr_tamano
            ) / 2
        )

        qr_y = (
            cuerpo_y -
            padding_y -
            qr_tamano
        )

        if mostrar_qr and ruta_qr:

            dibujar_contain(
                pdf,
                ruta_qr,
                qr_imagen_x,
                qr_y,
                qr_tamano,
                qr_tamano
            )

            pdf.setFillColor(
                colors.HexColor(
                    "#777777"
                )
            )

            pdf.setFont(
                fuente,
                py(9)
            )

            texto_qr = (
                "Escanea para registrar asistencia"
            )

            texto_qr = ajustar_texto(
                texto_qr,
                fuente,
                py(9),
                qr_contenedor
            )

            pdf.drawCentredString(
                qr_x +
                qr_contenedor / 2,
                qr_y -
                py(8),
                texto_qr
            )

        # ========================================================
    # DATOS
    with _mover_bloque_credencial(pdf, configuracion, "datos", ESCALA_X, ESCALA_Y):
        # ========================================================

        if mostrar_foto:

            datos_x = (
                foto_x +
                foto_ancho +
                px(22)
            )

        else:

            datos_x = (
                x +
                padding_x
            )

        if mostrar_qr:

            limite_derecho = (
                qr_x -
                px(22)
            )

        else:

            limite_derecho = (
                x +
                ancho -
                padding_x
            )

        ancho_datos = (
            limite_derecho -
            datos_x
        )

        if ancho_datos < px(80):

            ancho_datos = px(80)

        # ========================================================
        # NOMBRE
        # ========================================================

        nombre_tamano = py(
            tamano_nombre
        )

        nombre_lineas = dividir_texto(
            nombre,
            fuente_negrita,
            nombre_tamano,
            ancho_datos
        )

        pdf.setFillColor(
            color_texto
        )

        pdf.setFont(
            fuente_negrita,
            nombre_tamano
        )

        nombre_y = (
            cuerpo_y -
            py(35)
        )

        for indice_linea, linea_nombre in enumerate(nombre_lineas):
            pdf.drawString(
                datos_x,
                nombre_y - indice_linea * nombre_tamano * 1.1,
                linea_nombre
            )

        # ========================================================
        # DATOS INFERIORES
        # ========================================================

        posicion_y = (
            nombre_y -
            len(nombre_lineas) * nombre_tamano * 1.1 -
            py(15)
        )

        tamano_datos = py(13)

        def dibujar_dato(
            etiqueta,
            valor
        ):

            nonlocal posicion_y

            if not valor:
                valor = ""

            pdf.setFont(
                fuente_negrita,
                tamano_datos
            )

            pdf.setFillColor(
                color_texto
            )

            pdf.drawString(
                datos_x,
                posicion_y,
                etiqueta
            )

            ancho_etiqueta = stringWidth(
                etiqueta,
                fuente_negrita,
                tamano_datos
            )

            pdf.setFont(
                fuente,
                tamano_datos
            )

            valor_ajustado = ajustar_texto(
                str(valor),
                fuente,
                tamano_datos,
                max(
                    ancho_datos -
                    ancho_etiqueta -
                    px(5),
                    px(20)
                )
            )

            pdf.drawString(
                datos_x +
                ancho_etiqueta +
                px(5),
                posicion_y,
                valor_ajustado
            )

            posicion_y -= py(24)

        # ========================================================
        # MATRICULA
        # ========================================================

        if mostrar_matricula:

            dibujar_dato(
                "Matrícula:",
                matricula
            )

        # ========================================================
        # GRUPO
        # ========================================================

        if mostrar_grupo:

            dibujar_dato(
                "Grupo:",
                nombre_grupo
            )

        # ========================================================
        # GRADO
        # ========================================================

        if mostrar_grado:

            valor_grado = grado

            if grado:

                valor_grado = (
                    f"{grado}°"
                )

            dibujar_dato(
                "Grado:",
                valor_grado
            )

        # ========================================================
        # TURNO
        # ========================================================

        if mostrar_turno:

            dibujar_dato(
                "Turno:",
                turno
            )

        # ========================================================
    # PIE
    with _mover_bloque_credencial(pdf, configuracion, "pie", ESCALA_X, ESCALA_Y):
        #
        # HTML:
        # min-height: 42px
        # ========================================================

        texto_pie = str(
            configuracion.get(
                "texto_pie",
                ""
            ) or ""
        ).strip()

        if texto_pie:

            pie_alto = py(42)

            pdf.setFillColor(
                color_secundario
            )

            pdf.rect(
                x,
                y,
                ancho,
                pie_alto,
                fill=1,
                stroke=0
            )

            pdf.setFillColor(
                colors.white
            )

            tamano_pie = py(11)

            pdf.setFont(
                fuente,
                tamano_pie
            )

            texto_pie = ajustar_texto(
                texto_pie,
                fuente,
                tamano_pie,
                ancho - px(50)
            )

            pdf.drawCentredString(
                x +
                ancho / 2,
                y +
                py(15),
                texto_pie
            )

        # ========================================================
    # BORDE
    # ========================================================

    pdf.setStrokeColor(
        color_principal
    )

    pdf.setLineWidth(
        px(1)
    )

    pdf.roundRect(
        x,
        y,
        ancho,
        alto,
        radio,
        fill=0,
        stroke=1
    )

    pdf.restoreState()

# ============================================================
# GENERAR PDF
# ============================================================

def generar_pdf_credenciales(

    alumnos,

    configuracion,

    ruta_pdf,

    cantidad_por_hoja=8,

    solo_qr=False,

    progress_callback=None,

):

    print()

    print(
        "=========================================="
    )

    print(
        "GENERANDO PDF DE CREDENCIALES SICAE"
    )

    print(
        "Cantidad de alumnos:",
        len(alumnos)
    )

    print(
        "Credenciales por hoja:",
        cantidad_por_hoja
    )

    print(
        "=========================================="
    )


    configuracion = (
        configuracion or {}
    )


    try:

        cantidad_por_hoja = int(
            cantidad_por_hoja
        )

    except Exception:

        cantidad_por_hoja = 8


    if cantidad_por_hoja not in {

        1,
        2,
        4,
        8

    }:

        cantidad_por_hoja = 8


    ruta_pdf = Path(
        ruta_pdf
    )


    ruta_pdf.parent.mkdir(

        parents=True,

        exist_ok=True

    )


    posiciones = calcular_posiciones(cantidad_por_hoja)

    if progress_callback:
        progress_callback(0, len(alumnos))


    pdf = canvas.Canvas(

        str(ruta_pdf),

        pagesize=letter

    )


    indice = 0


    while indice < len(alumnos):

        credenciales_pagina = []

        for posicion in posiciones:

            if indice >= len(alumnos):
                break

            x, y = posicion

            if solo_qr:
                alumno = alumnos[indice]
                ruta_qr = buscar_o_generar_qr(alumno)
                if ruta_qr:
                    lado_qr = min(CREDENCIAL_ALTO * 0.72, CREDENCIAL_ANCHO * 0.52)
                    dibujar_contain(
                        pdf,
                        ruta_qr,
                        x + (CREDENCIAL_ANCHO - lado_qr) / 2,
                        y + 25,
                        lado_qr,
                        lado_qr,
                    )
                    pdf.saveState()
                    pdf.setFillColor(colors.black)
                    pdf.setFont("Helvetica-Bold", 8.5)
                    pdf.drawCentredString(
                        x + CREDENCIAL_ANCHO / 2,
                        y + 10,
                        str(alumno.get("matricula") or "Sin matrícula"),
                    )
                    pdf.restoreState()
            else:
                credenciales_pagina.append((alumnos[indice], x, y))
                dibujar_credencial(
                    pdf,
                    alumnos[indice],
                    configuracion,
                    x,
                    y
                )

            indice += 1
            if progress_callback:
                progress_callback(indice, len(alumnos))


        pdf.showPage()

        diseño_libre = (configuracion.get("layout") or {}).get("_free") or {}
        reverso = diseño_libre.get("back") or {}
        if not solo_qr and reverso.get("enabled"):
            # En dúplex con giro por borde largo, la cara posterior debe
            # reflejar las columnas para que coincida con el frente al cortar.
            for alumno, x, y in credenciales_pagina:
                x_reverso = HOJA_ANCHO - x - CREDENCIAL_ANCHO
                dibujar_credencial(
                    pdf,
                    alumno,
                    configuracion,
                    x_reverso,
                    y,
                    lado="reverso",
                )
            pdf.showPage()


    pdf.save()


    print()

    print(
        "=========================================="
    )

    print(
        "PDF GENERADO CORRECTAMENTE"
    )

    print(
        "Credencial:",
        f"{CREDENCIAL_ANCHO:.2f} x "
        f"{CREDENCIAL_ALTO:.2f} puntos"
    )

    print(
        "Tamaño físico:",
        "85.60 x 53.98 mm"
    )

    print(
        "Credenciales por hoja:",
        cantidad_por_hoja
    )

    print(
        "Archivo:",
        ruta_pdf
    )

    print(
        "=========================================="
    )

    print()


    return ruta_pdf

# ============================================================
# GENERAR PDF DE CREDENCIAL DEL PERSONAL
# ============================================================

def generar_pdf_credencial_personal(
    personal,
    configuracion,
    ruta_pdf
):

    configuracion = configuracion or {}

    ruta_pdf = Path(ruta_pdf)

    ruta_pdf.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    c = canvas.Canvas(
        str(ruta_pdf),
        pagesize=letter
    )

    # ========================================================
    # TAMAÑO DE LA CREDENCIAL
    # ========================================================

    ancho = CREDENCIAL_ANCHO
    alto = CREDENCIAL_ALTO

    margen_x = (
        HOJA_ANCHO - ancho
    ) / 2

    margen_y = (
        HOJA_ALTO - alto
    ) / 2



    # ========================================================
    # ESCALA IGUAL A LA CREDENCIAL DE ESTUDIANTES
    # ========================================================

    HTML_ANCHO_PERSONAL = 700
    HTML_ALTO_PERSONAL = 400

    ESCALA_X_PERSONAL = min(
        CREDENCIAL_ANCHO / HTML_ANCHO_PERSONAL,
        CREDENCIAL_ALTO / HTML_ALTO_PERSONAL
    )

    ESCALA_Y_PERSONAL = ESCALA_X_PERSONAL

    def pxp(valor):
        return valor * ESCALA_X_PERSONAL

    def pyp(valor):
        return valor * ESCALA_Y_PERSONAL

    c.saveState()
    clip_card = c.beginPath()
    clip_card.roundRect(
        margen_x,
        margen_y,
        ancho,
        alto,
        sx(22)
    )
    c.clipPath(clip_card, stroke=0, fill=0)
    if _dibujar_diseno_libre(c, personal, configuracion, margen_x, margen_y, personal=True):
        c.restoreState()
        c.showPage()
        diseño_libre = (configuracion.get("layout") or {}).get("_free") or {}
        reverso = diseño_libre.get("back") or {}
        if reverso.get("enabled"):
            c.saveState()
            clip_reverso = c.beginPath()
            clip_reverso.roundRect(margen_x, margen_y, ancho, alto, sx(22))
            c.clipPath(clip_reverso, stroke=0, fill=0)
            _dibujar_diseno_libre(c, personal, configuracion, margen_x, margen_y, personal=True, lado="reverso")
            c.restoreState()
            c.showPage()
        c.save()
        return ruta_pdf
    # ========================================================
    # COLORES
    # ========================================================

    color_principal = color_hex(
        configuracion.get(
            "color_principal",
            "#2563eb"
        ),
        "#2563eb"
    )

    color_secundario = color_hex(
        configuracion.get(
            "color_secundario",
            "#475569"
        ),
        "#475569"
    )

    color_texto = color_hex(
        configuracion.get(
            "color_texto",
            "#1e293b"
        ),
        "#1e293b"
    )


    # ========================================================
    # FUENTES
    # ========================================================

    fuente_nombre = configuracion.get(
        "fuente",
        "Arial"
    )

    fuente_normal = obtener_fuente(
        fuente_nombre
    )

    fuente_negrita = obtener_fuente_negrita(
        fuente_nombre
    )


    # ========================================================
    # CREDENCIAL
    # ========================================================

    # Fondo blanco

    c.setFillColor(
        colors.white
    )

    c.roundRect(
        margen_x,
        margen_y,
        ancho,
        alto,
        sx(25),
        fill=1,
        stroke=0
    )


    # Borde

    c.setStrokeColor(
        color_principal
    )

    c.setLineWidth(
        sx(3)
    )

    c.roundRect(
        margen_x,
        margen_y,
        ancho,
        alto,
        sx(25),
        fill=0,
        stroke=1
    )


    # ========================================================
    # ENCABEZADO
    # ========================================================

    encabezado_alto = sy(95)

    y_encabezado = (
        margen_y +
        alto -
        encabezado_alto
    )

    c.setFillColor(
        color_principal
    )

    c.roundRect(
        margen_x,
        y_encabezado,
        ancho,
        encabezado_alto,
        sx(25),
        fill=1,
        stroke=0
    )

    # Rectángulo para eliminar las esquinas inferiores
    # redondeadas del encabezado.

    c.rect(
        margen_x,
        y_encabezado,
        ancho,
        encabezado_alto / 2,
        fill=1,
        stroke=0
    )


    # ========================================================
    # LOGO
    with _mover_bloque_credencial(c, configuracion, "institucion", ESCALA_X_PERSONAL, ESCALA_Y_PERSONAL):
        # ========================================================

        logo = configuracion.get(
            "logo"
        )

        if logo:

            ruta_logo = (
                UPLOADS_DIR /
                str(logo)
            )

            if ruta_logo.exists():

                try:

                    c.drawImage(
                        ImageReader(
                            str(ruta_logo)
                        ),
                        margen_x + sx(25),
                        margen_y + alto - sy(77.5),
                        width=pxp(60),
                        height=pyp(60),
                        preserveAspectRatio=True,
                        anchor="c",
                        mask="auto"
                    )

                except Exception as error:

                    print(
                        "ERROR CARGANDO LOGO:",
                        error
                    )


        # ========================================================
        # INSTITUCIÓN
        # ========================================================

        institucion = str(
            configuracion.get(
                "nombre_institucion",
                "SICAE WEB"
            )
            or ""
        )

        subtitulo = str(
            configuracion.get(
                "subtitulo",
                ""
            )
            or ""
        )


        x_institucion = margen_x + sx(100 if logo else 25)

        y_institucion = (
            margen_y +
            alto -
            sy(45)
        )


        c.setFillColor(
            colors.white
        )

        c.setFont(
            fuente_negrita,
            pyp(21)
        )

        c.drawString(
            x_institucion,
            y_institucion,
            institucion[:45]
        )


        if subtitulo:

            c.setFont(
                fuente_normal,
                pyp(12)
            )

            c.drawString(
                x_institucion,
                y_institucion - sy(25),
                subtitulo[:65]
            )

    c.setFont(fuente_negrita, sy(12))
    with _mover_bloque_credencial(c, configuracion, "titulo", ESCALA_X_PERSONAL, ESCALA_Y_PERSONAL):
        c.drawRightString(
            margen_x + ancho - sx(25),
            margen_y + alto - sy(59),
            "CREDENCIAL DEL PERSONAL"
        )


        # ========================================================
    # CONTENIDO
    # ========================================================

    contenido_top = (
        margen_y +
        alto -
        sy(110)
    )

    contenido_bottom = (
        margen_y +
        sy(49)
    )


    # ========================================================
    # FOTO
    with _mover_bloque_credencial(c, configuracion, "foto", ESCALA_X_PERSONAL, ESCALA_Y_PERSONAL):
        # ========================================================

        if configuracion.get(
            "mostrar_foto",
            True
        ):

            foto = personal.get(
                "foto"
            )

            ruta_foto = buscar_imagen(foto)
            x_foto = margen_x + pxp(25)
            y_foto = contenido_bottom + pyp(52)
            ancho_foto = pxp(120)
            alto_foto = pyp(145)
            borde_foto = colors.HexColor("#e5e7eb")

            if not dibujar_cover(c, ruta_foto, x_foto, y_foto, ancho_foto, alto_foto):
                dibujar_silueta_foto(c, x_foto, y_foto, ancho_foto, alto_foto, borde_foto)
            else:
                c.setStrokeColor(borde_foto)
                c.setLineWidth(sx(3))
                c.roundRect(x_foto, y_foto, ancho_foto, alto_foto, pxp(10), fill=0, stroke=1)


        # ========================================================
    # DATOS
    with _mover_bloque_credencial(c, configuracion, "datos", ESCALA_X_PERSONAL, ESCALA_Y_PERSONAL):
        # ========================================================

        x_datos = margen_x + pxp(
            167 if configuracion.get("mostrar_foto", True) else 25
        )

        y_datos = (
            margen_y +
            alto -
            pyp(145)
        )


        # ========================================================
        # NOMBRE
        # ========================================================

        nombre = " ".join(
            str(
                personal.get(
                    campo,
                    ""
                )
                or ""
            ).strip()

            for campo in [
                "nombre",
                "apellido_paterno",
                "apellido_materno"
            ]

            if str(
                personal.get(
                    campo,
                    ""
                )
                or ""
            ).strip()
        )


        tamano_nombre = configuracion.get(
            "tamano_nombre",
            28
        )

        try:

            tamano_nombre = float(
                tamano_nombre
            )

        except Exception:

            tamano_nombre = 28

        try:
            ancho_qr_diseno = float(configuracion.get("tamano_qr", 300))
        except Exception:
            ancho_qr_diseno = 300
        ancho_qr_diseno = max(100, min(ancho_qr_diseno, 500)) if configuracion.get("mostrar_qr", True) else 0
        ancho_datos_diseno = max(
            40,
            700 - (167 if configuracion.get("mostrar_foto", True) else 25)
            - 25 - (ancho_qr_diseno + 22 if ancho_qr_diseno else 0)
        )
        tamano_nombre_pdf = pyp(tamano_nombre)
        lineas_nombre = dividir_texto(
            nombre,
            fuente_negrita,
            tamano_nombre_pdf,
            pxp(ancho_datos_diseno)
        )

        c.setFillColor(
            color_texto
        )

        c.setFont(
            fuente_negrita,
            tamano_nombre_pdf
        )

        for indice_linea, linea_nombre in enumerate(lineas_nombre):
            c.drawString(
                x_datos,
                y_datos - indice_linea * tamano_nombre_pdf * 1.1,
                linea_nombre
            )


        # ========================================================
        # DATOS DEL PERSONAL
        # ========================================================

        y = (
            y_datos -
            len(lineas_nombre) * tamano_nombre_pdf * 1.1 -
            pyp(15)
        )


        def dibujar_dato(
            etiqueta,
            valor
        ):

            nonlocal y

            if valor is None:
                return

            valor = str(
                valor
            ).strip()

            if not valor:
                return


            c.setFillColor(
                color_texto
            )


            # Etiqueta

            if etiqueta:

                c.setFont(
                    fuente_negrita,
                    pyp(13)
                )

                c.drawString(
                    x_datos,
                    y,
                    etiqueta
                )

                ancho_etiqueta = stringWidth(
                    etiqueta,
                    fuente_negrita,
                    pyp(13)
                )

                c.setFont(
                    fuente_normal,
                    pyp(13)
                )

                c.drawString(
                    x_datos +
                    ancho_etiqueta +
                    pxp(5),
                    y,
                    valor[:35]
                )

            else:

                c.setFont(
                    fuente_normal,
                    pyp(13)
                )

                c.drawString(
                    x_datos,
                    y,
                    valor[:35]
                )


            y -= pyp(24)


        # ========================================================
        # NÚMERO DE EMPLEADO
        # ========================================================

        if configuracion.get(
            "mostrar_matricula",
            True
        ):

            dibujar_dato(
                "Número de empleado:",
                personal.get(
                    "numero_empleado"
                )
            )


        # ========================================================
        # TIPO DE PERSONAL
        # ========================================================

        if configuracion.get(
            "mostrar_tipo_personal",
            True
        ):

            dibujar_dato(
                "Tipo de personal:",
                personal.get(
                    "tipo_personal"
                )
                or
                "No especificado"
            )


        # ========================================================
        # CARGO
        # ========================================================

        if configuracion.get(
            "mostrar_cargo",
            True
        ):

            dibujar_dato(
                "Cargo:",
                personal.get(
                    "cargo"
                )
                or
                "No especificado"
            )


        # ========================================================
        # ÁREA
        # ========================================================

        if configuracion.get(
            "mostrar_area",
            False
        ):

            dibujar_dato(
                "Área:",
                personal.get(
                    "area"
                )
                or
                "No especificada"
            )


        # ========================================================
        # CORREO
        # ========================================================

        if configuracion.get(
            "mostrar_correo",
            False
        ):

            dibujar_dato(
                "Correo:",
                personal.get(
                    "correo"
                )
            )


        # ========================================================
        # TELÉFONO
        # ========================================================

        if configuracion.get(
            "mostrar_telefono",
            False
        ):

            dibujar_dato(
                "Teléfono:",
                personal.get(
                    "telefono"
                )
            )


        # ========================================================
    # QR
    with _mover_bloque_credencial(c, configuracion, "qr", ESCALA_X_PERSONAL, ESCALA_Y_PERSONAL):
        # ========================================================

        if configuracion.get(
            "mostrar_qr",
            True
        ):

            ruta_qr = buscar_o_generar_qr(personal, personal=True)


            tamano_qr = configuracion.get("tamano_qr", 300)

            try:
                tamano_qr = float(tamano_qr)
            except Exception:
                tamano_qr = 300

            tamano_qr = max(100, min(tamano_qr, 500))

            if ruta_qr:
                x_qr = margen_x + sx(700 - 25 - tamano_qr)
                altura_cuerpo_util = 263 - 44
                altura_qr_con_texto = tamano_qr + 15
                espacio_inferior = max(
                    (altura_cuerpo_util - altura_qr_con_texto) / 2,
                    0
                )
                y_qr = margen_y + sy(42 + 22 + espacio_inferior + 15)


                try:

                    c.drawImage(
                        ImageReader(
                            str(ruta_qr)
                        ),
                        x_qr,
                        y_qr,
                        width=pxp(tamano_qr),
                        height=pyp(tamano_qr),
                        preserveAspectRatio=False,
                        mask="auto"
                    )


                    c.setFillColor(
                        colors.HexColor(
                            "#64748b"
                        )
                    )

                    c.setFont(
                        fuente_normal,
                        pyp(9)
                    )

                    c.drawCentredString(
                        x_qr + pxp(tamano_qr) / 2,
                        y_qr - pyp(8),
                        "Presentar para registro"
                    )

                except Exception as error:

                    print(
                        "ERROR CARGANDO QR DEL PERSONAL:",
                        error
                    )


        # ========================================================
    # PIE
    with _mover_bloque_credencial(c, configuracion, "pie", ESCALA_X_PERSONAL, ESCALA_Y_PERSONAL):
        # ========================================================

        texto_pie = str(
            configuracion.get(
                "texto_pie",
                ""
            )
            or ""
        )


        if texto_pie:

            pie_alto = sy(42)

            c.setFillColor(
                color_secundario
            )

            c.rect(
                margen_x,
                margen_y,
                ancho,
                pie_alto,
                fill=1,
                stroke=0
            )


            c.setFillColor(
                colors.white
            )

            tamano_pie = pyp(11)

            c.setFont(
                fuente_normal,
                tamano_pie
            )

            texto_pie = ajustar_texto(
                texto_pie,
                fuente_normal,
                tamano_pie,
                ancho - pxp(50)
            )

            c.drawCentredString(
                margen_x +
                ancho / 2,
                margen_y +
                pyp(15),
                texto_pie
            )


        # ========================================================
    # FINALIZAR PDF
    # ========================================================

    c.restoreState()

    c.showPage()

    c.save()





























