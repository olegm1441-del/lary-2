from __future__ import annotations

import re
from typing import Any

from app.data.modules import get_module


REQUIRED_FIELDS: dict[str, set[str]] = {
    "social-research": {"region", "direction", "target_group", "problem"},
    "legal-acts": {"program_level", "region", "direction", "target_group"},
    "salary": {"role", "region", "functionality", "months", "employee_count", "employment_percent", "cofunding"},
    "support-letter": {"competition", "partner_role", "project_title", "target_value", "region_value", "support_type"},
    "presentation": {"project_description"},
    "scenario-plan": {"scenario_type", "description", "duration", "preparation", "participants"},
}


def analyze_field_quality(module_slug: str, field_key: str, value: Any, form_context: dict[str, Any] | None = None) -> dict:
    module = get_module(module_slug)
    if not module or module["status"] != "active":
        raise ValueError("Такой модуль пока недоступен.")

    context = {str(key): _string(value) for key, value in (form_context or {}).items()}
    text = _string(value)
    field_key = str(field_key)

    if module_slug == "legal-acts" and field_key == "region" and _is_regional_legal_search(context.get("program_level", "")) and not text:
        return _error("Для региональных документов нужен регион.")

    if module_slug == "scenario-plan" and field_key == "scenario_type" and not text:
        return _error("Выберите вид сценарного плана.")

    if not text:
        if module_slug == "support-letter" and field_key == "partner":
            return _warning("Если организация пока неизвестна, оставьте поле пустым и добавьте вручную позже.")
        if module_slug == "support-letter" and field_key == "contribution_amount":
            return _warning("Если сумма неизвестна, Лари оставит место для ручной вставки.")
        if field_key in REQUIRED_FIELDS.get(module_slug, set()):
            return _error("Заполните это поле, чтобы запустить.")
        return _success()

    if field_key in {"problem", "description", "project_description", "functionality", "details"} and _word_count(text) < 10:
        return _warning(
            "Добавьте 1–2 детали: кто участвует, где проходит проект и что нужно подтвердить.",
            ["Добавить территорию", "Оставить так"],
        )

    if field_key == "target_group":
        if _is_broad_target_group(text):
            return _warning(
                "Уточните возраст, статус и территорию. Например: молодежь 18–25 лет из Екатеринбурга.",
                ["Добавить возраст", "Добавить территорию"],
            )
        if not _has_age(text):
            return _warning("Добавьте возраст или диапазон. Например: подростки 12–17 лет.", ["Добавить возраст", "Оставить так"])

    if field_key in {"problem", "description", "project_description"} and not _has_territory(text, context):
        return _warning("Добавьте территорию: регион, город, район или площадку.", ["Добавить территорию", "Оставить так"])

    if module_slug == "salary":
        if field_key == "employee_count" and _to_float(text) <= 0:
            return _error("Количество сотрудников должно быть больше нуля.")
        if field_key == "employment_percent" and (_to_float(text) <= 0 or _to_float(text) > 100):
            return _error("Занятость одного сотрудника не может быть больше 100%.")
        if field_key == "months" and _to_float(text) <= 0:
            return _error("Срок работы должен быть больше нуля.")
        if field_key == "functionality" and _word_count(text) < 10:
            return _warning("Опишите 2–3 обязанности: что делает специалист и к каким мероприятиям относится.")

    if module_slug == "support-letter" and field_key == "contribution_amount" and _has_letters(text) and not _has_digits(text):
        return _error("Укажите вклад числом в рублях или оставьте поле пустым.")

    if module_slug == "presentation" and field_key == "project_description" and len(text) < 500:
        return _warning("Материала мало. Можно запускать, но добавьте идею, аудиторию, сроки и результаты, если они есть.")

    if module_slug == "scenario-plan" and field_key == "participants" and not _has_digits(text):
        return _warning("Добавьте количество участников или зрителей, если оно уже известно.")

    return _success()


def _success() -> dict:
    return {"status": "success", "should_block": False, "message": "", "chips": [], "rewrite_suggestion": None}


def _warning(message: str, chips: list[str] | None = None) -> dict:
    return {"status": "warning", "should_block": False, "message": _limit(message), "chips": (chips or ["Оставить так"])[:3], "rewrite_suggestion": None}


def _error(message: str, chips: list[str] | None = None) -> dict:
    return {"status": "error", "should_block": True, "message": _limit(message), "chips": (chips or [])[:3], "rewrite_suggestion": None}


def _limit(message: str) -> str:
    return message[:140]


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


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
