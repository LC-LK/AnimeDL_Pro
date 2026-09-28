"""
Módulo del Scraper de Anime.
Proporciona la lógica para navegar por JkAnime, extraer enlaces de servidores y obtener links directos de MediaFire.
"""
import re
import json
import base64
import os

# Expresiones regulares pre-compiladas
RE_SERVERS = re.compile(r'var\s+servers\s*=\s*(\[.*?\]);')

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
        
        Decodifica la variable JavaScript 'servers' presente en el HTML del episodio,
        la cual contiene enlaces en Base64.
        
        Args:
            page (Page): Objeto Page de Playwright con el capítulo cargado.
            
        Returns:
            dict: Mapeo de nombre del servidor (ej: 'Mediafire') a su URL decodificada.
        """
        content = await page.content()
        match = RE_SERVERS.search(content)
        if not match: return {}
        
        links = {}
        try:
            servers = json.loads(match.group(1))
            for s in servers:
                name = s.get('server', 'Unknown')
                remote = s.get('remote')
                if remote:
                    decoded = base64.b64decode(remote).decode('utf-8')
                    links[name] = decoded
        except Exception: pass
        return links

    async def get_next_url(self, page):
        """
        Localiza el enlace al siguiente capítulo de la serie.
        
        Args:
            page (Page): Objeto Page de Playwright.
            
        Returns:
            str: URL del siguiente episodio o None si es el último disponible.
        """
        next_btn = await page.query_selector("a:has-text('Siguiente')")
        return await next_btn.get_attribute('href') if next_btn else None

    async def get_anime_info(self, page):
        """
        Extrae la URL de la miniatura (poster) del anime.
        
        Intenta obtener la imagen desde la página principal del anime, metaetiquetas OG
        o patrones de URL de activos conocidos en el sitio.
        
        Args:
            page (Page): Objeto Page de Playwright.
            
        Returns:
            str: URL absoluta de la imagen de portada.
        """
        try:
            anime_link_el = await page.query_selector(".breadcrumb a:nth-child(2)")
            
            if anime_link_el:
                anime_main_url = await anime_link_el.get_attribute("href")
                if anime_main_url and "jkanime.net" in anime_main_url:
                    temp_page = await page.context.new_page()
                    try:
                        # Bloqueo de recursos innecesarios
                        await temp_page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media", "stylesheet"] else route.continue_())
                        await temp_page.goto(anime_main_url, wait_until="domcontentloaded", timeout=10000)
                        
                        img_el = await temp_page.query_selector(".anime_info_img img")
                        if img_el:
                            src = await img_el.get_attribute("src")
                            if src: return src
                    except Exception: pass
                    finally: await temp_page.close()

            images = await page.query_selector_all("img")
            for img in images:
                src = await img.get_attribute("src")
                if src and "/assets/images/animes/" in src:
                    return src
            
            og_image = await page.query_selector("meta[property='og:image']")
            if og_image:
                return await og_image.get_attribute("content")
        except Exception:
            pass
        return "https://jkanime.net/assets/images/no-poster.jpg"

    async def get_mediafire_direct_link(self, server_url):
        """
        Navega a la página de MediaFire para obtener el enlace directo al archivo de video.
        
        Maneja la detección de archivos eliminados o no disponibles y extrae la
        extensión del archivo original.
        
        Args:
            server_url (str): URL de la página intermedia de MediaFire.
            
        Returns:
            tuple: (direct_link, extension) o (None, None) en caso de fallo o archivo borrado.
        """
        page = await self.context.new_page()
        try:
            # Bloqueo agresivo de recursos para acelerar la carga
            await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media", "stylesheet"] else route.continue_())
            
            # Reducido timeout de carga a 7 segundos    
            await page.goto(server_url, timeout=3000, wait_until="domcontentloaded")
            content = await page.content()
            
            unavailable_markers = [
                "The file you attempted to download has been removed",
                "The file you are looking for is currently unavailable"
            ]
            if any(marker in content for marker in unavailable_markers):
                return None, None
            
            # Reducido timeout de espera por el botón a 5 segundos
            d_btn = await page.wait_for_selector("#downloadButton", timeout=3000)
            direct_link = await d_btn.get_attribute('href')
            original_name = await d_btn.get_attribute('aria-label') or "video"
            extension = os.path.splitext(original_name)[1] or ".mp4"
            
            return direct_link, extension
        except Exception:
            return None, None
        finally:
            await page.close()
