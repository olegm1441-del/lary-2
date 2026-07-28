# Статус реализации LARI 2

Дата обновления: 28 июля 2026.

Статусы: `planned`, `in_progress`, `ready`, `blocked`.

## Фазы

| Фаза | Статус | Что входит | Условие перехода |
| --- | --- | --- | --- |
| 0. Foundation docs | ready | Master architecture, ADR, registry schemas, feature flags, migration plan, product docs | Registry tests проходят; пользовательское поведение не изменено |
| 1. Global shell + multi-contest | planned | Брендинг, четыре конкурса, selector, matrix, заглушка, баланс, common shell, mobile navigation | Утвержден план фазы 1 |
| 2. Example/help/question marks | planned | Versioned examples, global help, module help, contextual question marks | Фаза 1 принята |
| 3. Expert recommendations | planned | Consent, рекомендации, уточнения, TTL, redaction, admin | Фаза 2 принята |
| 4. Salary | planned | Навигация позиций, partial calculation, competence, verified official source | Подтверждена региональная база Росстата |
| 5. Support letters | planned | Несколько партнеров, отдельные DOCX, ZIP | Фаза 4 или отдельное назначение |
| 6. Actuality | planned | Источники 2024+, URL verification, похожие проекты | Готов ingest snapshot ПФКИ |
| 7. Presentation | blocked | Template-driven PPTX 8–12 слайдов | Нужны PPTX-шаблон и 2–3 референса |
| 8. Other/new modules | planned | Все модули через profiles | Готов common shell |
| 9. Payments/subscriptions | planned | Hardened universal runs, будущие планы за flags | Отдельное решение по тарифам |

## Module–contest profiles

Текущий runtime остается прежним до фазы 1. Матрица в `config/product/module-contest-profiles.json` является утвержденной целью миграции.

| Конкурс | Готовые профили | Готовятся |
| --- | --- | --- |
| ПФКИ | social-research, legal-acts, salary, support-letter, presentation, scenario-plan | check-application |
| Фонд президентских грантов | — | все 7 модулей |
| Росмолодёжь.Гранты | — | все 7 модулей |
| Гранты Первых | — | все 7 модулей |

## Известные ограничения фазы 0

- Registry пока не подключен к frontend/backend runtime; два legacy registry продолжают обслуживать production.
- `example` и `faq` manifests фиксируют legacy packs без versioned файлов. Полные assets и FAQ появятся в фазе 2.
- Методические материалы ФПГ, Росмолодёжь.Гранты и Грантов Первых не переданы; такие профили нельзя переводить в `ready`.
- Изменения БД и публичного UI в фазе 0 отсутствуют.
