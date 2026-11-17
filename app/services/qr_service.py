from pathlib import Path
from urllib.parse import quote

import qrcode


# ============================================================
# DIRECTORIOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_DIR = BASE_DIR / "static"

UPLOADS_DIR = STATIC_DIR / "uploads"


# ============================================================
# CREAR CARPETA DE UPLOADS
# ============================================================

UPLOADS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# GENERAR QR DE ALUMNO
# ============================================================

def generar_qr_alumno(
    matricula
):

    # --------------------------------------------------------
    # LIMPIAR MATRÍCULA
    # --------------------------------------------------------

    matricula = str(
        matricula
    ).strip()


    if not matricula:

        raise ValueError(
            "La matrícula no puede estar vacía."
        )


    # --------------------------------------------------------
    # NOMBRE DEL ARCHIVO
    # --------------------------------------------------------

    nombre_archivo = f"qr_{quote(matricula, safe='')}.png"


    # --------------------------------------------------------
    # RUTA
    # --------------------------------------------------------

    ruta_archivo = (
        UPLOADS_DIR /
        nombre_archivo
    )


    # --------------------------------------------------------
    # CONTENIDO DEL QR
    # --------------------------------------------------------
    #
    # IMPORTANTE:
    #
    # El escáner espera recibir directamente
    # la matrícula.
    #
    # Ejemplo:
    #
    # 22015085
    #
    # --------------------------------------------------------

    contenido = matricula


    # --------------------------------------------------------
    # CONFIGURACIÓN DEL QR
    # --------------------------------------------------------

    qr = qrcode.QRCode(

        version=1,

        error_correction=(
            qrcode.constants.ERROR_CORRECT_M
        ),

        box_size=10,

        border=4

    )


    # --------------------------------------------------------
    # AGREGAR MATRÍCULA
    # --------------------------------------------------------

    qr.add_data(
        contenido
    )


    # --------------------------------------------------------
    # GENERAR QR
    # --------------------------------------------------------

    qr.make(
        fit=True
    )


    # --------------------------------------------------------
    # CREAR IMAGEN
    # --------------------------------------------------------

    imagen = qr.make_image(

        fill_color="black",

        back_color="white"

    )


    # --------------------------------------------------------
    # GUARDAR
    # --------------------------------------------------------

    imagen.save(
        ruta_archivo
    )


    # --------------------------------------------------------
    # VERIFICAR
    # --------------------------------------------------------

    if not ruta_archivo.exists():

        raise RuntimeError(
            "No se pudo crear el archivo QR."
        )


    # --------------------------------------------------------
    # INFORMACIÓN
    # --------------------------------------------------------

    print()
    print("==========================================")
    print("QR GENERADO CORRECTAMENTE")
    print("Matrícula:", matricula)
    print("Archivo:", nombre_archivo)
    print("Ruta:", ruta_archivo)
    print("==========================================")
    print()


    return nombre_archivo

# ============================================================
# GENERAR QR DE PERSONAL
# ============================================================

def generar_qr_personal(
    numero_empleado
):

    numero_empleado = str(
        numero_empleado
    ).strip()


    if not numero_empleado:

        raise ValueError(
            "El número de empleado no puede estar vacío."
        )


    # --------------------------------------------------------
    # NOMBRE DEL ARCHIVO
    # --------------------------------------------------------

    nombre_archivo = f"qr_personal_{quote(numero_empleado, safe='')}.png"


    # --------------------------------------------------------
    # RUTA
    # --------------------------------------------------------

    ruta_archivo = (
        UPLOADS_DIR /
        nombre_archivo
    )


    # --------------------------------------------------------
    # CONTENIDO DEL QR
    # --------------------------------------------------------

    contenido = numero_empleado


    # --------------------------------------------------------
    # CONFIGURACIÓN DEL QR
    # --------------------------------------------------------

    qr = qrcode.QRCode(

        version=1,

        error_correction=(
            qrcode.constants.ERROR_CORRECT_M
        ),

        box_size=10,

        border=4

    )


    qr.add_data(
        contenido
    )


    qr.make(
        fit=True
    )


    # --------------------------------------------------------
    # CREAR IMAGEN
    # --------------------------------------------------------

    imagen = qr.make_image(

        fill_color="black",

        back_color="white"

    )


    # --------------------------------------------------------
    # GUARDAR
    # --------------------------------------------------------

    imagen.save(
        ruta_archivo
    )


    # --------------------------------------------------------
    # VERIFICAR
    # --------------------------------------------------------

    if not ruta_archivo.exists():

        raise RuntimeError(
            "No se pudo crear el archivo QR del personal."
        )


    print()
    print("==========================================")
    print("QR DE PERSONAL GENERADO CORRECTAMENTE")
    print("Número de empleado:", numero_empleado)
    print("Archivo:", nombre_archivo)
    print("Ruta:", ruta_archivo)
    print("==========================================")
    print()


    return nombre_archivo


def generar_qr_credencial_especial(referencia):
    """Genera un QR con un prefijo propio para evitar confundirlo con alumnos o personal."""
    referencia = str(referencia or "").strip()
    if not referencia:
        raise ValueError("La referencia de credencial no puede estar vacía.")
    nombre_archivo = f"qr_especial_{quote(referencia, safe='')}.png"
    ruta_archivo = UPLOADS_DIR / nombre_archivo
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(f"SICAE-ESPECIAL:{referencia}")
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(ruta_archivo)
    return nombre_archivo
