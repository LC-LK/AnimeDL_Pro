import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import os
import sys

# Añadir el directorio src al path para poder importar los módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.downloader import Downloader

class TestAnimeDownloader(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock del contexto de la app
        self.mock_app = MagicMock()
        self.mock_app.stop_requested = False
        self.mock_app.is_paused = asyncio.Event()
        self.mock_app.is_paused.set()
        
        self.downloader = Downloader(self.mock_app)

    @patch('aiohttp.ClientSession.get')
    async def test_download_chunked_success(self, mock_get):
        # Configurar mock de respuesta
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Length': '2048'}
        
        # Mock del iterador de contenido
        mock_content = AsyncMock()
        mock_content.iter_chunked.return_value = [b'a' * 1024, b'b' * 1024]
        mock_response.content = mock_content
        
        mock_get.return_value.__aenter__.return_value = mock_response

        # Mock del callback de progreso
        progress_callback = AsyncMock() # El callback en downloader.py se llama con await
        
        # Mock de open para no escribir en disco
        with patch('builtins.open', unittest.mock.mock_open()):
            mock_session = MagicMock()
            success = await self.downloader.download_chunked(
                mock_session,
                "http://example.com/video.mp4",
                "test.mp4",
                progress_callback
            )

        self.assertTrue(success)
        self.assertGreater(progress_callback.call_count, 0)

    async def test_stop_requested(self):
        # Simular que se solicita detener la descarga
        self.mock_app.stop_requested = True
        
        mock_session = MagicMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Length': '1024'}
        mock_response.content.iter_chunked.return_value = [b'data']
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with patch('builtins.open', unittest.mock.mock_open()):
                success = await self.downloader.download_chunked(
                    mock_session,
                    "http://example.com/video.mp4",
                    "test.mp4"
                )
        
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
