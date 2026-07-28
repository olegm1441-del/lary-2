# LARI 2 Phase 2: Examples, Help and Contextual Guidance

**Статус:** только план. Реализация не входит в Phase 1.

**Цель:** заменить legacy preview и разрозненные подсказки versioned example/FAQ packs, добавить общий help center и короткие контекстные объяснения без изменения генерации, оплаты и готовности конкурсов.

## Ограничения

- Работать после production-приемки Phase 1.
- Не переводить `preparing` profile в `ready` без утвержденных документов конкурса.
- Не передавать prompt text, provider config или внутренние error codes в frontend.
- Пример доступен только если manifest ссылается на существующий versioned asset того же module–contest profile.
- Подсказка не запускает AI и не списывает запуск.
- Текущие PFKI generation/download/payment flows остаются неизменными.

## Task 1. Versioned example packs

**Создать:**

- `config/product/examples/{contest}/{module}/{version}.json`
- JSON Schema для example pack.
- Loader validation: module, contest, version, profile version, sections, source date, public copy.
- Public endpoint `GET /api/modules/{module}/profiles/{contest}/example`.

**Проверки:**

- broken manifest reference ломает startup validation;
- profile mismatch возвращает safe 404;
- preparing profile не выдает generic example;
- HTML не содержит prompt/provider/internal markers.

## Task 2. Versioned FAQ packs

**Создать:**

- `config/product/faq/{contest}/{module}/{version}.json`
- FAQ schema: stable id, question, answer, optional field key, audience note.
- Endpoint `GET /api/modules/{module}/profiles/{contest}/faq`.

FAQ выбирается только через ready profile. Global FAQ хранится отдельно от contest-specific FAQ.

## Task 3. Global help center

**Маршруты:**

- `/help` — темы, поиск по утвержденным public packs, контакты.
- `/help/[topic]` — отдельная читаемая статья.

**UX:**

- язык без MVP/API/backend терминов;
- текст 18 px, touch target 44 px;
- mobile 390/430 без overflow;
- честная ссылка на поддержку, если ответа нет.

## Task 4. Module help

В `ModuleShell` задействовать уже типизированный `helpSlot`:

- «Что понадобится»;
- «Что получится»;
- FAQ для выбранного profile;
- ссылка на общий help topic.

Help не дублирует форму и не перекрывает primary CTA. На mobile открывается доступным drawer с Escape/focus return.

## Task 5. Contextual question marks

Добавить reusable `FieldHelp` рядом только с неоднозначными labels:

- button с доступным именем «Что означает …»;
- popover/dialog с утвержденным FAQ fragment;
- keyboard Enter/Space/Escape;
- focus return;
- без auto-open и без AI.

Не добавлять question mark к каждому полю.

## Task 6. Analytics and privacy

Разрешенные events: `help_opened`, `faq_opened`, `example_opened` с module_slug, contest_slug, profile_version и public item id. Не логировать пользовательские ответы, prompt или AI output.

## Task 7. QA and rollout

1. Unit/contract tests loaders и endpoints.
2. Frontend tests manifest-only examples, no dead controls, accessibility.
3. Responsive browser QA 390/430/768/1024/1440.
4. PFKI regression: six modules, downloads, free/paid runs unchanged.
5. Feature flags: `versioned_examples_enabled`, `faq_enabled`, `contextual_help_enabled`.
6. Production rollout по одному flag; rollback выключением flag без удаления packs.

## Definition of Done

- Нет fake examples и пустых help controls.
- Каждый открываемый example/FAQ существует и совпадает с выбранным profile.
- Preparing profiles не получают PFKI example/FAQ.
- Keyboard, Escape, focus return и 44 px targets подтверждены браузером.
- Public HTML не содержит internal data.
- Docs, screenshots, production smoke и rollback evidence приложены.
