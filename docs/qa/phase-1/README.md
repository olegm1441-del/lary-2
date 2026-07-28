# Phase 1 QA: multi-contest shell

Дата локальной проверки: 28 июля 2026.

## Проверенный путь

1. Каталог → модуль без выбранного конкурса.
2. Явный выбор одного из четырех конкурсов.
3. PFKI `ready` → выбор «Запустить модуль» или реального примера.
4. FPG `preparing` → короткое безопасное состояние без формы, оплаты и запуска.
5. PFKI form → автоматический draft v2 → refresh → back → восстановленный текст.
6. Mobile drawer этапов → Escape → drawer закрыт, focus возвращен кнопке «Этапы».

## Responsive matrix

Проверены страницы `/`, `/modules`, PFKI salary form, PFKI support-letter form и FPG salary preparing state.

| Width | Горизонтальный overflow | Основной font | Русские переносы |
| --- | --- | --- | --- |
| 390 | нет | 18 px | корректно |
| 430 | нет | 18 px | корректно |
| 768 | нет | 18 px | корректно |
| 1024 | нет | 18 px | корректно |
| 1440 | нет | 18 px | корректно |

Основные ссылки, кнопки и элементы управления имеют touch target не меньше 44 px. Нативные radio inputs внутри крупных labels визуально меньше 44 px, но весь label остается кликабельной областью.

## Интерактивные проверки

- Contest selector показывает все четыре конкурса и не открывает форму до выбора.
- PFKI ready state показывает только разрешенные действия.
- FPG preparing state не содержит form, payment CTA или run button.
- Drawer объявлен как `dialog`, имеет `aria-label="Этапы модуля"` и закрывается Escape.
- После Escape `aria-expanded=false`, focus возвращается кнопке «Этапы».
- Draft `social-research + pfki + anonymous` переживает refresh и browser back.
- Все 25 сочетаний route × width имеют `scrollWidth === clientWidth`.

## Screenshots

- `modules-1440-viewport.jpg`
- `salary-pfki-390-viewport.jpg`
- `support-letter-pfki-430-viewport.jpg`
- `salary-fpg-preparing-390-viewport.jpg`
- Полная матрица full-page PNG находится в этой же папке.

Production contract запускается отдельно после deploy:

```bash
PRODUCTION_BASE_URL=https://web-production-532a8.up.railway.app pnpm test
```

## Production evidence

Финальный runtime commit: `74864c23bb34176f1b50fb002e7ecaaf76d0f509`.

- Web deployment `7dbaea66-a0da-4936-8660-aabf91282426`: `SUCCESS`.
- API deployment с runtime flag `382e2f99-8c98-4fa8-9d92-37336c11dcec`: `SUCCESS`.
- `PRODUCT_REGISTRY_RUNTIME_ENABLED=true`.
- `FILE_STORAGE_DIR=/data/lary-generated`.
- `/health` → 200.
- `/api/contests` → четыре approved slugs.
- PFKI salary profile → `ready`; FPG salary profile → `preparing`.
- FPG run и profile-version mismatch → safe 409; usage до/после одинаковый.
- Реальный PFKI salary run → completed; DOCX zip-valid и читается `python-docx`.
- Реальный PFKI support-letter run → completed; DOCX без `{{...}}`, содержит партнера, проект и сумму.
- Проект, attached work и `contest_slug=pfki` пережили API restart.
- Durable DOCX `c04403a4-35b7-4991-91fc-d50388ca9133` пережил restart; SHA-256 до/после одинаковый: `2badbb728509ff6a1a13f45fd1952be162411df4ae6d6b8ded53450b753c8a16`.
- Rollback `PRODUCT_REGISTRY_RUNTIME_ENABLED=false` проверен без удаления additive columns; после smoke flag возвращен в `true`.
- Production browser QA: 390 px preparing, 390 px ready form и 1440 px catalog — 18 px body font, horizontal overflow отсутствует.
