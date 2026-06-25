import os
from urllib.parse import unquote
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("FILE_STORAGE_DIR", tempfile.mkdtemp(prefix="lary-api-test-"))

from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.ai_router import extract_gigachat_text  # noqa: E402
from app.services.vosk_model_manager import ensure_vosk_model_available  # noqa: E402
from app.services.vosk_speech import VoskSpeechError, transcribe_with_vosk  # noqa: E402
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

    def test_vosk_speech_reports_missing_model_cleanly(self):
        original_path = settings.vosk_model_path
        settings.vosk_model_path = "/tmp/lary-missing-vosk-model"
        try:
            with self.assertRaises(VoskSpeechError) as error:
                transcribe_with_vosk(b"demo", "audio/x-pcm;bit=16;rate=16000")
        finally:
            settings.vosk_model_path = original_path

        self.assertEqual(error.exception.code, "vosk_model_missing")

    def test_speech_uses_vosk_provider_without_salute_key_requirement(self):
        original_provider = settings.speech_provider
        original_path = settings.vosk_model_path
        original_key = settings.salute_speech_authorization_key
        settings.speech_provider = "vosk"
        settings.vosk_model_path = "/tmp/lary-missing-vosk-model"
        settings.salute_speech_authorization_key = None
        try:
            speech = self.client.post("/api/speech/transcribe", files={"audio": ("voice.pcm", b"demo", "audio/x-pcm")})
        finally:
            settings.speech_provider = original_provider
            settings.vosk_model_path = original_path
            settings.salute_speech_authorization_key = original_key

        self.assertEqual(speech.status_code, 503)
        self.assertEqual(speech.json()["detail"]["code"], "vosk_model_missing")

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

    def test_module_sections_do_not_mix_advisory_copy_into_user_result(self):
        response = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "legal-acts",
                "inputs": {
                    "program_level": "Федеральные и региональные документы",
                    "region": "Краснодарский край, Краснодар",
                    "direction": "Музей",
                    "target_group": "молодежь от 18 до 22 лет, не пользующиеся пушкинской картой",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        result = self.client.get(f"/api/module-runs/{payload['run_id']}/result").json()
        sections_by_title = {section["title"]: section["body"] for section in result["sections"]}

        self.assertEqual(
            sections_by_title["Целевая группа"],
            "Основная аудитория: молодежь от 18 до 22 лет, не пользующиеся пушкинской картой.",
        )
        joined = "\n".join(section["body"] for section in result["sections"])
        self.assertNotIn("Уточните возраст, статус и территорию", joined)
        self.assertNotIn("Для финальной заявки нужны проверенные источники", joined)

    def test_legal_acts_ai_result_is_structured_without_raw_markdown(self):
        original_credentials = settings.gigachat_credentials
        settings.gigachat_credentials = "test"
        ai_text = """
### 1. **Федеральный уровень**
**Краткое описание:** Постановление Правительства РФ №… от _______ года, официальный источник: <правительство.рф>.

---

### 2. **Региональный уровень**
**Краткое описание:** Государственная программа Краснодарского края в сфере культуры — проверить актуальную редакцию.
"""
        try:
            with patch("app.services.module_engine.generate_with_gigachat", return_value=ai_text):
                response = self.client.post(
                    "/api/module-runs",
                    json={
                        "module_slug": "legal-acts",
                        "inputs": {
                            "program_level": "Федеральные и региональные документы",
                            "region": "Краснодарский край, Краснодар",
                            "direction": "Пушкинская карта и музей",
                            "target_group": "молодежь 18-22 лет",
                        },
                    },
                )
        finally:
            settings.gigachat_credentials = original_credentials

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        result = self.client.get(f"/api/module-runs/{payload['run_id']}/result").json()
        titles = [section["title"] for section in result["sections"]]
        joined = "\n".join([section["title"] + "\n" + section["body"] for section in result["sections"]])

        self.assertNotIn("AI-уточнение", titles)
        self.assertIn("Федеральный уровень", titles)
        self.assertIn("Региональный уровень", titles)
        self.assertNotIn("**", joined)
        self.assertNotIn("###", joined)
        self.assertNotIn("Краткое описание", joined)
        self.assertNotIn("<", joined)
        self.assertNotIn("__.__", joined)
        self.assertNotIn("№ от", joined)
        self.assertNotIn("№…", joined)
        self.assertNotIn("____", joined)

    def test_vosk_model_can_be_downloaded_from_configured_archive(self):
        temp_dir = Path(tempfile.mkdtemp(prefix="lary-vosk-model-test-"))
        archive_path = temp_dir / "model.zip"
        target_path = temp_dir / "mounted" / "vosk-model-small-ru-0.22"
        with ZipFile(archive_path, "w") as archive:
            archive.writestr("vosk-model-small-ru-0.22/conf/model.conf", "fake model for startup test")
            archive.writestr("vosk-model-small-ru-0.22/graph/phones/word_boundary.int", "fake")

        original_provider = settings.speech_provider
        original_path = settings.vosk_model_path
        original_url = settings.vosk_model_url
        original_auto_download = settings.vosk_auto_download
        settings.speech_provider = "vosk"
        settings.vosk_model_path = str(target_path)
        settings.vosk_model_url = archive_path.as_uri()
        settings.vosk_auto_download = True
        try:
            ensure_vosk_model_available()
        finally:
            settings.speech_provider = original_provider
            settings.vosk_model_path = original_path
            settings.vosk_model_url = original_url
            settings.vosk_auto_download = original_auto_download

        self.assertTrue((target_path / "conf" / "model.conf").exists())

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
