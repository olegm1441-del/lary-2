# Phase 1 final production reconciliation

Дата проверки: 28 июля 2026.

Статус Phase 1: `in_review`.

Причина: production reconciliation завершается этой задачей, но статус `ready` разрешен только после пользовательского плейтеста и явного подтверждения пользователя.

## Каноническая build identity

Единственным источником фактической версии production являются:

1. `<meta name="lari-build-sha">` и `X-Lari-Build-Sha` публичного web;
2. поле `build_sha` публичного API `/health`;
3. ожидаемый SHA, переданный строгому `test:production-contract`;
4. commit успешных Railway deployments сервисов `web` и `api` в environment `production`.

Все четыре значения обязаны быть непустыми и совпадать. Старые deployment IDs и SHA в `docs/qa/phase-1/README.md` помечены архивными.

## Обязательная production-проверка

```bash
cd apps/web
PRODUCTION_BASE_URL=https://web-production-532a8.up.railway.app \
EXPECTED_BUILD_SHA=<deployed-main-sha> \
pnpm test:production-contract
```

Команда завершается ошибкой без `PRODUCTION_BASE_URL` или `EXPECTED_BUILD_SHA`; silent skip запрещен.

## Responsive acceptance matrix

Проверяются widths 390, 430, 768, 1024 и 1440 для `/`, `/modules`, salary ready/preparing/selector, support-letter, `/pay` и `/account`.

Проверки:

- horizontal overflow отсутствует;
- мобильный баланс запусков виден и ведет на `/pay`;
- sidebar скрыт на телефоне, drawer остается внутри viewport;
- CTA и длинные названия конкурсов не перекрываются;
- Escape закрывает меню/drawer и возвращает focus;
- этап результата включается только после успешной генерации.

Свежие screenshots этого прогона сохраняются в этой папке.

## Фактический production smoke

- Публичный home, catalog и module routes проверены без cache.
- Общий бренд и четыре конкурса присутствуют; старый общий PFKI-брендинг отсутствует.
- Selector без конкурса не открывает форму.
- PFKI открывает decision/form/example только в PFKI-контексте.
- FPG показывает `preparing`, не создаёт run и не изменяет usage.
- Project contest автоматически подставляется по `project_id`.
- Смена конкурса сохраняет `project_id`; PFKI и FPG drafts изолированы, возврат к PFKI восстанавливает PFKI draft.
- Мобильные menu и stages drawer закрываются Escape и возвращают focus.
- После реальной генерации появляется `#result`; этап «Результат» становится доступным, переход к данным не удаляет результат.
- Anonymous/account cookie в production использует `SameSite=None; Secure`, поэтому проект и временные работы сохраняются между cross-origin запросами web → API.
- Salary run `7a9bccc2-9cff-44b7-88ce-b76374a70b4e`: DOCX zip-valid, читается `python-docx`, SHA-256 `cb8c42617307f9ef9c34658cd68c823aebc1a0f492ea8fad5e16a7f1aa00f992`.
- Support-letter run `abf60e6c-a9ab-42e4-b1c1-4bcd8b28e522`: DOCX zip-valid, читается `python-docx`, нет `{{...}}`, SHA-256 `3fdd4dabded609df5070b071422fb532ed071b2a9804d5bbe9b93e3fd1abf15a`.
- После production API restart оба файла скачались побайтно идентичными.

## Screenshots

- `home-390.jpg`, `home-768.jpg`;
- `modules-390.jpg`, `modules-430.jpg`, `modules-1440.jpg`;
- `m-salary-contest-fpg-390.jpg`;
- `m-salary-contest-pfki-1024.jpg`;
- `m-salary-contest-pfki-mode-start-430.jpg`, `m-salary-contest-pfki-mode-start-1440.jpg`;
- `m-support-letter-contest-pfki-mode-start-390.jpg`, `m-support-letter-contest-pfki-mode-start-430.jpg`;
- `pay-390.jpg`;
- `account-390.jpg`, `account-430.jpg`.
