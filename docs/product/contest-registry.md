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

## Данные, которых не хватает

Для ФПГ, Росмолодёжь.Гранты и Грантов Первых нужны актуальные положения, формы заявок, критерии и примеры приложений. До их передачи Codex не должен придумывать contest-specific требования.
