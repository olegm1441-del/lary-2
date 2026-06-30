from app.data.modules import get_module
from typing import Any


FIELD_ALIASES = {
    "регион": "region",
    "основное_направление": "direction",
    "целевая_группа": "target_group",
    "описание_проблемы": "problem",
    "дополнительные_сведения": "details",
    "уровень_поиска": "program_level",
    "должность": "role",
    "функционал": "functionality",
    "срок_работы": "months",
    "занятость_и_количество_людей": "workload",
    "количество_сотрудников_в_этой_роли": "employee_count",
    "занятость_одного_сотрудника_%": "employment_percent",
    "занятость_одного_сотрудника": "employment_percent",
    "занятость_в_часах": "employment_hours",
    "мероприятия_календарного_плана": "calendar_items",
    "софинансирование": "cofunding",
    "конкурс": "contest",
    "вид_поддержки": "support_types",
    "партнер": "partner_name",
    "организация_партнера": "partner_name",
    "название_партнера": "partner_name",
    "кто_партнер_и_чем_занимается": "partner_intro_block",
    "название_проекта": "project_title",
    "необходимость_проекта": "value_keywords",
    "значение_для_территории": "value_keywords",
    "ключевые_смыслы_и_значимость_проекта": "value_keywords",
    "вклад_партнера": "support_details",
    "тип_поддержки": "support_types",
    "что_именно_делает_партнер": "support_details",
    "вклад_в_рублях": "cofinance_block",
    "оценка_вклада,_рублей": "cofinance_block",
    "с_уважением": "signatory",
    "тип_презентации": "presentation_variant",
    "описание_проекта": "project_description",
    "количество_слайдов": "slide_count",
    "структура_или_календарный_план": "calendar_plan",
    "тип_сценария": "scenario_type",
    "краткое_описание": "description",
    "длительность": "duration",
    "подготовка": "preparation",
    "участники": "participants",
}


def normalize_inputs(module_slug: str, inputs: dict | None) -> dict[str, Any]:
    module = get_module(module_slug)
    canonical_fields = set(module["fields"]) if module else set()
    normalized: dict[str, Any] = {}

    for raw_key, raw_value in (inputs or {}).items():
        if raw_value is None:
            continue

        key = str(raw_key)
        canonical_key = key if key in canonical_fields else FIELD_ALIASES.get(_normalize_key(key), key)
        if isinstance(raw_value, list):
            value = [str(item).strip() for item in raw_value if str(item).strip()]
            if not value:
                continue
            normalized[canonical_key] = value
            continue

        value = str(raw_value).strip()
        if not value:
            continue
        normalized[canonical_key] = value

    return normalized


def primary_project_label(inputs: dict[str, Any]) -> str:
    for key in ("project_title", "title", "direction", "project_description", "description", "scenario_type", "role", "partner_name", "partner"):
        value = inputs.get(key)
        if value:
            return str(value)
    return "проект"


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_").replace("-", "_")
