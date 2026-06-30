from __future__ import annotations

import httpx

from app.services.salary_sources.common import USER_AGENT, VacancySalaryStats, human_search_url, int_mean, int_median, normalize_text
from app.services.salary_sources.models import SalarySourceResult


HH_AREA_IDS = {
    "екатеринбург": "3",
    "свердловская область": "1261",
    "москва": "1",
    "санкт-петербург": "2",
    "краснодар": "53",
    "краснодарский край": "1438",
    "казань": "88",
    "республика татарстан": "1624",
}


def fetch_hh_salary_sample(role: str, region: str, year: int | None = None) -> SalarySourceResult:
    area_id = HH_AREA_IDS.get(normalize_text(region).lower())
    if not area_id:
        return SalarySourceResult(
            source="hh",
            status="not_implemented",
            query_role=role,
            region=region,
            year=year,
            notes="Для региона пока нет mapping HH area id.",
        )

    params = {
        "text": role,
        "area": area_id,
        "only_with_salary": "true",
        "per_page": 100,
        "currency": "RUR",
    }
    source_url = human_search_url("https://hh.ru/search/vacancy", text=role, area=area_id, only_with_salary="true")
    try:
        response = httpx.get("https://api.hh.ru/vacancies", params=params, headers={"User-Agent": USER_AGENT}, timeout=10.0)
    except httpx.TimeoutException:
        return _result("unavailable", role, region, year, area_id, source_url, notes="HH API не ответил за 10 секунд.")
    except httpx.HTTPError as exc:
        return _result("unavailable", role, region, year, area_id, source_url, notes=f"HH API недоступен: {exc.__class__.__name__}.")

    if response.status_code in {403, 429}:
        return _result("blocked", role, region, year, area_id, source_url, notes="HH ограничил запрос.")
    if response.status_code >= 500:
        return _result("unavailable", role, region, year, area_id, source_url, notes="HH API временно недоступен.")
    if response.status_code >= 400:
        return _result("no_data", role, region, year, area_id, source_url, notes=f"HH API вернул HTTP {response.status_code}.")

    try:
        payload = response.json()
        items = payload.get("items") or []
    except ValueError:
        return _result("parse_error", role, region, year, area_id, source_url, notes="HH API вернул не JSON.")

    stats = calculate_hh_salary_stats(items)
    if not stats.sample_size or not stats.median:
        return _result("no_data", role, region, year, area_id, source_url, notes="HH не вернул вакансии с зарплатой в рублях.")

    return SalarySourceResult(
        source="hh",
        status="ok",
        query_role=role,
        matched_role=role,
        region=region,
        region_id=area_id,
        year=year,
        salary_value=stats.median,
        salary_type="vacancy_sample_median",
        sample_size=stats.sample_size,
        source_url=source_url,
        notes="HH показывает выборку текущих вакансий с указанной зарплатой, а не среднюю зарплату по году.",
    )


def calculate_hh_salary_stats(items: list[dict]) -> VacancySalaryStats:
    values: list[int] = []
    for item in items:
        salary = item.get("salary") or {}
        if salary.get("currency") != "RUR":
            continue
        salary_from = salary.get("from")
        salary_to = salary.get("to")
        if isinstance(salary_from, (int, float)) and isinstance(salary_to, (int, float)):
            values.append(int(round((salary_from + salary_to) / 2)))
        elif isinstance(salary_from, (int, float)):
            values.append(int(round(salary_from)))
        elif isinstance(salary_to, (int, float)):
            values.append(int(round(salary_to)))
    return VacancySalaryStats(sample_size=len(values), median=int_median(values), mean=int_mean(values), values=values)


def _result(status: str, role: str, region: str, year: int | None, area_id: str | None, source_url: str | None, notes: str | None = None) -> SalarySourceResult:
    return SalarySourceResult(
        source="hh",
        status=status,
        query_role=role,
        region=region,
        region_id=area_id,
        year=year,
        source_url=source_url,
        notes=notes,
    )

