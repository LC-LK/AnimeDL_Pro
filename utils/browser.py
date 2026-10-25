"""
Módulo de gestión del navegador.
Encargado de la inicialización y configuración de Playwright y sus navegadores.
Optimizado para rendimiento y evasión de detección de Cloudflare.
"""
import os
import sys
import subprocess

# UA fijo y coherente con el perfil (Chrome desktop). Se usa el MISMO UA en cabeceras,
# en navigator.userAgent y en los client-hints para no delatar un fingerprint híbrido.
STEALTH_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

# Client-hints que deben coincidir con STEALTH_UA (si no, Cloudflare detecta el mismatch).
STEALTH_HEADERS = {
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Sec-CH-UA": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}

# Script que se inyecta antes de cualquier script de la página para ocultar señales de automatización.
STEALTH_JS = r"""
// navigator.webdriver -> undefined (la señal de bot más clásica)
try {
  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  delete Object.getPrototypeOf(navigator).webdriver;
} catch (e) {}

// window.chrome (Playwright headless no lo expone por defecto)
try {
  if (!window.chrome) { window.chrome = {}; }
  if (!window.chrome.runtime) { window.chrome.runtime = {}; }
} catch (e) {}

// Idiomas coherentes con Accept-Language
try {
  Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en-US', 'en'] });
} catch (e) {}

// Plugins "reales" (headless devuelve lista vacía)
try {
  const fakePlugins = [
    { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
    { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
    { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
  ];
  Object.defineProperty(navigator, 'plugins', { get: () => fakePlugins });
  Object.defineProperty(navigator, 'mimeTypes', { get: () => [{ type: 'application/pdf' }] });
} catch (e) {}

// Client-hints del side JS alineados con las cabeceras HTTP
try {
  const brands = [
    { brand: 'Chromium', version: '130' },
    { brand: 'Google Chrome', version: '130' },
    { brand: 'Not?A_Brand', version: '24' },
  ];
  Object.defineProperty(navigator, 'userAgentData', {
    get: () => ({ brands: brands, mobile: false, platform: 'Windows' })
  });
} catch (e) {}

// permissions.query('notifications') debe reflejar Notification.permission (headless devuelve 'denied' raro)
try {
  if (navigator.permissions && navigator.permissions.query) {
    const originalQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (params) => (
      params && params.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(params)
    );
  }
} catch (e) {}

// WebGL vendor/renderer genéricos (evita "Google SwiftShader" = headless)
try {
  const getParameter = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function (p) {
    if (p === 37445) return 'Intel Inc.';
    if (p === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, p);
  };
} catch (e) {}
"""

# Argumentos de Chromium: rendimiento + estabilidad + evasión.
# NOTA: se han eliminado los flags que ROMPÍAN el challenge de Cloudflare o delataban automatización:
#   --single-process / --no-zygote  -> rompen los workers/iframes que usa Turnstile
#   --disable-web-security          -> huella de bot evidente
#   --disable-features=IsolateOrigins,site-per-process -> rompe el iframe cross-origin de Turnstile
#   --disable-http2                 -> Cabecera/protocolo distinto al de un navegador real
BROWSER_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-breakpad",
    "--disable-client-side-phishing-detection",
    "--disable-component-extensions-with-background-pages",
    "--disable-domain-reliability",
    "--disable-features=TranslateUI",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-search-engine-choice-screen",
    "--enable-features=NetworkService,NetworkServiceInProcess",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--no-first-run",
    "--no-default-browser-check",
    "--no-pings",
    "--password-store=basic",
    "--use-mock-keychain",
    "--window-size=1920,1080",
    "--hide-scrollbars",
    "--mute-audio",
    "--lang=es-ES",
]


def ensure_playwright_browsers():
    """
    Verifica e instala los binarios necesarios de Chromium para Playwright.
    Evita bucles infinitos y cierres inesperados en entornos congelados (.exe).
    """
    try:
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
                    print("[+] Instalación completada (SystemExit capturado).")
                finally:
                    _sys.argv = old_args
            except Exception as e:
                print(f"[!] Error en instalación interna: {e}")
                subprocess.run(["cmd.exe", "/c", "playwright install chromium"],
                               shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                           check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"[!] Error crítico al asegurar navegadores: {e}")
        return False


async def _apply_stealth(context):
    """Inyecta el script anti-detección en todas las páginas del contexto."""
    try:
        await context.add_init_script(STEALTH_JS)
    except Exception:
        pass
    return context


async def get_persistent_context(p, user_data_dir, logger=None):
    """
    Crea un contexto PERSISTENTE de Chromium con stealth aplicado.

    Al persistir el perfil en disco se conserva la cookie `cf_clearance` de Cloudflare
    entre ejecuciones: el challenge se resuelve una vez y luego se reutiliza.

    Returns:
        tuple: (context, browser) — browser es None en modo persistente.
    """
    if getattr(sys, 'frozen', False):
        user_local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(user_local_appdata, "ms-playwright")

    try:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            args=BROWSER_LAUNCH_ARGS,
            user_agent=STEALTH_UA,
            locale="es-ES",
            timezone_id="Europe/Madrid",
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            extra_http_headers=STEALTH_HEADERS,
        )
        await _apply_stealth(context)
        return context, None
    except Exception as e:
        # Fallback: navegador no persistente (perdemos cf_clearance pero seguimos funcionando)
        if logger:
            logger(f"[!] Contexto persistente no disponible ({str(e)[:80]}). Usando navegador normal.", type="warning")
        else:
            print(f"[!] Contexto persistente no disponible: {e}")

        if "executable doesn't exist" in str(e).lower():
            if ensure_playwright_browsers():
                pass

        browser = await p.chromium.launch(headless=True, args=BROWSER_LAUNCH_ARGS)
        context = await browser.new_context(
            user_agent=STEALTH_UA,
            locale="es-ES",
            timezone_id="Europe/Madrid",
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers=STEALTH_HEADERS,
        )
        await _apply_stealth(context)
        return context, browser
