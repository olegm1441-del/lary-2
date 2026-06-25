from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.data.modules import get_module
from app.services.ai_router import AiRouterError, generate_with_gigachat
from app.services.file_generators import generate_docx, generate_pdf, generate_pptx
from app.services.run_store import StoredRun, run_store


def create_module_run(module_slug: str, inputs: dict, presentation_variant: str | None = None) -> StoredRun:
    module = get_module(module_slug)
    if not module or module["status"] != "active":
        raise ValueError("Такой модуль пока недоступен.")

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
    project = str(inputs.get("project_title") or inputs.get("title") or "проект").strip()
    return f"{module['title']}: {project}"


def _build_summary(module: dict, inputs: dict) -> str:
    project = inputs.get("project_title") or inputs.get("title") or "ваш проект"
    region = inputs.get("region") or "выбранная территория"
    return f"Рабочий результат модуля «{module['title']}» для проекта «{project}» в контексте ПФКИ. Территория: {region}."


def _build_sections(module_slug: str, inputs: dict, presentation_variant: str | None) -> list[dict[str, str]]:
    project = str(inputs.get("project_title") or inputs.get("title") or "Проект").strip()
    region = str(inputs.get("region") or "территория проекта").strip()
    target_group = str(inputs.get("target_group") or "целевая группа").strip()
    problem = str(inputs.get("problem") or inputs.get("project_description") or inputs.get("description") or "описание нужно уточнить").strip()

    base = [
        {"title": "Проект", "body": f"Название или рабочая тема: {project}.\nТерритория: {region}."},
        {"title": "Целевая группа", "body": f"Основная аудитория: {target_group}. Уточните возраст, статус и территорию перед подачей."},
        {"title": "Актуальность", "body": f"Проблема или потребность: {problem}. Для финальной заявки нужны проверенные источники и свежие данные."},
    ]

    specific: dict[str, list[dict[str, str]]] = {
        "social-research": [
            {"title": "Доказательная база", "body": "Добавьте официальную статистику, региональные данные, исследования, ВЦИОМ/ФОМ/Росстат или профильные источники."},
            {"title": "Где использовать", "body": "Эти аргументы подходят для разделов актуальности, социальной значимости и описания проблемы."},
        ],
        "legal-acts": [
            {"title": "Правовая основа", "body": "Приоритет: официальные правовые порталы, сайты органов власти и региональные стратегии. Справочные базы нужно проверить вручную."},
            {"title": "Применение в заявке", "body": "К каждому документу добавьте короткое объяснение, почему он подтверждает необходимость проекта."},
        ],
        "salary": [
            {"title": "Формула", "body": "Базовая ставка или средняя зарплата × занятость × срок × количество сотрудников."},
            {"title": "Проверка", "body": "Занятость одного человека не может быть больше 100%. Номера мероприятий календарного плана нужно вставить вручную, если они неизвестны."},
        ],
        "support-letter": [
            {"title": "Социальная значимость", "body": str(inputs.get("target_value") or "Опишите, что меняется для целевой группы и почему партнер поддерживает проект.")},
            {"title": "Вклад партнера", "body": str(inputs.get("contribution") or "Если сумма неизвестна, оставьте формулировку без оценки вклада и проверьте ее с партнером.")},
            {"title": "Чек-лист оформления", "body": "Проверьте подпись, печать, дату, исходящий номер, реквизиты и корректного адресата конкурса."},
        ],
        "presentation": [
            {"title": "Решение", "body": "Презентация собирает идею, актуальность, аудиторию, механику, календарь, команду, результаты и бюджетную логику."},
            {"title": "Формат презентации", "body": "Вариант: демонстрация календарного плана." if presentation_variant == "calendar_plan" else "Вариант: защита заявки и демонстрация ценности проекта."},
        ],
        "scenario-plan": [
            {"title": "Сценарная структура", "body": "Разбейте событие на блоки: подготовка, вход участника, основная часть, финал, контрольные точки."},
            {"title": "Неизвестные параметры", "body": "Предложения Лари по судьям, ролям, переходам и длительности нужно проверить вручную."},
        ],
    }
    return base + specific.get(module_slug, [])


def _enrich_with_ai(module_slug: str, inputs: dict, sections: list[dict[str, str]]) -> list[dict[str, str]]:
    if not settings.gigachat_credentials:
        return sections

    prompt = (
        "Ты эксперт по заявкам ПФКИ. Улучши рабочий результат модуля "
        f"{module_slug}. Не выдумывай источники и факты. Данные пользователя: {inputs}. "
        "Верни 4-6 коротких разделов: название раздела и текст."
    )
    try:
        text = generate_with_gigachat(prompt)
    except AiRouterError:
        return sections
    except Exception:
        return sections

    return sections + [{"title": "AI-уточнение", "body": text[:2500]}]
