# Архитектурные решения LARI 2

## ADR-001. Один публичный product registry

- Дата: 2026-07-28
- Статус: принято
- Решение: `config/product/*.json` становится единым публичным registry для contests, modules, module–contest profiles, examples, FAQ и feature flags.
- Причина: текущие frontend JSON и backend Python list расходятся.
- Альтернативы: сохранить два registry; генерировать один из другого во время CI.
- Последствия: frontend и backend должны читать один набор данных; Phase 1 удалит runtime-зависимость от двух legacy registry после contract tests.

## ADR-002. Module–contest profile выбирает все contest-specific ресурсы

- Дата: 2026-07-28
- Статус: принято
- Решение: prompt, form, result schema, template, criteria, example, FAQ и source policy выбираются только по `module_slug + contest_slug + profile_version`.
- Причина: условные ветки по конкурсу не масштабируются и допускают запуск generic prompt для неподдерживаемой связки.
- Альтернативы: хранить contest fields внутри module; делать `if contest` в runners.
- Последствия: `preparing` и `disabled` profiles не запускают AI; prompt packs остаются только в backend.

## ADR-003. Универсальные запуски остаются коммерческой единицей

- Дата: 2026-07-28
- Статус: принято
- Решение: текущий universal run ledger сохраняется. Module-specific credits и подписки 3/7/30 дней выключены feature flags.
- Причина: это соответствует действующему платежному flow и не вводит неподтвержденные тарифы.
- Альтернативы: баланс по каждому модулю; подписка вместо запусков.
- Последствия: UI не использует слова ledger, credits или tokens; техническая ошибка не списывает запуск.

## ADR-004. Поэтапная миграция без behavior change в фазе 0

- Дата: 2026-07-28
- Статус: принято
- Решение: Phase 0 добавляет документацию, configs, schemas и tests, но не подключает их к production runtime.
- Причина: master architecture запрещает массовый rewrite и требует сохранить рабочие PFKI flows.
- Альтернативы: сразу заменить module shell и API.
- Последствия: короткий период существуют target registry и legacy runtime registry; рассинхронизация явно отражена в статусе и закрывается фазой 1.

## ADR-005. `contest_slug` заменяет свободную строку конкурса

- Дата: 2026-07-28
- Статус: принято
- Решение: проекты, работы, запуски и черновики получают `contest_slug`; legacy `ПФКИ` мигрирует в `pfki`.
- Причина: свободная строка не гарантирует связь с версией критериев и profile.
- Альтернативы: продолжить хранить display name; добавить отдельную таблицу без slug migration.
- Последствия: миграция выполняется additively и с rollback; payload без `contest_slug` временно трактуется как legacy PFKI.

## ADR-006. Profile gate расположен до коммерческого и AI-контуров

- Дата: 2026-07-28
- Статус: принято
- Решение: backend сначала разрешает `module_slug + contest_slug + profile_version`, и только затем проверяет бесплатный/оплаченный запуск и вызывает генератор.
- Причина: состояние `preparing` не должно создавать работу, расходовать попытку или отправлять данные AI-провайдеру.
- Альтернативы: проверять profile только на frontend; отклонять после создания run.
- Последствия: frontend-состояние не является границей безопасности; salary и generic runners используют один и тот же gate.

## ADR-007. Draft v2 изолируется конкурсом и проектом

- Дата: 2026-07-28
- Статус: принято
- Решение: ключ `lary:draft:v2:{module}:{contest}:{project|anonymous}`; legacy draft мигрирует только в PFKI.
- Причина: одинаковый модуль в разных конкурсах или проектах не должен смешивать ответы.
- Альтернативы: один draft на module; хранить только server-side.
- Последствия: hydration завершается до первой записи, чтобы refresh не перезаписал сохраненный draft пустым state.

## ADR-008. Railway service images получают проверяемые mirrors registry

- Дата: 2026-07-28
- Статус: принято
- Решение: авторский source of truth остается в `config/product`, а service-root snapshots содержат точные JSON mirrors в `apps/api/product-config` и `apps/web/product-config`.
- Причина: Railway исключает файлы выше настроенного service root, поэтому прямой monorepo import работает локально, но отсутствует в production image.
- Альтернативы: сменить root обоих production services на корень monorepo; дублировать registry без проверки.
- Последствия: contract test сравнивает parsed JSON каждого mirror с source registry; любое расхождение ломает CI/local verification.
