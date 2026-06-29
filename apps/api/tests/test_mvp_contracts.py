import os
import hashlib
import sqlite3
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
os.environ.setdefault("LARY_STATE_SQLITE_PATH", str(Path(tempfile.mkdtemp(prefix="lary-state-test-")) / "state.sqlite3"))

from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.ai_router import extract_gigachat_text  # noqa: E402
from app.services.vosk_model_manager import ensure_vosk_model_available  # noqa: E402
from app.services.vosk_speech import VoskSpeechError, transcribe_with_vosk  # noqa: E402
from app.services.run_store import run_store  # noqa: E402
from app.services.account_store import clear_account_store_for_tests, ensure_account_schema, simulate_account_store_restart_for_tests  # noqa: E402


class LaryMvpContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        run_store.clear()
        clear_account_store_for_tests()
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
        self.assertNotIn("pdf", created["downloads"])

        result_response = self.client.get(f"/api/module-runs/{created['run_id']}/result")
        self.assertEqual(result_response.status_code, 200)
        result = result_response.json()
        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(len(result["sections"]), 4)

        for fmt in ["docx"]:
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

    def test_usage_cookie_and_server_side_free_attempts_are_per_module(self):
        usage = self.client.get("/api/usage")
        self.assertEqual(usage.status_code, 200)
        self.assertIn("anon_session_id", usage.headers.get("set-cookie", ""))
        self.assertIn("HttpOnly", usage.headers.get("set-cookie", ""))
        self.assertTrue(usage.json()["modules"]["social-research"]["free_attempt_available"])

        first = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "social-research",
                "inputs": {
                    "region": "Республика Татарстан",
                    "direction": "музей",
                    "target_group": "молодежь 18-22 лет",
                    "problem": "низкая посещаемость музеев молодежью",
                },
            },
        )
        self.assertEqual(first.status_code, 200)

        after_first = self.client.get("/api/usage").json()
        self.assertFalse(after_first["modules"]["social-research"]["free_attempt_available"])
        self.assertTrue(after_first["modules"]["legal-acts"]["free_attempt_available"])

        repeat = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "social-research",
                "inputs": {
                    "region": "Республика Татарстан",
                    "direction": "музей",
                    "target_group": "молодежь 18-22 лет",
                    "problem": "повторная проверка той же темы",
                },
            },
        )
        self.assertEqual(repeat.status_code, 402)
        self.assertIn("необходимо купить запуск модуля", repeat.json()["detail"]["message"])

        other_module = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "legal-acts",
                "inputs": {
                    "program_level": "Федеральные и региональные документы",
                    "region": "Республика Татарстан",
                    "direction": "музей",
                    "target_group": "молодежь 18-22 лет",
                },
            },
        )
        self.assertEqual(other_module.status_code, 200)

    def test_promo_is_one_time_and_adds_paid_module_runs(self):
        promo = self.client.post("/api/promos/apply", json={"code": "LARY-START"})
        self.assertEqual(promo.status_code, 200)
        self.assertEqual(promo.json()["added_runs"], 3)
        self.assertEqual(promo.json()["remaining_runs"], 3)

        duplicate = self.client.post("/api/promos/apply", json={"code": "LARY-START"})
        self.assertEqual(duplicate.status_code, 409)
        self.assertIn("Промокод уже применен", duplicate.json()["detail"]["message"])

        first = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "social-research",
                "inputs": {
                    "region": "Москва",
                    "direction": "театр",
                    "target_group": "подростки 14-17 лет",
                    "problem": "мало доступных театральных занятий",
                },
            },
        )
        self.assertEqual(first.status_code, 200)
        paid_repeat = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "social-research",
                "inputs": {
                    "region": "Москва",
                    "direction": "театр",
                    "target_group": "подростки 14-17 лет",
                    "problem": "нужен второй вариант результата",
                },
            },
        )
        self.assertEqual(paid_repeat.status_code, 200)
        self.assertEqual(self.client.get("/api/usage").json()["paid_runs"], 2)

    def test_payment_webhook_is_idempotent_and_frontend_cannot_set_price(self):
        payment = self.client.post("/api/payments/create", json={"package": "single", "amount_rub": 1, "runs": 99})
        self.assertEqual(payment.status_code, 200)
        payload = payment.json()
        self.assertEqual(payload["amount_rub"], 320)
        self.assertEqual(payload["runs"], 1)

        status = self.client.get(f"/api/payments/{payload['payment_id']}")
        self.assertEqual(status.status_code, 200)
        self.assertIn(status.json()["status"], ["created", "pending"])

        webhook_payload = {
            "payment_id": payload["payment_id"],
            "provider_payment_id": "provider-payment-1",
            "status": "paid",
            "signature": "placeholder-signature",
        }
        webhook = self.client.post("/api/payments/webhook/placeholder", json=webhook_payload)
        self.assertEqual(webhook.status_code, 200)
        self.assertEqual(webhook.json()["runs_added"], 1)

        duplicate = self.client.post("/api/payments/webhook/placeholder", json=webhook_payload)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["runs_added"], 0)
        self.assertEqual(self.client.get("/api/usage").json()["paid_runs"], 1)

    def test_six_run_payment_package_amount_and_webhook_crediting(self):
        payment = self.client.post("/api/payments/create", json={"package": "six", "amount_rub": 1, "runs": 99})
        self.assertEqual(payment.status_code, 200)
        payload = payment.json()
        self.assertEqual(payload["amount_rub"], 1920)
        self.assertEqual(payload["runs"], 6)

        webhook_payload = {
            "payment_id": payload["payment_id"],
            "provider_payment_id": "provider-payment-six",
            "status": "paid",
            "signature": "placeholder-signature",
        }
        webhook = self.client.post("/api/payments/webhook/placeholder", json=webhook_payload)
        self.assertEqual(webhook.status_code, 200)
        self.assertEqual(webhook.json()["runs_added"], 6)

        duplicate = self.client.post("/api/payments/webhook/placeholder", json=webhook_payload)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["runs_added"], 0)
        self.assertEqual(self.client.get("/api/usage").json()["paid_runs"], 6)

    def test_payment_webhook_signature_is_checked_when_secret_is_configured(self):
        original_secret = settings.payment_webhook_secret
        settings.payment_webhook_secret = "test-secret"
        try:
            payment = self.client.post("/api/payments/create", json={"package": "single"}).json()
            invalid = self.client.post(
                "/api/payments/webhook/placeholder",
                json={
                    "payment_id": payment["payment_id"],
                    "provider_payment_id": "signed-provider-payment",
                    "status": "paid",
                    "signature": "wrong",
                },
            )
            self.assertEqual(invalid.status_code, 400)

            raw = f"test-secret:placeholder:{payment['payment_id']}:signed-provider-payment:paid"
            signature = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            valid = self.client.post(
                "/api/payments/webhook/placeholder",
                json={
                    "payment_id": payment["payment_id"],
                    "provider_payment_id": "signed-provider-payment",
                    "status": "paid",
                    "signature": signature,
                },
            )
            self.assertEqual(valid.status_code, 200)
            self.assertEqual(valid.json()["runs_added"], 1)
        finally:
            settings.payment_webhook_secret = original_secret

    def test_magic_link_attaches_temporary_work_to_account_and_project(self):
        created = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "support-letter",
                "inputs": {
                    "competition": "ПФКИ",
                    "partner": "Музей города",
                    "project_title": "Музейная смена",
                    "target_value": "подростки получают практику",
                    "region_value": "город Казань",
                },
            },
        )
        self.assertEqual(created.status_code, 200)
        run_id = created.json()["run_id"]

        temporary = self.client.get("/api/account/works")
        self.assertEqual(temporary.status_code, 200)
        self.assertEqual(temporary.json()["mode"], "temporary")
        self.assertEqual(temporary.json()["items"][0]["project"], "Без проекта")

        requested = self.client.post("/api/auth/magic-link/request", json={"email": "owner@example.com"})
        self.assertEqual(requested.status_code, 200)
        token = requested.json()["dev_token"]

        consumed = self.client.post("/api/auth/magic-link/consume", json={"token": token})
        self.assertEqual(consumed.status_code, 200)
        self.assertEqual(consumed.json()["attached_works"], 1)

        account_works = self.client.get("/api/account/works").json()
        self.assertEqual(account_works["mode"], "account")
        self.assertEqual(account_works["items"][0]["run_id"], run_id)
        self.assertEqual(account_works["items"][0]["project"], "Без проекта")

        project = self.client.post("/api/projects", json={"title": "Музейная заявка", "competition": "ПФКИ"})
        self.assertEqual(project.status_code, 200)
        attached = self.client.post(f"/api/projects/{project.json()['project_id']}/attach", json={"run_id": run_id})
        self.assertEqual(attached.status_code, 200)
        self.assertEqual(self.client.get("/api/account/works").json()["items"][0]["project"], "Музейная заявка")
        projects = self.client.get("/api/projects")
        self.assertEqual(projects.status_code, 200)
        self.assertEqual(projects.json()["items"][0]["works_count"], 1)

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

    def test_field_assistant_uses_deterministic_blocking_rules(self):
        social = self.client.post(
            "/api/field-assistant/analyze",
            json={
                "module_slug": "social-research",
                "field_key": "target_group",
                "field_label": "Целевая группа",
                "value": "молодежь",
                "form_context": {"region": "Республика Татарстан"},
            },
        )
        self.assertEqual(social.status_code, 200)
        self.assertEqual(social.json()["status"], "warning")
        self.assertFalse(social.json()["should_block"])
        self.assertIn("возраст", social.json()["message"])
        self.assertLessEqual(len(social.json()["message"]), 140)

        legal = self.client.post(
            "/api/field-assistant/analyze",
            json={
                "module_slug": "legal-acts",
                "field_key": "region",
                "field_label": "Регион",
                "value": "",
                "form_context": {"program_level": "Федеральные и региональные документы"},
            },
        )
        self.assertEqual(legal.status_code, 200)
        self.assertEqual(legal.json()["status"], "error")
        self.assertTrue(legal.json()["should_block"])
        self.assertEqual(legal.json()["message"], "Для региональных документов нужен регион.")

        salary = self.client.post(
            "/api/field-assistant/analyze",
            json={
                "module_slug": "salary",
                "field_key": "employment_percent",
                "field_label": "Занятость одного сотрудника, %",
                "value": "120",
                "form_context": {},
            },
        )
        self.assertEqual(salary.status_code, 200)
        self.assertEqual(salary.json()["status"], "error")
        self.assertTrue(salary.json()["should_block"])

        support_empty = self.client.post(
            "/api/field-assistant/analyze",
            json={
                "module_slug": "support-letter",
                "field_key": "contribution_amount",
                "field_label": "Вклад в рублях",
                "value": "",
                "form_context": {},
            },
        )
        self.assertEqual(support_empty.status_code, 200)
        self.assertEqual(support_empty.json()["status"], "warning")
        self.assertFalse(support_empty.json()["should_block"])

        support_letters = self.client.post(
            "/api/field-assistant/analyze",
            json={
                "module_slug": "support-letter",
                "field_key": "contribution_amount",
                "field_label": "Вклад в рублях",
                "value": "пятьдесят тысяч рублей",
                "form_context": {},
            },
        )
        self.assertEqual(support_letters.status_code, 200)
        self.assertEqual(support_letters.json()["status"], "error")
        self.assertTrue(support_letters.json()["should_block"])

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

    def test_support_letter_ai_does_not_write_cofinance_amounts(self):
        original_credentials = settings.gigachat_credentials
        settings.gigachat_credentials = "test"
        captured_prompts: list[str] = []

        def fake_gigachat(prompt: str) -> str:
            captured_prompts.append(prompt)
            return """
РАЗДЕЛ: Текст поддержки
ТЕКСТ: Проект важен для территории и помогает целевой группе получить доступ к культурным событиям.

РАЗДЕЛ: Вклад партнера
ТЕКСТ: Оценка вклада: 300 тыс. рублей. Финансовый вклад партнера составляет 300 000 рублей.
"""

        try:
            with patch("app.services.module_engine.generate_with_gigachat", side_effect=fake_gigachat):
                response = self.client.post(
                    "/api/module-runs",
                    json={
                        "module_slug": "support-letter",
                        "inputs": {
                            "project_title": "Музейная смена",
                            "region": "Краснодарский край",
                            "target_group": "молодежь 18-22 лет",
                            "target_value": "молодежь получает культурную практику",
                            "region_value": "проект усиливает музейную повестку региона",
                            "support_type": "Информационная поддержка",
                            "details": "партнер готов рассказать о проекте своей аудитории",
                        },
                    },
                )
        finally:
            settings.gigachat_credentials = original_credentials

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        result = self.client.get(f"/api/module-runs/{payload['run_id']}/result").json()
        joined = "\n".join([section["title"] + "\n" + section["body"] for section in result["sections"]])

        self.assertTrue(captured_prompts)
        self.assertIn("не пиши сумму софинансирования", captured_prompts[0].lower())
        self.assertNotIn("Оценка вклада: 300 тыс. рублей", joined)
        self.assertNotIn("Финансовый вклад партнера составляет 300 000 рублей", joined)
        self.assertNotIn("300 тыс", joined)
        self.assertNotIn("300 000 рублей", joined)
        self.assertIn("Проект важен для территории", joined)

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

    def test_result_can_be_saved_to_email_account_for_later_delivery(self):
        create_response = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "social-research",
                "inputs": {
                    "region": "Республика Татарстан",
                    "direction": "музей",
                    "target_group": "молодежь 18-22 лет",
                    "problem": "низкая посещаемость музеев молодежью",
                },
            },
        )
        self.assertEqual(create_response.status_code, 200)
        run_id = create_response.json()["run_id"]

        save_response = self.client.post(
            f"/api/module-runs/{run_id}/email-file",
            json={"email": "test@example.com", "password": "strong-pass"},
        )

        self.assertEqual(save_response.status_code, 200)
        payload = save_response.json()
        self.assertEqual(payload["status"], "saved")
        self.assertEqual(payload["email"], "test@example.com")
        self.assertIn("docx", payload["file_format"])
        self.assertIn("личном кабинете", payload["message"])

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

    def test_salary_split_fields_are_validated_before_generation(self):
        invalid = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "salary",
                "inputs": {
                    "role": "Координатор",
                    "region": "Республика Татарстан",
                    "functionality": "Координация команды и календарного плана",
                    "months": "0",
                    "employee_count": "1",
                    "employment_percent": "120",
                    "cofunding": "Собственные средства",
                },
            },
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("Срок работы должен быть больше нуля", invalid.json()["detail"]["message"])

        valid = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "salary",
                "inputs": {
                    "role": "Координатор",
                    "region": "Республика Татарстан",
                    "functionality": "Координация команды и календарного плана",
                    "months": "4",
                    "employee_count": "2",
                    "employment_percent": "40",
                    "employment_hours": "16 часов в неделю",
                    "cofunding": "Собственные средства",
                },
            },
        )
        self.assertEqual(valid.status_code, 200)
        result = self.client.get(f"/api/module-runs/{valid.json()['run_id']}/result").json()
        joined = "\n".join(section["body"] for section in result["sections"])
        self.assertIn("Количество сотрудников в этой роли: 2", joined)
        self.assertIn("Занятость одного сотрудника: 40%", joined)
        self.assertIn("ВСТАВЬТЕ НОМЕРА МЕРОПРИЯТИЙ КАЛЕНДАРНОГО ПЛАНА", joined)

    def test_sql_state_survives_restart_for_usage_magic_link_payment_and_project(self):
        created = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "social-research",
                "inputs": {
                    "region": "Республика Татарстан",
                    "direction": "музейная память",
                    "target_group": "молодежь 18-34 года",
                    "problem": "молодежь редко вовлечена в музейные проекты",
                },
            },
        )
        self.assertEqual(created.status_code, 200)
        run_id = created.json()["run_id"]

        project = self.client.post("/api/projects", json={"title": "Музейная заявка", "competition": "ПФКИ"})
        self.assertEqual(project.status_code, 200)
        project_id = project.json()["project_id"]
        attached = self.client.post(f"/api/projects/{project_id}/attach", json={"run_id": run_id})
        self.assertEqual(attached.status_code, 200)

        promo = self.client.post("/api/promos/apply", json={"code": "LARY-START"})
        self.assertEqual(promo.status_code, 200)

        payment = self.client.post("/api/payments/create", json={"package": "single"}).json()
        webhook = self.client.post(
            "/api/payments/webhook/placeholder",
            json={"payment_id": payment["payment_id"], "provider_payment_id": "restart-payment-1", "status": "paid"},
        )
        self.assertEqual(webhook.status_code, 200)

        magic = self.client.post("/api/auth/magic-link/request", json={"email": "restart@example.com"})
        self.assertEqual(magic.status_code, 200)
        token = magic.json()["dev_token"]

        run_store.clear()
        simulate_account_store_restart_for_tests()

        usage = self.client.get("/api/usage").json()
        self.assertFalse(usage["modules"]["social-research"]["free_attempt_available"])
        self.assertEqual(usage["paid_runs"], 4)

        works = self.client.get("/api/account/works").json()
        self.assertEqual(works["items"][0]["run_id"], run_id)
        self.assertEqual(works["items"][0]["project"], "Музейная заявка")

        consumed = self.client.post("/api/auth/magic-link/consume", json={"token": token})
        self.assertEqual(consumed.status_code, 200)
        self.assertEqual(consumed.json()["attached_works"], 1)

        repeated = self.client.post("/api/auth/magic-link/consume", json={"token": token})
        self.assertEqual(repeated.status_code, 400)

    def test_module_result_and_download_survive_run_store_restart(self):
        created = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "legal-acts",
                "inputs": {
                    "program_level": "Федеральные и региональные документы",
                    "region": "Республика Татарстан",
                    "direction": "музейная память",
                    "target_group": "молодежь 18-34 года",
                },
            },
        )
        self.assertEqual(created.status_code, 200)
        run_id = created.json()["run_id"]
        docx_path = Path(settings.file_storage_dir) / run_id / "legal-acts.docx"
        self.assertTrue(docx_path.exists())
        docx_path.unlink()

        run_store.clear()
        simulate_account_store_restart_for_tests()

        result = self.client.get(f"/api/module-runs/{run_id}/result")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["run_id"], run_id)
        self.assertIn("docx", result.json()["downloads"])

        download = self.client.get(f"/api/module-runs/{run_id}/download/docx")
        self.assertEqual(download.status_code, 200)
        self.assertGreater(len(download.content), 500)

    def test_deleted_work_is_removed_from_account_and_old_links(self):
        created = self.client.post(
            "/api/module-runs",
            json={
                "module_slug": "support-letter",
                "inputs": {
                    "project_title": "Музейная смена",
                    "partner": "Музей города",
                    "target_value": "молодежь получает практику",
                },
            },
        )
        self.assertEqual(created.status_code, 200)
        run_id = created.json()["run_id"]

        deleted = self.client.delete(f"/api/account/works/{run_id}")
        self.assertEqual(deleted.status_code, 200)

        works = self.client.get("/api/account/works").json()
        self.assertEqual(works["items"], [])
        self.assertEqual(self.client.get(f"/api/module-runs/{run_id}/result").status_code, 404)
        self.assertEqual(self.client.get(f"/api/module-runs/{run_id}/download/docx").status_code, 404)

    def test_sql_bootstrap_migrates_legacy_devices_and_works_tables(self):
        original_path = settings.state_sqlite_path
        legacy_db = Path(tempfile.mkdtemp(prefix="lary-legacy-state-")) / "state.sqlite3"
        conn = sqlite3.connect(legacy_db)
        try:
            conn.execute(
                """
                create table devices (
                    id text primary key,
                    user_id text,
                    fingerprint text not null unique,
                    first_seen_at text,
                    last_seen_at text
                )
                """
            )
            conn.execute(
                """
                create table works (
                    id text primary key,
                    run_id text not null unique,
                    anon_session_id text,
                    user_id text,
                    project_id text,
                    module_slug text not null,
                    title text not null,
                    status text not null,
                    file_format text not null,
                    download_path text not null,
                    created_at text,
                    expires_at text
                )
                """
            )
            conn.execute("create table credit_ledger (id text primary key)")
            conn.commit()
        finally:
            conn.close()

        settings.state_sqlite_path = str(legacy_db)
        run_store.clear()
        try:
            ensure_account_schema()
            legacy_client = TestClient(app)
            usage = legacy_client.get("/api/usage")
            self.assertEqual(usage.status_code, 200)
            created = legacy_client.post(
                "/api/module-runs",
                json={
                    "module_slug": "social-research",
                    "inputs": {
                        "region": "Республика Татарстан",
                        "direction": "музей",
                        "target_group": "молодежь 18-34 года",
                        "problem": "молодежь редко участвует в музейных проектах",
                    },
                },
            )
            self.assertEqual(created.status_code, 200)
            self.assertEqual(legacy_client.get("/api/account/works").status_code, 200)
        finally:
            settings.state_sqlite_path = original_path


if __name__ == "__main__":
    unittest.main()
