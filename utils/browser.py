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
    Evita bucles infinitos y cierres inesperados en entornos congelados (.exe).
    """
    try:
        # Configurar ruta de navegadores para entorno .exe (User/AppData/Local/ms-playwright)
        if getattr(sys, 'frozen', False):
            user_local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(user_local_appdata, "ms-playwright")

        if getattr(sys, 'frozen', False):
            try:
                # IMPORTANTE: playwright.main() llama a sys.exit() al terminar.
                # Debemos capturar SystemExit para que el .exe no se cierre tras instalar.
                from playwright.__main__ import main as playwright_main
                import sys as _sys
                
                old_args = _sys.argv
                _sys.argv = ["playwright", "install", "chromium"]
                
                print("[*] Iniciando instalación de Chromium...")
                try:
                    playwright_main()
                except SystemExit:
                    # Capturamos el exit de Playwright para continuar con nuestra App
                    print("[+] Instalación completada (SystemExit capturado).")
                finally:
                    _sys.argv = old_args
            except Exception as e:
                print(f"[!] Error en instalación interna: {e}")
                # Fallback a comando de sistema si falla lo anterior
                subprocess.run(["cmd.exe", "/c", "playwright install chromium"], 
                             shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            # En modo desarrollo usamos el ejecutable de python
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                         check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"[!] Error crítico al asegurar navegadores: {e}")
        return False

async def get_browser_instance(p, logger=None):
    """
    Crea y devuelve una instancia configurada de un navegador headless.
    Permite una instalación automática y silenciosa si los binarios no existen.
    """
    try:
        # Configurar ruta de navegadores para entorno .exe
        if getattr(sys, 'frozen', False):
            user_local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(user_local_appdata, "ms-playwright")
            
        # Intentar lanzamiento normal
        return await p.chromium.launch(headless=True)
    except Exception as e:
        # Si falla en el .exe o por falta de binarios, intentamos instalarlos
        if "executable doesn't exist" in str(e).lower() or getattr(sys, 'frozen', False):
            msg = "[!] Navegador no encontrado. Instalando componentes necesarios (esto puede tardar unos minutos)..."
            print(msg)
            if logger:
                logger(msg, type="warning")
                
            if ensure_playwright_browsers():
                try:
                    return await p.chromium.launch(headless=True)
                except Exception as e2:
                    raise Exception(f"Error tras instalación: {str(e2)}")
        
        raise Exception(f"Playwright no pudo encontrar Chromium. Por favor, asegúrate de tener conexión a internet. Error: {str(e)}")
