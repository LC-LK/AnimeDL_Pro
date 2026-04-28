"""
Punto de entrada principal de la aplicación AnimeDL.
Inicializa el entorno y lanza la interfaz de usuario de Flet.
"""
import flet as ft
import asyncio
import os
import sys
import multiprocessing
from ui.app import AnimeDownloaderApp

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
