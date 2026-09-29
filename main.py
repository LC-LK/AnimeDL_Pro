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

# Referencia global para cleanup
_app_instance = None

async def on_window_close(e):
    """Cleanup al cerrar la ventana."""
    global _app_instance
    if _app_instance:
        # Guardar config INMEDIATAMENTE (force save)
        from config.manager import force_save
        await force_save(_app_instance.config)
        # Cerrar browser context
        await _app_instance.close_browser()
        # Cerrar sesión aiohttp
        await _app_instance.downloader.close_session()
        # Cerrar connector compartido
        from core.downloader import close_shared_connector
        await close_shared_connector()
        _app_instance = None

def main(page: ft.Page):
    """
    Función de arranque.
    """
    global _app_instance
    _app_instance = AnimeDownloaderApp(page)
    page.on_window_event = lambda e: asyncio.create_task(on_window_close(e)) if e.data == "close" else None

if __name__ == "__main__":
    # Soporte crítico para PyInstaller y multiprocessing
    multiprocessing.freeze_support()

    # Configuración de entorno para el ejecutable (.exe)
    if getattr(sys, 'frozen', False):
        user_local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(user_local_appdata, "ms-playwright")

    # Iniciar la aplicación Flet con soporte para assets
    # Definimos la carpeta raíz del proyecto como assets_dir para encontrar src/img
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ft.app(target=main, assets_dir=base_dir)
