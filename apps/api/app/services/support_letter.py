from __future__ import annotations

import json
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate

from app.services.ai_router import generate_with_gigachat


USER_FRIENDLY_GENERATION_ERROR = "Не получилось подготовить письмо. Данные сохранены. Попробуйте еще раз через минуту."
SUPPORT_LETTER_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "support_letter_pfki.docx"

SUPPORT_TYPE_OPTIONS = [
    "Информационная поддержка",
    "Организационная поддержка",
    "Экспертная поддержка",
    "Консультационная поддержка",
    "Помещение",
    "Оборудование",
    "Материальная поддержка",
    "Финансовый вклад",
    "Подарки / призы",
    "Полиграфия",
    "Иная поддержка",
]


class SupportLetterValidationError(ValueError):
    pass


class SupportLetterGenerationError(ValueError):
    pass


@dataclass(frozen=True)
class CofinanceValue:
    raw_digits: str
    formatted: str


@dataclass(frozen=True)
class NormalizedSupportLetterPayload:
    contest: str
    project_title: str
    partner_name: str
    partner_intro_block: str
    value_keywords: str
    support_types: list[str]
    support_details: str
    cofinance: CofinanceValue
    signatory: str


@dataclass(frozen=True)
class SupportLetterDocument:
    docx_bytes: bytes
    filename: str
    normalized: NormalizedSupportLetterPayload
    ai_value_block: str
    ai_support_block: str


def build_support_letter_document(inputs: dict[str, Any]) -> SupportLetterDocument:
    payload = normalize_support_letter_payload(inputs)
    ai_value_block = _generate_ai_block(_build_value_prompt(payload), "ai_value_block", 1000)
    ai_support_block = _generate_ai_block(_build_support_prompt(payload), "ai_support_block", 900)
    docx_bytes = render_support_letter_docx(payload, ai_value_block, ai_support_block)

    return SupportLetterDocument(
        docx_bytes=docx_bytes,
        filename=sanitize_filename(payload.partner_name),
        normalized=payload,
        ai_value_block=ai_value_block,
        ai_support_block=ai_support_block,
    )


def render_support_letter_docx(payload: NormalizedSupportLetterPayload, ai_value_block: str, ai_support_block: str) -> bytes:
    if not SUPPORT_LETTER_TEMPLATE.exists():
        raise SupportLetterGenerationError(USER_FRIENDLY_GENERATION_ERROR)

    template = DocxTemplate(str(SUPPORT_LETTER_TEMPLATE))
    template.render(
        {
            "PARTNER_NAME": payload.partner_name,
            "PARTNER_INTRO_BLOCK": payload.partner_intro_block,
            "PROJECT_TITLE": payload.project_title,
            "AI_VALUE_BLOCK": _clean_docx_block(ai_value_block),
            "AI_SUPPORT_BLOCK": _clean_docx_block(ai_support_block),
            "COFINANCE_BLOCK": payload.cofinance.formatted,
            "SIGNATORY": payload.signatory,
        }
    )
    buffer = BytesIO()
    template.save(buffer)
    return buffer.getvalue()


def normalize_support_letter_payload(inputs: dict[str, Any]) -> NormalizedSupportLetterPayload:
    contest = _string(inputs.get("contest") or inputs.get("competition") or "ПФКИ")
    if contest.lower() in {"pfki", "пфки"}:
        contest = "ПФКИ"
    if contest != "ПФКИ":
        raise SupportLetterValidationError("Для этого шаблона выберите конкурс ПФКИ.")

    project_title = normalize_project_title(_required(inputs, "project_title", "Название проекта нужно заполнить."))
    partner_name = normalize_partner_name(_required(inputs, "partner_name", "Введите название партнера."))
    partner_intro_block = normalize_partner_intro(_required(inputs, "partner_intro_block", "Опишите, кто партнер и чем занимается."))
    value_keywords = _required(inputs, "value_keywords", "Добавьте ключевые смыслы проекта: для кого, где и почему проект важен.")
    support_types = normalize_support_types(inputs.get("support_types"))
    support_details = _required(inputs, "support_details", "Опишите, что именно делает партнер.")
    cofinance = normalize_cofinance(_required(inputs, "cofinance_block", "Введите оценку вклада только числом, без слова “рублей”."))
    signatory = normalize_signatory(_required(inputs, "signatory", "Введите строку подписанта для блока “С уважением”."))

    _validate_length(project_title, 3, 180, "Название проекта должно быть от 3 до 180 символов.")
    _validate_length(partner_name, 2, 180, "Название партнера должно быть от 2 до 180 символов.")
    _validate_length(partner_intro_block, 10, 220, "Описание партнера должно быть от 10 до 220 символов.")
    _validate_length(value_keywords, 30, 1200, "Ключевые смыслы проекта должны быть от 30 до 1200 символов.")
    _validate_length(support_details, 30, 1500, "Описание поддержки должно быть от 30 до 1500 символов.")
    _validate_length(signatory, 5, 220, "Подписант должен быть от 5 до 220 символов.")

    return NormalizedSupportLetterPayload(
        contest=contest,
        project_title=project_title,
        partner_name=partner_name,
        partner_intro_block=partner_intro_block,
        value_keywords=value_keywords,
        support_types=support_types,
        support_details=support_details,
        cofinance=cofinance,
        signatory=signatory,
    )


def normalize_partner_name(value: str) -> str:
    return _normalize_guillemets(_collapse_spaces(value))


def normalize_project_title(value: str) -> str:
    cleaned = _collapse_spaces(value)
    cleaned = _strip_outer_quotes(cleaned)
    cleaned = re.sub(r"«([^»]+)»", r"„\1“", cleaned)
    cleaned = _replace_straight_quote_pairs(cleaned, "„", "“")
    return _collapse_spaces(cleaned)


def normalize_partner_intro(value: str) -> str:
    return _collapse_spaces(value).rstrip(".!?:; ")


def normalize_signatory(value: str) -> str:
    return _normalize_guillemets(_collapse_spaces(value))


def normalize_support_types(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_values = [str(item).strip() for item in value]
    else:
        raw_values = re.split(r"[;\n,]+", str(value or ""))

    seen: set[str] = set()
    result: list[str] = []
    for raw in raw_values:
        item = _collapse_spaces(raw)
        if not item:
            continue
        canonical = next((option for option in SUPPORT_TYPE_OPTIONS if option.lower() == item.lower()), item)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)

    if not result:
        raise SupportLetterValidationError("Выберите хотя бы один вид поддержки.")
    return result


def normalize_cofinance(value: str) -> CofinanceValue:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise SupportLetterValidationError("Введите оценку вклада только числом, без слова “рублей”.")
    if re.search(r"[^\d\s]", cleaned) or re.search(r"[A-Za-zА-Яа-яЁё₽]", cleaned):
        raise SupportLetterValidationError("Введите оценку вклада только числом, без слова “рублей”.")

    digits = re.sub(r"\D+", "", cleaned)
    if not digits:
        raise SupportLetterValidationError("Введите оценку вклада только числом, без слова “рублей”.")
    number = int(digits)
    if number <= 0:
        raise SupportLetterValidationError("Оценка вклада должна быть больше нуля.")

    return CofinanceValue(raw_digits=digits, formatted=f"{number:,}".replace(",", " "))


def sanitize_filename(partner_name: str) -> str:
    cleaned = _collapse_spaces(str(partner_name or ""))
    cleaned = cleaned.replace('"', "").replace("'", "")
    cleaned = re.sub(r"[\\/:\*\?<>\|\n\r\t]+", " ", cleaned)
    cleaned = _collapse_spaces(cleaned).strip(" .")
    if not cleaned:
        cleaned = "партнер"
    return f"Письмо поддержки_ПФКИ_{cleaned[:80]}.docx"


def _generate_ai_block(prompt: str, key: str, max_length: int) -> str:
    retry_prompt = (
        f"{prompt}\n\n"
        f"Предыдущий ответ не подошел. Верни только валидный JSON вида {{\"{key}\": \"готовый текст\"}}. "
        "Без Markdown, без комментариев и без дополнительных ключей."
    )
    errors: list[Exception] = []

    for attempt_prompt in (prompt, retry_prompt):
        try:
            raw = generate_with_gigachat(attempt_prompt)
            return _extract_json_field(raw, key, max_length)
        except Exception as exc:  # noqa: BLE001 - provider/parser details are intentionally hidden from users.
            errors.append(exc)

    raise SupportLetterGenerationError(USER_FRIENDLY_GENERATION_ERROR) from errors[-1]


def _build_value_prompt(payload: NormalizedSupportLetterPayload) -> str:
    facts = {
        "project_title": payload.project_title,
        "partner_name": payload.partner_name,
        "partner_intro_block": payload.partner_intro_block,
        "value_keywords": payload.value_keywords,
    }
    return (
        "Ты помогаешь подготовить письмо поддержки проекта для заявки ПФКИ.\n"
        "Составь один готовый абзац или короткий блок о ценности проекта для письма от партнера.\n"
        "Нужно писать от лица партнера во множественном числе: «Видим необходимость проекта...», «Считаем важным...». "
        "Без обращения, без подписи, без суммы, без названия адресата, без Markdown.\n"
        "Факты пользователя не выдумывай и не расширяй точными данными.\n"
        "Верни только валидный JSON с ключом ai_value_block.\n"
        f"Данные: {json.dumps(facts, ensure_ascii=False)}"
    )


def _build_support_prompt(payload: NormalizedSupportLetterPayload) -> str:
    facts = {
        "project_title": payload.project_title,
        "partner_name": payload.partner_name,
        "support_types": payload.support_types,
        "support_details": payload.support_details,
    }
    return (
        "Ты помогаешь подготовить письмо поддержки проекта для заявки ПФКИ.\n"
        "Составь готовое описание поддержки партнера: 1-3 коротких пункта или один компактный абзац. "
        "Используй только выбранные виды поддержки и фактическое описание пользователя. "
        "Без обращения, без подписи, без суммы, без Markdown и без слов о том, что это черновик.\n"
        "Верни только валидный JSON с ключом ai_support_block.\n"
        f"Данные: {json.dumps(facts, ensure_ascii=False)}"
    )


def _extract_json_field(raw: str, key: str, max_length: int) -> str:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]

    data = json.loads(text)
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Missing JSON key: {key}")

    cleaned = _clean_docx_block(value)
    if len(cleaned) < 20:
        raise ValueError(f"JSON field is too short: {key}")
    return cleaned[:max_length].rstrip()


def _clean_docx_block(value: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in str(value or "").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        line = line.replace("**", "").replace("###", "").replace("##", "").replace("#", "")
        line = re.sub(r"^\s*[-–—]\s*$", "", line)
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _required(inputs: dict[str, Any], key: str, message: str) -> str:
    value = _string(inputs.get(key))
    if not value:
        raise SupportLetterValidationError(message)
    return value


def _string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _validate_length(value: str, minimum: int, maximum: int, message: str) -> None:
    length = len(value.strip())
    if length < minimum or length > maximum:
        raise SupportLetterValidationError(message)


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _strip_outer_quotes(value: str) -> str:
    pairs = [("«", "»"), ("„", "“"), ('"', '"'), ("'", "'")]
    cleaned = value.strip()
    changed = True
    while changed and len(cleaned) >= 2:
        changed = False
        for left, right in pairs:
            if cleaned.startswith(left) and cleaned.endswith(right):
                cleaned = cleaned[len(left) : len(cleaned) - len(right)].strip()
                changed = True
    return cleaned


def _normalize_guillemets(value: str) -> str:
    cleaned = _replace_straight_quote_pairs(value, "«", "»")
    cleaned = re.sub(r"„([^“]+)“", r"«\1»", cleaned)
    return cleaned


def _replace_straight_quote_pairs(value: str, left: str, right: str) -> str:
    pieces = str(value).split('"')
    if len(pieces) < 3:
        return value.replace('"', "")

    result: list[str] = []
    for index, piece in enumerate(pieces):
        result.append(piece)
        if index < len(pieces) - 1:
            result.append(left if index % 2 == 0 else right)
    return "".join(result).replace(left + right, "")
