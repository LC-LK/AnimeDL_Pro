"""
Módulo de gestión del navegador.
Encargado de la inicialización y configuración de Playwright y sus navegadores.
Optimizado para rendimiento y evasión de detección.
"""
import os
import sys
import subprocess

# Argumentos optimizados para Chromium headless - rendimiento + stealth
BROWSER_LAUNCH_ARGS = [
    "--headless=new",
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-site-isolation-trials",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-client-side-phishing-detection",
    "--disable-component-extensions-with-background-pages",
    "--disable-domain-reliability",
    "--disable-features=TranslateUI",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-renderer-backgrounding",
    "--disable-search-engine-choice-screen",
    "--enable-features=NetworkService,NetworkServiceInProcess",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--no-first-run",
    "--no-default-browser-check",
    "--no-pings",
    "--password-store=basic",
    "--use-mock-keychain",
    "--window-size=1280,720",
]

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
    Crea y devuelve una instancia configurada de un navegador headless optimizada.
    Permite una instalación automática y silenciosa si los binarios no existen.
    """
    try:
        # Configurar ruta de navegadores para entorno .exe
        if getattr(sys, 'frozen', False):
            user_local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(user_local_appdata, "ms-playwright")
            
        # Intentar lanzamiento normal con args optimizados
        return await p.chromium.launch(headless=True, args=BROWSER_LAUNCH_ARGS)
    except Exception as e:
        # Si falla en el .exe o por falta de binarios, intentamos instalarlos
        if "executable doesn't exist" in str(e).lower() or getattr(sys, 'frozen', False):
            msg = "[!] Navegador no encontrado. Instalando componentes necesarios (esto puede tardar unos minutos)..."
            print(msg)
            if logger:
                logger(msg, type="warning")
                
            if ensure_playwright_browsers():
                try:
                    return await p.chromium.launch(headless=True, args=BROWSER_LAUNCH_ARGS)
                except Exception as e2:
                    raise Exception(f"Error tras instalación: {str(e2)}")
        
        raise Exception(f"Playwright no pudo encontrar Chromium. Por favor, asegúrate de tener conexión a internet. Error: {str(e)}")
