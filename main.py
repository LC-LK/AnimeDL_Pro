"""
Punto de entrada principal de la aplicación AnimeDL.
Inicializa el entorno y lanza la interfaz de usuario de Flet.
"""
import flet as ft
import asyncio
import os
import sys
import multiprocessing
import ssl
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except ImportError:
    pass

from ui.app import AnimeDownloaderApp

# Parche global para errores de SSL en entornos sin certificados (común en Windows limpio)
# Se aplica antes de iniciar Flet para que afecte a la descarga de binarios si es necesaria.
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

def main(page: ft.Page):
    """
    Función de arranque.
    """
    AnimeDownloaderApp(page)

if __name__ == "__main__":
    # Soporte crítico para PyInstaller y multiprocessing
    multiprocessing.freeze_support()

    # Configuración de entorno para el ejecutable (.exe)
    if getattr(sys, 'frozen', False):
        user_local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(user_local_appdata, "ms-playwright")

    # Iniciar la aplicación Flet
    ft.app(target=main)
