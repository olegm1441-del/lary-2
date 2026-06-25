import os
import tempfile
import unittest

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("FILE_STORAGE_DIR", tempfile.mkdtemp(prefix="lary-api-test-"))

from app.main import app  # noqa: E402
from app.services.run_store import run_store  # noqa: E402


class LaryMvpContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        run_store.clear()
        self.client = TestClient(app)

    def test_modules_catalog_exposes_six_active_modules_and_future_check(self):
        response = self.client.get("/api/modules")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        active = [item["slug"] for item in payload["items"] if item["status"] == "active"]
        future = [item["slug"] for item in payload["items"] if item["status"] == "coming_soon"]

        self.assertEqual(
            active,
            [
                "social-research",
                "legal-acts",
                "salary",
                "support-letter",
                "presentation",
                "scenario-plan",
            ],
        )
        self.assertEqual(future, ["check-application"])

    def test_module_run_generates_result_and_downloadable_files(self):
        create_response = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "support-letter",
                "inputs": {
                    "project_title": "Фестиваль дворового футбола",
                    "region": "Республика Татарстан",
                    "target_group": "подростки 12-17 лет",
                    "problem": "мало регулярных дворовых событий",
                    "partner": "местная спортивная школа",
                },
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created = create_response.json()
        self.assertEqual(created["status"], "completed")
        self.assertIn("run_id", created)
        self.assertIn("docx", created["downloads"])
        self.assertIn("pdf", created["downloads"])

        result_response = self.client.get(f"/api/module-runs/{created['run_id']}/result")
        self.assertEqual(result_response.status_code, 200)
        result = result_response.json()
        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(len(result["sections"]), 4)

        for fmt in ["docx", "pdf"]:
            download = self.client.get(f"/api/module-runs/{created['run_id']}/download/{fmt}")
            self.assertEqual(download.status_code, 200)
            self.assertGreater(len(download.content), 500)

    def test_presentation_run_generates_real_pptx(self):
        response = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "presentation",
                "presentation_variant": "calendar_plan",
                "inputs": {
                    "project_title": "Культурный фестиваль малых городов",
                    "region": "Свердловская область",
                    "target_group": "семьи с детьми",
                    "problem": "нужно показать календарный план проекта",
                    "project_description": "Фестиваль с мастер-классами, концертом и выставкой.",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "completed")
        self.assertIn("pptx", payload["downloads"])

        download = self.client.get(f"/api/module-runs/{payload['run_id']}/download/pptx")
        self.assertEqual(download.status_code, 200)
        self.assertGreater(len(download.content), 10_000)
        self.assertEqual(download.content[:2], b"PK")

    def test_payment_promo_and_speech_contracts_are_friendly(self):
        payment = self.client.post("/api/payments/create", json={"package": "single"})
        self.assertEqual(payment.status_code, 200)
        self.assertEqual(payment.json()["amount_rub"], 320)

        promo = self.client.post("/api/promos/apply", json={"code": "LARY-START"})
        self.assertEqual(promo.status_code, 200)
        self.assertEqual(promo.json()["added_runs"], 3)

        speech = self.client.post("/api/speech/transcribe", files={"audio": ("voice.webm", b"demo", "audio/webm")})
        self.assertEqual(speech.status_code, 503)
        self.assertIn("Голосовой ввод временно недоступен", speech.json()["detail"]["message"])


if __name__ == "__main__":
    unittest.main()
