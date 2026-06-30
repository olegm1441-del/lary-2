from __future__ import annotations

import html
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
PLACEHOLDER = "____"

SUPPORT_TYPE_OPTIONS = [
    "Информационная",
    "Консультационная",
    "Организационная",
    "Материальная",
    "Финансовая",
    "Иная",
]

SUPPORT_TYPE_LABELS = {
    "Информационная": "Информационная поддержка",
    "Консультационная": "Консультационная поддержка",
    "Организационная": "Организационная поддержка",
    "Материальная": "Материальная поддержка",
    "Финансовая": "Финансовая поддержка",
    "Иная": "Иная поддержка",
}

FORBIDDEN_PARTNER_RETRY_INSTRUCTION = (
    "Убери формулировки, где организация-партнер выглядит как заявитель или реализатор проекта. "
    "Партнер только оказывает поддержку. Верни JSON по той же схеме."
)

OFFENSIVE_LANGUAGE_PATTERNS = [
    "негр",
    "хач",
    "чурк",
    "пидор",
    "пида",
    "хуй",
    "хуе",
    "пизд",
    "еба",
    "ёба",
    "бля",
    "сука",
]


class SupportLetterValidationError(ValueError):
    pass


class SupportLetterGenerationError(ValueError):
    pass


class ForbiddenPartnerWordingError(ValueError):
    pass


class SupportTypeScopeError(ValueError):
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
    ai_value_block = _generate_ai_block(
        _build_value_prompt(payload),
        "ai_value_block",
        1100,
        lambda text: _validate_ai_block(text, "ai_value_block", 1100, payload.partner_name),
    )
    ai_support_block = _generate_ai_block(
        _build_support_prompt(payload),
        "ai_support_block",
        900,
        lambda text: _validate_support_block(text, payload.partner_name, payload.support_types),
    )
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
        },
        autoescape=True,
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

    project_title = _optional_with_placeholder(inputs, "project_title", normalize_project_title)
    partner_name = _optional_with_placeholder(inputs, "partner_name", normalize_partner_name)
    partner_intro_block = _optional_with_placeholder(inputs, "partner_intro_block", normalize_partner_intro)
    value_keywords = _required(inputs, "value_keywords", "Добавьте ключевые смыслы проекта: для кого, где и почему проект важен.")
    support_types = normalize_support_types(inputs.get("support_types"))
    support_details = _required(inputs, "support_details", "Опишите, что именно делает партнер.")
    cofinance = normalize_cofinance(_string(inputs.get("cofinance_block")))
    signatory = _optional_with_placeholder(inputs, "signatory", normalize_signatory)

    _validate_optional_length(project_title, 3, 180, "Название проекта должно быть от 3 до 180 символов.")
    _validate_optional_length(partner_name, 2, 180, "Название партнера должно быть от 2 до 180 символов.")
    _validate_optional_length(partner_intro_block, 10, 220, "Описание партнера должно быть от 10 до 220 символов.")
    _validate_length(value_keywords, 30, 1200, "Ключевые смыслы проекта должны быть от 30 до 1200 символов.")
    _validate_length(support_details, 30, 1500, "Описание поддержки должно быть от 30 до 1500 символов.")
    _validate_optional_length(signatory, 5, 220, "Подписант должен быть от 5 до 220 символов.")

    _validate_official_language(project_title)
    _validate_official_language(partner_name)
    _validate_official_language(partner_intro_block)
    _validate_official_language(support_details)
    _validate_official_language(signatory)

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
    return _capitalize_inside_quotes(_normalize_guillemets(_collapse_spaces(value)))


def normalize_project_title(value: str) -> str:
    cleaned = _collapse_spaces(value)
    cleaned = _strip_outer_quotes(cleaned)
    cleaned = re.sub(r"«([^»]+)»", r"„\1“", cleaned)
    cleaned = _replace_straight_quote_pairs(cleaned, "„", "“")
    cleaned = _capitalize_first_letter(cleaned)
    cleaned = _capitalize_inside_quotes(cleaned)
    return _collapse_spaces(cleaned)


def normalize_partner_intro(value: str) -> str:
    return _collapse_spaces(value).rstrip(".!?:; ")


def normalize_signatory(value: str) -> str:
    return _capitalize_inside_quotes(_normalize_guillemets(_collapse_spaces(value)))


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
        canonical = next((option for option in SUPPORT_TYPE_OPTIONS if option.lower() == item.lower()), None)
        if canonical is None:
            raise SupportLetterValidationError("Выберите вид поддержки из списка.")
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)

    if not result:
        raise SupportLetterValidationError("Выберите хотя бы один вид поддержки.")
    return result


def normalize_cofinance(value: str) -> CofinanceValue:
    cleaned = str(value or "").strip()
    if not cleaned:
        return CofinanceValue(raw_digits="", formatted=PLACEHOLDER)
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
    if not cleaned or not cleaned.replace("_", "").strip():
        cleaned = "партнер"
    return f"Письмо поддержки_ПФКИ_{cleaned[:80]}.docx"


def _generate_ai_block(prompt: str, key: str, max_length: int, validator) -> str:
    errors: list[Exception] = []
    attempt_prompt = prompt

    for _ in range(2):
        try:
            raw = generate_with_gigachat(attempt_prompt)
            value = _extract_json_field(raw, key, max_length)
            validator(value)
            return value
        except ForbiddenPartnerWordingError as exc:
            errors.append(exc)
            attempt_prompt = f"{prompt}\n\n{FORBIDDEN_PARTNER_RETRY_INSTRUCTION}"
        except SupportTypeScopeError as exc:
            errors.append(exc)
            attempt_prompt = (
                f"{prompt}\n\n"
                "Используй только выбранные виды поддержки. Убери невыбранные виды поддержки. "
                f"Верни только валидный JSON вида {{\"{key}\": \"готовый текст\"}}."
            )
        except Exception as exc:  # noqa: BLE001 - provider/parser details are intentionally hidden from users.
            errors.append(exc)
            attempt_prompt = (
                f"{prompt}\n\n"
                f"Предыдущий ответ не подошел. Верни только валидный JSON вида {{\"{key}\": \"готовый текст\"}}. "
                "Без Markdown, без комментариев и без дополнительных ключей."
            )

    raise SupportLetterGenerationError(USER_FRIENDLY_GENERATION_ERROR) from errors[-1]


def _build_value_prompt(payload: NormalizedSupportLetterPayload) -> str:
    project_title = _prompt_project_title(payload)
    partner_name = _prompt_partner_name(payload)
    partner_intro = "" if payload.partner_intro_block == PLACEHOLDER else payload.partner_intro_block
    return (
        "SYSTEM:\n"
        "Ты профессиональный грантрайтер ПФКИ. Твоя задача — написать короткий официальный блок о значимости проекта для письма поддержки.\n\n"
        "Письмо создается от лица организации-партнера. Организация-партнер поддерживает проект, но НЕ является заявителем и НЕ является организацией, реализующей проект, если это прямо не указано во входных данных.\n\n"
        "Нельзя:\n"
        "- писать, что проект реализуется организацией-партнером;\n"
        "- писать “проект, реализуемый [название партнера]”;\n"
        "- писать, что партнер создает, проводит или организует весь проект;\n"
        "- выдумывать факты, суммы, должности, награды, прошлые партнерства и результаты;\n"
        "- обещать победу в конкурсе или получение гранта;\n"
        "- использовать неподтвержденные слова “уникальный”, “беспрецедентный”, “лучший”, “крупнейший”;\n"
        "- писать общие фразы без связи с целевой группой, территорией или значимостью проекта;\n"
        "- добавлять блок поддержки, подпись, адресата, дату или исходящий номер.\n\n"
        "Пиши официально, коротко, спокойно и конкретно. Не повторяй название организации-партнера без необходимости.\n\n"
        "Верни строго валидный JSON без markdown, комментариев и пояснений.\n\n"
        "Схема ответа:\n"
        "{\n"
        '  "ai_value_block": "..."\n'
        "}\n\n"
        "USER:\n"
        "Составь блок {{AI_VALUE_BLOCK}} для письма поддержки ПФКИ.\n\n"
        "Входные данные:\n"
        f"- Название проекта: {project_title}\n"
        f"- Организация-партнер: {partner_name}\n"
        f"- Кто партнер и чем занимается: {partner_intro}\n"
        f"- Ключевые смыслы и значимость проекта: {payload.value_keywords}\n\n"
        "Требования к блоку:\n"
        "1. Начни строкой: “Видим необходимость проекта в следующем:”\n"
        "2. Далее дай 3 нумерованных пункта.\n"
        "3. Каждый пункт — одно короткое предложение.\n"
        "4. Пункты должны раскрывать влияние проекта на целевую группу: психологическое, социальное, семейное, культурное, образовательное, творческое или территориальное значение.\n"
        "5. После трех пунктов добавь один короткий абзац: “Видим особенным этот проект для нашей территории ...”\n"
        "6. Не пиши, что проект реализуется организацией-партнером.\n"
        "7. Не повторяй название организации-партнера, если без него можно обойтись.\n"
        "8. Не пиши больше 1100 символов.\n"
        "9. Не добавляй приветствие, подпись, адресата, блок поддержки и фразу про софинансирование.\n"
        "10. Если входные данные неполные, используй только то, что есть, и пиши аккуратно без выдумывания.\n\n"
        "Верни только JSON:\n"
        "{\n"
        '  "ai_value_block": "..."\n'
        "}"
    )


def _build_support_prompt(payload: NormalizedSupportLetterPayload) -> str:
    project_title = _prompt_project_title(payload)
    partner_name = _prompt_partner_name(payload)
    support_types = "; ".join(payload.support_types)
    return (
        "SYSTEM:\n"
        "Ты профессиональный грантрайтер ПФКИ. Твоя задача — написать короткий и конкретный блок о поддержке, которую организация-партнер готова оказать проекту.\n\n"
        "Письмо создается от лица организации-партнера. Организация-партнер НЕ является заявителем и НЕ является организацией, реализующей проект, если это прямо не указано во входных данных.\n\n"
        "Нельзя:\n"
        "- писать, что проект реализуется организацией-партнером;\n"
        "- писать “проект, реализуемый [название партнера]”;\n"
        "- писать, что партнер создает, проводит или организует весь проект, если во входных данных указана только поддержка;\n"
        "- выдумывать виды поддержки, суммы, площади, охваты, тиражи, даты, должности и прошлый опыт;\n"
        "- добавлять виды поддержки, которые не выбраны пользователем;\n"
        "- писать фразу про софинансирование;\n"
        "- писать сумму софинансирования, оценку вклада в рублях, денежный эквивалент поддержки или фразу “Оценка вклада”;\n"
        "- добавлять приветствие, подпись, адресата, дату или исходящий номер;\n"
        "- использовать рекламный пафос и канцелярскую воду.\n\n"
        "Пиши официально, коротко и конкретно. Лучше использовать формулировки “готовы оказать”, “готовы предоставить”, “готовы разместить”, “готовы содействовать”, а не “реализуем проект”.\n\n"
        "Верни строго валидный JSON без markdown, комментариев и пояснений.\n\n"
        "Схема ответа:\n"
        "{\n"
        '  "ai_support_block": "..."\n'
        "}\n\n"
        "USER:\n"
        "Составь блок {{AI_SUPPORT_BLOCK}} для письма поддержки ПФКИ.\n\n"
        "Входные данные:\n"
        f"- Название проекта: {project_title}\n"
        f"- Организация-партнер: {partner_name}\n"
        f"- Выбранные виды поддержки: {support_types}\n"
        f"- Что именно делает партнер: {payload.support_details}\n"
        "- Сумма софинансирования не передается в нейросеть: она подставляется в документ отдельно.\n\n"
        "Требования к блоку:\n"
        "1. Напиши только по выбранным видам поддержки.\n"
        "2. Для каждого выбранного вида поддержки сделай отдельный короткий абзац.\n"
        "3. Каждый абзац начинается с названия вида поддержки и двоеточия.\n"
        "4. Формат:\n"
        "   “Информационная поддержка: ...”\n"
        "   “Консультационная поддержка: ...”\n"
        "   “Организационная поддержка: ...”\n"
        "   “Материальная поддержка: ...”\n"
        "   “Финансовая поддержка: ...”\n"
        "   “Иная поддержка: ...”\n"
        "5. В каждом абзаце 2–3 коротких предложения.\n"
        "6. Каждый абзац должен объяснять, что именно партнер готов сделать, предоставить, разместить, организовать, оплатить или обеспечить.\n"
        "7. Не пиши, что проект реализуется организацией-партнером.\n"
        "8. Не повторяй название организации-партнера, если без него можно обойтись.\n"
        "9. Не добавляй невыбранные виды поддержки.\n"
        "10. Не добавляй фразу “Оцениваем наш вклад...” — она уже есть в шаблоне.\n"
        "11. Не пиши сумму софинансирования, оценку вклада, денежный эквивалент поддержки и суммы в рублях.\n"
        "12. Не добавляй приветствие, подпись, адресата, дату, исходящий номер.\n"
        "13. Весь блок — максимум 900 символов.\n"
        "14. Если информации мало, пиши осторожно и не выдумывай детали.\n\n"
        "Верни только JSON:\n"
        "{\n"
        '  "ai_support_block": "..."\n'
        "}"
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

    cleaned = _remove_ai_cofinance_amounts(_clean_docx_block(value))
    if len(cleaned) < 20:
        raise ValueError(f"JSON field is too short: {key}")
    if len(cleaned) > max_length:
        raise ValueError(f"JSON field is too long: {key}")
    return cleaned.rstrip()


def _clean_docx_block(value: str) -> str:
    text = _remove_html_markup(value)
    cleaned_lines: list[str] = []
    for raw_line in text.replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        line = line.replace("**", "").replace("###", "").replace("##", "").replace("#", "")
        line = re.sub(r"^\s*[-–—]\s*$", "", line)
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _remove_ai_cofinance_amounts(value: str) -> str:
    money_token = r"(?:\d[\d\s.,]*|[а-яё]+)\s*(?:тыс\.?|тысяч[аи]?|млн\.?|миллион[а-яё]*)?\s*(?:руб(?:\.|лей|ля|ль)?|₽)"
    forbidden_token = r"(?:оценк[аиу]\s+вклада|сумм[ауы]\s+софинансирования|финансов[а-яё\s]+вклад|денежн[а-яё\s]+эквивалент)"
    money_pattern = re.compile(
        money_token,
        re.IGNORECASE,
    )
    forbidden_terms = re.compile(
        forbidden_token,
        re.IGNORECASE,
    )
    forbidden_money_fragment = re.compile(
        rf"{forbidden_token}[^.!?\n]*?{money_token}\.?",
        re.IGNORECASE,
    )

    cleaned_lines: list[str] = []
    for raw_line in str(value or "").splitlines():
        line = forbidden_money_fragment.sub("", raw_line.strip())
        sentences = re.split(r"(?<=[.!?])\s+", line)
        cleaned_sentences = [
            sentence
            for sentence in sentences
            if sentence
            and not (forbidden_terms.search(sentence) and (money_pattern.search(sentence) or re.search(r"\d", sentence)))
            and not re.fullmatch(r"(?:руб(?:\.|лей|ля|ль)?|₽)[.!?]?", sentence.strip(), re.IGNORECASE)
        ]
        if cleaned_sentences:
            cleaned_lines.append(" ".join(cleaned_sentences))
    return "\n".join(cleaned_lines).strip()


def _remove_html_markup(value: str) -> str:
    text = html.unescape(str(value or "")).replace("\u00a0", " ")
    text = re.sub(r"(?is)<\s*br\s*/?\s*>", "\n", text)
    text = re.sub(r"(?is)</\s*(p|div|li|tr|h[1-6])\s*>", "\n", text)
    text = re.sub(r"(?is)<\s*li(?:\s[^>]*)?>", "- ", text)
    text = re.sub(r"(?is)<[^>\n]{1,200}>", "", text)
    return text


def _required(inputs: dict[str, Any], key: str, message: str) -> str:
    value = _string(inputs.get(key))
    if not value:
        raise SupportLetterValidationError(message)
    return value


def _optional_with_placeholder(inputs: dict[str, Any], key: str, normalizer) -> str:
    value = _string(inputs.get(key))
    if not value:
        return PLACEHOLDER
    normalized = normalizer(value)
    return normalized or PLACEHOLDER


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


def _validate_optional_length(value: str, minimum: int, maximum: int, message: str) -> None:
    if value == PLACEHOLDER:
        return
    _validate_length(value, minimum, maximum, message)


def _validate_official_language(value: str) -> None:
    if not value or value == PLACEHOLDER:
        return
    scan = _normalize_for_scan(value)
    if any(pattern in scan for pattern in OFFENSIVE_LANGUAGE_PATTERNS):
        raise SupportLetterValidationError("Исправьте формулировку: письмо поддержки должно быть официальным и корректным.")


def _validate_ai_block(text: str, key: str, max_length: int, partner_name: str) -> None:
    if len(text) > max_length:
        raise ValueError(f"JSON field is too long: {key}")
    _validate_no_partner_as_implementer(text, partner_name)


def _validate_support_block(text: str, partner_name: str, selected_support_types: list[str]) -> None:
    _validate_ai_block(text, "ai_support_block", 900, partner_name)
    _validate_support_type_scope(text, selected_support_types)


def _validate_no_partner_as_implementer(text: str, partner_name: str) -> None:
    if not partner_name or partner_name == PLACEHOLDER:
        return
    scan = _normalize_for_scan(text)
    partner = re.escape(_normalize_for_scan(partner_name))
    if not partner:
        return
    patterns = [
        rf"реализуем\w*\s+{partner}",
        rf"реализуется\s+{partner}",
        rf"проект\s+котор\w*\s+реализует\s+{partner}",
        rf"{partner}\s+реализует\s+проект",
        rf"{partner}\s+организует\s+проект",
        rf"{partner}\s+создает\s+проект",
        rf"организатор\w*\s+проект\w*\s+{partner}",
    ]
    if any(re.search(pattern, scan) for pattern in patterns):
        raise ForbiddenPartnerWordingError("AI made partner look like project implementer.")


def _validate_support_type_scope(text: str, selected_support_types: list[str]) -> None:
    scan = _normalize_for_scan(text)
    selected_labels = {_normalize_for_scan(SUPPORT_TYPE_LABELS[item]) for item in selected_support_types}
    selected_short_labels = {_normalize_for_scan(f"{item}:") for item in selected_support_types}
    for support_type, label in SUPPORT_TYPE_LABELS.items():
        normalized_label = _normalize_for_scan(label)
        normalized_short = _normalize_for_scan(f"{support_type}:")
        if normalized_label in selected_labels or normalized_short in selected_short_labels:
            continue
        if normalized_label in scan or normalized_short in scan:
            raise SupportTypeScopeError("AI added unselected support type.")


def _prompt_project_title(payload: NormalizedSupportLetterPayload) -> str:
    return "Название проекта не указано" if payload.project_title == PLACEHOLDER else payload.project_title


def _prompt_partner_name(payload: NormalizedSupportLetterPayload) -> str:
    return "Организация-партнер не указана" if payload.partner_name == PLACEHOLDER else payload.partner_name


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


def _capitalize_first_letter(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return match.group(0).upper()

    return re.sub(r"[A-Za-zА-Яа-яЁё]", repl, str(value or ""), count=1)


def _capitalize_inside_quotes(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{_capitalize_first_letter(match.group(2))}{match.group(3)}"

    cleaned = re.sub(r"(«)([^»]+)(»)", repl, str(value or ""))
    cleaned = re.sub(r"(„)([^“]+)(“)", repl, cleaned)
    return cleaned


def _normalize_for_scan(value: str) -> str:
    text = str(value or "").lower().replace("ё", "е")
    text = re.sub(r"[«»„“\"'`]+", "", text)
    text = re.sub(r"[^0-9a-zа-я]+", " ", text)
    return _collapse_spaces(text)


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
