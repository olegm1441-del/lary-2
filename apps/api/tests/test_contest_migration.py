import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")

from app.core.config import settings
from app.main import app
from app.services.account_store import clear_account_store_for_tests, ensure_account_schema, load_persisted_run


class ContestMigrationTest(unittest.TestCase):
    def setUp(self):
        clear_account_store_for_tests()
        self.client = TestClient(app)

    def test_schema_migration_is_restart_safe(self):
        first = ensure_account_schema()
        second = ensure_account_schema()
        self.assertEqual(first["status"], "ok")
        self.assertEqual(second["status"], "ok")

    def test_new_project_accepts_contest_slug_and_keeps_display_name(self):
        response = self.client.post("/api/projects", json={"title": "Музей", "contest_slug": "fpg"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["contest_slug"], "fpg")
        self.assertEqual(response.json()["competition"], "Фонд президентских грантов")

    def test_conflicting_legacy_and_slug_values_are_rejected(self):
        response = self.client.post(
            "/api/projects",
            json={"title": "Музей", "competition": "ПФКИ", "contest_slug": "fpg"},
        )
        self.assertEqual(response.status_code, 400)

    def test_legacy_run_persists_pfki_context_and_profile_version(self):
        with patch.object(settings, "product_registry_runtime_enabled", True):
            response = self.client.post(
                "/api/module-runs",
                json={
                    "module_slug": "social-research",
                    "inputs": {
                        "region": "Москва",
                        "direction": "театр",
                        "target_group": "подростки",
                        "problem": "мало занятий",
                    },
                },
            )
        self.assertEqual(response.status_code, 200)
        persisted = load_persisted_run(response.json()["run_id"])
        self.assertEqual(persisted.contest_slug, "pfki")
        self.assertEqual(persisted.profile_version, "1.0.0")


if __name__ == "__main__":
    unittest.main()
