import os
from urllib.parse import unquote
import tempfile
import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("FILE_STORAGE_DIR", tempfile.mkdtemp(prefix="lary-api-test-"))

from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.ai_router import extract_gigachat_text  # noqa: E402
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

    def test_ai_test_errors_are_user_friendly(self):
        original_credentials = settings.gigachat_credentials
        settings.gigachat_credentials = None
        try:
            response = self.client.post("/api/ai/test", json={"text": "проект про дворовый футбол"})
        finally:
            settings.gigachat_credentials = original_credentials

        self.assertEqual(response.status_code, 503)
        self.assertIn("AI-проверка временно недоступна", response.json()["detail"]["message"])
        self.assertNotIn("GigaChat", str(response.json()))

    def test_gigachat_response_text_is_extracted_from_current_sdk_shape(self):
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="  Рабочий ответ Лари  "),
                )
            ]
        )

        self.assertEqual(extract_gigachat_text(response), "Рабочий ответ Лари")

    def test_speech_rejects_browser_webm_before_provider_call(self):
        original_key = settings.salute_speech_authorization_key
        settings.salute_speech_authorization_key = "test-key"
        try:
            speech = self.client.post("/api/speech/transcribe", files={"audio": ("voice.webm", b"demo", "audio/webm")})
        finally:
            settings.salute_speech_authorization_key = original_key

        self.assertEqual(speech.status_code, 415)
        self.assertEqual(speech.json()["detail"]["code"], "unsupported_audio_format")

    def test_social_research_keeps_user_inputs_and_russian_download_filename(self):
        response = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "social-research",
                "inputs": {
                    "region": "Республика Татарстан",
                    "direction": "дворовой футбол",
                    "target_group": "подростки 12-17 лет",
                    "problem": "мало регулярных дворовых событий для подростков в малых городах",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        result = self.client.get(f"/api/module-runs/{payload['run_id']}/result").json()
        joined = "\n".join([result["title"], result["summary"]] + [section["body"] for section in result["sections"]])

        self.assertIn("Республика Татарстан", joined)
        self.assertIn("дворовой футбол", joined)
        self.assertIn("подростки 12-17 лет", joined)
        self.assertNotIn("территория проекта", joined)
        self.assertNotIn("целевая группа", joined)

        download = self.client.get(f"/api/module-runs/{payload['run_id']}/download/docx")
        content_disposition = unquote(download.headers["content-disposition"])
        self.assertIn("Анализ социальной значимости", content_disposition)

    def test_legacy_russian_field_keys_are_normalized(self):
        response = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "social-research",
                "inputs": {
                    "регион": "Республика Татарстан",
                    "основное_направление": "дворовой футбол",
                    "целевая_группа": "подростки 12-17 лет",
                    "описание_проблемы": "мало регулярных дворовых событий",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        result = self.client.get(f"/api/module-runs/{payload['run_id']}/result").json()
        joined = "\n".join([result["title"], result["summary"]] + [section["body"] for section in result["sections"]])
        self.assertIn("Республика Татарстан", joined)
        self.assertIn("дворовой футбол", joined)

    def test_module_validation_returns_contextual_inline_hints(self):
        response = self.client.post(
            "/api/modules/social-research/validate-inputs",
            json={
                "inputs": {
                    "region": "Татарстан",
                    "target_group": "подростки",
                    "problem": "мало событий",
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        messages = [item["message"] for item in payload["hints"]]
        self.assertTrue(any("город" in message or "район" in message for message in messages))
        self.assertTrue(any("возраст" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
