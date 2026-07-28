# План миграции к multi-contest architecture

## Цель

Перевести production с двух legacy module registry и свободной строки конкурса на единый public registry и `contest_slug`, сохранив текущие PFKI flows и возможность rollback.

## Шаг 0. Foundation

- Добавить target registry, JSON Schemas, manifests, feature flags и product docs.
- Добавить tests уникальности slugs, ссылочной целостности matrix и обязательных ids ready profiles.
- Не подключать registry к runtime и не менять БД/UI.

Rollback: удалить новые config/docs/tests; production behavior не затрагивается.

## Шаг 1. Read-only runtime registry

- Backend загружает и валидирует registry при startup.
- Добавляются read-only endpoints contests/modules/profiles.
- Frontend читает typed public metadata через один adapter.
- Legacy PFKI endpoints и payload остаются рабочими.

Rollback: feature flag возвращает legacy loaders; DB schema не меняется.

## Шаг 2. Additive DB migration

- Добавить nullable `contest_slug` и `profile_version` без удаления `competition`.
- Backfill `ПФКИ → pfki`.
- Добавить indexes и referential checks после проверки backfill.
- Новые writes сохраняют оба поля в migration window.

Rollback: приложение читает legacy `competition`; новые nullable columns остаются безвредными.

## Шаг 3. Draft and localStorage migration

- Новый version key включает module, contest и project.
- Legacy draft получает `contest_slug=pfki`.
- Смена конкурса не удаляет совместимые fields; несовместимая schema требует подтверждения.

Rollback: сохранять legacy draft copy до успешного чтения новой версии.

## Шаг 4. Profile-gated generation

- Backend разрешает prompt/template/example/FAQ только через ready profile.
- Payload без contest временно получает `pfki` и marker `legacy=true`.
- `preparing/disabled` profile возвращает user-safe status без вызова AI и без списания запуска.

Rollback: для PFKI можно временно включить legacy profile adapter; другие конкурсы не запускаются.

## Шаг 5. Завершение migration window

- Проверить долю legacy payload и старых drafts.
- Удалить dual write и свободную строку только отдельной migration.
- Обновить architecture status, API docs и changelog.

Критерий: нет legacy reads в течение согласованного окна, все PFKI E2E и payment flows проходят.

## Production rollout фазы 1

1. Деплой `main` выполняется с `PRODUCT_REGISTRY_RUNTIME_ENABLED=false`.
2. Проверяются `/health`, read-only product API, idempotent migration и legacy PFKI routes.
3. Flag включается только у production API.
4. Проверяются четыре конкурса, ready/preparing profiles, PFKI salary/support-letter generation, DOCX и usage ledger.
5. Проверяется, что `preparing` profile не создает run и не меняет баланс.
6. Для rollback flag возвращается в `false`; additive columns не удаляются.

Все Railway-команды обязаны содержать `--environment production`. Test environment в rollout не участвует.
