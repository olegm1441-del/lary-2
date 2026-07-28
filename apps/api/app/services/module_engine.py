from pathlib import Path
import re
from uuid import uuid4

from app.core.config import settings
from app.data.modules import get_module
from app.services.ai_router import AiRouterError, generate_with_gigachat
from app.services.file_generators import generate_docx, generate_pdf, generate_pptx
from app.services.module_inputs import normalize_inputs, primary_project_label
from app.services.run_store import StoredRun, run_store
from app.services.support_letter import SupportLetterDocument, build_support_letter_document
from app.services.social_research import build_social_research_document
from app.services.scenario_plan import build_scenario_plan_document


def create_module_run(module_slug: str, inputs: dict, presentation_variant: str | None = None) -> StoredRun:
    module = get_module(module_slug)
    if not module or module["status"] != "active":
        raise ValueError("Такой модуль пока недоступен.")

    inputs = normalize_inputs(module_slug, inputs)
    _validate_module_create_inputs(module_slug, inputs)

    if module_slug == "support-letter":
        return _create_support_letter_run(module, inputs)
    if module_slug == "social-research":
        return _create_social_research_run(module, inputs)
    if module_slug == "scenario-plan":
        return _create_scenario_plan_run(module, inputs)

    run_id = str(uuid4())
    title = _result_title(module, inputs)
    sections = _build_sections(module_slug, inputs, presentation_variant)
    summary = _build_summary(module, inputs)
    sections = _enrich_with_ai(module_slug, inputs, sections)

    run_dir = Path(settings.file_storage_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {}
    downloads: dict[str, str] = {}

    if "docx" in module["output_formats"]:
        path = run_dir / f"{module_slug}.docx"
        generate_docx(path, title, summary, sections)
        files["docx"] = str(path)
        downloads["docx"] = f"/api/module-runs/{run_id}/download/docx"

    if "pdf" in module["output_formats"]:
        path = run_dir / f"{module_slug}.pdf"
        generate_pdf(path, title, summary, sections)
        files["pdf"] = str(path)
        downloads["pdf"] = f"/api/module-runs/{run_id}/download/pdf"

    if "pptx" in module["output_formats"]:
        path = run_dir / f"{module_slug}.pptx"
        generate_pptx(path, title, summary, sections, presentation_variant or "grant_defense")
        files["pptx"] = str(path)
        downloads["pptx"] = f"/api/module-runs/{run_id}/download/pptx"

    return run_store.save(
        StoredRun(
            run_id=run_id,
            module_slug=module_slug,
            title=title,
            status="completed",
            summary=summary,
            sections=sections,
            downloads=downloads,
            files=files,
        )
    )


def _create_social_research_run(module: dict, inputs: dict) -> StoredRun:
    run_id = str(uuid4())
    run_dir = Path(settings.file_storage_dir) / run_id
    path = run_dir / "Анализ социальной значимости.docx"
    document = build_social_research_document(inputs, output_path=path)
    summary = "Доказательный материал собран из проверенных источников. Перед подачей сопоставьте выводы с фактическими данными проекта."
    return run_store.save(
        StoredRun(
            run_id=run_id,
            module_slug="social-research",
            title=document.output.document_title,
            status="completed",
            summary=summary,
            sections=document.sections,
            downloads={"docx": f"/api/module-runs/{run_id}/download/docx"},
            files={"docx": str(path)},
        )
    )


def _create_scenario_plan_run(module: dict, inputs: dict) -> StoredRun:
    run_id = str(uuid4())
    run_dir = Path(settings.file_storage_dir) / run_id
    path = run_dir / "Сценарный план.docx"
    document = build_scenario_plan_document(inputs, output_path=path)
    return run_store.save(
        StoredRun(
            run_id=run_id,
            module_slug="scenario-plan",
            title=document.output.document_title,
            status="completed",
            summary="Сценарный план проверен по таймингам и подготовлен для ручной сверки с календарным планом проекта.",
            sections=document.sections,
            downloads={"docx": f"/api/module-runs/{run_id}/download/docx"},
            files={"docx": str(path)},
        )
    )


def _create_support_letter_run(module: dict, inputs: dict) -> StoredRun:
    document = build_support_letter_document(inputs)
    run_id = str(uuid4())
    run_dir = Path(settings.file_storage_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / document.filename
    path.write_bytes(document.docx_bytes)

    title = f"{module['title']}: {document.normalized.project_title}"
    summary = "Письмо поддержки готово. Перед загрузкой в заявку проверьте текст, дату, исходящий номер, подпись и печать при наличии."
    sections = _support_letter_sections(document)
    downloads = {"docx": f"/api/module-runs/{run_id}/download/docx"}
    files = {"docx": str(path)}

    return run_store.save(
        StoredRun(
            run_id=run_id,
            module_slug="support-letter",
            title=title,
            status="completed",
            summary=summary,
            sections=sections,
            downloads=downloads,
            files=files,
        )
    )


def _support_letter_sections(document: SupportLetterDocument) -> list[dict[str, str]]:
    payload = document.normalized
    return [
        {
            "title": "Письмо поддержки готово",
            "body": "Скачайте DOCX, распечатайте письмо, укажите дату и исходящий номер, подпишите и поставьте печать при наличии.",
        },
        {
            "title": "Партнер и проект",
            "body": "\n".join(
                [
                    f"Партнер: {payload.partner_name}.",
                    f"Описание партнера: {payload.partner_intro_block}.",
                    f"Проект: {payload.project_title}.",
                ]
            ),
        },
        {
            "title": "Вклад партнера",
            "body": "\n".join(
                [
                    f"Вид поддержки: {'; '.join(payload.support_types)}.",
                    f"Описание поддержки: {payload.support_details}.",
                    f"Оценка вклада: {payload.cofinance.formatted} рублей.",
                ]
            ),
        },
        {
            "title": "Что проверить перед загрузкой",
            "body": "Проверьте, что письмо напечатано на бланке партнера при наличии, подписант указан корректно, а сумма вклада совпадает с бюджетом и софинансированием заявки.",
        },
    ]


def _validate_module_create_inputs(module_slug: str, inputs: dict[str, str]) -> None:
    if module_slug != "salary":
        return

    if not str(inputs.get("role") or "").strip():
        raise ValueError("Укажите должность или нажмите «Не знаю».")

    months = _to_positive_float(inputs.get("months"))
    if months is None:
        raise ValueError("Срок работы должен быть больше нуля.")

    employee_count = _to_positive_float(inputs.get("employee_count"))
    if employee_count is None and "workload" not in inputs:
        raise ValueError("Укажите количество сотрудников в этой роли.")

    employment_percent = _to_positive_float(inputs.get("employment_percent"))
    if employment_percent is None and "workload" not in inputs:
        raise ValueError("Укажите занятость одного сотрудника в процентах.")
    if employment_percent is not None and employment_percent > 100:
        raise ValueError("Занятость одного сотрудника не может быть больше 100%.")


def _to_positive_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = str(value).replace(",", ".").strip()
    if not cleaned:
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number if number > 0 else None


def improve_run(run_id: str, instruction: str) -> StoredRun:
    run = run_store.get(run_id)
    if not run:
        raise KeyError(run_id)

    improved_sections = run.sections + [
        {
            "title": "Улучшение результата",
            "body": f"Запрос на улучшение: {instruction}. Текст следует перечитать и адаптировать под фактические данные проекта.",
        }
    ]
    updated = StoredRun(
        run_id=run.run_id,
        module_slug=run.module_slug,
        title=run.title,
        status=run.status,
        summary=run.summary,
        sections=improved_sections,
        downloads=run.downloads,
        files=run.files,
        created_at=run.created_at,
    )
    return run_store.save(updated)


def _result_title(module: dict, inputs: dict) -> str:
    project = primary_project_label(inputs)
    return f"{module['title']}: {project}"


def _build_summary(module: dict, inputs: dict) -> str:
    project = primary_project_label(inputs)
    region = inputs.get("region") or inputs.get("region_value") or "выбранная территория"
    return f"Рабочий результат модуля «{module['title']}» для проекта «{project}» в контексте ПФКИ. Территория: {region}."


def _build_sections(module_slug: str, inputs: dict, presentation_variant: str | None) -> list[dict[str, str]]:
    project = primary_project_label(inputs)
    direction = str(inputs.get("direction") or "").strip()
    region = str(inputs.get("region") or "территория проекта").strip()
    target_group = str(inputs.get("target_group") or "целевая группа").strip()
    problem = str(inputs.get("problem") or inputs.get("project_description") or inputs.get("description") or "описание нужно уточнить").strip()
    calendar_items = str(inputs.get("calendar_items") or "").strip()
    calendar_note = calendar_items or "ВСТАВЬТЕ НОМЕРА МЕРОПРИЯТИЙ КАЛЕНДАРНОГО ПЛАНА"

    base = [
        {"title": "Проект", "body": _project_body(project, direction, region)},
        {"title": "Целевая группа", "body": f"Основная аудитория: {_sentence(target_group)}"},
        {"title": "Актуальность", "body": f"Проблема или потребность: {_sentence(problem)}"},
    ]

    specific: dict[str, list[dict[str, str]]] = {
        "social-research": [
            {"title": "Доказательная база", "body": f"Ищите данные по теме «{direction or project}» для территории «{region}»: официальная статистика, региональные данные, исследования, ВЦИОМ/ФОМ/Росстат или профильные источники."},
        ],
        "legal-acts": [
            {"title": "Запрос на подбор НПА", "body": "\n".join([
                f"Тема поиска: {direction or project}.",
                f"Территория: {region}.",
                f"Целевая группа: {target_group}.",
                f"Уровень поиска: {inputs.get('program_level') or 'федеральный, региональный и муниципальный уровень'}.",
            ])},
            {"title": "Что должно попасть в подборку", "body": "Федеральные акты и программы, региональные документы выбранного субъекта, муниципальные документы выбранного города или района, а также официальные программы в сфере культуры, молодежной политики и доступности культурных мероприятий."},
        ],
        "salary": [
            {"title": "Расчет", "body": "\n".join([
                f"Должность: {inputs.get('role') or project}.",
                f"Срок работы: {inputs.get('months') or 'уточнить'} мес.",
                f"Количество сотрудников в этой роли: {inputs.get('employee_count') or 'уточнить'}.",
                f"Занятость одного сотрудника: {inputs.get('employment_percent') or 'уточнить'}%.",
                f"Занятость в часах: {inputs.get('employment_hours') or 'не указана'}.",
                f"Мероприятия календарного плана: {calendar_note}.",
            ])},
            {"title": "Формула", "body": "Средняя месячная ставка по должности × занятость одного сотрудника в процентах × срок работы в месяцах × количество сотрудников."},
            {"title": "Обоснование должности", "body": str(inputs.get("functionality") or "Опишите функционал сотрудника и связь с мероприятиями календарного плана.")},
            {"title": "Что проверить вручную", "body": "Источник средней зарплаты по региону, корректность процента занятости, номера мероприятий календарного плана и соответствие суммы бюджету заявки."},
        ],
        "support-letter": [
            {"title": "Ключевые смыслы и значимость проекта", "body": str(inputs.get("value_keywords") or "Опишите, для кого и почему партнер поддерживает проект.")},
            {"title": "Вклад партнера", "body": "\n".join([
                f"Вид поддержки: {inputs.get('support_types') or 'уточнить'}",
                f"Оценка вклада, рублей: {inputs.get('cofinance_block') or 'уточнить'}",
                f"Что именно делает партнер: {inputs.get('support_details') or 'не указано'}",
            ])},
            {"title": "Чек-лист оформления", "body": "Проверьте подпись, печать, дату, исходящий номер, реквизиты и корректного адресата конкурса."},
        ],
        "presentation": [
            {"title": "Решение", "body": "Презентация собирает идею, актуальность, аудиторию, механику, календарь, команду, результаты и бюджетную логику."},
            {"title": "Формат презентации", "body": "\n".join([
                "Вариант: демонстрация календарного плана." if presentation_variant == "calendar_plan" else "Вариант: защита заявки и демонстрация ценности проекта.",
                f"Шаблон: {inputs.get('visual_style') or 'официальный'}.",
                f"Количество слайдов: {inputs.get('slide_count') or 'Лари выберет'}.",
            ])},
        ],
        "scenario-plan": [
            {"title": "Сценарная структура", "body": "Разбейте событие на блоки: подготовка, вход участника, основная часть, финал, контрольные точки."},
            {"title": "Неизвестные параметры", "body": "Предложения Лари по судьям, ролям, переходам и длительности нужно проверить вручную."},
        ],
    }
    return base + specific.get(module_slug, [])


def _project_body(project: str, direction: str, region: str) -> str:
    lines = [f"Название или рабочая тема: {project}."]
    if direction and direction != project:
        lines.append(f"Основное направление: {direction}.")
    lines.append(f"Территория: {region}.")
    return "\n".join(lines)


def _sentence(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return "не указано."
    return cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."


def _enrich_with_ai(module_slug: str, inputs: dict, sections: list[dict[str, str]]) -> list[dict[str, str]]:
    if not settings.gigachat_credentials:
        return sections

    prompt = _build_ai_prompt(module_slug, inputs)
    try:
        text = generate_with_gigachat(prompt)
    except AiRouterError:
        return sections
    except Exception:
        return sections

    return sections + _parse_ai_sections(module_slug, text)


def _build_ai_prompt(module_slug: str, inputs: dict) -> str:
    shared_rules = (
        "Ты — эксперт по заявкам ПФКИ. Подготовь текстовые блоки результата для выбранного модуля.\n"
        "Формат ответа строго такой, без Markdown и без дополнительных комментариев:\n"
        "РАЗДЕЛ: Название раздела\n"
        "ТЕКСТ: Готовый текст раздела для вставки в рабочий документ.\n\n"
        "РАЗДЕЛ: Название следующего раздела\n"
        "ТЕКСТ: Готовый текст следующего раздела.\n\n"
        "Запрещено использовать символы **, ###, ---, слово «Краткое описание» и технический заголовок «AI-уточнение».\n"
        "Не пиши воду и объяснения о том, что нужно сделать. Пиши готовый текст.\n"
        "Не выдумывай точные номера, даты и реквизиты документов. Если реквизит не гарантирован, напиши «проверить реквизиты на официальном источнике».\n"
        f"Данные пользователя: {inputs}.\n"
    )
    module_rules = {
        "social-research": (
            "Нужны разделы: Социальная проблема, Целевая группа, Доказательная база, Обоснование социальной значимости, Что проверить вручную. "
            "В доказательной базе перечисли типы официальных источников и какие показатели искать по территории."
        ),
        "legal-acts": (
            "Нужна подборка нормативных документов по теме проекта. Обязательно сделай разделы: Федеральный уровень, Региональный уровень, Муниципальный уровень, "
            "Программы и стратегии, Как использовать в заявке. В каждом разделе давай названия актов, программ, постановлений или официальных порталов, "
            "их уровень, официальный источник проверки и связь с темой проекта/целевой группой/территорией. Не указывай номера, даты и реквизиты актов, если они не даны пользователем. "
            "Для темы Пушкинской карты учитывай именно федеральный проект/программу «Пушкинская карта», молодежь, культуру, посещение учреждений культуры, музеи и регион/город пользователя. "
            "Не подменяй «Пушкинскую карту» социальной картой."
        ),
        "salary": (
            "Нужны разделы: Расчет, Формула, Обоснование должности, Занятость и количество людей, Что проверить вручную. "
            "Не добавляй предложения по оптимизации, если пользователь не просил."
        ),
        "support-letter": (
            "Нужны разделы: Партнер и проект, Значимость проекта, Вклад партнера, Чек-лист оформления. "
            "Пиши как рабочую заготовку письма поддержки без подписи и без выдуманных реквизитов."
        ),
        "presentation": (
            "Нужны разделы: Структура презентации, Слайды 1-3, Слайды 4-7, Слайды 8-12, Визуальные акценты. "
            "Пиши конкретное содержание слайдов без технических пояснений."
        ),
        "scenario-plan": (
            "Нужны разделы: Логика события, Блоки сценария, Роли и переходы, Тайминг, Что проверить вручную. "
            "Пиши рабочий сценарный план, а не общие рекомендации."
        ),
    }
    return shared_rules + "\n" + module_rules.get(module_slug, "Сделай 4-6 смысловых разделов по модулю, готовых для вставки в документ.")


def _parse_ai_sections(module_slug: str, text: str) -> list[dict[str, str]]:
    cleaned = _clean_ai_text(text)
    if not cleaned:
        return []

    sections: list[dict[str, str]] = []
    current_title: str | None = None
    current_body: list[str] = []

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        title = _extract_ai_title(line)
        if title:
            if current_title and current_body:
                sections.append({"title": current_title, "body": _clean_ai_text("\n".join(current_body))[:2500]})
            current_title = title
            current_body = []
            continue

        if line.lower().startswith("текст:"):
            line = line.split(":", 1)[1].strip()
        if line:
            current_body.append(line)

    if current_title and current_body:
        sections.append({"title": current_title, "body": _clean_ai_text("\n".join(current_body))[:2500]})

    if not sections:
        return [_postprocess_ai_section(module_slug, {"title": _fallback_ai_title(module_slug), "body": cleaned[:2500]})]
    return [_postprocess_ai_section(module_slug, section) for section in sections if section["title"] != "AI-уточнение"][:6]


def _extract_ai_title(line: str) -> str | None:
    normalized = _clean_ai_line(line).strip(": ")
    lowered = normalized.lower()
    if lowered.startswith("разделы заявки") or lowered.startswith("текст:"):
        return None
    if lowered.startswith("раздел:"):
        return normalized.split(":", 1)[1].strip()
    heading = re.match(r"^(?:#{1,6}\s*)?(?:\d+[.)]\s*)?(.+)$", normalized)
    if heading and (line.lstrip().startswith("#") or re.match(r"^\d+[.)]\s+", normalized)):
        title = heading.group(1).strip(": ")
        if len(title) <= 80 and not title.endswith("."):
            return title
    return None


def _clean_ai_text(text: str) -> str:
    lines = []
    for raw_line in str(text or "").replace("\r", "\n").split("\n"):
        line = _clean_ai_line(raw_line)
        if not line or line == "---":
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _clean_ai_line(line: str) -> str:
    cleaned = str(line or "").strip()
    cleaned = cleaned.replace("**", "").replace("###", "").replace("##", "").replace("#", "")
    cleaned = cleaned.replace("Краткое описание:", "").replace("краткое описание:", "")
    cleaned = re.sub(r"^\s*[-–—]\s*$", "", cleaned)
    return cleaned.strip()


def _postprocess_ai_section(module_slug: str, section: dict[str, str]) -> dict[str, str]:
    if module_slug != "legal-acts":
        return section

    body = section["body"]
    body = re.sub(r"\s*№\s*от\s*__\.___\.20__\s*г\.,?", " (реквизиты проверить на официальном источнике)", body)
    body = re.sub(r"\s*№\s*[_.…]*\s*от\s*[_\s.]+(?:года|г\.)?", " (реквизиты проверить на официальном источнике)", body)
    body = re.sub(r"№\s*[_.…]+", "(реквизиты проверить на официальном источнике)", body)
    body = re.sub(r"от\s*[_\s.]{3,}\s*(?:года|г\.)?", "реквизиты проверить на официальном источнике", body)
    body = re.sub(r"<[^>\n]+>", "официальный сайт органа власти", body)
    body = re.sub(r"\s{2,}", " ", body)
    body = body.replace("источник: официальный сайт органа власти", "источник: официальный сайт органа власти")
    return {"title": section["title"], "body": body.strip()}


def _fallback_ai_title(module_slug: str) -> str:
    return {
        "social-research": "Обоснование социальной значимости",
        "legal-acts": "Нормативные акты и программы по теме",
        "salary": "Расчет и обоснование",
        "support-letter": "Рабочий текст письма поддержки",
        "presentation": "Структура презентации",
        "scenario-plan": "Сценарный план",
    }.get(module_slug, "Дополнение к результату")
