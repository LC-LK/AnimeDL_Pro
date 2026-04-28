"""
Módulo de utilidades generales.
Contiene funciones auxiliares para manejo de rutas y carga diferida de módulos.
"""
import os
import sys
import time

# Marcador de tiempo de inicio de la aplicación para cálculos de rendimiento
START_TIME = time.time()

# Referencias globales para módulos cargados bajo demanda (Lazy Loading)
async_playwright = None
aiohttp = None

def resource_path(relative_path):
    """
    Obtiene la ruta absoluta para un recurso, compatible con PyInstaller.
    
    Esta función permite acceder a archivos incluidos en el paquete (imágenes, iconos, etc.)
    independientemente de si la aplicación se ejecuta como script o ejecutable congelado.
    
    Args:
        relative_path (str): La ruta relativa del archivo dentro del proyecto.
        
    Returns:
        str: Ruta absoluta completa al recurso solicitado.
    """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def lazy_import_network():
    """
    Carga dinámicamente los módulos pesados de red (Playwright y aiohttp).
    
    Se utiliza para reducir el tiempo de arranque inicial de la interfaz de usuario,
    postergando la importación de bibliotecas grandes hasta que realmente se necesiten
    para una operación de descarga o scraping.
    
    Returns:
        tuple: Una tupla conteniendo (async_playwright, aiohttp).
    """
    global async_playwright, aiohttp
    if async_playwright is None:
        from playwright.async_api import async_playwright as _ap
        async_playwright = _ap
    if aiohttp is None:
        import aiohttp as _ah
        aiohttp = _ah
    return async_playwright, aiohttp
