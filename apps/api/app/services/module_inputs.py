from app.data.modules import get_module


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
    "конкурс": "competition",
    "вид_поддержки": "partner_role",
    "партнер": "partner",
    "название_проекта": "project_title",
    "необходимость_проекта": "target_value",
    "значение_для_территории": "region_value",
    "вклад_партнера": "contribution",
    "тип_поддержки": "support_type",
    "вклад_в_рублях": "contribution_amount",
    "стиль_письма": "style",
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


def normalize_inputs(module_slug: str, inputs: dict | None) -> dict[str, str]:
    module = get_module(module_slug)
    canonical_fields = set(module["fields"]) if module else set()
    normalized: dict[str, str] = {}

    for raw_key, raw_value in (inputs or {}).items():
        if raw_value is None:
            continue

        key = str(raw_key)
        value = str(raw_value).strip()
        if not value:
            continue

        canonical_key = key if key in canonical_fields else FIELD_ALIASES.get(_normalize_key(key), key)
        normalized[canonical_key] = value

    return normalized


def primary_project_label(inputs: dict[str, str]) -> str:
    for key in ("project_title", "title", "direction", "project_description", "description", "scenario_type", "role", "partner"):
        value = inputs.get(key)
        if value:
            return value
    return "проект"


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_").replace("-", "_")
