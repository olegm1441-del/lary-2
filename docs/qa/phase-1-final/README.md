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
