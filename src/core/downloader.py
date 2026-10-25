"""
Módulo de Descarga.
Implementa una lógica de descarga robusta con soporte para fragmentación,
reintentos automáticos y control de flujo (pausa/parada).
Optimizado para conexiones MediaFire y alta velocidad.
"""
import os
import time
import random
import asyncio
import aiohttp
from config.manager import USER_AGENTS

# Configuración de timeouts optimizados para MediaFire
MEDIAFIRE_CONNECT_TIMEOUT = 15  # Conexión inicial
MEDIAFIRE_READ_TIMEOUT = 30     # Lectura de chunks
MEDIAFIRE_TOTAL_TIMEOUT = None  # Sin límite total para archivos grandes
CHUNK_SIZE = 512 * 1024         # 512KB chunks para mejor throughput

# TCPConnector compartido para connection pooling (keep-alive, DNS cache)
_SHARED_CONNECTOR = None

def get_shared_connector():
    """Obtiene o crea el TCPConnector compartido para reutilizar conexiones."""
    global _SHARED_CONNECTOR
    if _SHARED_CONNECTOR is None or _SHARED_CONNECTOR.closed:
        _SHARED_CONNECTOR = aiohttp.TCPConnector(
            limit=20,               # Max conexiones simultáneas totales
            limit_per_host=5,       # Max por host (MediaFire)
            ttl_dns_cache=300,      # DNS cache 5 min
            keepalive_timeout=30,   # Keep-alive 30s
            enable_cleanup_closed=True
        )
    return _SHARED_CONNECTOR

async def close_shared_connector():
    """Cierra el connector compartido al cerrar la app."""
    global _SHARED_CONNECTOR
    if _SHARED_CONNECTOR and not _SHARED_CONNECTOR.closed:
        await _SHARED_CONNECTOR.close()
        _SHARED_CONNECTOR = None

class Downloader:
    """
    Clase encargada de la transferencia de archivos de video.
    
    Utiliza descargas segmentadas (HTTP Range requests) para permitir la pausa
    y reanudación. Incluye lógica para detectar velocidades de descarga
    excesivamente bajas y reintentar la conexión.
    """
    def __init__(self, app_context):
        """
        Inicializa el descargador con el contexto de la aplicación para control de estado.
        
        Args:
            app_context (object): Referencia a la instancia principal de la App para
                                  acceder a flags de pausa y cancelación.
        """
        self.app = app_context
        self._session = None

    @property
    def session(self):
        """Obtiene o crea una sesión aiohttp reutilizable con connection pooling."""
        if self._session is None or self._session.closed:
            connector = get_shared_connector()
            timeout = aiohttp.ClientTimeout(
                total=MEDIAFIRE_TOTAL_TIMEOUT,
                connect=MEDIAFIRE_CONNECT_TIMEOUT,
                sock_read=MEDIAFIRE_READ_TIMEOUT
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": random.choice(USER_AGENTS)}
            )
        return self._session

    async def close_session(self):
        """Cierra la sesión si existe."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def download_chunked(self, *args, **kwargs):
        """
        Ejecuta la descarga de un archivo de forma asíncrona y segmentada.
        Soporta dos firmas para compatibilidad:
        - Legacy: download_chunked(session, url, path, progress_callback)
        - Nueva:  download_chunked(url, path, progress_callback=None, session=None)
        
        Optimizado para MediaFire con headers específicos y timeouts ajustados.
        
        Returns:
            bool: True si el archivo se descargó completamente, False si fue cancelado o falló tras reintentos.
        """
        # Detectar firma por posición/keywords
        if len(args) >= 2 and isinstance(args[0], str) and not isinstance(args[1], aiohttp.ClientSession):
            # Nueva firma: (url, path, progress_callback, session)
            url = args[0]
            path = args[1]
            progress_callback = args[2] if len(args) > 2 else kwargs.get('progress_callback')
            session = args[3] if len(args) > 3 else kwargs.get('session')
        else:
            # Legacy: (session, url, path, progress_callback)
            session = args[0]
            url = args[1]
            path = args[2]
            progress_callback = args[3] if len(args) > 3 else kwargs.get('progress_callback')
        
        # Usar sesión compartida si no se proporciona una
        if session is None:
            session = self.session
        
        return await self._download_impl(session, url, path, progress_callback)

    async def _download_impl(self, session, url, path, progress_callback=None):
        """
        Implementación interna de la descarga segmentada.
        """
        downloaded_bytes = 0
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "*/*",
                    "Accept-Encoding": "identity",  # Evitar compresión para rangos
                    "Connection": "keep-alive",
                    "Range": f"bytes={downloaded_bytes}-" if downloaded_bytes > 0 else ""
                }
                
                # Timeout compatible con tests legacy y optimizado para MediaFire
                timeout = aiohttp.ClientTimeout(
                    total=MEDIAFIRE_TOTAL_TIMEOUT,
                    connect=MEDIAFIRE_CONNECT_TIMEOUT,
                    sock_read=MEDIAFIRE_READ_TIMEOUT
                )
                
                response = await session.get(url, headers=headers, timeout=timeout)
                try:
                    if response.status not in [200, 206]:
                        raise Exception(f"HTTP {response.status}")
                    
                    # Soporte para Content-Range en respuestas 206
                    content_range = response.headers.get('Content-Range')
                    if content_range and downloaded_bytes == 0:
                        try:
                            total_size = int(content_range.split('/')[-1])
                        except (ValueError, IndexError):
                            total_size = int(response.headers.get('content-length', 0))
                    else:
                        total_size = int(response.headers.get('content-length', 0)) + downloaded_bytes
                    
                    mode = 'ab' if downloaded_bytes > 0 else 'wb'
                    
                    with open(path, mode) as f:
                        start_time = time.time()
                        last_chunk_time = time.time()
                        low_speed_start_time = None
                        bytes_since_last_update = 0
                        
                        async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                            if self.app.stop_requested: 
                                response.close()
                                return False
                            await self.app.is_paused.wait()
                            
                            f.write(chunk)
                            chunk_len = len(chunk)
                            downloaded_bytes += chunk_len
                            bytes_since_last_update += chunk_len
                            
                            now = time.time()
                            if now - last_chunk_time > 0.5:
                                elapsed = now - start_time
                                speed = downloaded_bytes / elapsed if elapsed > 0 else 0
                                speed_mb = speed / (1024 * 1024)
                                progress = downloaded_bytes / total_size if total_size > 0 else 0
                                
                                if progress_callback:
                                    await progress_callback(progress, downloaded_bytes, total_size, speed_mb)
                                
                                # Detección de estancamiento (Stall) o velocidad muy baja (< 500 KB/s)
                                if speed_mb < 0.5:
                                    if low_speed_start_time is None:
                                        low_speed_start_time = now
                                    elif now - low_speed_start_time > 5:
                                        # Forzar reintento si la velocidad es baja por más de 5 segundos
                                        if hasattr(self.app, 'log'):
                                            self.app.log(f"  [!] Velocidad muy baja ({speed_mb:.2f} MB/s). Reintentando...", type="warning")
                                        break 
                                else:
                                    low_speed_start_time = None
                                
                                last_chunk_time = now
                                bytes_since_last_update = 0
                        
                        if downloaded_bytes >= total_size:
                            return True
                finally:
                    response.close()
                        
            except asyncio.TimeoutError:
                retry_count += 1
                if hasattr(self.app, 'log'):
                    self.app.log(f"  [!] Timeout de conexión (Intento {retry_count}/{max_retries})", type="warning")
                await asyncio.sleep(2 * retry_count)
                
            except aiohttp.ClientError as e:
                retry_count += 1
                if hasattr(self.app, 'log'):
                    self.app.log(f"  [!] Error de cliente HTTP (Intento {retry_count}/{max_retries}): {str(e)}", type="warning")
                await asyncio.sleep(2 * retry_count)
                
            except Exception as e:
                retry_count += 1
                if hasattr(self.app, 'log'):
                    self.app.log(f"  [!] Error de descarga (Intento {retry_count}/{max_retries}): {str(e)}", type="warning")
                await asyncio.sleep(2 * retry_count)
                
        return False
