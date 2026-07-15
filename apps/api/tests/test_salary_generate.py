import json
import os
import unittest
from unittest.mock import patch

from docx import Document
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")

from app.main import app  # noqa: E402
from app.services.account_store import clear_account_store_for_tests  # noqa: E402
from app.services.salary_calculator import SalaryGenerateRequest, create_salary_run  # noqa: E402
from app.services.salary_sources.models import SalarySourceResult  # noqa: E402


class SalaryGenerateTest(unittest.TestCase):
    def setUp(self):
        clear_account_store_for_tests()

    def _payload(self, **overrides):
        payload = {
            "region": "Свердловская область",
            "source_scope": "all",
            "cofinance_source": "own_legal_entity_funds",
            "positions": [
                {
                    "role_title": "координатор проектов",
                    "staff_count": 1,
                    "duration_months": 4,
                    "workload_mode": "percent",
                    "workload_value": 40,
                    "functionality": "",
                    "calendar_events": "1.1–1.4, 2.1–2.3, 3.1",
                }
            ],
        }
        payload.update(overrides)
        return payload

    def test_generate_calculates_percent_position_and_persists_run(self):
        source = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="координатор проектов",
            matched_role="координатор проекта",
            region="Свердловская область",
            year=2025,
            salary_value=68_372,
            salary_type="mean",
            source_url="https://sverdlovskaya-oblast.gorodrabot.ru/salaries/koordinator-proekta?y=2025",
            notes="Источник показывает зарплатные предложения в вакансиях, а не фактически выплаченную заработную плату.",
        )

        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[source]):
            response = client.post("/api/modules/salary/generate", json=self._payload())

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module_slug"], "salary")
        self.assertEqual(payload["total_amount"], 109_395)
        self.assertIn("plain_text", payload)
        self.assertIn("К включению в бюджет: 109 395 руб.", payload["plain_text"])
        self.assertIn("Сотрудник выполняет функции, связанные с обеспечением задач проекта", payload["plain_text"])
        self.assertIn("docx", payload["downloads"])

        persisted = client.get(f"/api/module-runs/{payload['run_id']}/result")
        self.assertEqual(persisted.status_code, 200)
        self.assertIn("Расчет зарплаты", persisted.json()["title"])

    def test_generate_calculates_multiple_positions_and_hours_formula(self):
        coordinator = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="координатор проекта",
            matched_role="координатор проекта",
            region="Свердловская область",
            salary_value=70_000,
            salary_type="mean",
            source_url="https://gorodrabot.ru/1",
        )
        organizer = SalarySourceResult(
            source="trudvsem",
            status="ok",
            query_role="организатор мероприятий",
            matched_role="организатор мероприятий",
            region="Свердловская область",
            salary_value=80_000,
            salary_type="vacancy_sample_median",
            sample_size=40,
            source_url="https://trudvsem.ru/2",
        )

        def fake_sources(role, region, year=None):
            return [organizer] if "организатор" in role else [coordinator]

        payload = self._payload(
            source_scope="aggregators",
            cofinance_source="partner_letter_funds",
            positions=[
                {
                    "role_title": "координатор проекта",
                    "staff_count": 1,
                    "duration_months": 4,
                    "workload_mode": "percent",
                    "workload_value": 40,
                    "functionality": "ведет списки участников, согласует расписание, собирает обратную связь",
                    "calendar_events": "1.1–1.4",
                },
                {
                    "role_title": "организатор мероприятий",
                    "staff_count": 2,
                    "duration_months": 3,
                    "workload_mode": "hours_total",
                    "workload_value": 96,
                    "functionality": "",
                    "calendar_events": "",
                },
            ],
        )

        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", side_effect=fake_sources):
            response = client.post("/api/modules/salary/generate", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_amount"], 204_530)
        self.assertIn("70 000 руб. × 40% × 4 мес. × 1", body["plain_text"])
        self.assertIn("80 000 руб. / 166 × 96 ч. × 2", body["plain_text"])
        self.assertIn("Итого к включению в бюджет: 204 530 руб.", body["plain_text"])
        self.assertIn("привлеченные средства согласно письму поддержки", body["plain_text"])
        self.assertNotIn("Позиция 1", body["plain_text"])
        self.assertNotIn("Позиция 2", body["plain_text"])

    def test_generate_uses_position_level_cofinance_sources(self):
        coordinator = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="координатор проекта",
            region="Свердловская область",
            salary_value=70_000,
            salary_type="mean",
            source_url="https://gorodrabot.ru/1",
        )
        organizer = SalarySourceResult(
            source="trudvsem",
            status="ok",
            query_role="организатор мероприятий",
            region="Свердловская область",
            salary_value=80_000,
            salary_type="vacancy_sample_median",
            source_url="https://trudvsem.ru/2",
        )

        def fake_sources(role, region, year=None):
            return [organizer] if "организатор" in role else [coordinator]

        payload = {
            "region": "Свердловская область",
            "positions": [
                {
                    "role_title": "координатор проекта",
                    "staff_count": 1,
                    "duration_months": 4,
                    "workload_mode": "percent",
                    "workload_value": 40,
                    "functionality": "",
                    "calendar_events": "1",
                    "cofinance_source": "own_legal_entity_funds",
                },
                {
                    "role_title": "организатор мероприятий",
                    "staff_count": 1,
                    "duration_months": 3,
                    "workload_mode": "percent",
                    "workload_value": 50,
                    "functionality": "",
                    "calendar_events": "2",
                    "cofinance_source": "partner_letter_funds",
                },
            ],
        }

        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", side_effect=fake_sources):
            response = client.post("/api/modules/salary/generate", json=payload)

        self.assertEqual(response.status_code, 200)
        text = response.json()["plain_text"]
        self.assertIn("Источник софинансирования: собственные средства юридического лица.", text)
        self.assertIn("Источник софинансирования: привлеченные средства согласно письму поддержки.", text)

    def test_generate_selects_highest_eligible_source_not_first(self):
        lower = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="координатор проекта",
            region="Свердловская область",
            salary_value=59_003,
            salary_type="mean",
            source_url="https://gorodrabot.ru/low",
        )
        higher = SalarySourceResult(
            source="trudvsem",
            status="ok",
            query_role="координатор проекта",
            region="Свердловская область",
            salary_value=74_000,
            salary_type="vacancy_sample_median",
            sample_size=99,
            source_url="https://trudvsem.ru/high",
        )

        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[lower, higher]):
            response = client.post("/api/modules/salary/generate", json=self._payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["positions"][0]["salary_value"], 74_000)
        self.assertIn("Работа России", response.json()["plain_text"])

    def test_production_generate_ignores_inactive_sources_even_if_they_have_higher_values(self):
        gorodrabot = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="координатор проекта",
            region="Свердловская область",
            salary_value=59_003,
            salary_type="mean",
            source_url="https://gorodrabot.ru/low",
        )
        trudvsem = SalarySourceResult(
            source="trudvsem",
            status="ok",
            query_role="координатор проекта",
            region="Свердловская область",
            salary_value=74_000,
            salary_type="vacancy_sample_median",
            source_url="https://trudvsem.ru/high",
        )
        hh = SalarySourceResult(
            source="hh",
            status="ok",
            query_role="координатор проекта",
            region="Свердловская область",
            salary_value=200_000,
            salary_type="vacancy_sample_median",
            source_url="https://hh.ru/high",
        )
        rosstat = SalarySourceResult(
            source="rosstat",
            status="ok",
            query_role="координатор проекта",
            region="Свердловская область",
            salary_value=180_000,
            salary_type="official_region_mean",
            source_url="https://rosstat.gov.ru/high",
        )

        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[gorodrabot, trudvsem, hh, rosstat], create=True):
            response = client.post("/api/modules/salary/generate", json=self._payload())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["positions"][0]["source"], "trudvsem")
        self.assertEqual(body["positions"][0]["salary_value"], 74_000)
        self.assertNotIn("HH", body["plain_text"])
        self.assertNotIn("Росстат", body["plain_text"])

    def test_production_generate_uses_ai_aliases_only_when_active_sources_have_no_salary(self):
        alias_source = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="координатор проекта",
            matched_role="координатор проекта",
            region="Свердловская область",
            salary_value=88_000,
            salary_type="mean",
            source_url="https://gorodrabot.ru/fallback",
        )
        no_data = [
            SalarySourceResult(source="gorodrabot", status="no_data", query_role="редкая роль", region="Свердловская область"),
            SalarySourceResult(source="trudvsem", status="unavailable", query_role="редкая роль", region="Свердловская область"),
        ]
        payload = self._payload(
            positions=[
                {
                    "role_title": "редкая роль",
                    "staff_count": 1,
                    "duration_months": 2,
                    "workload_mode": "percent",
                    "workload_value": 50,
                    "functionality": "",
                    "calendar_events": "",
                }
            ],
        )

        def fake_sources(role, region, year=None, **kwargs):
            return [alias_source] if role == "координатор проекта" else no_data

        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", side_effect=fake_sources, create=True), \
            patch("app.services.salary_calculator.request_ai_role_aliases", return_value=["координатор проекта"]) as ai_aliases:
            response = client.post("/api/modules/salary/generate", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["positions"][0]["source"], "gorodrabot")
        self.assertEqual(response.json()["positions"][0]["salary_value"], 88_000)
        ai_aliases.assert_called_once()

    def test_user_functionality_is_ai_normalized_and_calendar_events_are_formatted(self):
        source = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="маркетолог",
            matched_role="маркетолог",
            region="Санкт-Петербург",
            year=2025,
            salary_value=92_780,
            salary_type="mean",
            source_url="https://spb.gorodrabot.ru/salaries/marketolog?y=2025",
        )
        payload = self._payload(
            region="Санкт-Петербург",
            positions=[
                {
                    "role_title": "маркетолог",
                    "staff_count": 5,
                    "duration_months": 3,
                    "workload_mode": "hours_total",
                    "workload_value": 123,
                    "functionality": "формирует анонс кампанию и освещение проекта",
                    "calendar_events": "1,2,3",
                }
            ],
        )

        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[source], create=True), \
            patch("app.services.salary_calculator.request_ai_functionality_normalization", return_value="формирует анонсную кампанию проекта, готовит и координирует информационное освещение, согласует публикации и передает материалы ответственным членам команды.", create=True):
            response = client.post("/api/modules/salary/generate", json=payload)

        self.assertEqual(response.status_code, 200)
        plain_text = response.json()["plain_text"]
        self.assertIn("92 780 руб. / 166 × 123 ч. × 5", plain_text)
        self.assertIn("формирует анонсную кампанию проекта", plain_text)
        self.assertNotIn("формирует анонс кампанию", plain_text)
        self.assertIn("Календарный план: мероприятия № 1, 2, 3.", plain_text)

    def test_ugly_raw_functionality_is_not_rendered_in_plain_text_or_docx_and_docx_name_is_clean(self):
        source = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="дворник",
            matched_role="дворник",
            region="Республика Татарстан",
            year=2025,
            salary_value=36_589,
            salary_type="mean",
            source_url="https://tatarstan.gorodrabot.ru/salaries/dvornik?y=2025",
        )
        normalized = (
            "Сотрудник обеспечивает санитарное состояние и порядок на территории, используемой для мероприятий проекта. "
            "В период реализации проекта выполняет уборку площадки до и после мероприятий № 1 и 4, помогает поддерживать безопасные и комфортные условия для участников и посетителей."
        )
        payload = SalaryGenerateRequest(
            region="Республика Татарстан",
            cofinance_source="own_legal_entity_funds",
            positions=[
                {
                    "role_title": "дворник",
                    "staff_count": 1,
                    "duration_months": 4,
                    "workload_mode": "percent",
                    "workload_value": 30,
                    "functionality": "чистит всю территорию его а города казань каждый день с утра до вечера за наши деньги",
                    "calendar_events": "1,4",
                }
            ],
        )

        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[source], create=True), \
            patch("app.services.salary_calculator.request_ai_functionality_normalization", return_value=normalized, create=True):
            run, generated = create_salary_run(payload)

        self.assertIn("расчет_зарплаты_1_дворник", run.files["docx"])
        self.assertIn(normalized, generated.plain_text)
        self.assertNotIn("за наши деньги", generated.plain_text)
        self.assertNotIn("Обоснование: сумма рассчитана", generated.plain_text)
        self.assertNotIn("Примечание к источнику", generated.plain_text)
        self.assertNotIn("Что проверить вручную", generated.plain_text)

        doc = Document(run.files["docx"])
        doc_text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        self.assertIn(normalized, doc_text)
        self.assertNotIn("за наши деньги", doc_text)
        self.assertNotIn("Обоснование: сумма рассчитана", doc_text)
        self.assertNotIn("Примечание к источнику", doc_text)
        self.assertNotIn("Что проверить вручную", doc_text)
        self.assertNotIn("Проверить вручную перед подачей", doc_text)

    def test_role_aware_safe_fallback_keeps_ugly_functionality_out_when_ai_unavailable(self):
        source = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="дворник",
            matched_role="дворник",
            region="Республика Татарстан",
            year=2025,
            salary_value=36_589,
            salary_type="mean",
            source_url="https://tatarstan.gorodrabot.ru/salaries/dvornik?y=2025",
        )
        payload = self._payload(
            region="Республика Татарстан",
            positions=[
                {
                    "role_title": "дворник",
                    "staff_count": 1,
                    "duration_months": 4,
                    "workload_mode": "percent",
                    "workload_value": 30,
                    "functionality": "чистит всю территорию его а города казань каждый день с утра до вечера за наши деньги",
                    "calendar_events": "1,4",
                }
            ],
        )

        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[source]), \
            patch("app.services.salary_calculator.request_ai_functionality_normalization", return_value=None):
            response = client.post("/api/modules/salary/generate", json=payload)

        self.assertEqual(response.status_code, 200)
        text = response.json()["plain_text"]
        self.assertIn("Сотрудник обеспечивает санитарное состояние и порядок на территории", text)
        self.assertIn("мероприятий № 1, 4", text)
        self.assertNotIn("за наши деньги", text)

    def test_source_notes_and_generic_obosnovanie_are_not_rendered(self):
        source = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="координатор проекта",
            matched_role="координатор проекта",
            region="Свердловская область",
            salary_value=70_000,
            salary_type="mean",
            source_url="https://gorodrabot.ru/source",
        )
        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[source], create=True):
            response = client.post("/api/modules/salary/generate", json=self._payload())

        self.assertEqual(response.status_code, 200)
        text = response.json()["plain_text"]
        self.assertNotIn("Примечание к источнику:", text)
        self.assertNotIn("GorodRabot показывает зарплатные предложения", text)
        self.assertNotIn("Обоснование: сумма рассчитана", text)

    def test_empty_calendar_uses_exact_manual_placeholder_without_extra_period(self):
        source = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="координатор проекта",
            matched_role="координатор проекта",
            region="Свердловская область",
            salary_value=70_000,
            salary_type="mean",
            source_url="https://gorodrabot.ru/source",
        )
        payload = self._payload()
        payload["positions"][0]["calendar_events"] = ""

        client = TestClient(app)
        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[source], create=True):
            response = client.post("/api/modules/salary/generate", json=payload)

        self.assertEqual(response.status_code, 200)
        text = response.json()["plain_text"]
        expected = "Календарный план: УКАЖИТЕ НОМЕРА МЕРОПРИЯТИЙ КАЛЕНДАРНОГО ПЛАНА"
        self.assertIn(expected, text)
        self.assertNotIn(expected + ".", text)

    def test_source_scope_filters_sources(self):
        from app.services.salary_sources.aggregator import source_names_for_scope

        self.assertEqual(source_names_for_scope("aggregators"), {"gorodrabot", "hh", "trudvsem"})
        self.assertEqual(source_names_for_scope("official"), {"rosstat"})
        self.assertEqual(source_names_for_scope("active"), {"gorodrabot", "trudvsem"})

    def test_ai_role_aliases_retry_invalid_json_and_reject_salary_payload(self):
        from app.services.salary_calculator import request_ai_role_aliases

        calls: list[str] = []

        def fake_ai(prompt: str):
            calls.append(prompt)
            if len(calls) == 1:
                return "не json"
            return json.dumps(
                {
                    "search_roles": [
                        "координатор проекта",
                        "администратор проекта",
                        "90000 рублей",
                        "https://hh.ru/search/vacancy?text=координатор",
                    ],
                },
                ensure_ascii=False,
            )

        result = request_ai_role_aliases(
            role_title="координатор",
            region="Свердловская область",
            role_query_variants=["координатор", "координатор проекта"],
            ai_generate=fake_ai,
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(result, ["администратор проекта"])

    def test_ai_text_composition_is_rejected_when_numbers_change(self):
        from app.services.salary_calculator import SalaryPositionOutput, request_ai_text_composition

        position = SalaryPositionOutput(
            role_title="координатор проекта",
            matched_role="координатор проекта",
            staff_count=1,
            duration_months=4,
            workload_mode="percent",
            workload_value=40,
            salary_value=68_372,
            source="gorodrabot",
            source_url="https://gorodrabot.ru/source",
            amount=109_395,
            formula="68 372 руб. × 40% × 4 мес. × 1",
            text="К включению в бюджет: 109 395 руб.",
        )

        invalid = request_ai_text_composition(
            "Свердловская область",
            [position],
            109_395,
            "К включению в бюджет: 109 395 руб.",
            ai_generate=lambda prompt: json.dumps({"plain_text": "К включению в бюджет: 1 руб.", "items": []}, ensure_ascii=False),
        )
        valid = request_ai_text_composition(
            "Свердловская область",
            [position],
            109_395,
            "К включению в бюджет: 109 395 руб.",
            ai_generate=lambda prompt: json.dumps(
                {
                    "plain_text": "68 372 руб. × 40% × 4 мес. × 1. К включению в бюджет: 109 395 руб. https://gorodrabot.ru/source",
                    "items": [],
                },
                ensure_ascii=False,
            ),
        )

        self.assertIsNone(invalid)
        self.assertIsNotNone(valid)

    def test_overlong_ai_functionality_is_retried_and_shortened(self):
        from app.services.salary_calculator import SalaryPositionInput, request_ai_functionality_normalization

        calls: list[str] = []
        long_text = "Очень длинный текст. " * 40
        short_text = "Сотрудник сопровождает задачи проекта по своей должности. Участвует в подготовке и проведении мероприятий календарного плана."

        def fake_ai(prompt: str):
            calls.append(prompt)
            return json.dumps({"functional_text": long_text if len(calls) == 1 else short_text}, ensure_ascii=False)

        result = request_ai_functionality_normalization(
            SalaryPositionInput(
                role_title="координатор проекта",
                staff_count=1,
                duration_months=4,
                workload_mode="percent",
                workload_value=40,
                functionality="делает все",
                calendar_events="1,2",
            ),
            region="Свердловская область",
            calendar_events="мероприятия № 1, 2",
            ai_generate=fake_ai,
        )

        self.assertEqual(result, short_text)
        self.assertEqual(len(calls), 2)

    def test_ai_role_aliases_do_not_accept_salary_json(self):
        from app.services.salary_calculator import request_ai_role_aliases

        salary_payload = json.dumps(
            {
                "status": "ok",
                "source_url": "https://hh.ru/search/vacancy?text=координатор",
                "query_role": "координатор",
                "matched_role": "координатор",
                "region": "Свердловская область",
                "year": 2025,
                "salary_value": 90000,
                "salary_type": "vacancy_sample_median",
                "confidence": "medium",
            },
            ensure_ascii=False,
        )

        result = request_ai_role_aliases(
            role_title="координатор",
            region="Свердловская область",
            role_query_variants=["координатор"],
            ai_generate=lambda prompt: salary_payload,
        )

        self.assertEqual(result, [])

    def test_soft_error_when_no_salary_source_and_no_fallback(self):
        client = TestClient(app)
        no_data = SalarySourceResult(source="gorodrabot", status="no_data", query_role="редкая роль", region="Свердловская область")
        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[no_data]), \
            patch("app.services.salary_calculator.request_ai_role_aliases", return_value=[]):
            response = client.post("/api/modules/salary/generate", json=self._payload())

        self.assertEqual(response.status_code, 400)
        self.assertIn("Не удалось найти подтвержденные данные", response.json()["detail"]["message"])
        self.assertEqual(response.json()["detail"]["error_code"], "SALARY_SOURCE_NO_CONFIRMED_RESULT")

    def test_salary_source_error_does_not_consume_free_attempt(self):
        client = TestClient(app)
        before = client.get("/api/usage").json()
        self.assertTrue(before["modules"]["salary"]["free_attempt_available"])

        no_data = SalarySourceResult(source="gorodrabot", status="no_data", query_role="редкая роль", region="Свердловская область")
        with patch("app.services.salary_calculator.collect_production_salary_source_results", return_value=[no_data]), \
            patch("app.services.salary_calculator.request_ai_role_aliases", return_value=[]):
            response = client.post("/api/modules/salary/generate", json=self._payload())

        after = client.get("/api/usage").json()
        self.assertEqual(response.status_code, 400)
        self.assertTrue(after["modules"]["salary"]["free_attempt_available"])
        self.assertEqual(after["paid_runs"], before["paid_runs"])


if __name__ == "__main__":
    unittest.main()
