"""
Módulo de gestión del navegador.
Encargado de la inicialización y configuración de Playwright y sus navegadores.
"""
import os
import sys
import subprocess

def ensure_playwright_browsers():
    """
    Verifica e instala los binarios necesarios de Chromium para Playwright.
    """
    try:
        # Asegurar que la variable de entorno esté configurada antes de cualquier operación
        if getattr(sys, 'frozen', False):
            user_local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(user_local_appdata, "ms-playwright")

        # IMPORTANTE: En el .exe NO debemos llamar a sys.executable de forma recursiva
        # porque sys.executable es el propio .exe y causaría un bucle infinito.
        if getattr(sys, 'frozen', False):
            try:
                # Intentamos la instalación usando la API interna de playwright directamente
                from playwright.__main__ import main as playwright_main
                import sys as _sys
                
                # Guardar args originales para restaurarlos después
                old_args = _sys.argv
                # Simulamos la llamada: playwright install chromium
                _sys.argv = ["playwright", "install", "chromium"]
                try:
                    # Esto ejecuta la lógica de instalación dentro del mismo proceso
                    playwright_main()
                finally:
                    _sys.argv = old_args
            except Exception as e:
                print(f"Error en instalación interna: {e}")
                # Si falla lo anterior, como último recurso intentamos llamar a un comando de sistema
                # pero NUNCA al propio ejecutable (sys.executable)
                subprocess.run(["cmd.exe", "/c", "playwright install chromium"], 
                             shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            # En modo script (desarrollo), el comportamiento estándar es seguro
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                         check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Error al asegurar navegadores: {e}")
        return False

async def get_browser_instance(p):
    """
    Crea y devuelve una instancia configurada de un navegador headless.
    """
    try:
        # Configurar ruta de navegadores para entorno .exe
        if getattr(sys, 'frozen', False):
            user_local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(user_local_appdata, "ms-playwright")
            
        # Intentar lanzamiento normal
        return await p.chromium.launch(headless=True)
    except Exception as e:
        # Si falla en el .exe, es probable que falten los binarios
        if getattr(sys, 'frozen', False):
            print(f"Navegador no encontrado. Intentando instalación silenciosa...")
            if ensure_playwright_browsers():
                try:
                    return await p.chromium.launch(headless=True)
                except Exception as e2:
                    raise Exception(f"Error tras instalación: {str(e2)}")
        
        raise Exception(f"Playwright no pudo encontrar Chromium. Por favor, asegúrate de tener conexión a internet. Error: {str(e)}")
