# Реестр конкурсов

Source of truth: `config/product/contests.json`.

## Первый набор

| Slug | Название | Статус |
| --- | --- | --- |
| pfki | Президентский фонд культурных инициатив | active |
| fpg | Фонд президентских грантов | preparing |
| rosmolodezh | Росмолодёжь.Гранты | preparing |
| first_grants | Гранты Первых | preparing |

## Правила

- `slug` хранится в Project, Draft, Run, Work и product events.
- Display name не используется как идентификатор.
- `docs_version` фиксирует версию criteria pack.
- Профиль можно перевести в `ready` только после получения актуальных документов, form schema, prompt/template, example, FAQ и tests.
- `preparing` profile виден в selector, но не запускает генерацию.
- Неподдерживаемая связка показывает: «Для этого конкурса модуль пока готовится» и действие «Выбрать другой конкурс».
- Prompt packs и provider credentials никогда не входят в public registry.

## Runtime фазы 1

- `GET /api/contests` возвращает четыре публичных варианта.
- Frontend требует явный выбор конкурса до формы.
- Legacy payload без `contest_slug` получает `pfki` только на время migration window.
- Проект хранит `contest_slug`, а deep link переносит `contest` и `project_id` в модуль.
- Draft key имеет вид `lary:draft:v2:{module}:{contest}:{project|anonymous}`.
- Переключатель `PRODUCT_REGISTRY_RUNTIME_ENABLED` включает profile gating на backend и служит аварийным rollback без удаления данных.

## Данные, которых не хватает

Для ФПГ, Росмолодёжь.Гранты и Грантов Первых нужны актуальные положения, формы заявок, критерии и примеры приложений. До их передачи Codex не должен придумывать contest-specific требования.
