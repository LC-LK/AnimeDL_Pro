"""
Módulo de Descarga.
Implementa una lógica de descarga robusta con soporte para fragmentación,
reintentos automáticos y control de flujo (pausa/parada).
"""
import os
import time
import random
import asyncio
import aiohttp
from config.manager import USER_AGENTS

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

    async def download_chunked(self, session, url, path, progress_callback=None):
        """
        Ejecuta la descarga de un archivo de forma asíncrona y segmentada.
        
        Implementa un bucle de reintentos y gestiona la escritura en disco en modo
        binario (append si se reanuda). Notifica el progreso a través de un callback.
        
        Args:
            session (aiohttp.ClientSession): Sesión de red activa.
            url (str): URL directa del archivo a descargar.
            path (str): Ruta local de destino.
            progress_callback (callable, optional): Función que recibe (progreso, bytes_descargados, total, velocidad).
            
        Returns:
            bool: True si el archivo se descargó completamente, False si fue cancelado o falló tras reintentos.
        """
        downloaded_bytes = 0
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Range": f"bytes={downloaded_bytes}-" if downloaded_bytes > 0 else ""
                }
                
                timeout = aiohttp.ClientTimeout(total=None, connect=30, sock_read=60)
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    if response.status not in [200, 206]:
                        raise Exception(f"HTTP {response.status}")
                    
                    total_size = int(response.headers.get('content-length', 0)) + downloaded_bytes
                    mode = 'ab' if downloaded_bytes > 0 else 'wb'
                    
                    with open(path, mode) as f:
                        start_time = time.time()
                        last_chunk_time = time.time()
                        low_speed_start_time = None
                        
                        async for chunk in response.content.iter_chunked(512 * 1024): # 512KB chunks
                            if self.app.stop_requested: return False
                            await self.app.is_paused.wait()
                            
                            f.write(chunk)
                            downloaded_bytes += len(chunk)
                            
                            now = time.time()
                            if now - last_chunk_time > 0.5:
                                elapsed = now - start_time
                                speed = downloaded_bytes / elapsed if elapsed > 0 else 0
                                speed_mb = speed / (1024 * 1024)
                                progress = downloaded_bytes / total_size if total_size > 0 else 0
                                
                                if progress_callback:
                                    await progress_callback(progress, downloaded_bytes, total_size, speed_mb)
                                
                                # Detección de estancamiento (Stall) o velocidad muy baja
                                if speed_mb < 2.0:
                                    if low_speed_start_time is None:
                                        low_speed_start_time = now
                                    elif now - low_speed_start_time > 3:
                                        # Forzar reintento si la velocidad es baja por más de 3 segundos
                                        if hasattr(self.app, 'log'):
                                            self.app.log(f"  [!] Velocidad muy baja ({speed_mb:.2f} MB/s). Reintentando...", type="warning")
                                        break 
                                else:
                                    low_speed_start_time = None
                                
                                last_chunk_time = now
                        
                        if downloaded_bytes >= total_size:
                            return True
                            
            except Exception as e:
                retry_count += 1
                if hasattr(self.app, 'log'):
                    self.app.log(f"  [!] Error de descarga (Intento {retry_count}/{max_retries}): {str(e)}", type="warning")
                await asyncio.sleep(2 * retry_count)
                
        return False
