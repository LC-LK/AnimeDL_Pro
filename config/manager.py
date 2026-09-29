"""
Módulo de gestión de configuración.
Este módulo maneja la carga, guardado y localización del archivo de configuración JSON.
"""
import os
import sys
import json
import re
import asyncio
from threading import Lock

# Estado para debounce de guardado
_save_buffer = None
_save_task = None
_save_lock = Lock()
_debounce_delay = 0.5  # 500ms

def get_config_path():
    """
    Obtiene la ruta absoluta del archivo de configuración.
    
    Determina la ubicación adecuada para 'config.json' basándose en si la aplicación
    se está ejecutando como un script de Python o como un ejecutable congelado (PyInstaller).
    
    Returns:
        str: Ruta absoluta completa al archivo de configuración.
    """
    if getattr(sys, 'frozen', False):
        # En el .exe, primero intentamos en la carpeta del ejecutable
        exe_dir = os.path.dirname(sys.executable)
        # Si estamos en AppData (PyInstaller por defecto a veces usa carpetas temporales), 
        # mejor usar una carpeta fija en el usuario para persistencia real
        if "AppData" in exe_dir:
            user_config_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AnimeDownloader")
            os.makedirs(user_config_dir, exist_ok=True)
            return os.path.join(user_config_dir, "config.json")
        return os.path.join(exe_dir, "config.json")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.json")

CONFIG_FILE = get_config_path()

def _get_config_file():
    """Retorna la ruta del archivo de config (para tests y runtime)."""
    return CONFIG_FILE

# Lista de User-Agents modernos y diversos para rotar en peticiones HTTP/Playwright
# Incluye Chrome 126+, Firefox 128+, Edge 126+, Safari 17+ en Windows/macOS/Linux
USER_AGENTS = [
    # Chrome 126+ Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome 126+ Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome 126+ macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox 128+ Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    # Firefox 128+ Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    # Firefox 128+ macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    # Edge 126+ (Chromium-based)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Safari 17+ macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
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
    
    if os.path.exists(_get_config_file()):
        try:
            with open(_get_config_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migración simple si es necesario
                if "history" in data and "following" not in data:
                    data["following"] = {}
                    for url, info in data["history"].items():
                        base_url = re.sub(r'\d+/$', '', url)
                        data["following"][base_url] = info
                        data["following"][base_url]["last_url"] = url
                return data
        except json.JSONDecodeError as e:
            print(f"Error decodificando config.json: {e}")
            # Si el archivo está corrupto, quizás sea mejor no sobreescribirlo con defaults
            # pero por ahora devolvemos defaults para que la app no explote
            return default_config
        except Exception as e:
            print(f"Error cargando config.json: {e}")
            return default_config
    return default_config

async def _save_immediate(config):
    """Escritura inmediata a disco (sin debounce). Usar para cleanup/export."""
    try:
        with open(_get_config_file(), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando config.json: {e}")
        return False

def _schedule_debounced_save(config, loop):
    """Programa escritura debounced (500ms). Seguro para hilos."""
    global _save_buffer, _save_task
    with _save_lock:
        _save_buffer = config
        if _save_task and not _save_task.done():
            _save_task.cancel()
        async def _debounced_write():
            try:
                await asyncio.sleep(_debounce_delay)
                with _save_lock:
                    if _save_buffer is not None:
                        await _save_immediate(_save_buffer)
                        _save_buffer = None
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Error en debounced save: {e}")
        _save_task = asyncio.create_task(_debounced_write())

def save_config(config):
    """
    Guarda la configuración con debounce (500ms).
    Para guardado inmediato, usar force_save().
    
    Args:
        config (dict): Diccionario de configuración a persistir.
        
    Returns:
        bool: True si se programó correctamente (la escritura real es asíncrona).
    """
    try:
        # Intentar obtener loop actual; si no hay, crear tarea en loop nuevo
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No hay loop corriendo (ej. llamado desde hilo sync)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        _schedule_debounced_save(config, loop)
        return True
    except Exception as e:
        print(f"Error programando save_config: {e}")
        return False

async def force_save(config):
    """
    Guarda la configuración INMEDIATAMENTE (sin debounce).
    Usar en: cierre de app, export, cambios críticos.
    
    Args:
        config (dict): Diccionario de configuración a persistir.
        
    Returns:
        bool: True si el guardado fue exitoso.
    """
    global _save_buffer, _save_task
    with _save_lock:
        # Cancelar cualquier write pendiente
        if _save_task and not _save_task.done():
            _save_task.cancel()
        _save_buffer = None
    return await _save_immediate(config)


def _get_config_file():
    """Retorna la ruta del archivo de config (para tests)."""
    return CONFIG_FILE


def reset_config_manager():
    """Resetea el estado del debounce (para tests)."""
    global _save_buffer, _save_task
    with _save_lock:
        _save_buffer = None
        if _save_task and not _save_task.done():
            _save_task.cancel()


def save_config_sync(config):
    """
    Guarda la configuración de forma SÍNCRONA (para tests/legacy).
    No usa debounce.
    """
    try:
        with open(_get_config_file(), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando config.json (sync): {e}")
        return False
