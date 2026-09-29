"""
Módulo del Scraper de Anime.
Proporciona la lógica para navegar por JkAnime, extraer enlaces de servidores y obtener links directos de MediaFire.
Optimizado para rendimiento y estabilidad en conexiones.
Incluye cache en memoria para requests/responses de sesión (Sprint 2.3).
"""
import re
import json
import base64
import os

# Expresiones regulares pre-compiladas
RE_SERVERS = re.compile(r'var\s+servers\s*=\s*(\[.*?\]);')
RE_SLUG = re.compile(r'jkanime\.net/([^/]+)/\d+/?')
RE_SLUG_MAIN = re.compile(r'jkanime\.net/([^/]+)/?$')

# ============ REQUEST/RESPONSE CACHE (Sprint 2.3) ============
# Cache en memoria para la sesión actual - evita requests redundantes
# Clave: URL, Valor: datos cacheados
_request_cache = {
    "html": {},      # url -> html content
    "servers": {},   # url -> dict servers
    "next_url": {},  # url -> next_url str
    "mf_direct": {}, # mf_url -> (direct_link, ext)
}

def get_cached_html(url):
    """Obtiene HTML cacheado o None."""
    return _request_cache["html"].get(url)

def set_cached_html(url, html):
    """Guarda HTML en cache."""
    _request_cache["html"][url] = html

def get_cached_servers(url):
    """Obtiene servers cacheados o None."""
    return _request_cache["servers"].get(url)

def set_cached_servers(url, servers):
    """Guarda servers en cache."""
    _request_cache["servers"][url] = servers

def get_cached_next_url(url):
    """Obtiene next_url cacheado o None."""
    return _request_cache["next_url"].get(url)

def set_cached_next_url(url, next_url):
    """Guarda next_url en cache."""
    _request_cache["next_url"][url] = next_url

def get_cached_mf_direct(mf_url):
    """Obtiene MediaFire direct link cacheado o None."""
    return _request_cache["mf_direct"].get(mf_url)

def set_cached_mf_direct(mf_url, direct_link, ext):
    """Guarda MediaFire direct link en cache."""
    _request_cache["mf_direct"][mf_url] = (direct_link, ext)

def clear_request_cache():
    """Limpia todo el cache de requests (para tests o nueva sesión)."""
    global _request_cache
    _request_cache = {
        "html": {},
        "servers": {},
        "next_url": {},
        "mf_direct": {},
    }

def get_cache_stats():
    """Retorna estadísticas del cache."""
    return {
        "html": len(_request_cache["html"]),
        "servers": len(_request_cache["servers"]),
        "next_url": len(_request_cache["next_url"]),
        "mf_direct": len(_request_cache["mf_direct"]),
    }

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
        
        Args:
            page (Page): Objeto Page de Playwright con el capítulo cargado.
            
        Returns:
            dict: Mapeo de nombre del servidor (ej: 'Mediafire') a su URL decodificada.
        """
        url = page.url
        # Cache hit
        cached = get_cached_servers(url)
        if cached is not None:
            return cached
        
        content = await page.content()
        # Cache HTML también
        set_cached_html(url, content)
        
        match = RE_SERVERS.search(content)
        if not match: 
            set_cached_servers(url, {})
            return {}
        
        links = {}
        try:
            servers = json.loads(match.group(1))
            for s in servers:
                name = s.get('server', 'Unknown')
                remote = s.get('remote')
                if remote:
                    decoded = base64.b64decode(remote).decode('utf-8')
                    links[name] = decoded
        except Exception:
            pass
        
        set_cached_servers(url, links)
        return links

    async def get_next_url(self, page):
        """
        Localiza el enlace al siguiente capítulo de la serie.
        Con cache: si ya visitamos esta URL, retorna next_url cacheado.
        
        Args:
            page (Page): Objeto Page de Playwright.
            
        Returns:
            str: URL del siguiente episodio o None si es el último disponible.
        """
        url = page.url
        # Cache hit
        cached = get_cached_next_url(url)
        if cached is not None:
            return cached
        
        next_btn = await page.query_selector("a:has-text('Siguiente')")
        next_url = await next_btn.get_attribute('href') if next_btn else None
        
        set_cached_next_url(url, next_url)
        return next_url

    async def get_anime_info(self, page):
        """
        Extrae la URL de la miniatura (poster) del anime.
        Construye la URL directa del CDN a partir del slug del anime (más rápido y fiable).
        El slug se extrae de la URL de la página actual (ej: /one-piece/1180/ -> one-piece).
        
        Args:
            page (Page): Objeto Page de Playwright (página del capítulo).
            
        Returns:
            str: URL absoluta de la imagen de portada desde CDN.
        """
        try:
            # 1. Extraer slug directamente de la URL actual (más fiable que breadcrumb)
            # URL típica: https://jkanime.net/one-piece/1180/ -> slug = "one-piece"
            current_url = page.url
            slug_match = RE_SLUG.search(current_url)
            if slug_match:
                slug = slug_match.group(1)
                # URL directa del CDN (patrón confirmado en config.json)
                return f"https://cdn.jkdesa.com/assets/images/animes/image/{slug}.jpg"
            
            # 2. Fallback: breadcrumb (enlace al anime principal)
            anime_link_el = await page.query_selector(".breadcrumb a:nth-child(2)")
            if anime_link_el:
                anime_main_url = await anime_link_el.get_attribute("href")
                if anime_main_url and "jkanime.net" in anime_main_url:
                    slug_match = RE_SLUG_MAIN.search(anime_main_url)
                    if slug_match:
                        slug = slug_match.group(1)
                        return f"https://cdn.jkdesa.com/assets/images/animes/image/{slug}.jpg"
            
            # 3. Fallback: og:image en página actual
            og_image = await page.query_selector("meta[property='og:image']")
            if og_image:
                content = await og_image.get_attribute("content")
                if content and "/assets/images/animes/" in content:
                    return content
            
            # 4. Fallback: buscar imágenes con patrón conocido en página actual
            images = await page.query_selector_all("img")
            for img in images:
                src = await img.get_attribute("src")
                if src and "/assets/images/animes/" in src:
                    return src
        except Exception:
            pass
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
                return f"https://cdn.jkdesa.com/assets/images/animes/image/{slug}.jpg"
            
            # 2. Fallback: og:image
            og_image = await page.query_selector("meta[property='og:image']")
            if og_image:
                content = await og_image.get_attribute("content")
                if content and "/assets/images/animes/" in content:
                    return content
            
            # 3. Fallback: patrones en imágenes
            images = await page.query_selector_all("img")
            for img in images:
                src = await img.get_attribute("src")
                if src and "/assets/images/animes/" in src:
                    return src
        except Exception:
            pass
        return "https://jkanime.net/assets/images/no-poster.jpg"

    async def get_mediafire_direct_link(self, server_url):
        """
        Navega a la página de MediaFire para obtener el enlace directo al archivo de video.
        Con cache: si ya visitamos esta URL de MF, retorna link directo cacheado.
        
        Optimizado con timeouts reducidos y bloqueo agresivo de recursos.
        
        Args:
            server_url (str): URL de la página intermedia de MediaFire.
            
        Returns:
            tuple: (direct_link, extension) o (None, None) en caso de fallo o archivo borrado.
        """
        # Cache hit
        cached = get_cached_mf_direct(server_url)
        if cached is not None:
            return cached
        
        page = await self.context.new_page()
        try:
            # Bloqueo agresivo de recursos para acelerar la carga
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "font", "media", "stylesheet"] 
                else route.continue_())
            
            # Timeout de navegación reducido a 5 segundos
            await page.goto(server_url, timeout=5000, wait_until="domcontentloaded")
            
            # Verificación rápida de archivo no disponible
            content = await page.content()
            if "has been removed" in content or "currently unavailable" in content:
                set_cached_mf_direct(server_url, None, None)
                return None, None
            
            # Espera por botón de descarga con timeout reducido
            d_btn = await page.wait_for_selector("#downloadButton", timeout=4000)
            direct_link = await d_btn.get_attribute('href')
            original_name = await d_btn.get_attribute('aria-label') or "video"
            extension = os.path.splitext(original_name)[1] or ".mp4"
            
            set_cached_mf_direct(server_url, direct_link, extension)
            return direct_link, extension
        except Exception:
            set_cached_mf_direct(server_url, None, None)
            return None, None
        finally:
            await page.close()
