from __future__ import annotations

import re

import httpx

from app.services.salary_sources.common import USER_AGENT, normalize_text, parse_salary_number, slugify_ru, strip_html
from app.services.salary_sources.models import SalarySourceResult


REGION_SLUGS = {
    "свердловская область": "sverdlovskaya-oblast",
    "екатеринбург": "ekaterinburg",
    "москва": "moskva",
    "санкт-петербург": "sankt-peterburg",
    "краснодарский край": "krasnodarskiy-kray",
    "краснодар": "krasnodar",
    "республика татарстан": "tatarstan",
    "казань": "kazan",
}

GORODRABOT_NOTES = "Источник показывает зарплатные предложения в вакансиях, а не фактически выплаченную заработную плату."


def fetch_gorodrabot_salary(role: str, region: str, year: int) -> SalarySourceResult:
    region_slug = REGION_SLUGS.get(normalize_text(region).lower(), slugify_ru(region))
    profession_slug = slugify_ru(role)
    source_url = f"https://{region_slug}.gorodrabot.ru/salaries/{profession_slug}?y={year}"
    try:
        response = httpx.get(source_url, headers={"User-Agent": USER_AGENT}, timeout=5.0, follow_redirects=True)
    except httpx.TimeoutException:
        return _result("unavailable", role, region, year, source_url, notes="GorodRabot не ответил за 10 секунд.")
    except httpx.HTTPError as exc:
        return _result("unavailable", role, region, year, source_url, notes=f"GorodRabot недоступен: {exc.__class__.__name__}.")

    if response.status_code in {403, 429}:
        return _result("blocked", role, region, year, source_url, notes=GORODRABOT_NOTES)
    if response.status_code >= 500:
        return _result("unavailable", role, region, year, source_url, notes=GORODRABOT_NOTES)
    if response.status_code >= 400:
        return _result("no_data", role, region, year, source_url, notes=GORODRABOT_NOTES)

    parsed = parse_gorodrabot_salary_page(response.text)
    salary_value = parsed.get("mean") or parsed.get("median") or parsed.get("mode")
    salary_type = "mean" if parsed.get("mean") else "median" if parsed.get("median") else "mode" if parsed.get("mode") else None
    if not salary_value:
        return _result("parse_error", role, region, year, source_url, notes=GORODRABOT_NOTES)

    return SalarySourceResult(
        source="gorodrabot",
        status="ok",
        query_role=role,
        matched_role=role,
        region=region,
        region_id=region_slug,
        year=year,
        salary_value=salary_value,
        salary_type=salary_type,
        source_url=source_url,
        notes=GORODRABOT_NOTES,
    )


def parse_gorodrabot_salary_page(html: str) -> dict[str, int | None]:
    text = strip_html(html)
    return {
        "mean": _find_labeled_salary(text, ["средняя", "среднюю"]),
        "median": _find_labeled_salary(text, ["медианная", "медианную"]),
        "mode": _find_labeled_salary(text, ["модальная", "модальную"]),
    }


def _find_labeled_salary(text: str, labels: list[str]) -> int | None:
    for label in labels:
        patterns = [
            rf"{label}[^0-9]{{0,120}}(\d[\d\s]{{2,}})\s*(?:руб|₽)",
            rf"(\d[\d\s]{{2,}})\s*(?:руб|₽)[^а-яё]{{0,80}}{label}",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return parse_salary_number(match.group(1))
    return None


def _result(status: str, role: str, region: str, year: int, source_url: str, notes: str | None = None) -> SalarySourceResult:
    return SalarySourceResult(
        source="gorodrabot",
        status=status,
        query_role=role,
        matched_role=role if status == "ok" else None,
        region=region,
        year=year,
        source_url=source_url,
        notes=notes,
    )
