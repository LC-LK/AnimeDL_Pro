import unittest
import os
import sys
from unittest.mock import patch

# Añadir src al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.helpers import resource_path, lazy_import_network

class TestUtils(unittest.TestCase):
    def test_resource_path_normal(self):
        """Prueba resource_path en entorno normal (no congelado)."""
        path = resource_path("test.txt")
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(path.endswith("test.txt"))

    @patch('sys._MEIPASS', '/tmp/app', create=True)
    def test_resource_path_frozen(self):
        """Prueba resource_path en entorno congelado (PyInstaller)."""
        path = resource_path("test.txt")
        self.assertEqual(path, os.path.join('/tmp/app', 'test.txt'))

    def test_lazy_import_network(self):
        """Prueba que lazy_import_network devuelva los módulos correctos."""
        # Nota: Esto realmente importará los módulos si no están cargados
        ap, ah = lazy_import_network()
        self.assertIsNotNone(ap)
        self.assertIsNotNone(ah)
        
        # Verificar que se mantienen en caché global
        ap2, ah2 = lazy_import_network()
        self.Is(ap, ap2)
        self.Is(ah, ah2)

    def Is(self, a, b):
        self.assertTrue(a is b)

if __name__ == '__main__':
    unittest.main()
