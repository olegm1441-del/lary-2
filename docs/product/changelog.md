# Product changelog

## 2026-07-28

### Исправления по пользовательскому плейтесту

- Карточки модулей передают явный `intent=start|example`; после выбора готового конкурса открывается нужный сценарий, а URL без intent сохраняет экран решения.
- Inline-подсказки переведены на стабильные `id` и `operation`, учитывают весь контекст формы и не дублируют уже заполненный регион.
- Для завершённой работы сохраняется нормализованный fingerprint входных данных: идентичный повтор блокируется, изменённые данные предлагают обновить результат, прежний результат остаётся доступен.
- Состояние результата хранится отдельно по module + contest + project и восстанавливается после refresh.
- Модуль «Актуальность» получил новые поля, проверяемые источники не ранее 2024 года, строгий JSON-контракт, backend-проверку URL/чисел/географии и специализированный DOCX.
- Модуль «Сценарный план» получил отдельные поля мероприятия, строгий JSON-контракт, проверку числа дней, таймингов, пересечений, операционных блоков и специализированный DOCX.
- Добавлен общий `LARI_DOCX_STYLE_GUIDE.md`.
- Статус Phase 1 остаётся `in_review` до production smoke и подтверждения пользовательского плейтеста.

### Phase 1: global shell + multi-contest

- Статус Phase 1 возвращен в `in_review` до внешней production-проверки и пользовательского плейтеста.
- Добавлена проверяемая build identity: скрытый web meta marker, HTTP header и безопасное поле `build_sha` в API `/health`.
- Production contract вынесен в отдельную обязательную команду без silent skip, с `no-store`, no-cache headers и уникальными query parameters.
- Contest context проекта автоматически подставляется в модуль, сохраняет `project_id`, обновляет `contest_slug` через project API и изолирует drafts по конкурсам.
- Example CTA больше не подставляет PFKI без выбора конкурса и не показывает пример неподдерживаемого профиля.
- Универсальный баланс запусков доступен в мобильной шапке; технические названия коммерческого учета пользователю не показываются.
- Этап «Результат» становится доступен после успешной генерации, ведет к реальной секции `#result` и работает в desktop/mobile navigation.
- Production anonymous/account cookies переведены на `SameSite=None; Secure`, чтобы временные работы и проекты сохранялись между Railway web/API hostnames.
- Устранено мобильное обрезание карточек и длинного selector конкурса в `/account` на 390/430 px.
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
