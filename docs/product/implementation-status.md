# Статус реализации LARI 2

Дата обновления: 28 июля 2026.

Статусы: `planned`, `in_progress`, `in_review`, `ready`, `blocked`.

## Фазы

| Фаза | Статус | Что входит | Условие перехода |
| --- | --- | --- | --- |
| 0. Foundation docs | ready | Master architecture, ADR, registry schemas, feature flags, migration plan, product docs | Registry tests проходят; пользовательское поведение не изменено |
| 1. Global shell + multi-contest | in_review | Брендинг, четыре конкурса, selector, matrix, безопасное состояние `preparing`, баланс, common shell, mobile navigation, draft v2, durable files | Production reconciliation и пользовательский плейтест не завершены. Статус `ready` разрешено вернуть только после внешней проверки фактического production-домена, устранения CJM-дефектов, production smoke, передачи сценария ручного плейтеста и подтверждения пользователя |
| 2. Example/help/question marks | planned | Versioned examples, global help, module help, contextual question marks | Фаза 1 принята |
| 3. Expert recommendations | planned | Consent, рекомендации, уточнения, TTL, redaction, admin | Фаза 2 принята |
| 4. Salary | planned | Навигация позиций, partial calculation, competence, verified official source | Подтверждена региональная база Росстата |
| 5. Support letters | planned | Несколько партнеров, отдельные DOCX, ZIP | Фаза 4 или отдельное назначение |
| 6. Actuality | planned | Источники 2024+, URL verification, похожие проекты | Готов ingest snapshot ПФКИ |
| 7. Presentation | blocked | Template-driven PPTX 8–12 слайдов | Нужны PPTX-шаблон и 2–3 референса |
| 8. Other/new modules | planned | Все модули через profiles | Готов common shell |
| 9. Payments/subscriptions | planned | Hardened universal runs, будущие планы за flags | Отдельное решение по тарифам |

## Module–contest profiles

Runtime читает матрицу из `config/product/module-contest-profiles.json`. Backend разрешает генерацию только для профиля `ready`; `preparing` и неизвестные связки отклоняются до AI, создания работы и списания запуска.

| Конкурс | Готовые профили | Готовятся |
| --- | --- | --- |
| ПФКИ | social-research, legal-acts, salary, support-letter, presentation, scenario-plan | check-application |
| Фонд президентских грантов | — | все 7 модулей |
| Росмолодёжь.Гранты | — | все 7 модулей |
| Гранты Первых | — | все 7 модулей |

## Известные ограничения после фазы 1

- Детальные legacy form metadata пока дополняют общий registry на frontend; публичные module/contest metadata имеют один source of truth в `config/product`.
- `example` и `faq` manifests фиксируют legacy packs без versioned файлов. Полные versioned assets и FAQ появятся в фазе 2.
- Методические материалы ФПГ, Росмолодёжь.Гранты и Грантов Первых не переданы; такие профили нельзя переводить в `ready`.
- Payload без `contest_slug` временно трактуется как legacy `pfki`; удаление fallback требует отдельного migration window.
- Additive DB columns остаются при rollback. Runtime возвращается на legacy PFKI через `PRODUCT_REGISTRY_RUNTIME_ENABLED=false`.
