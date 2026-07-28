# Приватность и сроки хранения

## Принципы

- Собирать только данные, необходимые для выбранного module и contest.
- Не просить пользователя создавать проект или account до первого результата.
- Не писать полные inputs, prompts, AI responses, файлы и персональные данные в application logs.
- В технических логах допустимы run id, module, contest, status, duration, error code, file size и source status.

## Черновики и результаты

- Anonymous draft и result должны иметь явный срок хранения и owner key.
- Account works и projects хранятся в PostgreSQL до удаления пользователем или по правилам legal documents.
- Production-файлы хранятся на Railway Volume в `/data/lary-generated`; локальная разработка использует `/tmp/lary-generated`.
- БД хранит owner, run, format и lifecycle status; download остается доступен после restart production API.
- Удаление work должно удалять или ставить в очередь связанные файлы без воздействия на чужие записи.

## Help и expert threads

- Срок: 30 дней, затем hard delete scheduled cleanup.
- Идентификатор: псевдонимизированный session/thread id.
- Consent: `consent_at` и `displayed_notice_version`.
- Ограничение: до 3 рекомендаций и до 5 уточняющих сообщений на expert thread.
- До записи выполняется redaction email, phone, passport-like numbers, ИНН/СНИЛС patterns where feasible.
- Admin UI не показывает email/ФИО как отдельные поля.
- Пользователь может удалить thread раньше срока.
- Manual CSV export требует admin access и audit log.

## Админ-доступ

Internal route отсутствует в публичной навигации. Доступ — allowlist account/email или отдельная admin session. Экран показывает redacted content и технический контекст, но не раскрывает чужие account identifiers без необходимости.
