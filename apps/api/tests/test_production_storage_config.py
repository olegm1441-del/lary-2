import unittest

from app.core.config import default_file_storage_dir


class ProductionStorageConfigTest(unittest.TestCase):
    def test_production_defaults_to_the_mounted_volume(self):
        self.assertEqual(default_file_storage_dir("production"), "/data/lary-generated")

    def test_non_production_keeps_temporary_storage(self):
        self.assertEqual(default_file_storage_dir("development"), "/tmp/lary-generated")


if __name__ == "__main__":
    unittest.main()
