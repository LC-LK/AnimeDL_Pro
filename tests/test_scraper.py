import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Añadir src al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.scraper import AnimeScraper

class TestScraper(unittest.IsolatedAsyncioTestCase):
    async def test_get_server_links(self):
        """Prueba la extracción de enlaces de servidores desde el HTML."""
        mock_context = MagicMock()
        scraper = AnimeScraper(mock_context)
        
        mock_page = AsyncMock()
        # HTML simplificado con múltiples servidores para probar el bucle
        mock_page.content.return_value = """
        <html>
            <script>
                var servers = [
                    {"server": "Mediafire", "remote": "aHR0cHM6Ly93d3cubWVkaWFmaXJlLmNvbS9maWxlL3Rlc3Q="},
                    {"server": "Mega", "remote": "aHR0cHM6Ly9tZWdhLm56L2YvYWJjZGU="}
                ];
            </script>
        </html>
        """
        
        links = await scraper.get_server_links(mock_page)
        
        # Verificar Mediafire
        self.assertIn("Mediafire", links)
        self.assertEqual(links["Mediafire"], "https://www.mediafire.com/file/test")
        
        # Verificar Mega
        self.assertIn("Mega", links)
        self.assertEqual(links["Mega"], "https://mega.nz/f/abcde")

    async def test_get_next_url(self):
        """Prueba la obtención de la URL del siguiente capítulo."""
        mock_context = MagicMock()
        scraper = AnimeScraper(mock_context)
        
        mock_page = AsyncMock()
        mock_btn = AsyncMock()
        mock_btn.get_attribute.return_value = "https://jkanime.net/anime/2/"
        
        mock_page.query_selector.return_value = mock_btn
        
        next_url = await scraper.get_next_url(mock_page)
        self.assertEqual(next_url, "https://jkanime.net/anime/2/")
        mock_page.query_selector.assert_called_with("a:has-text('Siguiente')")

if __name__ == '__main__':
    unittest.main()
