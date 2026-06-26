from app.data.modules import get_module
from app.services.module_inputs import normalize_inputs


def validate_module_inputs(module_slug: str, inputs: dict | None) -> dict:
    module = get_module(module_slug)
    if not module or module["status"] != "active":
        raise ValueError("Такой модуль пока недоступен.")

    normalized = normalize_inputs(module_slug, inputs)
    hints = _common_hints(normalized)

    if module_slug == "salary":
        hints.extend(_salary_hints(normalized))
    if module_slug == "legal-acts" and not normalized.get("program_level"):
        hints.append(_hint("program_level", "Выберите, искать федеральные документы, региональные или оба варианта."))
    if module_slug == "presentation" and not normalized.get("project_description"):
        hints.append(_hint("project_description", "Добавьте 2-3 предложения о проекте: формат, участники, итоговое событие."))

    return {
        "module_slug": module_slug,
        "status": "needs_attention" if hints else "ready",
        "hints": hints,
    }


def _common_hints(inputs: dict[str, str]) -> list[dict[str, str]]:
    hints: list[dict[str, str]] = []
    region = inputs.get("region") or inputs.get("region_value") or ""
    target_group = inputs.get("target_group") or ""
    problem = inputs.get("problem") or inputs.get("description") or inputs.get("project_description") or ""

    if region and _looks_like_region_only(region):
        hints.append(_hint("region", "Если проект муниципальный, укажите город или район. Это сделает результат точнее."))
    if target_group and _is_too_broad_target_group(target_group):
        hints.append(_hint("target_group", "Уточните целевую группу: возраст, статус или территория помогут сделать результат точнее."))
    if problem and len(problem) < 45:
        hints.append(_hint("problem", "Добавьте 1-2 детали: что именно не так сейчас, где это происходит и кого касается."))

    return hints


def _salary_hints(inputs: dict[str, str]) -> list[dict[str, str]]:
    hints: list[dict[str, str]] = []
    employment_percent = _to_float(inputs.get("employment_percent"))
    if employment_percent is not None and employment_percent > 100:
        hints.append(_hint("employment_percent", "Занятость одного человека не может быть больше 100%. Если людей несколько, укажите количество сотрудников отдельно."))
    employee_count = _to_float(inputs.get("employee_count"))
    if employee_count is not None and employee_count <= 0:
        hints.append(_hint("employee_count", "Количество сотрудников должно быть больше нуля."))
    months = _to_float(inputs.get("months"))
    if months is not None and months <= 0:
        hints.append(_hint("months", "Срок работы должен быть больше нуля."))
    if not inputs.get("calendar_items"):
        hints.append(_hint("calendar_items", "Если номера мероприятий пока неизвестны, Лари оставит место для ручной вставки."))
    return hints


def _looks_like_region_only(value: str) -> bool:
    lower = value.lower()
    region_markers = ("республика", "область", "край", "округ", "татарстан", "башкортостан", "удмуртия")
    city_markers = ("город", "г.", "район", "село", "поселок", "посёлок", "деревня", "казань", "екатеринбург", "москва")
    return any(marker in lower for marker in region_markers) and not any(marker in lower for marker in city_markers)


def _is_too_broad_target_group(value: str) -> bool:
    lower = value.lower().strip()
    broad_values = {"дети", "подростки", "молодежь", "молодёжь", "семьи", "взрослые", "пенсионеры", "люди"}
    return lower in broad_values or len(lower) < 12


def _hint(field_key: str, message: str, tone: str = "attention") -> dict[str, str]:
    return {"field_key": field_key, "message": message, "tone": tone}


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = str(value).replace(",", ".").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None
