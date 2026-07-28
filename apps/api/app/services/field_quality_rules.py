from __future__ import annotations

import re
from typing import Any

from app.data.modules import get_module


REQUIRED_FIELDS: dict[str, set[str]] = {
    "social-research": {"region", "direction", "target_group", "problem"},
    "legal-acts": {"program_level", "region", "direction", "target_group"},
    "salary": {"role", "region", "functionality", "months", "employee_count", "employment_percent", "cofunding"},
    "support-letter": {"value_keywords", "support_types", "support_details"},
    "presentation": {"project_description"},
    "scenario-plan": {
        "scenario_type",
        "event_title",
        "event_idea",
        "location",
        "participants",
        "beneficiary_audience",
        "schedule",
        "preparation",
        "team_equipment_constraints",
    },
}


def analyze_field_quality(module_slug: str, field_key: str, value: Any, form_context: dict[str, Any] | None = None) -> dict:
    module = get_module(module_slug)
    if not module or module["status"] != "active":
        raise ValueError("Такой модуль пока недоступен.")

    context = {str(key): _string(value) for key, value in (form_context or {}).items()}
    covered_by_fields = [key for key, context_value in context.items() if context_value and key != field_key]
    text = _string(value)
    field_key = str(field_key)

    if module_slug == "legal-acts" and field_key == "region" and _is_regional_legal_search(context.get("program_level", "")) and not text:
        return _error("Для региональных документов нужен регион.", covered_by_fields=covered_by_fields)

    if module_slug == "scenario-plan" and field_key == "scenario_type" and not text:
        return _error("Выберите вид сценарного плана.", covered_by_fields=covered_by_fields)

    if not text:
        if module_slug == "support-letter" and field_key == "value_keywords":
            return _error("Добавьте ключевые смыслы проекта: для кого, где и почему проект важен.", covered_by_fields=covered_by_fields)
        if module_slug == "support-letter" and field_key == "support_types":
            return _error("Выберите хотя бы один вид поддержки.", covered_by_fields=covered_by_fields)
        if module_slug == "support-letter" and field_key == "support_details":
            return _error("Опишите, что именно делает партнер.", covered_by_fields=covered_by_fields)
        if field_key in REQUIRED_FIELDS.get(module_slug, set()):
            return _error("Заполните это поле, чтобы запустить.", covered_by_fields=covered_by_fields)
        return _success(covered_by_fields)

    if field_key in {"problem", "event_idea", "project_description", "functionality", "constraints", "team_equipment_constraints"} and _word_count(text) < 10:
        if field_key == "problem":
            return _warning(
                "Добавьте, как проявляется проблема или к какому последствию она приводит.",
                [
                    _suggest("add_consequence", "Добавить последствие", "Это ограничивает доступ целевой группы к подходящим возможностям участия."),
                    _dismiss(),
                ],
                covered_by_fields,
            )
        return _warning(
            "Добавьте 1–2 смысловые детали, которые относятся именно к этому полю.",
            [_suggest("add_detail", "Добавить деталь", "Уточните наблюдаемое проявление и ожидаемый результат."), _dismiss()],
            covered_by_fields,
        )

    if field_key == "target_group":
        if _is_broad_target_group(text):
            return _warning(
                "Уточните возраст и социальный статус участников.",
                [_suggest("add_age", "Добавить возраст", "12–22 лет"), _suggest("add_status", "Уточнить статус", "учащиеся и молодые специалисты"), _dismiss()],
                covered_by_fields,
            )
        if not _has_age(text):
            return _warning(
                "Добавьте возраст или диапазон. Например: подростки 12–17 лет.",
                [_suggest("add_age", "Добавить возраст", "12–17 лет"), _dismiss()],
                covered_by_fields,
            )

    if field_key in {"problem", "event_idea", "project_description"} and not _has_territory(text, context):
        return _warning(
            "Укажите территорию в отдельном поле «Регион».",
            [_dismiss()],
            covered_by_fields,
        )

    if module_slug == "salary":
        if field_key == "employee_count" and _to_float(text) <= 0:
            return _error("Количество сотрудников должно быть больше нуля.", covered_by_fields=covered_by_fields)
        if field_key == "employment_percent" and (_to_float(text) <= 0 or _to_float(text) > 100):
            return _error("Занятость одного сотрудника не может быть больше 100%.", covered_by_fields=covered_by_fields)
        if field_key == "months" and _to_float(text) <= 0:
            return _error("Срок работы должен быть больше нуля.", covered_by_fields=covered_by_fields)
        if field_key == "functionality" and _word_count(text) < 10:
            return _warning("Опишите 2–3 обязанности: что делает специалист и к каким мероприятиям относится.", covered_by_fields=covered_by_fields)

    if module_slug == "support-letter":
        official_hint = _official_language_hint(field_key, text)
        if official_hint:
            return official_hint
        if field_key == "cofinance_block" and (not _has_digits(text) or _has_letters(text) or any(char in text for char in "₽.,;:")):
            return _error("Введите оценку вклада только числом, без слова “рублей”.", covered_by_fields=covered_by_fields)
        if field_key in {"value_keywords", "support_details"} and _word_count(text) < 8:
            return _warning("Добавьте 1–2 факта: для кого проект, что делает партнер и где это произойдет.", covered_by_fields=covered_by_fields)

    if module_slug == "presentation" and field_key == "project_description" and len(text) < 500:
        return _warning("Материала мало. Можно запускать, но добавьте идею, аудиторию, сроки и результаты, если они есть.", covered_by_fields=covered_by_fields)

    if module_slug == "scenario-plan" and field_key in {"participants", "schedule"} and not _has_digits(text):
        return _warning("Добавьте количество участников или зрителей, если оно уже известно.", covered_by_fields=covered_by_fields)

    return _success(covered_by_fields)


def _success(covered_by_fields: list[str] | None = None) -> dict:
    return {
        "status": "success",
        "should_block": False,
        "message": "",
        "suggestions": [],
        "covered_by_fields": covered_by_fields or [],
        "rewrite_suggestion": None,
    }


def _warning(
    message: str,
    suggestions: list[dict] | None = None,
    covered_by_fields: list[str] | None = None,
) -> dict:
    return {
        "status": "warning",
        "should_block": False,
        "message": _limit(message),
        "suggestions": (suggestions or [_dismiss()])[:3],
        "covered_by_fields": covered_by_fields or [],
        "rewrite_suggestion": None,
    }


def _error(
    message: str,
    suggestions: list[dict] | None = None,
    covered_by_fields: list[str] | None = None,
) -> dict:
    return {
        "status": "error",
        "should_block": True,
        "message": _limit(message),
        "suggestions": (suggestions or [])[:3],
        "covered_by_fields": covered_by_fields or [],
        "rewrite_suggestion": None,
    }


def _suggest(suggestion_id: str, label: str, text: str) -> dict:
    return {"id": suggestion_id, "label": label, "operation": "suggest_text", "text": text}


def _dismiss() -> dict:
    return {"id": "keep_current", "label": "Оставить так", "operation": "dismiss", "text": ""}


def _limit(message: str) -> str:
    return message[:140]


def _string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _official_language_hint(field_key: str, text: str) -> dict | None:
    if field_key not in {"partner_name", "partner_intro_block", "project_title", "support_details", "signatory"}:
        return None
    scan = _normalize_for_scan(text)
    offensive = ["негр", "хач", "чурк", "пидор", "пида", "хуй", "хуе", "пизд", "еба", "ебл", "бля", "сука"]
    if any(item in scan for item in offensive):
        return _error("Исправьте формулировку: письмо поддержки должно быть официальным и корректным.")

    testish = ["кринж", "кринжульки", "asdf", "ыва"]
    if any(item in scan for item in testish) or re.fullmatch(r"(тест|test)(\s+\d+)?", scan):
        return _warning("Проверьте официальность формулировок: письмо поддержки будет загружаться в заявку ПФКИ.")

    informal_signatory = ["адмирал", "генералиссимус", "повелитель", "магистр", "рыбаков олегинс"]
    if field_key == "signatory" and any(item in scan for item in informal_signatory):
        return _warning("Проверьте официальность формулировок: письмо поддержки будет загружаться в заявку ПФКИ.")

    return None


def _normalize_for_scan(value: str) -> str:
    text = str(value or "").lower().replace("ё", "е")
    text = re.sub(r"[«»„“\"'`]+", "", text)
    text = re.sub(r"[^0-9a-zа-я]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _word_count(value: str) -> int:
    return len([part for part in re.split(r"\s+", value.strip()) if part])


def _is_broad_target_group(value: str) -> bool:
    normalized = value.strip().lower().replace("ё", "е")
    return normalized in {"молодежь", "дети", "жители", "люди", "население", "общество"}


def _has_age(value: str) -> bool:
    return bool(re.search(r"\d{1,2}\s*[–—-]\s*\d{1,2}|\d{1,2}\+|\b\d{1,2}\s*(лет|года|год)\b", value, re.IGNORECASE))


def _has_territory(value: str, context: dict[str, str]) -> bool:
    text = f"{value} {context.get('region', '')} {context.get('region_value', '')}".lower()
    return bool(
        re.search(
            r"республика|область|край|город|г\.|район|поселок|посёлок|село|деревня|москва|санкт-петербург|казань|екатеринбург|краснодар|татарстан",
            text,
            re.IGNORECASE,
        )
    )


def _is_regional_legal_search(program_level: str) -> bool:
    lower = program_level.lower()
    return "регион" in lower and "только федераль" not in lower


def _to_float(value: str) -> float:
    cleaned = re.sub(r"[^\d,.\-]", "", value).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _has_letters(value: str) -> bool:
    return bool(re.search(r"[a-zа-яё]", value, re.IGNORECASE))


def _has_digits(value: str) -> bool:
    return bool(re.search(r"\d", value))
