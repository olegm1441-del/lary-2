import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")

from app.main import app
from app.core.config import settings


class ProductApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_contests_endpoint_returns_four_public_choices(self):
        response = self.client.get("/api/contests")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["slug"] for item in response.json()["items"]],
            ["pfki", "fpg", "rosmolodezh", "first_grants"],
        )

    def test_profile_endpoint_returns_preparing_without_private_prompt(self):
        response = self.client.get("/api/modules/salary/profiles/fpg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "preparing")
        self.assertNotIn("system_prompt", response.text)

    def test_unknown_profile_is_safe_404(self):
        response = self.client.get("/api/modules/unknown/profiles/pfki")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["message"], "Такая задача не найдена.")

    def test_registry_flag_keeps_single_modules_route_owner(self):
        with patch.object(settings, "product_registry_runtime_enabled", True):
            response = self.client.get("/api/modules")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["items"]), 7)
        owners = [
            route
            for route in app.routes
            if getattr(route, "path", None) == "/api/modules" and "GET" in getattr(route, "methods", set())
        ]
        self.assertEqual(len(owners), 1)


if __name__ == "__main__":
    unittest.main()
