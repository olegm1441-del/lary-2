from __future__ import annotations

import httpx

from app.services.salary_sources.common import USER_AGENT, VacancySalaryStats, human_search_url, int_mean, int_median
from app.services.salary_sources.models import SalarySourceResult


def fetch_trudvsem_salary_sample(role: str, region: str, year: int | None = None) -> SalarySourceResult:
    source_url = human_search_url("https://trudvsem.ru/vacancy/search", text=role, region=region)
    api_url = "https://opendata.trudvsem.ru/api/v1/vacancies"
    params = {"text": role, "region": region, "limit": 100}
    try:
        response = httpx.get(api_url, params=params, headers={"User-Agent": USER_AGENT}, timeout=5.0)
    except httpx.TimeoutException:
        return _result("unavailable", role, region, year, source_url, notes="Trudvsem API не ответил за 10 секунд.")
    except httpx.HTTPError as exc:
        return _result("unavailable", role, region, year, source_url, notes=f"Trudvsem API недоступен: {exc.__class__.__name__}.")

    if response.status_code in {403, 429}:
        return _result("blocked", role, region, year, source_url, notes="Trudvsem ограничил запрос.")
    if response.status_code >= 500:
        return _result("unavailable", role, region, year, source_url, notes="Trudvsem API временно недоступен.")
    if response.status_code >= 400:
        return _result("not_implemented", role, region, year, source_url, notes=f"Формат Trudvsem API требует уточнения: HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError:
        return _result("parse_error", role, region, year, source_url, notes="Trudvsem вернул не JSON.")

    items = _extract_vacancy_items(payload)
    stats = calculate_trudvsem_salary_stats(items)
    if not stats.sample_size or not stats.median:
        return _result("no_data", role, region, year, source_url, notes="Trudvsem не вернул структурированные зарплаты по запросу.")

    return SalarySourceResult(
        source="trudvsem",
        status="ok",
        query_role=role,
        matched_role=role,
        region=region,
        year=year,
        salary_value=stats.median,
        salary_type="vacancy_sample_median",
        sample_size=stats.sample_size,
        source_url=str(response.url),
        notes="Работа России показывает вакансии работодателей; формат API может отличаться по регионам и должностям.",
    )


def calculate_trudvsem_salary_stats(items: list[dict]) -> VacancySalaryStats:
    values: list[int] = []
    for item in items:
        vacancy = item.get("vacancy") if isinstance(item.get("vacancy"), dict) else item
        salary_min = vacancy.get("salary_min") or vacancy.get("salary_from") or vacancy.get("salary")
        salary_max = vacancy.get("salary_max") or vacancy.get("salary_to")
        if isinstance(salary_min, str) and salary_min.isdigit():
            salary_min = int(salary_min)
        if isinstance(salary_max, str) and salary_max.isdigit():
            salary_max = int(salary_max)
        if isinstance(salary_min, (int, float)) and isinstance(salary_max, (int, float)) and salary_max:
            values.append(int(round((salary_min + salary_max) / 2)))
        elif isinstance(salary_min, (int, float)) and salary_min:
            values.append(int(round(salary_min)))
        elif isinstance(salary_max, (int, float)) and salary_max:
            values.append(int(round(salary_max)))
    return VacancySalaryStats(sample_size=len(values), median=int_median(values), mean=int_mean(values), values=values)


def _extract_vacancy_items(payload: dict) -> list[dict]:
    if isinstance(payload.get("results"), dict) and isinstance(payload["results"].get("vacancies"), list):
        return payload["results"]["vacancies"]
    if isinstance(payload.get("vacancies"), list):
        return payload["vacancies"]
    if isinstance(payload.get("results"), list):
        return payload["results"]
    return []


def _result(status: str, role: str, region: str, year: int | None, source_url: str, notes: str | None = None) -> SalarySourceResult:
    return SalarySourceResult(source="trudvsem", status=status, query_role=role, region=region, year=year, source_url=source_url, notes=notes)
