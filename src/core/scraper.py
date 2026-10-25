"""
Módulo del Scraper de Anime.
Proporciona la lógica para navegar por JkAnime, extraer enlaces de servidores y obtener links directos de MediaFire.
Optimizado para rendimiento, estabilidad y robustez en conexiones.
Incluye cache en memoria para requests/responses de sesión.
"""
import re
import json
import base64
import os
import asyncio
import logging

# Configurar logging para debug
logger = logging.getLogger(__name__)

# Expresiones regulares pre-compiladas - MÚLTIPLES PATRONES PARA ROBUSTEZ
RE_SERVERS = [
    re.compile(r'var\s+servers\s*=\s*(\[.*?\]);', re.DOTALL),
    re.compile(r'var\s+servers\s*=\s*(\[[\s\S]*?\]);', re.DOTALL),
    re.compile(r'"servers"\s*:\s*(\[[\s\S]*?\])', re.DOTALL),
    re.compile(r'servers\s*:\s*(\[[\s\S]*?\])', re.DOTALL),
]
RE_SLUG = re.compile(r'jkanime\.net/([^/]+)/\d+/?')
RE_SLUG_MAIN = re.compile(r'jkanime\.net/([^/]+)/?$')
RE_EPISODE = re.compile(r'/(\d+)/?$')
RE_TITLE_CLEAN = re.compile(r'\s*[-–—]\s*(?:Sub\s+Espa[nñ]ol|Espa[nñ]ol|Latino|Subtitulado).*$', re.IGNORECASE)
RE_BASE_NAME = re.compile(r'\s*\d+$')

# Patrones para detectar Cloudflare Challenge (interstitial).
# IMPORTANTE: se usan patrones ESPECÍFICOS del interstitial de Cloudflare.
# No se incluye "turnstile" ni "cloudflare" genéricos porque pueden aparecer en
# páginas válidas (widget de login, footers) y provocarían falsos positivos.
RE_CF_CHALLENGE = [
    re.compile(r'__cf_chl_rt_tk', re.IGNORECASE),
    re.compile(r'cf-browser-verification', re.IGNORECASE),
    re.compile(r'challenge-platform', re.IGNORECASE),
    re.compile(r'cdn-cgi/challenge', re.IGNORECASE),
    re.compile(r'cf-chl-', re.IGNORECASE),
    re.compile(r'#challenge-running', re.IGNORECASE),
    re.compile(r'checking your browser', re.IGNORECASE),
    re.compile(r'just a moment', re.IGNORECASE),
    re.compile(r'ray id:', re.IGNORECASE),
    re.compile(r'cf-error-details', re.IGNORECASE),
]

# ============ REQUEST/RESPONSE CACHE (Sprint 2.3) ============
# Cache en memoria para la sesión actual - evita requests redundantes
# Clave: URL, Valor: datos cacheados
_request_cache = {
    "html": {},      # url -> html content
    "servers": {},   # url -> dict servers
    "next_url": {},  # url -> next_url str
    "mf_direct": {}, # mf_url -> (direct_link, ext)
}

# TTL del cache en segundos (0 = sin expiración)
_CACHE_TTL = 300
_cache_timestamps = {}

def _is_cache_valid(url, cache_type):
    """Verifica si el cache es válido según TTL."""
    if _CACHE_TTL <= 0:
        return True
    key = f"{cache_type}:{url}"
    if key not in _cache_timestamps:
        return False
    return (asyncio.get_event_loop().time() - _cache_timestamps[key]) < _CACHE_TTL

def _set_cache_timestamp(url, cache_type):
    """Establece timestamp para el cache."""
    _cache_timestamps[f"{cache_type}:{url}"] = asyncio.get_event_loop().time()

def get_cached_html(url):
    """Obtiene HTML cacheado o None."""
    if _is_cache_valid(url, "html"):
        return _request_cache["html"].get(url)
    return None

def set_cached_html(url, html):
    """Guarda HTML en cache."""
    if html and len(html) > 100:  # Solo cachear HTMLs válidos
        _request_cache["html"][url] = html
        _set_cache_timestamp(url, "html")

def get_cached_servers(url):
    """Obtiene servers cacheados o None."""
    if _is_cache_valid(url, "servers"):
        return _request_cache["servers"].get(url)
    return None

def set_cached_servers(url, servers):
    """Guarda servers en cache."""
    if servers:  # Solo cachear si hay servidores
        _request_cache["servers"][url] = servers
        _set_cache_timestamp(url, "servers")

def get_cached_next_url(url):
    """Obtiene next_url cacheado o None."""
    if _is_cache_valid(url, "next_url"):
        return _request_cache["next_url"].get(url)
    return None

def set_cached_next_url(url, next_url):
    """Guarda next_url en cache."""
    if next_url:  # Solo cachear URLs válidas
        _request_cache["next_url"][url] = next_url
        _set_cache_timestamp(url, "next_url")

def get_cached_mf_direct(mf_url):
    """Obtiene MediaFire direct link cacheado o None."""
    if _is_cache_valid(mf_url, "mf_direct"):
        return _request_cache["mf_direct"].get(mf_url)
    return None

def set_cached_mf_direct(mf_url, direct_link, ext):
    """Guarda MediaFire direct link en cache."""
    if direct_link:
        _request_cache["mf_direct"][mf_url] = (direct_link, ext)
        _set_cache_timestamp(mf_url, "mf_direct")

def clear_request_cache():
    """Limpia todo el cache de requests (para tests o nueva sesión)."""
    global _request_cache, _cache_timestamps
    _request_cache = {
        "html": {},
        "servers": {},
        "next_url": {},
        "mf_direct": {},
    }
    _cache_timestamps.clear()

def get_cache_stats():
    """Retorna estadísticas del cache."""
    return {
        "html": len(_request_cache["html"]),
        "servers": len(_request_cache["servers"]),
        "next_url": len(_request_cache["next_url"]),
        "mf_direct": len(_request_cache["mf_direct"]),
    }


def _is_cf_challenge(content: str) -> bool:
    """Detecta si el contenido es una página de Cloudflare Challenge."""
    if not content or not isinstance(content, str):
        return False
    content_lower = content.lower()
    for pattern in RE_CF_CHALLENGE:
        if pattern.search(content_lower):
            return True
    return False


# Selectores de elementos que indican que el interstitial sigue ACTIVO.
_CHALLENGE_SELECTORS = [
    '#challenge-running',
    '#cf-challenge-running',
    '.challenge-form',
    '#challenge-form',
    '[data-ray]',
    '.ray-id',
    '#turnstile',
    'iframe[src*="challenge"]',
    'iframe[src*="turnstile"]',
]

# Longitud mínima para considerar que el contenido ya es la página real y no un
# interstitial vacío o a medio cargar.
_MIN_REAL_CONTENT = 1500


async def _challenge_active(page) -> bool:
    """True si hay algún elemento visible del interstitial de Cloudflare."""
    for selector in _CHALLENGE_SELECTORS:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                return True
        except Exception:
            continue
    return False


async def _wait_for_cf_challenge(page, max_wait: int = 60) -> bool:
    """
    Espera a que se complete el Cloudflare Challenge.

    Se considera COMPLETADO únicamente cuando:
      - no queda ningún elemento visible del interstitial, Y
      - el contenido no coincide con los patrones del challenge, Y
      - el contenido tiene longitud suficiente como para ser la página real.

    Returns True si se completó, False si timeout.
    """
    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) < max_wait:
        try:
            content = await page.content()
            challenge_shown = _is_cf_challenge(content)

            if not challenge_shown and not await _challenge_active(page):
                # Guarda contra el "falso positivo": una página en blanco o a medio
                # cargar no tiene patrones de challenge pero tampoco es contenido real.
                if len(content) >= _MIN_REAL_CONTENT:
                    logger.info("Cloudflare Challenge completado (contenido real)")
                    return True
        except Exception as e:
            logger.debug(f"Error en _wait_for_cf_challenge: {e}")

        await asyncio.sleep(1.5)

    logger.warning(f"Timeout esperando Cloudflare Challenge ({max_wait}s)")
    # Último intento: verificar si ya pasó
    try:
        content = await page.content()
        if not _is_cf_challenge(content) and len(content) >= _MIN_REAL_CONTENT \
                and not await _challenge_active(page):
            return True
    except Exception:
        pass
    return False


class AnimeScraper:
    """
    Clase especializada en la extracción de datos de la plataforma JkAnime.
    
    Implementa métodos para identificar servidores de video, obtener el siguiente
    capítulo en una serie y recuperar metadatos como miniaturas de portada.
    """
    def __init__(self, context):
        """
        Inicializa el scraper con un contexto de navegador de Playwright.
        
        Args:
            context (BrowserContext): Contexto de Playwright para realizar las peticiones.
        """
        self.context = context

    async def get_server_links(self, page):
        """
        Analiza el contenido de la página para extraer los servidores de video disponibles.
        Con cache: si ya visitamos esta URL, retorna servers cacheados.
        MÚLTIPLES PATRONES REGEX para máxima compatibilidad.
        
        Args:
            page (Page): Objeto Page de Playwright con el capítulo cargado.
            
        Returns:
            dict: Mapeo de nombre del servidor (ej: 'Mediafire') a su URL decodificada.
        """
        url = page.url
        # Validar que URL sea string válida para cache
        url_str = str(url) if url else ""
        if not url_str or not url_str.startswith("http"):
            url_str = f"page_{id(page)}"  # Fallback para tests/mocks
        # Cache hit
        cached = get_cached_servers(url_str)
        if cached is not None:
            return cached
        
        # Reintento de navegación si falla
        content = None
        for attempt in range(3):
            try:
                content = await page.content()
                if content and len(content) > 500:
                    break
            except Exception as e:
                if attempt == 2:
                    logger.warning(f"get_server_links: error obteniendo contenido: {e}")
                await asyncio.sleep(1)
        
        if not content or len(content) < 50:
            logger.warning(f"get_server_links: contenido muy corto o vacío para {url_str}")
            set_cached_servers(url_str, {})
            return {}
        
        # Detectar y esperar Cloudflare Challenge
        if _is_cf_challenge(content):
            logger.warning(f"Cloudflare Challenge detectado en {url_str}, esperando...")
            await _wait_for_cf_challenge(page, max_wait=30)
            # Obtener contenido después del challenge
            content = await page.content()
        
        if not content or len(content) < 50:
            logger.warning(f"get_server_links: contenido muy corto o vacío para {url_str}")
            set_cached_servers(url_str, {})
            return {}
        
        # Cache HTML también
        set_cached_html(url_str, content)
        
        # MÚLTIPLES PATRONES REGEX - probar cada uno
        links = {}
        for i, pattern in enumerate(RE_SERVERS):
            match = pattern.search(content)
            if match:
                try:
                    servers = json.loads(match.group(1))
                    for s in servers:
                        name = s.get('server', 'Unknown')
                        remote = s.get('remote')
                        if remote:
                            try:
                                decoded = base64.b64decode(remote).decode('utf-8')
                                links[name] = decoded
                            except Exception:
                                continue
                    if links:
                        break  # Éxito, usar este patrón
                except json.JSONDecodeError:
                    continue
        
        # Log para debug si no se encontraron servidores
        if not links:
            logger.warning(f"get_server_links: NO se encontraron servidores en {url} (patrones probados: {len(RE_SERVERS)})")
            # Log de muestra del HTML para debug
            logger.debug(f"HTML sample (primeros 2000 chars): {content[:2000]}")
        
        set_cached_servers(url_str, links)
        return links

    async def get_next_url(self, page):
        """
        Localiza el enlace al siguiente capítulo de la serie.
        Con cache: si ya visitamos esta URL, retorna next_url cacheado.
        MÚLTIPLES SELECTORES para máxima compatibilidad.
        
        Args:
            page (Page): Objeto Page de Playwright.
            
        Returns:
            str: URL del siguiente episodio o None si es el último disponible.
        """
        url = page.url
        # Validar que URL sea string válida para cache
        url_str = str(url) if url else ""
        if not url_str or not url_str.startswith("http"):
            url_str = f"page_{id(page)}"  # Fallback para tests/mocks
        # Cache hit
        cached = get_cached_next_url(url_str)
        if cached is not None:
            return cached

        # Si la página actual es un interstitial de Cloudflare, esperar a que se
        # resuelva ANTES de intentar leer selectores. Sin esto, los selectores no
        # encuentran nada y el fallback numérico inventa capítulos que no existen.
        try:
            content = await page.content()
            if _is_cf_challenge(content):
                logger.warning(f"Cloudflare Challenge detectado en {url_str}, esperando...")
                if not await _wait_for_cf_challenge(page, max_wait=30):
                    # El challenge no se resolvió: NO adivinar el siguiente capítulo.
                    logger.warning("Cloudflare no resuelto; se omite detección de siguiente capítulo.")
                    set_cached_next_url(url_str, None)
                    return None
        except Exception as e:
            logger.debug(f"get_next_url: error verificando challenge: {e}")

        # MÚLTIPLES SELECTORES - probar en orden de prioridad
        selectors = [
            "a:has-text('Siguiente')",
            "a:has-text('Siguiente >')",
            "a:has-text('Next')",
            "a.next-episode",
            "a[rel='next']",
            "nav.pagination a:last-child",
            ".pagination a:last-child",
            "a.btn-next",
        ]
        
        next_url = None
        for selector in selectors:
            try:
                next_btn = await page.query_selector(selector)
                if next_btn:
                    href = await next_btn.get_attribute('href')
                    if href and 'jkanime.net' in href:
                        next_url = href
                        break
            except Exception:
                continue
        
        # FALLBACK: Construir URL del siguiente episodio desde la URL actual
        if not next_url:
            try:
                current_url = page.url
                ep_match = RE_EPISODE.search(current_url)
                if ep_match:
                    current_ep = int(ep_match.group(1))
                    next_ep = current_ep + 1
                    # Reemplazar número de episodio en URL
                    next_url = RE_EPISODE.sub(f'{next_ep}/', current_url)
                    # Validar que la URL construida es diferente
                    if next_url == current_url:
                        next_url = None
            except Exception:
                pass
        
        set_cached_next_url(url_str, next_url)
        return next_url

    async def get_anime_info(self, page):
        """
        Extrae la URL de la miniatura (poster) del anime.
        Construye la URL directa del CDN a partir del slug del anime (más rápido y fiable).
        El slug se extrae de la URL de la página actual (ej: /one-piece/1180/ -> one-piece).
        MÚLTIPLES FALLBACKS para máxima robustez.
        
        Args:
            page (Page): Objeto Page de Playwright (página del capítulo).
            
        Returns:
            str: URL absoluta de la imagen de portada desde CDN.
        """
        try:
            # 1. Extraer slug directamente de la URL actual (más fiable)
            current_url = page.url
            slug_match = RE_SLUG.search(current_url)
            if slug_match:
                slug = slug_match.group(1)
                if slug and len(slug) > 1:
                    cdn_url = f"https://cdn.jkdesa.com/assets/images/animes/image/{slug}.jpg"
                    logger.debug(f"get_anime_info: CDN URL desde slug URL: {cdn_url}")
                    return cdn_url
            
            # 2. Fallback: breadcrumb - múltiples selectores
            breadcrumb_selectors = [
                ".breadcrumb a:nth-child(2)",
                ".breadcrumb a[href*='jkanime.net']:not(:first-child)",
                "nav.breadcrumb a:nth-child(2)",
                ".breadcrumb li:nth-child(2) a",
                "ol.breadcrumb li:nth-child(2) a",
            ]
            for selector in breadcrumb_selectors:
                try:
                    anime_link_el = await page.query_selector(selector)
                    if anime_link_el:
                        anime_main_url = await anime_link_el.get_attribute("href")
                        if anime_main_url and "jkanime.net" in anime_main_url:
                            slug_match = RE_SLUG_MAIN.search(anime_main_url)
                            if slug_match:
                                slug = slug_match.group(1)
                                if slug and len(slug) > 1:
                                    cdn_url = f"https://cdn.jkdesa.com/assets/images/animes/image/{slug}.jpg"
                                    logger.debug(f"get_anime_info: CDN URL desde breadcrumb: {cdn_url}")
                                    return cdn_url
                except Exception:
                    continue
            
            # 3. Fallback: JSON-LD structured data
            try:
                json_ld = await page.query_selector('script[type="application/ld+json"]')
                if json_ld:
                    content = await json_ld.text_content()
                    data = json.loads(content)
                    if isinstance(data, list):
                        data = data[0]
                    if data.get('image'):
                        img = data['image']
                        if isinstance(img, list):
                            img = img[0]
                        if isinstance(img, str) and 'jkanime' in img:
                            logger.debug(f"get_anime_info: CDN URL desde JSON-LD: {img}")
                            return img
            except Exception:
                pass
            
            # 4. Fallback: og:image
            try:
                og_selectors = [
                    'meta[property="og:image"]',
                    'meta[name="og:image"]',
                    'meta[property="twitter:image"]',
                ]
                for selector in og_selectors:
                    og_image = await page.query_selector(selector)
                    if og_image:
                        content = await og_image.get_attribute("content")
                        if content and ("assets/images/animes" in content or "cdn.jkdesa" in content):
                            logger.debug(f"get_anime_info: CDN URL desde og:image: {content}")
                            return content
            except Exception:
                pass
            
            # 5. Fallback: buscar imágenes con patrón conocido en página actual
            try:
                images = await page.query_selector_all("img")
                for img in images:
                    src = await img.get_attribute("src")
                    if src and ("/assets/images/animes/" in src or "cdn.jkdesa.com" in src):
                        logger.debug(f"get_anime_info: CDN URL desde img tag: {src}")
                        return src
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"get_anime_info: error inesperado: {e}")
        return "https://jkanime.net/assets/images/no-poster.jpg"
    
    async def get_anime_info_from_page(self, page):
        """
        Versión ligera: extrae thumbnail SOLO de la página actual (sin navegación extra).
        Usado para 'Seguir' rápido - intenta extraer slug de la URL, og:image y patrones.
        
        Args:
            page (Page): Objeto Page de Playwright (página del capítulo).
            
        Returns:
            str: URL de la imagen o placeholder si no se encuentra.
        """
        try:
            # 1. Extraer slug directamente de la URL actual
            current_url = page.url
            slug_match = RE_SLUG.search(current_url)
            if slug_match:
                slug = slug_match.group(1)
                if slug and len(slug) > 1:
                    return f"https://cdn.jkdesa.com/assets/images/animes/image/{slug}.jpg"
            
            # 2. Fallback: og:image
            try:
                og_image = await page.query_selector('meta[property="og:image"]')
                if og_image:
                    content = await og_image.get_attribute("content")
                    if content and "/assets/images/animes/" in content:
                        return content
            except Exception:
                pass
            
            # 3. Fallback: patrones en imágenes
            try:
                images = await page.query_selector_all("img")
                for img in images:
                    src = await img.get_attribute("src")
                    if src and "/assets/images/animes/" in src:
                        return src
            except Exception:
                pass
        except Exception:
            pass
        return "https://jkanime.net/assets/images/no-poster.jpg"

    async def get_mediafire_direct_link(self, server_url):
        """
        Navega a la página de MediaFire para obtener el enlace directo al archivo de video.
        Con cache: si ya visitamos esta URL de MF, retorna link directo cacheado.
        MÚLTIPLES SELECTORES Y REINTENTOS para máxima robustez.
        
        Optimizado con timeouts aumentados y bloqueo selectivo de recursos.
        
        Args:
            server_url (str): URL de la página intermedia de MediaFire.
            
        Returns:
            tuple: (direct_link, extension) o (None, None) en caso de fallo o archivo borrado.
        """
        # Cache hit
        mf_url_str = str(server_url) if server_url else ""
        if not mf_url_str or not mf_url_str.startswith("http"):
            mf_url_str = f"mf_{id(server_url)}"
        cached = get_cached_mf_direct(mf_url_str)
        if cached is not None:
            return cached
        
        # Reintentos en caso de fallos transitorios
        max_attempts = 3
        for attempt in range(max_attempts):
            page = await self.context.new_page()
            try:
                # El bloqueo global del contexto ya omite recursos pesados.
                # NO se espera "networkidle": MediaFire mantiene conexiones abiertas
                # (ads/trackers/long-polling) y esa espera añadía hasta 15s al inicio.
                await page.goto(server_url, timeout=30000, wait_until="domcontentloaded")

                # 1) CAMINO RÁPIDO: el botón suele estar en el DOM casi de inmediato.
                #    Se busca primero para evitar serializar todo el HTML de MediaFire.
                d_btn = None
                try:
                    d_btn = await page.wait_for_selector("#downloadButton", timeout=2500, state="attached")
                except Exception:
                    d_btn = None

                # 2) No apareció el botón: comprobar Cloudflare y archivo borrado.
                if not d_btn:
                    content = await page.content()
                    if _is_cf_challenge(content):
                        logger.warning(f"MediaFire: Cloudflare Challenge detectado en {server_url}, esperando...")
                        await _wait_for_cf_challenge(page, max_wait=25)
                        content = await page.content()

                    # Fallo rápido de archivo borrado/no disponible
                    if "has been removed" in content or "currently unavailable" in content or "File not found" in content:
                        logger.warning(f"MediaFire: archivo no disponible en {server_url}")
                        set_cached_mf_direct(mf_url_str, None, None)
                        return None, None

                    # 3) Fallbacks cortos para el botón tras resolver el challenge
                    for selector, wait_ms in (
                        ("#downloadButton", 5000),
                        ("a[href*='download']", 1500),
                        ("a.btn-download", 1000),
                        ("[data-download]", 1000),
                    ):
                        try:
                            d_btn = await page.wait_for_selector(selector, timeout=wait_ms, state="attached")
                            if d_btn:
                                break
                        except Exception:
                            continue

                if not d_btn:
                    raise Exception("No se encontró botón de descarga con ningún selector")

                direct_link = await d_btn.get_attribute('href')

                # MediaFire puede ofuscar el enlace en data-scrambled-url (base64)
                if not direct_link or not direct_link.startswith("http"):
                    try:
                        scrambled = await d_btn.get_attribute('data-scrambled-url')
                        if scrambled:
                            direct_link = base64.b64decode(scrambled).decode('utf-8')
                    except Exception:
                        pass

                original_name = await d_btn.get_attribute('aria-label') or "video"

                # Intentar obtener nombre del archivo desde otros atributos
                if not original_name or original_name == "video":
                    try:
                        original_name = await d_btn.get_attribute('data-filename') or "video"
                    except Exception:
                        pass

                extension = os.path.splitext(original_name)[1] or ".mp4"

                if not direct_link:
                    raise Exception("Enlace directo vacío")

                logger.info(f"MediaFire: enlace directo obtenido para {server_url}")
                set_cached_mf_direct(mf_url_str, direct_link, extension)
                return direct_link, extension
                
            except Exception as e:
                logger.warning(f"MediaFire intento {attempt + 1}/{max_attempts} falló: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2)
                    continue
                set_cached_mf_direct(mf_url_str, None, None)
                # Log HTML para debug
                try:
                    content = await page.content()
                    logger.debug(f"MediaFire HTML sample (primeros 3000 chars): {content[:3000]}")
                except Exception:
                    pass
                return None, None
            finally:
                await page.close()
        
        return None, None