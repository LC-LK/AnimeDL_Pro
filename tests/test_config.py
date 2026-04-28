import unittest
import os
import json
import sys
from unittest.mock import patch, MagicMock

# Añadir src al path para poder importar los módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.manager import load_config, save_config, get_config_path

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.test_config_file = "test_config.json"
        # Parchear CONFIG_FILE en el módulo
        self.patcher = patch('config.manager.CONFIG_FILE', self.test_config_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)

    def test_load_config_default(self):
        """Prueba que se cargue la configuración por defecto si el archivo no existe."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        
        config = load_config()
        self.assertIn("settings", config)
        self.assertIn("following", config)
        self.assertEqual(config["settings"]["view_mode"], "list")

    def test_save_and_load_config(self):
        """Prueba que se pueda guardar y cargar la configuración correctamente."""
        test_data = {
            "following": {"test_url": {"alias": "Test Anime"}},
            "settings": {"default_dir": "/tmp", "view_mode": "grid"}
        }
        
        save_success = save_config(test_data)
        self.assertTrue(save_success)
        self.assertTrue(os.path.exists(self.test_config_file))
        
        loaded_data = load_config()
        self.assertEqual(loaded_data["following"]["test_url"]["alias"], "Test Anime")
        self.assertEqual(loaded_data["settings"]["view_mode"], "grid")

    def test_config_migration(self):
        """Prueba la migración de 'history' a 'following'."""
        old_data = {
            "history": {
                "https://jkanime.net/anime/1/": {"alias": "Legacy Anime"}
            }
        }
        with open(self.test_config_file, "w", encoding="utf-8") as f:
            json.dump(old_data, f)
            
        config = load_config()
        self.assertIn("following", config)
        self.assertIn("https://jkanime.net/anime/", config["following"])
        self.assertEqual(config["following"]["https://jkanime.net/anime/"]["alias"], "Legacy Anime")

if __name__ == '__main__':
    unittest.main()
