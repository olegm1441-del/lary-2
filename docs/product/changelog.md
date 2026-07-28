# Product changelog

## 2026-07-28

### Phase 1: global shell + multi-contest

- Подключен валидируемый runtime `ProductRegistry` и безопасные public endpoints конкурсов, модулей и профилей.
- Добавлены additive contest/profile/project columns, idempotent backfill legacy PFKI и сохранение contest context в проектах, работах и запусках.
- Запуск блокируется до AI и списания, если module–contest profile не имеет статус `ready`.
- Публичный shell переведен на общий бренд, четыре конкурса, явный selector и безопасное состояние `preparing`.
- Добавлены draft keys v2 по module + contest + project с миграцией legacy PFKI и защитой от перезаписи при hydration.
- Добавлены общий ModuleShell, mobile drawer этапов, focus return по Escape и универсальный баланс оплаченных запусков.
- Выполнена responsive QA-матрица 390/430/768/1024/1440 без horizontal overflow; screenshots сохранены в `docs/qa/phase-1`.
- Rollback выполняется одним production flag `PRODUCT_REGISTRY_RUNTIME_ENABLED=false`; additive columns не удаляются.

### Phase 0: foundation

- Добавлен текстовый source of truth `LARI_MASTER_ARCHITECTURE.md`.
- Созданы public registries contests/modules/module–contest profiles.
- Зафиксированы example/FAQ manifests и feature flags.
- Добавлены JSON Schemas и tests ссылочной целостности.
- Созданы ADR, implementation status, registry, payment, data source, privacy и migration docs.
- Подготовлен детальный implementation plan фазы 1.
- Публичное поведение, API contracts и DB schema не изменены.
