# Product changelog

## 2026-07-28

### Phase 1: global shell + multi-contest

- Статус Phase 1 возвращен в `in_review` до внешней production-проверки и пользовательского плейтеста.
- Добавлена проверяемая build identity: скрытый web meta marker, HTTP header и безопасное поле `build_sha` в API `/health`.
- Production contract вынесен в отдельную обязательную команду без silent skip, с `no-store`, no-cache headers и уникальными query parameters.
- Contest context проекта автоматически подставляется в модуль, сохраняет `project_id`, обновляет `contest_slug` через project API и изолирует drafts по конкурсам.
- Example CTA больше не подставляет PFKI без выбора конкурса и не показывает пример неподдерживаемого профиля.
- Универсальный баланс запусков доступен в мобильной шапке; технические названия коммерческого учета пользователю не показываются.
- Этап «Результат» становится доступен после успешной генерации, ведет к реальной секции `#result` и работает в desktop/mobile navigation.
- Подключен валидируемый runtime `ProductRegistry` и безопасные public endpoints конкурсов, модулей и профилей.
- Добавлены additive contest/profile/project columns, idempotent backfill legacy PFKI и сохранение contest context в проектах, работах и запусках.
- Запуск блокируется до AI и списания, если module–contest profile не имеет статус `ready`.
- Публичный shell переведен на общий бренд, четыре конкурса, явный selector и безопасное состояние `preparing`.
- Добавлены draft keys v2 по module + contest + project с миграцией legacy PFKI и защитой от перезаписи при hydration.
- Добавлены общий ModuleShell, mobile drawer этапов, focus return по Escape и универсальный баланс оплаченных запусков.
- Выполнена responsive QA-матрица 390/430/768/1024/1440 без horizontal overflow; screenshots сохранены в `docs/qa/phase-1`.
- Добавлены проверяемые deployment mirrors product registry для изолированных Railway service roots.
- Production file storage переведен с ephemeral `/tmp` на подключенный Railway Volume `/data`.
- Rollback выполняется одним production flag `PRODUCT_REGISTRY_RUNTIME_ENABLED=false`; additive columns не удаляются.

### Phase 0: foundation

- Добавлен текстовый source of truth `LARI_MASTER_ARCHITECTURE.md`.
- Созданы public registries contests/modules/module–contest profiles.
- Зафиксированы example/FAQ manifests и feature flags.
- Добавлены JSON Schemas и tests ссылочной целостности.
- Созданы ADR, implementation status, registry, payment, data source, privacy и migration docs.
- Подготовлен детальный implementation plan фазы 1.
- Публичное поведение, API contracts и DB schema не изменены.
