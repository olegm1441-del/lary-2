import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")

from app.main import app  # noqa: E402
from app.services.account_store import clear_account_store_for_tests  # noqa: E402
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
        with patch("app.services.salary_calculator.collect_salary_source_results", return_value=[source]):
            response = client.post("/api/modules/salary/generate", json=self._payload())

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module_slug"], "salary")
        self.assertEqual(payload["total_amount"], 109_395)
        self.assertIn("plain_text", payload)
        self.assertIn("К включению в бюджет: 109 395 руб.", payload["plain_text"])
        self.assertIn("организационное сопровождение", payload["plain_text"])
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

        def fake_sources(role, region, source_scope, year=None):
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
        with patch("app.services.salary_calculator.collect_salary_source_results", side_effect=fake_sources):
            response = client.post("/api/modules/salary/generate", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_amount"], 208_000)
        self.assertIn("70 000 руб. × 40% × 4 мес. × 1", body["plain_text"])
        self.assertIn("80 000 руб. / 160 × 96 ч. × 2", body["plain_text"])
        self.assertIn("Итого по оплате труда: 208 000 руб.", body["plain_text"])
        self.assertIn("привлеченные средства согласно письму поддержки", body["plain_text"])

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
        with patch("app.services.salary_calculator.collect_salary_source_results", return_value=[lower, higher]):
            response = client.post("/api/modules/salary/generate", json=self._payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["positions"][0]["salary_value"], 74_000)
        self.assertIn("Trudvsem", response.json()["plain_text"])

    def test_source_scope_filters_sources(self):
        from app.services.salary_sources.aggregator import source_names_for_scope

        self.assertEqual(source_names_for_scope("aggregators"), {"gorodrabot", "hh", "trudvsem", "ai_salary_fallback"})
        self.assertEqual(source_names_for_scope("official"), {"rosstat", "ai_salary_fallback"})

    def test_ai_fallback_is_called_only_without_eligible_sources_and_invalid_json_retries_once(self):
        from app.services.salary_calculator import request_ai_salary_fallback

        calls: list[str] = []

        def fake_ai(prompt: str):
            calls.append(prompt)
            if len(calls) == 1:
                return "не json"
            return json.dumps(
                {
                    "status": "ok",
                    "source": "ai_salary_fallback",
                    "source_name": "HH",
                    "source_url": "https://hh.ru/search/vacancy?text=координатор",
                    "query_role": "координатор",
                    "matched_role": "координатор проекта",
                    "region": "Свердловская область",
                    "year": 2025,
                    "salary_value": 90000,
                    "salary_type": "vacancy_sample_median",
                    "confidence": "medium",
                    "notes": "Найден резервный ориентир.",
                },
                ensure_ascii=False,
            )

        result = request_ai_salary_fallback(
            role_title="координатор",
            region="Свердловская область",
            source_scope="all",
            role_query_variants=["координатор", "координатор проекта"],
            ai_generate=fake_ai,
            url_checker=lambda url: True,
        )

        self.assertEqual(len(calls), 2)
        self.assertIsNotNone(result)
        self.assertEqual(result.salary_value, 90_000)

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
            ai_generate=lambda prompt: json.dumps({"plain_text": "68 372 руб. К включению в бюджет: 109 395 руб.", "items": []}, ensure_ascii=False),
        )

        self.assertIsNone(invalid)
        self.assertIsNotNone(valid)

    def test_official_scope_ai_fallback_accepts_only_official_domains(self):
        from app.services.salary_calculator import request_ai_salary_fallback

        hh_payload = json.dumps(
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

        result = request_ai_salary_fallback(
            role_title="координатор",
            region="Свердловская область",
            source_scope="official",
            role_query_variants=["координатор"],
            ai_generate=lambda prompt: hh_payload,
            url_checker=lambda url: True,
        )

        self.assertIsNone(result)

    def test_soft_error_when_no_salary_source_and_no_fallback(self):
        client = TestClient(app)
        no_data = SalarySourceResult(source="gorodrabot", status="no_data", query_role="редкая роль", region="Свердловская область")
        with patch("app.services.salary_calculator.collect_salary_source_results", return_value=[no_data]), \
            patch("app.services.salary_calculator.request_ai_salary_fallback", return_value=None):
            response = client.post("/api/modules/salary/generate", json=self._payload())

        self.assertEqual(response.status_code, 400)
        self.assertIn("Не получилось автоматически найти зарплатный ориентир", response.json()["detail"]["message"])


if __name__ == "__main__":
    unittest.main()
