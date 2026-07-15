from __future__ import annotations

import re
from collections.abc import Callable

from app.services.salary_sources.gorodrabot import fetch_gorodrabot_salary
from app.services.salary_sources.hh import fetch_hh_salary_sample
from app.services.salary_sources.models import SalaryProbeResponse, SalarySourceResult
from app.services.salary_sources.rabota_ru import check_rabota_ru_salary_source
from app.services.salary_sources.rosstat import fetch_rosstat_region_wage
from app.services.salary_sources.trudvsem import fetch_trudvsem_salary_sample


ROLE_SYNONYMS = {
    "координатор": ["координатор проекта", "координатор мероприятий", "администратор проекта", "организатор мероприятий"],
    "организатор": ["организатор мероприятий", "организатор события", "координатор мероприятий", "event manager", "администратор мероприятий"],
    "куратор": ["куратор проекта", "координатор проекта", "руководитель проекта"],
    "режиссер": ["режиссер", "постановщик", "режиссер-постановщик", "художественный руководитель"],
    "администратор": ["администратор проекта", "координатор проекта", "администратор мероприятий"],
}

ACTIVE_PRODUCTION_SALARY_SOURCES = ("gorodrabot", "trudvsem")
PRODUCTION_ACTIVE_SOURCE_NAMES = ACTIVE_PRODUCTION_SALARY_SOURCES


def normalize_role_title(role: str) -> str:
    cleaned = " ".join(str(role or "").strip().lower().replace("ё", "е").split())
    cleaned = re.sub(r"\s*[-–—]\s*", "-", cleaned)
    return cleaned


def build_salary_role_queries(role: str) -> list[str]:
    cleaned = normalize_role_title(role)
    queries = [cleaned] if cleaned else []

    if cleaned:
        if "проектов" in cleaned:
            queries.append(cleaned.replace("проектов", "проекта"))
        if "проекта" in cleaned:
            queries.append(cleaned.replace("проекта", "проектов"))
        if "проектный" in cleaned:
            queries.append(cleaned.replace("проектный", "проекта"))
        stripped = re.sub(r"\b(проекта|проектов|проектный|проектная|проектное)\b", "", cleaned)
        stripped = " ".join(stripped.split())
        if stripped and stripped != cleaned:
            queries.append(stripped)
        if "-" in cleaned:
            queries.extend(part for part in cleaned.split("-") if part)

    for key, synonyms in ROLE_SYNONYMS.items():
        if key in cleaned:
            queries.extend(synonyms)
            break
    result: list[str] = []
    seen: set[str] = set()
    for query in queries:
        if query and query not in seen:
            seen.add(query)
            result.append(query)
    return result


def source_names_for_scope(source_scope: str) -> set[str]:
    if source_scope == "active":
        return production_source_names()
    if source_scope == "aggregators":
        return {"gorodrabot", "hh", "trudvsem"}
    if source_scope == "official":
        return {"rosstat"}
    return {"gorodrabot", "hh", "trudvsem", "rosstat"}


def production_source_names() -> set[str]:
    return set(PRODUCTION_ACTIVE_SOURCE_NAMES)


def collect_production_salary_source_results(role: str, region: str, year: int | None = None) -> list[SalarySourceResult]:
    actual_year = year or 2025
    return [
        _safe_probe("gorodrabot", lambda: _probe_role_queries(fetch_gorodrabot_salary, role, region, actual_year, min_sample_size=None)),
        _safe_probe("trudvsem", lambda: _probe_role_queries(fetch_trudvsem_salary_sample, role, region, actual_year, min_sample_size=None)),
    ]


def collect_salary_source_results(role: str, region: str, source_scope: str, year: int | None = None) -> list[SalarySourceResult]:
    actual_year = year or 2025
    results: list[SalarySourceResult] = []
    scope_sources = source_names_for_scope(source_scope)
    if "gorodrabot" in scope_sources:
        results.append(_safe_probe("gorodrabot", lambda: _probe_role_queries(fetch_gorodrabot_salary, role, region, actual_year, min_sample_size=None)))
    if "hh" in scope_sources:
        results.append(_safe_probe("hh", lambda: _probe_role_queries(fetch_hh_salary_sample, role, region, actual_year, min_sample_size=10)))
    if "trudvsem" in scope_sources:
        results.append(_safe_probe("trudvsem", lambda: _probe_role_queries(fetch_trudvsem_salary_sample, role, region, actual_year, min_sample_size=10)))
    if "rosstat" in scope_sources:
        results.append(_safe_probe("rosstat", lambda: fetch_rosstat_region_wage(region, actual_year, role=role)))
    return results


def probe_salary_sources(role: str, region: str, year: int) -> SalaryProbeResponse:
    results: list[SalarySourceResult] = []
    results.append(_safe_probe("gorodrabot", lambda: _probe_role_queries(fetch_gorodrabot_salary, role, region, year, min_sample_size=None)))
    results.append(_safe_probe("hh", lambda: _probe_role_queries(fetch_hh_salary_sample, role, region, year, min_sample_size=10)))
    results.append(_safe_probe("trudvsem", lambda: _probe_role_queries(fetch_trudvsem_salary_sample, role, region, year, min_sample_size=10)))
    results.append(_safe_probe("rosstat", lambda: fetch_rosstat_region_wage(region, year, role=role)))
    results.append(_safe_probe("rabota.ru", lambda: check_rabota_ru_salary_source(role, region, year)))
    recommended, warnings = choose_recommended(results, original_role=role)
    return SalaryProbeResponse(role=role, region=region, year=year, results=results, recommended=recommended, warnings=warnings)


def choose_recommended(results: list[SalarySourceResult], original_role: str | None = None) -> tuple[SalarySourceResult | None, list[str]]:
    warnings: list[str] = []
    by_source = {result.source: result for result in results}

    recommended = _ok_with_salary(by_source.get("gorodrabot"))
    if recommended:
        warnings.append("ГородРабот показывает зарплатные предложения в вакансиях, а не фактически выплаченную заработную плату.")
        _append_adjacent_warning(warnings, recommended, original_role)
        return recommended, warnings

    for source in ("hh", "trudvsem"):
        result = _ok_with_salary(by_source.get(source))
        if result and (result.sample_size or 0) >= 10:
            source_title = "HH" if source == "hh" else "Работа России"
            warnings.append(f"{source_title} показывает выборку вакансий, а не среднюю зарплату по году.")
            _append_adjacent_warning(warnings, result, original_role)
            return result, warnings

    rosstat = _ok_with_salary(by_source.get("rosstat"))
    if rosstat and rosstat.salary_type == "official_region_mean":
        warnings.append("Использован официальный региональный fallback вместо зарплаты по конкретной профессии.")
        return rosstat, warnings

    warnings.append("Не удалось автоматически найти надежный зарплатный ориентир.")
    return None, warnings


def _probe_role_queries(
    adapter: Callable[[str, str, int], SalarySourceResult],
    role: str,
    region: str,
    year: int,
    min_sample_size: int | None,
) -> SalarySourceResult:
    queries = build_salary_role_queries(role) or [role]
    first_result: SalarySourceResult | None = None
    for index, query in enumerate(queries):
        result = adapter(query, region, year)
        if first_result is None:
            first_result = result
        if result.status == "ok" and result.salary_value:
            if min_sample_size is None or (result.sample_size or 0) >= min_sample_size or index > 0:
                return _mark_adjacent_if_needed(result, original_role=role)
    return first_result or SalarySourceResult(source="unknown", status="no_data", query_role=role, region=region, year=year)


def _safe_probe(source: str, callback: Callable[[], SalarySourceResult]) -> SalarySourceResult:
    try:
        return callback()
    except Exception as exc:  # noqa: BLE001 - source failure must not break the probe.
        return SalarySourceResult(
            source=source,
            status="unavailable",
            query_role="",
            region="",
            notes=f"Источник не был обработан из-за ошибки: {exc.__class__.__name__}.",
        )


def _mark_adjacent_if_needed(result: SalarySourceResult, original_role: str) -> SalarySourceResult:
    if result.query_role.strip().lower() == original_role.strip().lower():
        return result
    data = result.model_dump()
    data["matched_role"] = result.matched_role or result.query_role
    note = "Использована смежная должность, потому что по исходной роли найдено мало данных."
    data["notes"] = f"{result.notes} {note}".strip() if result.notes else note
    return SalarySourceResult(**data)


def _ok_with_salary(result: SalarySourceResult | None) -> SalarySourceResult | None:
    if result and result.status == "ok" and result.salary_value:
        return result
    return None


def _append_adjacent_warning(warnings: list[str], result: SalarySourceResult, original_role: str | None) -> None:
    if original_role and result.query_role.strip().lower() != original_role.strip().lower():
        warnings.append("Использована смежная должность, потому что по исходной роли найдено мало данных.")
