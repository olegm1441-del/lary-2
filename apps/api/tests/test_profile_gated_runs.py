import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")

from app.core.config import settings
from app.main import app
from app.services.account_store import clear_account_store_for_tests, get_usage
from app.services.product_registry import get_product_registry


class ProfileGatedRunsTest(unittest.TestCase):
    def setUp(self):
        clear_account_store_for_tests()
        self.client = TestClient(app)

    def test_preparing_general_profile_does_not_call_engine_or_spend(self):
        with patch.object(settings, "product_registry_runtime_enabled", True):
            before = self.client.get("/api/usage").json()
            with patch("app.routers.module_runs.create_module_run") as engine:
                response = self.client.post(
                    "/api/module-runs",
                    json={"module_slug": "social-research", "contest_slug": "fpg", "inputs": {}},
                )
            after = self.client.get("/api/usage").json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["error_code"], "MODULE_CONTEST_PROFILE_PREPARING")
        engine.assert_not_called()
        self.assertEqual(before["paid_runs"], after["paid_runs"])
        self.assertEqual(before["modules"], after["modules"])

    def test_preparing_salary_profile_does_not_call_sources(self):
        with patch.object(settings, "product_registry_runtime_enabled", True):
            with patch("app.services.salary_calculator.collect_production_salary_source_results") as sources:
                response = self.client.post(
                    "/api/modules/salary/generate",
                    json={"contest_slug": "fpg", "region": "Москва", "positions": []},
                )
        self.assertEqual(response.status_code, 409)
        sources.assert_not_called()

    def test_profile_version_mismatch_is_safe_and_no_spend(self):
        with patch.object(settings, "product_registry_runtime_enabled", True):
            response = self.client.post(
                "/api/module-runs",
                json={
                    "module_slug": "social-research",
                    "contest_slug": "pfki",
                    "profile_version": "0.0.1",
                    "inputs": {"region": "Москва"},
                },
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["error_code"], "PROFILE_VERSION_MISMATCH")

    def test_legacy_payload_defaults_to_pfki_ready_profile(self):
        profile = get_product_registry().require_ready_profile("social-research", "pfki")
        self.assertEqual(profile.profile_version, "1.0.0")
        with patch.object(settings, "product_registry_runtime_enabled", True):
            response = self.client.post(
                "/api/module-runs",
                json={
                    "module_slug": "social-research",
                    "inputs": {
                        "region": "Москва",
                        "direction": "театр",
                        "target_group": "подростки 14–17 лет",
                        "problem": "мало доступных занятий",
                    },
                },
            )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
