import json
import os
import subprocess
import statistics
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")

from app.main import app  # noqa: E402
from app.services.salary_sources.aggregator import build_salary_role_queries, choose_recommended, probe_salary_sources  # noqa: E402
from app.services.salary_sources.gorodrabot import parse_gorodrabot_salary_page  # noqa: E402
from app.services.salary_sources.hh import calculate_hh_salary_stats  # noqa: E402
from app.services.salary_sources.models import SalarySourceResult  # noqa: E402
from app.services.salary_sources.trudvsem import fetch_trudvsem_salary_sample  # noqa: E402


class SalarySourcesTest(unittest.TestCase):
    def test_gorodrabot_parser_extracts_spaced_salary_numbers(self):
        html = """
        <html><body>
        <section>Средняя зарплата координатора в Свердловской области составляет 68 372 рубля</section>
        <section>Медианная зарплата — 61 100 руб.</section>
        <section>Модальная зарплата: 50 000 рублей</section>
        </body></html>
        """

        parsed = parse_gorodrabot_salary_page(html)

        self.assertEqual(parsed["mean"], 68372)
        self.assertEqual(parsed["median"], 61100)
        self.assertEqual(parsed["mode"], 50000)

    def test_hh_salary_stats_use_midpoint_and_median(self):
        items = [
            {"salary": {"from": 50_000, "to": 70_000, "currency": "RUR"}},
            {"salary": {"from": 80_000, "to": None, "currency": "RUR"}},
            {"salary": {"from": None, "to": 100_000, "currency": "RUR"}},
            {"salary": {"from": 1_000, "to": 2_000, "currency": "USD"}},
        ]

        stats = calculate_hh_salary_stats(items)

        self.assertEqual(stats.sample_size, 3)
        self.assertEqual(stats.median, 80_000)
        self.assertEqual(stats.mean, statistics.mean([60_000, 80_000, 100_000]))

    def test_build_salary_role_queries_includes_adjacent_project_roles(self):
        queries = build_salary_role_queries("координатор")

        self.assertEqual(queries[0], "координатор")
        self.assertIn("координатор проекта", queries)
        self.assertIn("организатор мероприятий", queries)
        self.assertEqual(len(queries), len(set(queries)))

    def test_choose_recommended_falls_back_when_gorodrabot_blocked(self):
        gorodrabot = SalarySourceResult(source="gorodrabot", status="blocked", query_role="координатор", region="Свердловская область")
        hh = SalarySourceResult(
            source="hh",
            status="ok",
            query_role="координатор",
            matched_role="координатор",
            region="Свердловская область",
            salary_value=70_000,
            salary_type="vacancy_sample_median",
            sample_size=12,
        )

        recommended, warnings = choose_recommended([gorodrabot, hh])

        self.assertEqual(recommended, hh)
        self.assertIn("HH показывает выборку вакансий", " ".join(warnings))

    def test_choose_recommended_uses_rosstat_as_official_fallback(self):
        rosstat = SalarySourceResult(
            source="rosstat",
            status="ok",
            query_role="координатор",
            matched_role=None,
            region="Свердловская область",
            salary_value=64_000,
            salary_type="official_region_mean",
        )

        recommended, warnings = choose_recommended([rosstat])

        self.assertEqual(recommended, rosstat)
        self.assertIn("официальный региональный fallback", " ".join(warnings))

    def test_adjacent_role_warning_is_explicit(self):
        result = SalarySourceResult(
            source="hh",
            status="ok",
            query_role="координатор проекта",
            matched_role="координатор проекта",
            region="Свердловская область",
            salary_value=72_000,
            salary_type="vacancy_sample_median",
            sample_size=14,
            notes="Использована смежная должность, потому что по исходной роли найдено мало данных.",
        )

        recommended, warnings = choose_recommended([result], original_role="координатор")

        self.assertEqual(recommended, result)
        self.assertIn("Использована смежная должность", " ".join(warnings))

    def test_aggregator_survives_one_source_exception(self):
        ok_result = SalarySourceResult(
            source="hh",
            status="ok",
            query_role="координатор",
            matched_role="координатор",
            region="Свердловская область",
            salary_value=75_000,
            salary_type="vacancy_sample_median",
            sample_size=20,
        )

        with patch("app.services.salary_sources.aggregator.fetch_gorodrabot_salary", side_effect=RuntimeError("boom")), \
            patch("app.services.salary_sources.aggregator.fetch_hh_salary_sample", return_value=ok_result), \
            patch("app.services.salary_sources.aggregator.fetch_trudvsem_salary_sample", return_value=SalarySourceResult(source="trudvsem", status="no_data", query_role="координатор", region="Свердловская область")), \
            patch("app.services.salary_sources.aggregator.fetch_rosstat_region_wage", return_value=SalarySourceResult(source="rosstat", status="unavailable", query_role="координатор", region="Свердловская область")), \
            patch("app.services.salary_sources.aggregator.check_rabota_ru_salary_source", return_value=SalarySourceResult(source="rabota.ru", status="not_implemented", query_role="координатор", region="Свердловская область")):
            response = probe_salary_sources("координатор", "Свердловская область", 2024)

        statuses = {item.source: item.status for item in response.results}
        self.assertEqual(statuses["gorodrabot"], "unavailable")
        self.assertEqual(response.recommended.source, "hh")
        self.assertTrue(response.warnings)

    def test_production_source_collection_uses_only_active_sources(self):
        from app.services.salary_sources.aggregator import collect_production_salary_source_results

        gorodrabot = SalarySourceResult(
            source="gorodrabot",
            status="ok",
            query_role="координатор проекта",
            region="Свердловская область",
            salary_value=70_000,
            salary_type="mean",
            source_url="https://gorodrabot.ru/source",
        )
        trudvsem = SalarySourceResult(
            source="trudvsem",
            status="ok",
            query_role="координатор проекта",
            region="Свердловская область",
            salary_value=80_000,
            salary_type="vacancy_sample_median",
            source_url="https://trudvsem.ru/source",
        )

        with patch("app.services.salary_sources.aggregator.fetch_gorodrabot_salary", return_value=gorodrabot) as gorodrabot_fetch, \
            patch("app.services.salary_sources.aggregator.fetch_trudvsem_salary_sample", return_value=trudvsem) as trudvsem_fetch, \
            patch("app.services.salary_sources.aggregator.fetch_hh_salary_sample") as hh_fetch, \
            patch("app.services.salary_sources.aggregator.fetch_rosstat_region_wage") as rosstat_fetch, \
            patch("app.services.salary_sources.aggregator.check_rabota_ru_salary_source") as rabota_fetch:
            results = collect_production_salary_source_results("координатор проекта", "Свердловская область", 2025)

        self.assertEqual([item.source for item in results], ["gorodrabot", "trudvsem"])
        gorodrabot_fetch.assert_called_once()
        trudvsem_fetch.assert_called_once()
        hh_fetch.assert_not_called()
        rosstat_fetch.assert_not_called()
        rabota_fetch.assert_not_called()

    def test_trudvsem_success_uses_actual_opendata_api_url(self):
        class FakeResponse:
            status_code = 200
            url = "https://opendata.trudvsem.ru/api/v1/vacancies?text=dvornik&region=tatarstan&limit=100"

            def json(self):
                return {
                    "results": {
                        "vacancies": [
                            {"vacancy": {"salary_min": 20_000, "salary_max": 30_000}},
                            {"vacancy": {"salary_min": 40_000, "salary_max": 50_000}},
                        ]
                    }
                }

        with patch("app.services.salary_sources.trudvsem.httpx.get", return_value=FakeResponse()):
            result = fetch_trudvsem_salary_sample("дворник", "Республика Татарстан", 2025)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.source_url, FakeResponse.url)
        self.assertTrue(result.source_url.startswith("https://opendata.trudvsem.ru/api/v1/vacancies"))

    def test_salary_probe_endpoint_is_available_in_test_env(self):
        client = TestClient(app)
        with patch("app.routers.modules.probe_salary_sources") as probe:
            probe.return_value = {
                "role": "координатор",
                "region": "Свердловская область",
                "year": 2024,
                "results": [],
                "recommended": None,
                "warnings": ["Не удалось автоматически найти надежный зарплатный ориентир."],
            }

            response = client.post(
                "/api/modules/salary/probe-sources",
                json={"role": "координатор", "region": "Свердловская область", "year": 2024},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "координатор")

    def test_batch_fixture_and_cli_mode_are_present(self):
        fixture = Path("apps/api/tests/fixtures/salary_live_cases.json")
        self.assertTrue(fixture.exists())
        cases = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 8)
        self.assertIn({"role": "маркетолог", "region": "Санкт-Петербург", "year": 2025}, cases)

        help_result = subprocess.run(
            [sys.executable, "apps/api/scripts/probe_salary_sources.py", "--help"],
            cwd=Path(__file__).resolve().parents[3],
            env={**os.environ, "PYTHONPATH": "apps/api"},
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("--batch", help_result.stdout)

    @unittest.skipUnless(os.getenv("RUN_LIVE_SALARY_SOURCE_TESTS") == "1", "live salary source probe is opt-in")
    def test_live_salary_source_probe_report(self):
        response = probe_salary_sources("координатор", "Свердловская область", 2024)
        print(json.dumps(response.model_dump(), ensure_ascii=False, indent=2))
        self.assertEqual(response.role, "координатор")
        self.assertEqual(response.region, "Свердловская область")
        self.assertTrue(response.results)


if __name__ == "__main__":
    unittest.main()
