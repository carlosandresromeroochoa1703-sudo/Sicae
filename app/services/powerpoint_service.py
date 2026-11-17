"""Render PowerPoint slides to PNG without rebuilding their visual elements."""

import os
import shutil
import subprocess
import tempfile
import zipfile
from xml.etree import ElementTree
from pathlib import Path

from PIL import Image


_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_EMU_PER_INCH = 914400


def _cantidad_diapositivas(origen: Path) -> int:
    with zipfile.ZipFile(origen) as paquete:
        presentacion = ElementTree.fromstring(paquete.read("ppt/presentation.xml"))
    lista = presentacion.find(f"{{{_P_NS}}}sldIdLst")
    return len(list(lista)) if lista is not None else 0


def _separar_una_diapositiva(origen: Path, imagen_completa: Path, destino_frente: Path, destino_reverso: Path) -> None:
    """Crop a one-slide, side-by-side front/back card design into two faces."""
    with zipfile.ZipFile(origen) as paquete:
        presentacion = ElementTree.fromstring(paquete.read("ppt/presentation.xml"))
        medidas = presentacion.find(f"{{{_P_NS}}}sldSz")
        diapositiva = ElementTree.fromstring(paquete.read("ppt/slides/slide1.xml"))
    if medidas is None:
        raise RuntimeError("No se pudo leer el tamaño de la diapositiva.")
    ancho_diapo = int(medidas.attrib.get("cx", 0))
    alto_diapo = int(medidas.attrib.get("cy", 0))
    arbol = diapositiva.find(f".//{{{_P_NS}}}spTree")
    if not ancho_diapo or not alto_diapo or arbol is None:
        raise RuntimeError("No se pudo localizar el diseño de las dos caras en la diapositiva.")

    candidatos = []
    for forma in list(arbol):
        transformacion = forma.find(f"{{{_P_NS}}}spPr/{{{_A_NS}}}xfrm")
        if transformacion is None:
            transformacion = forma.find(f"{{{_P_NS}}}grpSpPr/{{{_A_NS}}}xfrm")
        if transformacion is None:
            transformacion = forma.find(f"{{{_P_NS}}}xfrm")
        if transformacion is None:
            continue
        desplazamiento = transformacion.find(f"{{{_A_NS}}}off")
        extension = transformacion.find(f"{{{_A_NS}}}ext")
        if desplazamiento is None or extension is None:
            continue
        x = int(desplazamiento.attrib.get("x", 0))
        y = int(desplazamiento.attrib.get("y", 0))
        ancho = int(extension.attrib.get("cx", 0))
        alto = int(extension.attrib.get("cy", 0))
        proporcion = ancho / alto if alto else 0
        # Dos tarjetas horizontales juntas suelen ocupar entre 2.5 y 4.5 veces
        # su altura. Elegir la mayor forma de esa proporción evita usar la hoja.
        if ancho > 0 and alto > 0 and 2.5 <= proporcion <= 4.5:
            candidatos.append((ancho * alto, x, y, ancho, alto))
    if not candidatos:
        raise RuntimeError("La diapositiva única no contiene dos caras colocadas lado a lado. Separa frente y reverso en dos diapositivas.")

    _, x, y, ancho, alto = max(candidatos)
    with Image.open(imagen_completa) as imagen:
        caja = (
            max(0, round(x * imagen.width / ancho_diapo)),
            max(0, round(y * imagen.height / alto_diapo)),
            min(imagen.width, round((x + ancho) * imagen.width / ancho_diapo)),
            min(imagen.height, round((y + alto) * imagen.height / alto_diapo)),
        )
        compuesto = imagen.crop(caja)
        if compuesto.width < 2 or compuesto.height < 2:
            raise RuntimeError("No se pudo recortar el área de las credenciales.")
        mitad = compuesto.width // 2
        compuesto.crop((0, 0, mitad, compuesto.height)).save(destino_frente, format="PNG")
        compuesto.crop((mitad, 0, compuesto.width, compuesto.height)).save(destino_reverso, format="PNG")


def convertir_pptx_a_png(origen: Path, destino: Path, timeout: int = 120) -> None:
    origen = Path(origen).resolve()
    destino = Path(destino).resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if not powershell:
            raise RuntimeError("No se encontró PowerShell para exportar la diapositiva.")
        script = destino.parent / "exportar_diapositiva.ps1"
        script.write_text(
            "param([string]$InputPath, [string]$OutputPath)\n"
            "$ErrorActionPreference = 'Stop'\n"
            "$ppt = $null; $presentation = $null\n"
            "try {\n"
            "  $ppt = New-Object -ComObject PowerPoint.Application\n"
            "  $ppt.Visible = -1\n"
            "  $presentation = $ppt.Presentations.Open($InputPath, $true, $false, $false)\n"
            "  if ($presentation.Slides.Count -lt 1) { throw 'La presentación no tiene diapositivas.' }\n"
            "  $slide = $presentation.Slides.Item(1)\n"
            "  $ratio = $presentation.PageSetup.SlideHeight / $presentation.PageSetup.SlideWidth\n"
            "  if ($ratio -le 1) { $width = 1600; $height = [int][Math]::Round(1600 * $ratio) } else { $height = 1600; $width = [int][Math]::Round(1600 / $ratio) }\n"
            "  $slide.Export($OutputPath, 'PNG', $width, $height)\n"
            "} finally {\n"
            "  if ($presentation -ne $null) { $presentation.Close() }\n"
            "  if ($ppt -ne $null) { $ppt.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) }\n"
            "}\n",
            encoding="utf-8",
        )
        resultado = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), str(origen), str(destino)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if resultado.returncode != 0:
            raise RuntimeError((resultado.stderr or resultado.stdout or "PowerPoint no pudo exportar la diapositiva.")[-1200:])
    else:
        libreoffice = shutil.which("libreoffice") or shutil.which("soffice")
        pdftoppm = shutil.which("pdftoppm")
        if not libreoffice or not pdftoppm:
            raise RuntimeError("El servidor necesita LibreOffice Impress y Poppler para convertir archivos PowerPoint.")
        with tempfile.TemporaryDirectory(prefix="sicae-pptx-") as directorio:
            temporal = Path(directorio)
            perfil = (temporal / "perfil").as_uri()
            resultado = subprocess.run(
                [libreoffice, "--headless", f"-env:UserInstallation={perfil}", "--convert-to", "pdf", "--outdir", str(temporal), str(origen)],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            pdf = temporal / f"{origen.stem}.pdf"
            if resultado.returncode != 0 or not pdf.exists():
                raise RuntimeError((resultado.stderr or resultado.stdout or "LibreOffice no pudo convertir la presentación.")[-1200:])
            resultado = subprocess.run(
                [pdftoppm, "-f", "1", "-l", "1", "-singlefile", "-png", "-scale-to", "1600", str(pdf), str(temporal / "diapositiva")],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            png = temporal / "diapositiva.png"
            if resultado.returncode != 0 or not png.exists():
                raise RuntimeError((resultado.stderr or resultado.stdout or "No se pudo rasterizar la diapositiva.")[-1200:])
            shutil.copyfile(png, destino)

    if not destino.exists() or destino.stat().st_size == 0:
        raise RuntimeError("No se generó la imagen de la diapositiva.")


def convertir_pptx_a_dos_png(origen: Path, destino_frente: Path, destino_reverso: Path, timeout: int = 120) -> None:
    """Render two slides or split a single slide with side-by-side card faces."""
    origen = Path(origen).resolve()
    destino_frente = Path(destino_frente).resolve()
    destino_reverso = Path(destino_reverso).resolve()
    destino_frente.parent.mkdir(parents=True, exist_ok=True)
    destino_reverso.parent.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if not powershell:
            raise RuntimeError("No se encontró PowerShell para exportar las diapositivas.")
        script = destino_frente.parent / "exportar_dos_caras.ps1"
        ruta_unica = destino_frente.parent / "diapositiva_unica.png"
        script.write_text(
            "param([string]$InputPath, [string]$FrontPath, [string]$BackPath, [string]$SinglePath)\n"
            "$ErrorActionPreference = 'Stop'\n"
            "$ppt = $null; $presentation = $null\n"
            "try {\n"
            "  $ppt = New-Object -ComObject PowerPoint.Application\n"
            "  $ppt.Visible = -1\n"
            "  $presentation = $ppt.Presentations.Open($InputPath, $true, $false, $false)\n"
            "  $ratio = $presentation.PageSetup.SlideHeight / $presentation.PageSetup.SlideWidth\n"
            "  if ($ratio -le 1) { $width = 2000; $height = [int][Math]::Round(2000 * $ratio) } else { $height = 2000; $width = [int][Math]::Round(2000 / $ratio) }\n"
            "  if ($presentation.Slides.Count -ge 2) {\n"
            "    $presentation.Slides.Item(1).Export($FrontPath, 'PNG', $width, $height)\n"
            "    $presentation.Slides.Item(2).Export($BackPath, 'PNG', $width, $height)\n"
            "  } else {\n"
            "    $presentation.Slides.Item(1).Export($SinglePath, 'PNG', $width, $height)\n"
            "  }\n"
            "} finally {\n"
            "  if ($presentation -ne $null) { $presentation.Close() }\n"
            "  if ($ppt -ne $null) { $ppt.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) }\n"
            "}\n",
            encoding="utf-8",
        )
        resultado = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), str(origen), str(destino_frente), str(destino_reverso), str(ruta_unica)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if resultado.returncode != 0:
            raise RuntimeError((resultado.stderr or resultado.stdout or "PowerPoint no pudo exportar las dos diapositivas.")[-1200:])
        if _cantidad_diapositivas(origen) < 2:
            if not ruta_unica.exists():
                raise RuntimeError("PowerPoint no pudo exportar la diapositiva que contiene las dos caras.")
            _separar_una_diapositiva(origen, ruta_unica, destino_frente, destino_reverso)
    else:
        libreoffice = shutil.which("libreoffice") or shutil.which("soffice")
        pdftoppm = shutil.which("pdftoppm")
        if not libreoffice or not pdftoppm:
            raise RuntimeError("El servidor necesita LibreOffice Impress y Poppler para convertir PowerPoint.")
        with tempfile.TemporaryDirectory(prefix="sicae-pptx-duplex-") as directorio:
            temporal = Path(directorio)
            perfil = (temporal / "perfil").as_uri()
            resultado = subprocess.run(
                [libreoffice, "--headless", f"-env:UserInstallation={perfil}", "--convert-to", "pdf", "--outdir", str(temporal), str(origen)],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            pdf = temporal / f"{origen.stem}.pdf"
            if resultado.returncode != 0 or not pdf.exists():
                raise RuntimeError((resultado.stderr or resultado.stdout or "LibreOffice no pudo convertir la presentación.")[-1200:])
            cantidad = _cantidad_diapositivas(origen)
            if cantidad < 2:
                prefijo = temporal / "diapositiva-unica"
                resultado = subprocess.run(
                    [pdftoppm, "-f", "1", "-l", "1", "-singlefile", "-png", "-scale-to", "2000", str(pdf), str(prefijo)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                imagen = prefijo.with_suffix(".png")
                if resultado.returncode != 0 or not imagen.exists():
                    raise RuntimeError((resultado.stderr or resultado.stdout or "No se pudo rasterizar la diapositiva.")[-1200:])
                _separar_una_diapositiva(origen, imagen, destino_frente, destino_reverso)
            else:
                for pagina, destino in ((1, destino_frente), (2, destino_reverso)):
                    prefijo = temporal / f"cara-{pagina}"
                    resultado = subprocess.run(
                        [pdftoppm, "-f", str(pagina), "-l", str(pagina), "-singlefile", "-png", "-scale-to", "2000", str(pdf), str(prefijo)],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=False,
                    )
                    imagen = prefijo.with_suffix(".png")
                    if resultado.returncode != 0 or not imagen.exists():
                        raise RuntimeError((resultado.stderr or resultado.stdout or "Las primeras dos diapositivas no se pudieron exportar.")[-1200:])
                    shutil.copyfile(imagen, destino)

    for destino in (destino_frente, destino_reverso):
        if not destino.exists() or destino.stat().st_size == 0:
            raise RuntimeError("No se generaron las dos imágenes de las caras de la credencial.")
