# Реестр модулей

Source of truth: `config/product/modules.json`.

Module описывает универсальную прикладную задачу и не содержит prompt, критерии или шаблон конкретного конкурса. Связь с конкурсом определяется только `config/product/module-contest-profiles.json`.

## Поля module

- `slug`: стабильный технический идентификатор.
- `status`: `active`, `preparing` или `hidden`.
- `category`: пользовательская категория задачи.
- `title`: название задачи.
- `promise`: результат для пользователя без привязки к одному фонду.
- `duration`: ориентир времени.
- `output_formats`: редактируемые форматы результата.
- `feature_flags`: возможности конкретного module, не глобальные тарифные flags.

## Текущий набор

| Slug | Название | Формат | Состояние |
| --- | --- | --- | --- |
| social-research | Собрать доказательства актуальности | DOCX | active |
| legal-acts | Найти нормативные акты и программы | DOCX | active |
| salary | Рассчитать зарплату и обоснование | DOCX | active |
| support-letter | Сделать письмо поддержки | DOCX | active |
| presentation | Собрать презентацию | PPTX | active |
| scenario-plan | Составить сценарный план | DOCX | active |
| check-application | Проверить готовую заявку | DOCX | preparing |

## Definition of ready нового модуля

Нужны metadata, supported contests, form schema, prompt pack, result schema, template, example, FAQ, expert criteria, tests и обновленная документация. Нельзя добавлять модуль копированием page или через generic AI prompt.

## Переходный период

С фазы 1 публичные module metadata и module–contest profiles читаются из `config/product`. Legacy `apps/web/app/data/modules.json` пока содержит только детальные поля форм и примеры, которые объединяются с общим registry в одном typed frontend adapter. Backend legacy schema endpoint сохраняется для совместимости, но runnable profile всегда разрешается через `ProductRegistry` при включенном runtime flag.

Единственный владелец каталога — `GET /api/modules`. Отдельный endpoint профиля: `GET /api/modules/{module_slug}/profiles/{contest_slug}`.
