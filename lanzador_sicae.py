"""Arranca SICAE desde su propia carpeta, incluso si se mueve de equipo."""

import os
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn


BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
HOST = os.environ.get("SICAE_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
URL = f"http://127.0.0.1:{PORT}/"


def iniciar_servidor():
    uvicorn.run("main:app", host=HOST, port=PORT)


if __name__ == "__main__":
    servidor = threading.Thread(target=iniciar_servidor, daemon=True)
    servidor.start()

    limite = time.monotonic() + 30
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(URL, timeout=2):
                webbrowser.open(URL)
                break
        except (OSError, urllib.error.URLError):
            if not servidor.is_alive():
                raise SystemExit(
                    "SICAE no pudo iniciar. Revisa la consola y la configuracion de PostgreSQL."
                )
            time.sleep(0.5)
    else:
        raise SystemExit(
            "SICAE no respondio en 30 segundos. Revisa la consola y PostgreSQL."
        )

    servidor.join()
