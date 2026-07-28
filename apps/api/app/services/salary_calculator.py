from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Callable, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.ai_router import AiRouterError, generate_with_gigachat
from app.services.file_generators import generate_docx
from app.services.run_store import StoredRun, run_store
from app.services.salary_sources.aggregator import build_salary_role_queries, collect_production_salary_source_results, production_source_names, source_names_for_scope
from app.services.salary_sources.models import SalarySourceResult


SourceScope = Literal["all", "aggregators", "official", "active"]
WorkloadMode = Literal["percent", "hours_total"]
CofinanceSource = Literal["own_legal_entity_funds", "partner_letter_funds"]

CALENDAR_MANUAL_NOTE = "УКАЖИТЕ НОМЕРА МЕРОПРИЯТИЙ КАЛЕНДАРНОГО ПЛАНА"
SOFT_NO_SALARY_ERROR = "Не удалось найти подтвержденные данные по этой должности в выбранном регионе. Черновик сохранен. Уточните название должности и повторите расчет."
SALARY_SOURCE_NO_CONFIRMED_RESULT = "SALARY_SOURCE_NO_CONFIRMED_RESULT"
COFINANCE_LABELS = {
    "own_legal_entity_funds": "собственные средства юридического лица",
    "partner_letter_funds": "привлеченные средства согласно письму поддержки",
}

MONTHLY_HOURS_NORM = Decimal(166)

SOURCE_LABELS = {
    "gorodrabot": "ГородРабот",
    "hh": "HH",
    "trudvsem": "Работа России",
    "rosstat": "Росстат/ЕМИСС",
}

SOURCE_TYPE_LABELS = {
    "mean": "средняя заработная плата по должности",
    "median": "медианная заработная плата по должности",
    "mode": "модальная заработная плата по должности",
    "vacancy_sample_median": "медиана зарплатных предложений по вакансиям",
    "official_region_mean": "официальный региональный показатель средней зарплаты",
    "manual": "зарплатный ориентир",
}


class SalaryGenerationError(ValueError):
    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


class SalaryPositionInput(BaseModel):
    role_title: str = Field(..., min_length=1)
    staff_count: int = 1
    duration_months: float
    workload_mode: WorkloadMode = "percent"
    workload_value: float
    functionality: str = ""
    calendar_events: str = ""
    cofinance_source: CofinanceSource | None = None


class SalaryGenerateRequest(BaseModel):
    region: str = Field(..., min_length=1)
    contest_slug: str = "pfki"
    project_id: str | None = None
    profile_version: str | None = None
    source_scope: SourceScope = "all"
    cofinance_source: CofinanceSource | None = None
    positions: list[SalaryPositionInput] = Field(default_factory=list)


class SalaryPositionOutput(BaseModel):
    role_title: str
    matched_role: str | None = None
    staff_count: int
    duration_months: float
    workload_mode: WorkloadMode
    workload_value: float
    salary_value: int
    source: str
    source_title: str | None = None
    source_year: int | None = None
    source_url: str | None = None
    attempt_stage: str | None = None
    amount: int
    formula: str
    text: str
    warnings: list[str] = Field(default_factory=list)


class SalaryGenerationOutput(BaseModel):
    run_id: str | None = None
    module_slug: str = "salary"
    title: str
    summary: str
    plain_text: str
    positions: list[SalaryPositionOutput]
    total_amount: int
    warnings: list[str] = Field(default_factory=list)
    downloads: dict[str, str] = Field(default_factory=dict)


class SalaryGenerateResponse(SalaryGenerationOutput):
    status: str
    message: str


def create_salary_run(payload: SalaryGenerateRequest) -> tuple[StoredRun, SalaryGenerationOutput]:
    generated = generate_salary_result(payload)
    run_id = str(uuid4())
    generated.run_id = run_id

    run_dir = Path(settings.file_storage_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    filename = _salary_filename(payload)
    path = run_dir / filename

    sections = _sections_from_salary_output(generated)
    generate_docx(path, generated.title, generated.summary, sections, include_manual_checklist=False)
    downloads = {"docx": f"/api/module-runs/{run_id}/download/docx"}
    files = {"docx": str(path)}
    generated.downloads = downloads

    run = StoredRun(
        run_id=run_id,
        module_slug="salary",
        title=generated.title,
        status="completed",
        summary=generated.summary,
        sections=sections,
        downloads=downloads,
        files=files,
        contest_slug=payload.contest_slug,
        profile_version=payload.profile_version,
        project_id=payload.project_id,
    )
    run_store.save(run)
    return run, generated


def generate_salary_result(payload: SalaryGenerateRequest) -> SalaryGenerationOutput:
    _validate_salary_request(payload)
    positions: list[SalaryPositionOutput] = []
    warnings: list[str] = []

    for position in payload.positions:
        cofinance_key = position.cofinance_source or payload.cofinance_source
        cofinance_text = COFINANCE_LABELS[cofinance_key]  # type: ignore[index]
        attempt_stage = "active_sources"
        source_results = collect_production_salary_source_results(
            position.role_title,
            payload.region,
            year=_default_salary_year(),
        )
        selected, source_warnings = choose_highest_eligible_salary(source_results, payload.source_scope, original_role=position.role_title, allowed_sources=production_source_names())
        warnings.extend(source_warnings)
        if not selected:
            for alias in request_ai_role_aliases(
                role_title=position.role_title,
                region=payload.region,
                role_query_variants=build_salary_role_queries(position.role_title),
            )[:2]:
                alias_results = collect_production_salary_source_results(alias, payload.region, year=_default_salary_year(), max_role_queries=1)
                selected, alias_warnings = choose_highest_eligible_salary(alias_results, "active", original_role=position.role_title, allowed_sources=production_source_names())
                warnings.extend(alias_warnings)
                if selected:
                    attempt_stage = "ai_alias_backend_search"
                    break

        if not selected:
            raise SalaryGenerationError(SOFT_NO_SALARY_ERROR, SALARY_SOURCE_NO_CONFIRMED_RESULT)

        positions.append(_calculate_position(position, payload.region, selected, cofinance_text, attempt_stage=attempt_stage))

    total_amount = sum(item.amount for item in positions)
    plain_text = _compose_plain_text(payload.region, positions, total_amount)
    return SalaryGenerationOutput(
        title=f"Расчет зарплаты и обоснование: {payload.region}",
        summary=f"Регион: {payload.region}. Рабочий расчет оплаты труда для бюджета проекта ПФКИ.",
        plain_text=plain_text,
        positions=positions,
        total_amount=total_amount,
        warnings=[],
    )


def choose_highest_eligible_salary(
    results: list[SalarySourceResult],
    source_scope: SourceScope | str,
    original_role: str | None = None,
    allowed_sources: set[str] | None = None,
) -> tuple[SalarySourceResult | None, list[str]]:
    allowed = allowed_sources or source_names_for_scope(str(source_scope))
    eligible = [result for result in results if _is_eligible_salary_result(result, allowed)]
    warnings: list[str] = []
    if not eligible:
        return None, warnings

    selected = max(eligible, key=lambda result: int(result.salary_value or 0))
    return selected, _unique(warnings)


def request_ai_role_aliases(
    *,
    role_title: str,
    region: str,
    role_query_variants: list[str],
    ai_generate: Callable[[str], str] = generate_with_gigachat,
) -> list[str]:
    if ai_generate is generate_with_gigachat and not settings.gigachat_credentials:
        return []

    system_prompt = _salary_alias_system_prompt()
    user_prompt = _salary_alias_user_prompt(role_title, region, role_query_variants)
    prompts = [
        f"{system_prompt}\n\n{user_prompt}",
        f"{system_prompt}\n\nПредыдущий ответ был невалидным. Верни строго JSON вида {{\"search_roles\":[\"...\"]}} без markdown.\n\n{user_prompt}",
    ]

    for prompt in prompts:
        try:
            raw = ai_generate(prompt)
        except (AiRouterError, Exception):  # noqa: BLE001 - fallback must never break generation.
            return []
        parsed = _parse_json_object(raw)
        aliases = _validate_ai_role_aliases(parsed)
        if not aliases:
            continue
        existing = {item.strip().lower().replace("ё", "е") for item in role_query_variants + [role_title]}
        return [alias for alias in aliases if alias.strip().lower().replace("ё", "е") not in existing][:4]
    return []


def request_ai_text_composition(
    region: str,
    positions: list[SalaryPositionOutput],
    total_amount: int,
    deterministic_plain_text: str,
    ai_generate: Callable[[str], str] = generate_with_gigachat,
) -> str | None:
    if not settings.salary_enable_ai_text_composition:
        return None
    if ai_generate is generate_with_gigachat and not settings.gigachat_credentials:
        return None

    payload = {
        "region": region,
        "positions": [position.model_dump() for position in positions],
        "total_amount": total_amount,
        "required_calendar_note": CALENDAR_MANUAL_NOTE,
    }
    prompt = _salary_text_composition_prompt(payload)
    try:
        raw = ai_generate(prompt)
    except (AiRouterError, Exception):  # noqa: BLE001 - deterministic text remains the safe fallback.
        return None
    parsed = _parse_json_object(raw)
    if not parsed or not isinstance(parsed.get("plain_text"), str):
        return None
    plain_text = parsed["plain_text"].strip()
    if not plain_text:
        return None
    if not _ai_text_preserves_numbers(plain_text, positions, total_amount):
        return None
    if CALENDAR_MANUAL_NOTE in deterministic_plain_text and CALENDAR_MANUAL_NOTE not in plain_text:
        return None
    return plain_text


def _validate_salary_request(payload: SalaryGenerateRequest) -> None:
    if not payload.region.strip():
        raise ValueError("Выберите регион расчета.")
    if payload.source_scope not in {"all", "aggregators", "official", "active"}:
        raise ValueError("Выберите базу расчета.")
    if not payload.positions:
        raise ValueError("Добавьте хотя бы одну должность.")

    for position in payload.positions:
        cofinance_key = position.cofinance_source or payload.cofinance_source
        if cofinance_key not in COFINANCE_LABELS:
            raise ValueError("Выберите источник софинансирования для каждой должности.")
        if not position.role_title.strip():
            raise ValueError("Укажите должность в проекте.")
        if position.staff_count < 1:
            raise ValueError("Количество сотрудников должно быть не меньше 1.")
        if position.duration_months <= 0:
            raise ValueError("Укажите срок работы в месяцах.")
        if position.workload_mode == "percent" and not (0 < position.workload_value <= 100):
            raise ValueError("Процент занятости должен быть от 1 до 100.")
        if position.workload_mode == "hours_total" and position.workload_value <= 0:
            raise ValueError("Укажите количество часов за весь проект.")


def _calculate_position(position: SalaryPositionInput, region: str, source: SalarySourceResult, cofinance_text: str, *, attempt_stage: str = "active_sources") -> SalaryPositionOutput:
    salary = int(source.salary_value or 0)
    if position.workload_mode == "percent":
        raw = Decimal(salary) * Decimal(str(position.workload_value)) / Decimal(100) * Decimal(str(position.duration_months)) * Decimal(position.staff_count)
        amount = _round_rubles(raw)
        formula = f"{_money(salary)} руб. × {_percent(position.workload_value)} × {_number(position.duration_months)} мес. × {position.staff_count}"
        workload_text = f"{_percent(position.workload_value)} рабочего времени"
    else:
        hourly = Decimal(salary) / MONTHLY_HOURS_NORM
        raw = hourly * Decimal(str(position.workload_value)) * Decimal(position.staff_count)
        amount = _round_rubles(raw)
        formula = f"{_money(salary)} руб. / 166 × {_number(position.workload_value)} ч. × {position.staff_count}"
        workload_text = f"{_number(position.workload_value)} часов за весь проект на одного сотрудника"

    calendar_events = _format_calendar_events(position.calendar_events)
    functionality = (
        request_ai_functionality_normalization(position, region=region, calendar_events=calendar_events, ai_generate=generate_with_gigachat)
        or _safe_functionality_fallback(position, calendar_events)
    )
    source_title = SOURCE_LABELS.get(source.source, source.source)
    matched_role = source.matched_role or source.query_role
    calendar_line = (
        f"Календарный план: {calendar_events}"
        if calendar_events == CALENDAR_MANUAL_NOTE
        else f"Календарный план: {calendar_events}."
    )

    text_lines = [
        f"Должность: {position.role_title}.",
        f"Регион расчета: {region}.",
        f"Количество сотрудников: {position.staff_count}. Срок работы: {_number(position.duration_months)} мес. Занятость: {workload_text}.",
        f"Источник расчета: {source_title}, {_salary_type_label(source)} — {_money(salary)} руб. в месяц, {_source_period(source)}.",
        f"Ссылка на источник: {source.source_url or 'проверьте источник вручную'}.",
        f"Функционал сотрудника: {functionality}",
        calendar_line,
        f"Расчет: {formula} = {_money(amount)} руб.",
        f"К включению в бюджет: {_money(amount)} руб.",
        f"Источник софинансирования: {cofinance_text}.",
    ]

    return SalaryPositionOutput(
        role_title=position.role_title,
        matched_role=matched_role,
        staff_count=position.staff_count,
        duration_months=position.duration_months,
        workload_mode=position.workload_mode,
        workload_value=position.workload_value,
        salary_value=salary,
        source=source.source,
        source_title=source_title,
        source_year=source.year,
        source_url=source.source_url,
        attempt_stage=attempt_stage,
        amount=amount,
        formula=formula,
        text="\n".join(text_lines),
        warnings=[],
    )


def _compose_plain_text(region: str, positions: list[SalaryPositionOutput], total_amount: int) -> str:
    chunks = [f"Расчет оплаты труда для проекта ПФКИ\nРегион: {region}"]
    for item in positions:
        chunks.append(item.text)
    if len(positions) > 1:
        chunks.append(f"Итого к включению в бюджет: {_money(total_amount)} руб.")
    return "\n\n".join(chunks).strip()


def _sections_from_salary_output(output: SalaryGenerationOutput) -> list[dict[str, str]]:
    sections = [
        {"title": item.role_title, "body": item.text}
        for item in output.positions
    ]
    if len(output.positions) > 1:
        sections.append({"title": "Итого", "body": f"Итого к включению в бюджет: {_money(output.total_amount)} руб."})
    return sections


def _is_eligible_salary_result(result: SalarySourceResult, allowed_sources: set[str]) -> bool:
    if result.source not in allowed_sources:
        return False
    if result.status != "ok":
        return False
    if not isinstance(result.salary_value, int) or result.salary_value <= 0:
        return False
    if not result.source_url:
        return False
    return True


def _validate_ai_role_aliases(parsed: dict | None) -> list[str]:
    if not parsed:
        return []
    raw_roles = parsed.get("search_roles")
    if not isinstance(raw_roles, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_roles:
        if not isinstance(item, str):
            continue
        role = " ".join(item.strip().lower().replace("ё", "е").split())
        role = re.sub(r"\s*[-–—]\s*", "-", role)
        if len(role) < 3 or len(role) > 80:
            continue
        if re.search(r"\d|https?://|руб|₽", role, flags=re.IGNORECASE):
            continue
        if role not in seen:
            seen.add(role)
            result.append(role)
        if len(result) >= 4:
            break
    return result


def _salary_alias_system_prompt() -> str:
    return (
        "Ты нормализуешь название проектной должности для поиска зарплатных вакансий в России.\n"
        "Верни только 1–4 реально употребимых названия профессии на русском языке. "
        "Не придумывай зарплаты, ссылки, работодателей и статистику.\n"
        "Сохрани профессиональный смысл исходной должности. Сначала укажи максимально точный вариант, затем смежные.\n"
        "Верни строго JSON без markdown:\n{\"search_roles\":[\"...\"]}"
    )


def _salary_alias_user_prompt(role_title: str, region: str, role_query_variants: list[str]) -> str:
    return (
        "Подбери поисковые названия должности для backend-поиска зарплатных вакансий.\n"
        f"Входные данные:\n- Должность в проекте: {role_title}\n- Регион: {region}\n"
        f"- Уже проверенные варианты: {role_query_variants}\n\n"
        "Требования:\n"
        "1. Не возвращай зарплаты, суммы, ссылки, статистику и названия работодателей.\n"
        "2. Верни 1–4 названия должности, которые реально встречаются в вакансиях.\n"
        "3. Не меняй профессиональную область должности.\n"
        "4. Никакого текста вне JSON.\n"
        "Верни только JSON:\n{\"search_roles\":[\"...\"]}"
    )


def _salary_text_composition_prompt(payload: dict) -> str:
    return (
        "Ты профессиональный грантрайтер ПФКИ. Составь официальный текст расчета оплаты труда по уже рассчитанным данным. "
        "Числа, формулы, суммы, источники и ссылки менять запрещено. Если функционал сотрудника задан кратко или с ошибками, "
        "перепиши его официально и грамотно. Если функционал пустой, предложи типовой функционал по должности, не добавляя уникальных фактов проекта. "
        "Пиши коротко, ясно, без канцелярской воды.\n"
        "Собери результат расчета оплаты труда для заявки ПФКИ.\n"
        f"Данные: {json.dumps(payload, ensure_ascii=False)}\n"
        "Требования:\n"
        "1. Начни с заголовка: “Расчет оплаты труда для проекта ПФКИ”.\n"
        "2. Укажи регион.\n"
        "3. Для каждой позиции сделай отдельный блок.\n"
        "4. В каждом блоке обязательно укажи должность, количество сотрудников, срок работы, занятость, источник зарплаты, показатель, год/период, ссылку, функционал, календарный план, формулу, сумму и источник софинансирования.\n"
        "5. Не добавляй примечания к источникам и общий блок “Обоснование”.\n"
        "6. Не добавляй markdown-таблицы.\n"
        "7. Не меняй ни одного числа из данных.\n"
        "8. Верни JSON: {\"plain_text\":\"...\",\"position_summaries\":[\"...\"]}"
    )


def request_ai_functionality_normalization(
    position: SalaryPositionInput,
    *,
    region: str,
    calendar_events: str,
    ai_generate: Callable[[str], str] = generate_with_gigachat,
) -> str | None:
    if ai_generate is generate_with_gigachat and not settings.gigachat_credentials:
        return None

    user_functionality = " ".join(position.functionality.strip().split())
    prompts = [_functionality_normalization_prompt(position, region, calendar_events, user_functionality)]
    last_text: str | None = None
    for prompt in prompts:
        try:
            raw = ai_generate(prompt)
        except (AiRouterError, Exception):  # noqa: BLE001 - raw user text must never leak on AI failure.
            return None
        parsed = _parse_json_object(raw)
        text = _clean_functionality_text(parsed.get("functional_text") if parsed else None)
        if not text or _contains_disallowed_raw_functionality(text, user_functionality):
            continue
        if len(text) <= 650:
            return text
        last_text = text
        if len(prompts) == 1:
            prompts.append(_functionality_shorten_prompt(text))

    if last_text:
        shortened = _truncate_by_sentence(last_text, 650)
        if shortened and not _contains_disallowed_raw_functionality(shortened, user_functionality):
            return shortened
    return None


def _functionality_normalization_prompt(position: SalaryPositionInput, region: str, calendar_events: str, user_functionality: str) -> str:
    system_prompt = (
        "Ты профессиональный грантрайтер ПФКИ. Твоя задача — переписать или составить функционал сотрудника для обоснования оплаты труда в бюджете проекта.\n\n"
        "Пиши официально, конкретно и кратко. Не копируй сырой пользовательский текст дословно, если он разговорный, грубый, грамматически кривой или слишком общий.\n\n"
        "Нельзя:\n"
        "- добавлять неподтвержденные должности, суммы и источники;\n"
        "- писать просторечия, мат, шутки, обвинительные или неофициальные формулировки;\n"
        "- писать больше 650 символов;\n"
        "- обещать результат проекта;\n"
        "- менять должность сотрудника;\n"
        "- упоминать зарплатные источники.\n\n"
        "Если пользовательский функционал пустой или слабый, составь типовой функционал по должности и проектной занятости.\n\n"
        "Верни строго JSON без markdown:\n{\"functional_text\":\"...\"}"
    )
    workload_type = "% рабочего времени" if position.workload_mode == "percent" else "часы за весь проект"
    user_prompt = (
        "Составь официальный функционал сотрудника для расчета оплаты труда.\n\n"
        "Входные данные:\n"
        f"- Должность: {position.role_title}\n"
        f"- Регион: {region}\n"
        f"- Количество сотрудников: {position.staff_count}\n"
        f"- Срок работы: {_number(position.duration_months)} мес.\n"
        f"- Тип занятости: {workload_type}\n"
        f"- Занятость: {_number(position.workload_value)}\n"
        f"- Мероприятия календарного плана: {calendar_events if calendar_events != CALENDAR_MANUAL_NOTE else ''}\n"
        f"- Пользовательское описание функционала: {user_functionality}\n\n"
        "Требования:\n"
        "1. Напиши 2–4 коротких предложения.\n"
        "2. Общий объем — максимум 650 символов.\n"
        "3. Текст должен показывать, зачем эта должность нужна проекту.\n"
        "4. Если есть календарные мероприятия, привяжи функционал к сопровождению этих мероприятий.\n"
        "5. Если описание пользователя кривое или разговорное, используй его только как смысловую подсказку.\n"
        "6. Не вставляй сырой текст пользователя дословно.\n"
        "7. Не добавляй “Обоснование:” — нужен только сам функционал.\n\n"
        "Верни только JSON:\n{\"functional_text\":\"...\"}"
    )
    return f"{system_prompt}\n\n{user_prompt}"


def _functionality_shorten_prompt(text: str) -> str:
    return (
        "Сократи functional_text до 600 символов, сохрани официальный стиль. "
        "Верни строго JSON без markdown: {\"functional_text\":\"...\"}\n\n"
        f"functional_text: {text}"
    )


def _clean_functionality_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


def _contains_disallowed_raw_functionality(text: str, raw: str) -> bool:
    normalized_text = text.lower().replace("ё", "е")
    normalized_raw = raw.lower().replace("ё", "е").strip()
    if not normalized_text:
        return True
    if normalized_raw and normalized_raw in normalized_text:
        return True
    return any(phrase in normalized_text for phrase in ["за наши деньги", "с утра до вечера", "хер", "бляд", "нахуй"])


def _truncate_by_sentence(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    parts = re.split(r"(?<=[.!?])\s+", text)
    result = ""
    for part in parts:
        candidate = f"{result} {part}".strip()
        if len(candidate) > limit:
            break
        result = candidate
    if result:
        return result
    return text[: limit - 1].rstrip(" ,;:.") + "."


def _ai_text_preserves_numbers(text: str, positions: list[SalaryPositionOutput], total_amount: int) -> bool:
    normalized = re.sub(r"\D", "", text)
    required_numbers: list[int] = []
    for position in positions:
        required_numbers.extend([position.salary_value, position.amount, position.staff_count])
        required_numbers.append(int(position.workload_value) if float(position.workload_value).is_integer() else int(position.workload_value * 100))
        if position.workload_mode == "percent":
            required_numbers.append(int(position.duration_months) if float(position.duration_months).is_integer() else int(position.duration_months * 100))
        if position.source_url and position.source_url not in text:
            return False
    if len(positions) > 1:
        required_numbers.append(total_amount)
    return all(str(number) in normalized for number in required_numbers)


def _parse_json_object(raw: str) -> dict | None:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def _functionality_or_default(role_title: str, functionality: str) -> str:
    cleaned = functionality.strip()
    if len(cleaned) >= 30:
        return _polish_functionality(role_title, cleaned)
    role = role_title.strip() or "специалист"
    return (
        f"{role} выполняет организационное сопровождение проекта: согласует расписание, взаимодействует с участниками и командой, "
        "контролирует подготовку мероприятий, фиксирует посещаемость и передает данные для отчетности."
    )


def _safe_functionality_fallback(position: SalaryPositionInput, calendar_events: str) -> str:
    role = position.role_title.strip().lower().replace("ё", "е")
    calendar_reference = re.sub(r"^мероприятия\b", "мероприятий", calendar_events)
    calendar_tail = "" if calendar_events == CALENDAR_MANUAL_NOTE else f" {calendar_reference}"
    if "дворник" in role or "убор" in role:
        return (
            "Сотрудник обеспечивает санитарное состояние и порядок на территории, используемой для мероприятий проекта. "
            f"В период реализации проекта выполняет уборку площадки до и после{calendar_tail}, помогает поддерживать безопасные и комфортные условия для участников и посетителей."
        )
    if "маркетолог" in role or "smm" in role or "смм" in role:
        return "Сотрудник формирует анонсную кампанию проекта, готовит и координирует информационное освещение. Согласует публикации, передает материалы ответственным членам команды и сопровождает коммуникации по мероприятиям календарного плана."
    return "Сотрудник выполняет функции, связанные с обеспечением задач проекта по своей должности, участвует в подготовке и сопровождении мероприятий календарного плана."


def _polish_functionality(role_title: str, functionality: str) -> str:
    cleaned = " ".join(functionality.strip().split())
    lower = cleaned.lower().replace("ё", "е")
    if "анонс камп" in lower and "освещ" in lower:
        return "формирует анонсную кампанию проекта, готовит и координирует информационное освещение, согласует публикации и передает материалы ответственным членам команды."
    replacements = {
        "анонс кампанию": "анонсную кампанию проекта",
        "анонс компанию": "анонсную кампанию проекта",
        "освещение проекта": "информационное освещение проекта",
    }
    polished = cleaned
    for source, target in replacements.items():
        polished = re.sub(source, target, polished, flags=re.IGNORECASE)
    return polished[0].lower() + polished[1:] if polished else _functionality_or_default(role_title, "")


def _format_calendar_events(value: str) -> str:
    cleaned = " ".join(str(value or "").strip().split())
    if not cleaned:
        return CALENDAR_MANUAL_NOTE
    parts = [part.strip() for part in re.split(r"[,;]+", cleaned) if part.strip()]
    if len(parts) > 1:
        return f"мероприятия № {', '.join(parts)}"
    if re.fullmatch(r"[\d\s,.;–—-]+", cleaned):
        return f"мероприятия № {cleaned}"
    return cleaned


def _salary_type_label(source: SalarySourceResult) -> str:
    return SOURCE_TYPE_LABELS.get(str(source.salary_type or ""), "зарплатный ориентир")


def _source_period(source: SalarySourceResult) -> str:
    return f"{source.year} год" if source.year else "актуальный доступный период"


def _salary_filename(payload: SalaryGenerateRequest) -> str:
    total_staff = sum(max(0, int(position.staff_count)) for position in payload.positions) or 1
    role = payload.positions[0].role_title if payload.positions else "должность"
    unique_roles = {position.role_title.strip().lower().replace("ё", "е") for position in payload.positions if position.role_title.strip()}
    if len(unique_roles) > 1:
        role = f"{role}_и_еще_{len(unique_roles) - 1}"
    safe_role = re.sub(r"[^0-9A-Za-zА-Яа-яЁё _-]+", "", role).strip().lower().replace(" ", "_") or "должность"
    return f"расчет_зарплаты_{total_staff}_{safe_role}.docx"


def _default_salary_year() -> int:
    return max(2024, date.today().year - 1)


def _round_rubles(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _money(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _percent(value: float) -> str:
    return f"{_number(value)}%"


def _number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value).replace(".", ",")


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
