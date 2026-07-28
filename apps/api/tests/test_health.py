import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")

from app.core.config import settings
from app.main import app


class HealthContractTest(unittest.TestCase):
    def test_health_exposes_only_safe_build_identity(self):
        with patch.object(settings, "build_sha", "abc123"):
            response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "build_sha": "abc123"})

    def test_build_sha_is_never_empty(self):
        self.assertTrue(settings.build_sha.strip())


if __name__ == "__main__":
    unittest.main()
