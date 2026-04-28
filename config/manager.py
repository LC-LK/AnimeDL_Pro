"""
Módulo de gestión de configuración.
Este módulo maneja la carga, guardado y localización del archivo de configuración JSON.
"""
import os
import sys
import json
import re

def get_config_path():
    """
    Obtiene la ruta absoluta del archivo de configuración.
    
    Determina la ubicación adecuada para 'config.json' basándose en si la aplicación
    se está ejecutando como un script de Python o como un ejecutable congelado (PyInstaller).
    
    Returns:
        str: Ruta absoluta completa al archivo de configuración.
    """
    if getattr(sys, 'frozen', False):
        # En el .exe, guardamos en la misma carpeta que el ejecutable para portabilidad
        return os.path.join(os.path.dirname(sys.executable), "config.json")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.json")

CONFIG_FILE = get_config_path()

# Lista de User-Agents para rotar en las peticiones HTTP
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def load_config():
    """
    Carga la configuración y el historial desde el archivo JSON.
    
    Si el archivo no existe, se crea una configuración por defecto. También maneja
    migraciones de esquemas de datos antiguos si se detectan.
    
    Returns:
        dict: Diccionario que contiene la configuración de la aplicación y el historial de anime.
    """
    default_config = {
        "following": {}, # { "anime_base_url": { "alias": "...", "last_chapter": 0, "last_url": "..." } }
        "settings": {
            "default_dir": os.getcwd(),
            "auto_check": True,
            "view_mode": "list",
            "grid_size": 150
        }
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migración simple si es necesario
                if "history" in data and "following" not in data:
                    data["following"] = {}
                    for url, info in data["history"].items():
                        base_url = re.sub(r'\d+/$', '', url)
                        data["following"][base_url] = info
                        data["following"][base_url]["last_url"] = url
                return data
        except Exception:
            pass
    return default_config

def save_config(config):
    """
    Guarda el estado actual de la configuración en el archivo JSON.
    
    Args:
        config (dict): El diccionario de configuración completo que se desea persistir.
        
    Returns:
        bool: True si el guardado fue exitoso, False en caso contrario.
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False
