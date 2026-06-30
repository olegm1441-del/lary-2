from __future__ import annotations

from app.services.salary_sources.models import SalarySourceResult


def check_rabota_ru_salary_source(role: str, region: str, year: int | None = None) -> SalarySourceResult:
    return SalarySourceResult(
        source="rabota.ru",
        status="not_implemented",
        query_role=role,
        matched_role=None,
        region=region,
        year=year,
        source_url="https://www.rabota.ru/",
        notes="Публичный API зарплат по должности/региону не подтвержден; production scraping Rabota.ru не включен.",
    )

