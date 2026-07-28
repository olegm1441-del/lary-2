# Модель запусков и оплаты

## Действующая коммерческая единица

Один универсальный запуск дает одну успешную генерацию, расчет или сборку результата в любом доступном module–contest profile. Источник истины — серверный `credit_ledger`.

## Списание

1. Backend определяет владельца: account или anonymous session.
2. Проверяет бесплатную попытку конкретного модуля.
3. Если бесплатной попытки нет, резервирует один универсальный запуск.
4. Запуск списывается только после успешного сохранения результата и файла.
5. Validation, provider, source, storage или file-generation error не списывает запуск.
6. Повторный запрос с тем же idempotency key не списывает запуск повторно.

## Платежные состояния

`created → pending → paid` или `created/pending → failed/cancelled/refunded`.

- Сумма и число запусков определяются backend package catalog.
- Frontend не передает доверенную сумму.
- Webhook проверяет подпись и идемпотентность по provider payment id.
- Оплаченные запуски начисляются ledger entry с `payment_id`.
- Возврат или ручная корректировка отражается отдельной ledger entry, а не изменением истории.

## Возврат в черновик

Переход на оплату сохраняет `module_slug`, `contest_slug`, `project_id`, `draft_id` и безопасный return URL. После оплаты пользователь возвращается в тот же module и видит сохраненный draft.

## Feature flags

Source of truth: `config/product/feature-flags.json`.

- `UNIVERSAL_RUNS_ENABLED=true`
- `MODULE_SPECIFIC_RUNS_ENABLED=false`
- `SUBSCRIPTIONS_ENABLED=false`
- `SUBSCRIPTION_3_DAYS_ENABLED=false`
- `SUBSCRIPTION_7_DAYS_ENABLED=false`
- `SUBSCRIPTION_30_DAYS_ENABLED=false`

Публичный UI пока показывает только универсальные запуски. Будущие подписки нельзя включать без отдельного продуктового решения, тарифов, оферты и webhook tests.
