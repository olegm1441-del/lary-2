from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.ai_router import AiRouterError, generate_with_gigachat
from app.services.file_generators import generate_docx
from app.services.run_store import StoredRun, run_store
from app.services.salary_sources.aggregator import build_salary_role_queries, collect_salary_source_results, source_names_for_scope
from app.services.salary_sources.models import SalarySourceResult


SourceScope = Literal["all", "aggregators", "official"]
WorkloadMode = Literal["percent", "hours_total"]
CofinanceSource = Literal["own_legal_entity_funds", "partner_letter_funds"]

CALENDAR_MANUAL_NOTE = "УКАЖИТЕ НОМЕРА МЕРОПРИЯТИЙ КАЛЕНДАРНОГО ПЛАНА"
SOFT_NO_SALARY_ERROR = "Не получилось автоматически найти зарплатный ориентир. Данные сохранены. Попробуйте изменить должность или регион и запустить расчет еще раз."
ALLOWED_FALLBACK_DOMAINS = {"gorodrabot.ru", "hh.ru", "trudvsem.ru", "rosstat.gov.ru", "fedstat.ru"}
OFFICIAL_FALLBACK_DOMAINS = {"rosstat.gov.ru", "fedstat.ru"}

COFINANCE_LABELS = {
    "own_legal_entity_funds": "собственные средства юридического лица",
    "partner_letter_funds": "привлеченные средства согласно письму поддержки",
}

SOURCE_LABELS = {
    "gorodrabot": "GorodRabot",
    "hh": "HH",
    "trudvsem": "Trudvsem",
    "rosstat": "Росстат/ЕМИСС",
    "ai_salary_fallback": "резервный поиск по открытым источникам",
}


class SalaryPositionInput(BaseModel):
    role_title: str = Field(..., min_length=1)
    staff_count: int = 1
    duration_months: float
    workload_mode: WorkloadMode = "percent"
    workload_value: float
    functionality: str = ""
    calendar_events: str = ""


class SalaryGenerateRequest(BaseModel):
    region: str = Field(..., min_length=1)
    source_scope: SourceScope = "all"
    cofinance_source: CofinanceSource
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
    source_url: str | None = None
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
    filename = _salary_filename(payload.region)
    path = run_dir / filename

    sections = _sections_from_salary_output(generated)
    generate_docx(path, generated.title, generated.summary, sections)
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
    )
    run_store.save(run)
    return run, generated


def generate_salary_result(payload: SalaryGenerateRequest) -> SalaryGenerationOutput:
    _validate_salary_request(payload)
    positions: list[SalaryPositionOutput] = []
    warnings: list[str] = []
    cofinance_text = COFINANCE_LABELS[payload.cofinance_source]

    for position in payload.positions:
        source_results = collect_salary_source_results(
            position.role_title,
            payload.region,
            payload.source_scope,
            year=_default_salary_year(),
        )
        selected, source_warnings = choose_highest_eligible_salary(source_results, payload.source_scope, original_role=position.role_title)
        warnings.extend(source_warnings)
        if not selected:
            fallback = request_ai_salary_fallback(
                role_title=position.role_title,
                region=payload.region,
                source_scope=payload.source_scope,
                role_query_variants=build_salary_role_queries(position.role_title),
            )
            if fallback:
                selected = fallback
                warnings.append("Зарплатный ориентир найден резервным способом. Проверьте источник перед подачей заявки.")

        if not selected:
            raise ValueError(SOFT_NO_SALARY_ERROR)

        positions.append(_calculate_position(position, payload.region, selected, cofinance_text))

    total_amount = sum(item.amount for item in positions)
    deterministic_plain_text = _compose_plain_text(payload.region, positions, total_amount)
    plain_text = request_ai_text_composition(payload.region, positions, total_amount, deterministic_plain_text) or deterministic_plain_text
    return SalaryGenerationOutput(
        title=f"Расчет зарплаты и обоснование: {payload.region}",
        summary="Расчет готов. Проверьте источник зарплаты, занятость, календарный план и итоговые суммы перед подачей заявки.",
        plain_text=plain_text,
        positions=positions,
        total_amount=total_amount,
        warnings=_unique(warnings),
    )


def choose_highest_eligible_salary(
    results: list[SalarySourceResult],
    source_scope: SourceScope | str,
    original_role: str | None = None,
) -> tuple[SalarySourceResult | None, list[str]]:
    allowed = source_names_for_scope(str(source_scope))
    eligible = [result for result in results if _is_eligible_salary_result(result, allowed)]
    warnings: list[str] = []
    if not eligible:
        return None, warnings

    selected = max(eligible, key=lambda result: int(result.salary_value or 0))
    if selected.source in {"gorodrabot", "hh", "trudvsem"}:
        warnings.append(f"{SOURCE_LABELS.get(selected.source, selected.source)} показывает зарплатные предложения или выборку вакансий, а не фактически выплаченную заработную плату.")
    if selected.salary_type == "official_region_mean":
        warnings.append("Использован официальный региональный показатель, а не статистика по конкретной должности.")
    if original_role and (selected.matched_role or selected.query_role).strip().lower() != original_role.strip().lower():
        warnings.append(f"Использована смежная должность: {selected.matched_role or selected.query_role}, потому что по исходной формулировке найдено мало данных.")
    if selected.source == "ai_salary_fallback" and selected.confidence == "low":
        warnings.append("Резервный источник имеет низкую уверенность. Проверьте его вручную перед подачей заявки.")
    return selected, _unique(warnings)


def request_ai_salary_fallback(
    *,
    role_title: str,
    region: str,
    source_scope: str,
    role_query_variants: list[str],
    ai_generate: Callable[[str], str] = generate_with_gigachat,
    url_checker: Callable[[str], bool] | None = None,
) -> SalarySourceResult | None:
    if ai_generate is generate_with_gigachat and not settings.gigachat_credentials:
        return None

    system_prompt = _salary_fallback_system_prompt()
    user_prompt = _salary_fallback_user_prompt(role_title, region, source_scope, role_query_variants)
    prompts = [
        f"{system_prompt}\n\n{user_prompt}",
        f"{system_prompt}\n\nПредыдущий ответ был невалидным. Верни валидный JSON строго по схеме.\n\n{user_prompt}",
    ]

    checker = url_checker or _fallback_url_reachable
    for prompt in prompts:
        try:
            raw = ai_generate(prompt)
        except (AiRouterError, Exception):  # noqa: BLE001 - fallback must never break generation.
            return None
        parsed = _parse_json_object(raw)
        if not parsed:
            continue
        allowed_domains = OFFICIAL_FALLBACK_DOMAINS if source_scope == "official" else ALLOWED_FALLBACK_DOMAINS
        result = _validate_ai_salary_payload(parsed, checker, allowed_domains)
        if result:
            return result
        if parsed.get("status") == "no_data":
            return None
    return None


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
    if payload.source_scope not in {"all", "aggregators", "official"}:
        raise ValueError("Выберите базу расчета.")
    if payload.cofinance_source not in COFINANCE_LABELS:
        raise ValueError("Выберите источник софинансирования.")
    if not payload.positions:
        raise ValueError("Добавьте хотя бы одну должность.")

    for position in payload.positions:
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


def _calculate_position(position: SalaryPositionInput, region: str, source: SalarySourceResult, cofinance_text: str) -> SalaryPositionOutput:
    salary = int(source.salary_value or 0)
    if position.workload_mode == "percent":
        raw = Decimal(salary) * Decimal(str(position.workload_value)) / Decimal(100) * Decimal(str(position.duration_months)) * Decimal(position.staff_count)
        amount = _round_rubles(raw)
        formula = f"{_money(salary)} руб. × {_percent(position.workload_value)} × {_number(position.duration_months)} мес. × {position.staff_count}"
        workload_text = f"{_percent(position.workload_value)} рабочего времени"
    else:
        hourly = Decimal(salary) / Decimal(160)
        raw = hourly * Decimal(str(position.workload_value)) * Decimal(position.staff_count)
        amount = _round_rubles(raw)
        formula = f"{_money(salary)} руб. / 160 × {_number(position.workload_value)} ч. × {position.staff_count}"
        workload_text = f"{_number(position.workload_value)} часов за весь проект на одного сотрудника"

    functionality = _functionality_or_default(position.role_title, position.functionality)
    calendar_events = position.calendar_events.strip() or CALENDAR_MANUAL_NOTE
    source_title = SOURCE_LABELS.get(source.source, source.source)
    matched_role = source.matched_role or source.query_role

    warnings: list[str] = []
    if matched_role and matched_role.strip().lower() != position.role_title.strip().lower():
        warnings.append(f"Использована смежная должность: {matched_role}, потому что по исходной формулировке найдено мало данных.")
    if source.salary_type == "official_region_mean":
        warnings.append("Использован официальный региональный показатель, а не статистика по конкретной должности.")

    text_lines = [
        f"Должность: {position.role_title}.",
        f"Регион расчета: {region}.",
        f"Количество сотрудников: {position.staff_count}. Срок работы: {_number(position.duration_months)} мес. Занятость: {workload_text}.",
        f"Источник зарплаты: {source_title}; показатель: {_money(salary)} руб. в месяц; год/период: {source.year or 'актуальный доступный период'}.",
        f"Ссылка на источник: {source.source_url or 'проверьте источник вручную'}.",
        f"Функционал сотрудника: {functionality}",
        f"Календарный план: {calendar_events}.",
        f"Расчет: {formula} = {_money(amount)} руб.",
        f"К включению в бюджет: {_money(amount)} руб.",
        f"Обоснование: сумма рассчитана пропорционально занятости сотрудника в проекте и относится к выполнению задач календарного плана. В бюджет включается только часть оплаты труда, связанная с заявляемым проектом.",
        f"Источник софинансирования: {cofinance_text}.",
    ]
    if warnings:
        text_lines.append("Примечание: " + " ".join(warnings))

    return SalaryPositionOutput(
        role_title=position.role_title,
        matched_role=matched_role,
        staff_count=position.staff_count,
        duration_months=position.duration_months,
        workload_mode=position.workload_mode,
        workload_value=position.workload_value,
        salary_value=salary,
        source=source.source,
        source_url=source.source_url,
        amount=amount,
        formula=formula,
        text="\n".join(text_lines),
        warnings=warnings,
    )


def _compose_plain_text(region: str, positions: list[SalaryPositionOutput], total_amount: int) -> str:
    chunks = [f"Расчет оплаты труда для проекта ПФКИ\nРегион: {region}"]
    for index, item in enumerate(positions, start=1):
        chunks.append(f"Позиция {index}. {item.role_title}\n{item.text}")
    if len(positions) > 1:
        chunks.append(f"Итого по оплате труда: {_money(total_amount)} руб.")
    return "\n\n".join(chunks).strip()


def _sections_from_salary_output(output: SalaryGenerationOutput) -> list[dict[str, str]]:
    sections = [
        {"title": item.role_title, "body": item.text}
        for item in output.positions
    ]
    if len(output.positions) > 1:
        sections.append({"title": "Итого", "body": f"Итого по оплате труда: {_money(output.total_amount)} руб."})
    if output.warnings:
        sections.append({"title": "Что проверить вручную", "body": "\n".join(output.warnings)})
    return sections


def _is_eligible_salary_result(result: SalarySourceResult, allowed_sources: set[str]) -> bool:
    if result.source not in allowed_sources:
        return False
    if result.status != "ok":
        return False
    if not isinstance(result.salary_value, int) or result.salary_value <= 0:
        return False
    if result.source != "ai_salary_fallback" and not result.source_url:
        return False
    if result.source == "ai_salary_fallback" and result.confidence == "low":
        return False
    return True


def _validate_ai_salary_payload(payload: dict, url_checker: Callable[[str], bool], allowed_domains: set[str]) -> SalarySourceResult | None:
    if payload.get("status") != "ok":
        return None
    source_url = str(payload.get("source_url") or "")
    if not source_url.startswith("https://") or not _is_allowed_fallback_url(source_url, allowed_domains):
        return None
    if not url_checker(source_url):
        return None
    try:
        salary_value = int(payload.get("salary_value"))
    except (TypeError, ValueError):
        return None
    if salary_value <= 0:
        return None
    confidence = str(payload.get("confidence") or "medium")
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"
    salary_type = str(payload.get("salary_type") or "vacancy_sample_median")
    if salary_type not in {"mean", "median", "mode", "vacancy_sample_median", "official_region_mean", "manual"}:
        salary_type = "vacancy_sample_median"

    return SalarySourceResult(
        source="ai_salary_fallback",
        status="ok",
        query_role=str(payload.get("query_role") or ""),
        matched_role=str(payload.get("matched_role") or payload.get("query_role") or ""),
        region=str(payload.get("region") or ""),
        year=_safe_int(payload.get("year")),
        salary_value=salary_value,
        salary_type=salary_type,  # type: ignore[arg-type]
        source_url=source_url,
        notes=str(payload.get("notes") or ""),
        confidence=confidence,  # type: ignore[arg-type]
    )


def _salary_fallback_system_prompt() -> str:
    return (
        "Ты помогаешь backend-сервису найти зарплатный ориентир для расчета бюджета проекта. "
        "Верни только валидный JSON по схеме. Никакого текста вне JSON.\n"
        "Тебе нельзя выдумывать данные. Если ты не можешь указать проверяемый источник и ссылку, верни status=\"no_data\".\n"
        "Используй только открытые источники зарплат/вакансий из допустимых доменов: gorodrabot.ru, hh.ru, trudvsem.ru, rosstat.gov.ru, fedstat.ru.\n"
        "Нельзя использовать форумы, статьи без методики, агрегаторы без ссылки на страницу выдачи или источники без публичной проверки.\n"
        "Если находишь данные по смежной должности, обязательно укажи matched_role и notes.\n"
        "Верни строго JSON: {\"status\":\"ok|no_data\",\"source\":\"ai_salary_fallback\",\"source_name\":\"...\",\"source_url\":\"https://...\","
        "\"query_role\":\"...\",\"matched_role\":\"...\",\"region\":\"...\",\"year\":2025,\"salary_value\":123456,"
        "\"salary_type\":\"mean|median|vacancy_sample_median|official_region_mean\",\"confidence\":\"high|medium|low\",\"notes\":\"...\"}"
    )


def _salary_fallback_user_prompt(role_title: str, region: str, source_scope: str, role_query_variants: list[str]) -> str:
    return (
        "Найди зарплатный ориентир для расчета оплаты труда в проекте.\n"
        f"Входные данные:\n- Должность в проекте: {role_title}\n- Регион: {region}\n- Тип источников: {source_scope}\n"
        f"- Допустимые варианты поиска должности: {role_query_variants}\n"
        "Требования:\n"
        "1. Верни одно число salary_value в рублях в месяц.\n"
        "2. Выбирай наиболее высокий подтвержденный показатель из найденных допустимых источников.\n"
        "3. Если источник дает данные по смежной должности, укажи matched_role и объясни это в notes.\n"
        "4. Если данные только по региону, а не по должности, salary_type должен быть official_region_mean.\n"
        "5. Если не можешь указать проверяемую ссылку, верни status=\"no_data\".\n"
        "6. Никакого текста вне JSON.\n"
        "Верни только JSON по заданной схеме."
    )


def _salary_text_composition_prompt(payload: dict) -> str:
    return (
        "Ты профессиональный грантрайтер ПФКИ. Твоя задача — оформить расчет заработной платы и обоснование для заявки.\n"
        "Нельзя: менять зарплатные числа; менять формулу; менять итоговые суммы; выдумывать источник зарплаты; "
        "писать, что данные официальные, если source не rosstat; скрывать, что использована смежная должность; писать длинно и канцелярски.\n"
        "Если функционал сотрудника пустой или слишком короткий, предложи типовой функционал по должности в проекте.\n"
        "Верни строго валидный JSON без markdown: {\"plain_text\":\"...\",\"items\":[{\"role_title\":\"...\",\"text\":\"...\"}]}.\n"
        "Структура текста по каждой позиции:\n"
        "1. Должность, регион, количество сотрудников, срок работы, занятость.\n"
        "2. Источник зарплаты: источник, год/период, найденная зарплата, ссылка или название источника.\n"
        "3. Функционал сотрудника: 1 абзац.\n"
        "4. Календарный план: если номера мероприятий есть — указать их; если нет — написать точную фразу "
        f"«{CALENDAR_MANUAL_NOTE}».\n"
        "5. Расчет: показать формулу.\n"
        "6. К включению в бюджет: сумма в рублях.\n"
        "7. Обоснование: 1 короткий абзац, почему занятость и сумма относятся к проекту.\n"
        "8. Источник софинансирования.\n"
        "Если позиций несколько, после всех позиций добавь итоговую строку.\n"
        "Пиши официально, конкретно и компактно. Не добавляй вступление про Лари. Не добавляй обещаний победы в конкурсе. Не добавляй непроверенные данные.\n"
        f"Входные данные JSON: {json.dumps(payload, ensure_ascii=False)}"
    )


def _ai_text_preserves_numbers(text: str, positions: list[SalaryPositionOutput], total_amount: int) -> bool:
    normalized = re.sub(r"\D", "", text)
    required_numbers: list[int] = []
    for position in positions:
        required_numbers.extend([position.salary_value, position.amount])
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


def _fallback_url_reachable(url: str) -> bool:
    try:
        response = httpx.head(url, timeout=5.0, follow_redirects=True)
        if response.status_code < 400:
            return True
        response = httpx.get(url, timeout=5.0, follow_redirects=True)
        return response.status_code < 400
    except httpx.HTTPError:
        return False


def _is_allowed_fallback_url(url: str, allowed_domains: set[str] = ALLOWED_FALLBACK_DOMAINS) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


def _functionality_or_default(role_title: str, functionality: str) -> str:
    cleaned = functionality.strip()
    if len(cleaned.split()) >= 5:
        return cleaned
    role = role_title.strip() or "специалист"
    return (
        f"{role} выполняет организационное сопровождение проекта: согласует расписание, взаимодействует с участниками и командой, "
        "контролирует подготовку мероприятий, фиксирует посещаемость и передает данные для отчетности."
    )


def _salary_filename(region: str) -> str:
    safe_region = re.sub(r"[^0-9A-Za-zА-Яа-яЁё _-]+", "", region).strip().replace(" ", "_") or "регион"
    return f"Расчет зарплаты_ПФКИ_{safe_region}_{date.today().isoformat()}.docx"


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


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
