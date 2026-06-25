MODULES = [
    {
        "slug": "social-research",
        "status": "active",
        "title": "Анализ социальной значимости",
        "task_title": "Собрать доказательства актуальности",
        "duration": "4-7 минут",
        "competition": "ПФКИ",
        "output_formats": ["docx"],
        "fields": ["region", "direction", "target_group", "problem", "details"],
    },
    {
        "slug": "legal-acts",
        "status": "active",
        "title": "Нормативные акты и программы",
        "task_title": "Найти правовую основу проекта",
        "duration": "3-6 минут",
        "competition": "ПФКИ",
        "output_formats": ["docx"],
        "fields": ["program_level", "region", "direction", "target_group", "details"],
    },
    {
        "slug": "salary",
        "status": "active",
        "title": "Расчет зарплаты и обоснования",
        "task_title": "Рассчитать зарплату",
        "duration": "5-8 минут",
        "competition": "ПФКИ",
        "output_formats": ["docx"],
        "fields": ["role", "region", "functionality", "months", "workload", "calendar_items", "cofunding"],
    },
    {
        "slug": "support-letter",
        "status": "active",
        "title": "Письмо поддержки или коммерческое предложение",
        "task_title": "Сделать письмо поддержки",
        "duration": "4-7 минут",
        "competition": "ПФКИ",
        "output_formats": ["docx"],
        "fields": ["competition", "partner_role", "partner", "project_title", "target_value", "region_value", "contribution"],
    },
    {
        "slug": "presentation",
        "status": "active",
        "title": "Презентация проекта",
        "task_title": "Собрать презентацию",
        "duration": "10-12 минут",
        "competition": "ПФКИ",
        "output_formats": ["pptx"],
        "fields": ["presentation_variant", "project_description", "visual_style", "calendar_plan", "details"],
    },
    {
        "slug": "scenario-plan",
        "status": "active",
        "title": "Сценарный план",
        "task_title": "Составить сценарный план",
        "duration": "6-10 минут",
        "competition": "ПФКИ",
        "output_formats": ["docx"],
        "fields": ["scenario_type", "description", "duration", "preparation", "participants", "details"],
    },
    {
        "slug": "check-application",
        "status": "coming_soon",
        "title": "Проверка готовой заявки",
        "task_title": "Проверить готовую заявку",
        "duration": "Скоро",
        "competition": "ПФКИ",
        "output_formats": ["docx"],
        "fields": ["file", "competition", "focus_sections", "email"],
    },
]


def get_modules() -> list[dict]:
    return MODULES


def get_module(slug: str) -> dict | None:
    return next((item for item in MODULES if item["slug"] == slug), None)
