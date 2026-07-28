# LARI 2.0

Master-архитектура продукта и техническое задание для Codex

> Первый общий документ: multi-contest architecture, универсальный UX модулей, помощь, примеры, экспертные рекомендации, платежная модель, данные и дорожная карта.


| Параметр | Значение |
| --- | --- |
| Статус | Source of truth для последующих технических заданий |
| Версия | 1.0 · 18 июля 2026 |
| Целевая ветка | main; test-среда не разворачивается без отдельной команды |
| Основной стек | Next.js / React / Tailwind; FastAPI; PostgreSQL; GigaChat; DOCX/PPTX |
| Рабочий процесс | Superpowers: design → plan → tests → implementation → verification → documentation |


> Критическое правило исполнения
> Этот документ не означает «реализовать всё одним коммитом». Он фиксирует целевую архитектуру и порядок реализации. Codex должен выполнять только явно назначенную фазу, но каждое решение сверять с данным документом.


# Содержание

1. Назначение документа и picture of done

2. Подтвержденные продуктовые решения

3. UX-принципы LARI

4. Аудит текущего сайта и репозитория

5. Конкурентная среда и позиционирование

6. Целевая информационная архитектура

7. Multi-contest architecture

8. Единый каркас страницы модуля

9. Лендинг и каталог модулей

10. Примеры результатов

11. Помощь, FAQ и чат помощи

12. Экспертные рекомендации

13. Данные, приватность и админ-доступ

14. Запуски, оплаты и будущие подписки

15. Документация продукта в репозитории

16. Модуль расчета зарплаты

17. Модуль писем поддержки

18. Модуль актуальности и источников

19. Модуль презентаций

20. Остальные и новые модули

21. Мобильная версия и доступность

22. Backend/API/DB architecture

23. Prompt architecture

24. Тестирование и контроль качества

25. Этапы реализации

26. Инструкция Codex и acceptance criteria

27. Зависимости и данные, которые еще нужны

28. Источники и референсы


# 1. Назначение документа и picture of done

LARI превращается из сервиса, жестко привязанного к одному конкурсу, в модульное рабочее пространство для подготовки грантовых заявок. Пользователь выбирает прикладную задачу, конкурс и минимально необходимый набор данных, получает редактируемый файл, может вернуться к черновику, посмотреть пример, получить помощь и запросить экспертные рекомендации.


## 1.1. Финальная картина продукта

- Единое название во всем публичном интерфейсе: «Лари — AI-помощник по составлению грантовых заявок».
- На лендинге и в карточках нет жесткой формулировки «по заявке ПФКИ»; конкурс становится контекстом внутри модуля.
- Первый набор конкурсов: ПФКИ, Фонд президентских грантов, Росмолодёжь.Гранты, Гранты Первых.
- Каждая связка «модуль × конкурс» имеет отдельный статус готовности, форму, критерии, prompts, шаблоны, FAQ и примеры.
- При неподдерживаемой связке модуль остается видимым, но показывает спокойную заглушку и предлагает сменить конкурс.
- Все модули mobile-first, с понятной навигацией по шагам, примером результата, помощью и сохранением черновика.
- После результата доступны редактируемый файл, текстовый preview там, где это уместно, и «Рекомендации эксперта».
- Баланс универсальных запусков виден в шапке; будущие модульные кредиты и подписки заложены feature flags, но выключены.
- Архитектурная документация в репозитории обновляется одновременно с кодом.

## 1.2. Что не является picture of done

- Нельзя просто заменить слово «ПФКИ» в нескольких строках и оставить prompts, шаблоны и результаты жестко привязанными к ПФКИ.
- Нельзя добавлять новый конкурс через условные ветки вида if contest === ... в каждом компоненте.
- Нельзя превращать LARI в общий чат: основная единица продукта — модуль и рабочий файл.
- Нельзя показывать пользователю внутренние слова: prompt, backend, endpoint, JSON, provider error, blocked, unavailable.
- Нельзя реализовывать все фазы одним большим merge без поэтапной проверки.

# 2. Подтвержденные продуктовые решения


| Решение | Зафиксированное состояние |
| --- | --- |
| Бренд | «Лари — AI-помощник по составлению грантовых заявок». Использовать в header, metadata, footer, help и trust copy. |
| Выбор конкурса | При первом входе в модуль. Если у проекта конкурс уже сохранен, подставить его, но разрешить изменить. |
| Первый contest registry | ПФКИ; Фонд президентских грантов; Росмолодёжь.Гранты; Гранты Первых. |
| Неподдерживаемая связка | Модуль виден. Внутри показывается заглушка «Для этого конкурса модуль пока готовится» и кнопка смены конкурса. |
| Карточки | Строка/чипы «Подходит для». При 5+ конкурсах — «5 конкурсов» с доступным hover/focus/click popover. |
| Примеры | Текстовый preview + скачиваемый файл. Архитектура — на каждую готовую связку module × contest. |
| Эксперт | До 3 разных рекомендаций на результат + до 5 уточняющих сообщений. Контекст: форма, результат, конкурс, проект, связанные разделы. |
| Help-chat | Отвечает по интерфейсу и содержанию модуля, но не переписывает результат. |
| Логи чатов | PostgreSQL, 30 дней, псевдонимизированный session id, без email/ФИО в админке, предварительное уведомление. |
| Запуски | В main — универсальные запуски для любого модуля. Баланс в шапке. |
| Подписки | Архитектурный резерв на 3/7/30 дней; выключено feature flag до отдельного решения. |
| Письма поддержки | Несколько партнеров за один запуск, дублирование карточки, отдельный DOCX на партнера, ZIP для всех. |
| Свежесть исследований | Публикация не ранее 2024 года; более свежие материалы выше в приоритете. |
| Смежные проекты | Сначала база победителей ПФКИ; затем ФПГ, Росмолодёжь и иные подтвержденные проекты. |
| Презентация | PPTX, 8–12 слайдов, без логотипа LARI в пользовательском файле, единый узнаваемый стиль. |


# 3. UX-принципы LARI

Основа — приложенная UI/UX-библиотека LARI: task-first, anonymous-first, крупный интерфейс для аудитории 45–65+, inline coaching, рабочий файл как главная ценность, спокойные ошибки и отсутствие технического жаргона.


## 3.1. Базовые правила

- Сначала задача, потом регистрация и проект. Пользователь не обязан создавать проект до первого результата.
- Каждый экран отвечает на пять вопросов: что я делаю, что от меня нужно, что я получу, что будет при ошибке, как не потерять результат.
- Подсказка появляется рядом с полем и объясняет конкретное улучшение. Отдельный этап «проверить форму» не нужен.
- Блокировать запуск можно только критическими ошибками. Рекомендации не блокируют.
- «Не знаю» — нормальный сценарий в полях, где допустим placeholder/fallback.
- Голосовой ввод — только для длинных полей.
- После результата первым показывается скачивание файла, затем preview и следующие действия.
- Минимальный размер обычного текста — 16 px; основной текст форм — 18 px; кликабельная зона — не меньше 44×44 px.
- Все состояния: сохраняется, сохранено, готовится, готово, ошибка, файл скачан, скопировано, отправлено.
- На мобильном нет горизонтального скролла, узких sidebar и скрытых действий.

## 3.2. Тон интерфейса

- Короткие активные глаголы: «Выбрать конкурс», «Посмотреть пример», «Сформировать DOCX», «Получить рекомендацию».
- Не использовать AI-пафос: «революционный», «магический», «гарантированная победа».
- Не использовать английские системные слова в публичном UI.
- Не писать «готовая заявка»; писать «рабочий файл», «рабочий текст», «черновик для проверки».

# 4. Аудит текущего сайта и репозитория


## 4.1. Что уже является хорошей базой

- Task-first landing: быстрый старт, каталог задач, trust-блоки, рабочие DOCX/PPTX.
- Anonymous-first и один бесплатный запуск на модуль уже поддерживаются ledger-логикой.
- Существуют project/work/account entities, magic link, универсальные платные запуски и promo ledger.
- Есть generic module runner, отдельный salary runner, field assistant, voice input, result viewer и генераторы файлов.
- PostgreSQL уже является источником истины для запусков, работ, проектов и платежного ledger.

## 4.2. Основные архитектурные ограничения текущей версии


| Проблема | Где проявляется | Почему мешает |
| --- | --- | --- |
| ПФКИ захардкожен | apps/api/app/data/modules.py; apps/web/app/data/modules.json; file_generators.py; account_store.py; module_engine.py; публичный сайт | Нельзя надежно переключать contest-specific prompts, templates, criteria и examples. |
| Два registry | Frontend JSON и backend Python list | Риск рассинхронизации названий, полей, статусов и конкурсов. |
| Special-case modules | module-runner.tsx отдельно вызывает salary-module-runner.tsx; page.tsx имеет slug-ветки | При росте до 12–15 модулей появится множество if/else и разные UX-паттерны. |
| Generic AI prompt | module_engine.py содержит общий PFKI prompt и добавляет sections к deterministic output | Нельзя гарантировать формат, критерии и качество конкретного конкурса. |
| Project competition — строка | projects.competition и AccountWorkItem competition фактически ориентированы на ПФКИ | Нужен contest_slug и migration. |
| Examples встроены в page | ?example=1 и статические blocks | Нужны versioned example packs и реальные файлы module × contest. |
| Help статичен | apps/web/app/help/page.tsx | Нет module FAQ, contextual help и chat. |
| Payments placeholder | apps/api/app/routers/payments.py и payment-panel.tsx | Нужно зафиксировать универсальный ledger и будущее расширение без включения лишних сценариев. |


## 4.3. Текущие source-of-truth файлы, которые Codex обязан учитывать

- apps/web/app/data/modules.json
- apps/web/app/lib/lary-data.ts
- apps/web/app/components/module-runner.tsx
- apps/web/app/components/salary-module-runner.tsx
- apps/web/app/m/[slug]/page.tsx
- apps/web/app/components/lary-ui.tsx
- apps/web/app/help/page.tsx
- apps/web/app/components/payment-panel.tsx
- apps/api/app/data/modules.py
- apps/api/app/services/module_engine.py
- apps/api/app/services/account_store.py
- apps/api/app/services/salary_calculator.py
- apps/api/app/services/support_letter.py
- apps/api/app/services/file_generators.py
- docs/architecture.md

# 5. Конкурентная среда и позиционирование


| Продукт | Сильная сторона | Ограничение | Что берем / чем отличаемся |
| --- | --- | --- | --- |
| CHECK GRANT | Очень простой путь: загрузить PDF → получить рекомендации по официальным критериям. | Сам сервис указывает, что не готовит отдельные разделы заявки. | LARI не только проверяет, а создает конкретные редактируемые материалы; сохранить простоту сценария и видимую безопасность. |
| ГрантоРез | Multi-contest, бесплатное preview, баллы по критериям, итеративная доработка, дополнительные вопросы, проверяемые URL. | Фокус на экспертизе готовой заявки; сложная тарифная матрица. | Взять contest switching, экспертные рекомендации и верификацию ссылок; отличаться task-first модулями и памятью проекта. |
| Школа грантов | Живая экспертиза, реальные кейсы, чек-листы, практические разборы, доверие к личности эксперта. | Дорогой и медленный human-service, не self-service инструмент. | Перенести практическую логику в примеры, FAQ, экспертные рекомендации и module-specific criteria packs. |
| lary.pro | Известный бренд LARI, проверка файла, пакетные проверки, личный кабинет. | Наследуемая версия привязана к проверке и высоким разовым ценам; не модульная подготовка. | Новое позиционирование: рабочее пространство для подготовки, а не только проверка. |
| MPSTATS | Большой каталог точечных инструментов, единая подписка, обучение, помощь и рекомендации в продукте. | Высокая плотность функций и интерфейса, не подходит напрямую аудитории 45–65+. | Взять модель «много задач в одной системе», каталог, единый баланс доступа и contextual help, но оставить спокойный и крупный UI. |


> Позиционирование
> Главная дифференциация LARI: «не просто проверяем заявку и не заставляем изучать курс — создаем конкретный рабочий файл по выбранной задаче, сохраняем контекст проекта и сразу даем экспертную обратную связь».


# 6. Целевая информационная архитектура


## 6.1. Основные публичные разделы


```text
/
/modules
/m/[moduleSlug]
/help
/security
/pay
/account
/projects/[projectId]            (после отдельной фазы)
/run/[runId]/result
/docs/[legalSlug]
```


## 6.2. Основные сущности


| Сущность | Назначение | Ключевые поля |
| --- | --- | --- |
| Contest | Описание конкурса и версии документации | slug, name, short_name, status, official_url, docs_version, updated_at |
| Module | Универсальная прикладная задача | slug, title, category, promise, duration, output_formats, feature_flags |
| ModuleContestProfile | Конкретная реализация модуля под конкурс | module_slug, contest_slug, status, form_schema_id, prompt_pack_id, template_id, criteria_pack_id, example_pack_id, faq_pack_id |
| Project | Контекст проекта пользователя | id, title, contest_slug, region, structured_context, owner |
| Draft | Состояние формы до результата | module_slug, contest_slug, project_id, payload, updated_at |
| Run | Зафиксированный запуск | run_id, module_slug, contest_slug, project_id, status, input_snapshot, result_snapshot, files |
| ExamplePack | Текст и файл примера | module_slug, contest_slug, version, preview, file_assets |
| ExpertThread | Диалог рекомендаций по результату | run_id, session_id, consent, expires_at, message_count |
| HelpThread | Контекстная помощь без переписывания результата | module_slug, contest_slug, field_key, session_id, expires_at |
| AccessLedger | Универсальные запуски | owner_key, delta, source, run_id, payment_id |


# 7. Multi-contest architecture


## 7.1. Contest registry


```text
contest_slug: pfki | fpg | rosmolodezh | first_grants
status: active | preparing | hidden
name: full official name
short_name: chip label
official_url: official contest page
docs_version: version/date of criteria pack
updated_at: ISO date
```


## 7.2. Module–contest matrix


```text
status: ready | preparing | disabled
card_visibility: visible | hidden
form_schema_id
prompt_pack_id
result_schema_id
template_id
criteria_pack_id
example_pack_id
faq_pack_id
source_policy_id
```

Первый release может иметь все четыре конкурса в selector, но только готовые профили работают. Для остальных показывается заглушка. Это позволяет строить общую архитектуру без выдачи некачественных результатов.


## 7.3. Поведение selector конкурса

1. При входе проверить contest_slug текущего проекта.
1. Если есть — подставить его и сохранить возможность изменить.
1. Если нет — показать четыре конкурса крупными radio-card.
1. После выбора запросить module–contest profile.
1. Если ready — показать example/start и форму.
1. Если preparing — показать заглушку, список доступных конкурсов и кнопку «Выбрать другой конкурс».
1. Смена конкурса не должна молча удалять введенные данные. Показывать confirmation только если схема несовместима.

## 7.4. Единый registry без дублирования

Рекомендуемая структура: один публичный registry в JSON, доступный frontend и backend; закрытые prompts остаются только в backend.


```text
config/product/
  contests.json
  modules.json
  module-contest-profiles.json
  examples-manifest.json
  faq-manifest.json

apps/api/app/prompt_packs/
  pfki/
  fpg/
  rosmolodezh/
  first_grants/

apps/api/app/templates/
  <contest>/<module>/...
```


> Безопасность prompts
> Не отправлять prompt packs в frontend bundle. Frontend знает только ids и UI/schema metadata; backend разрешает id в реальный prompt/template.


# 8. Единый каркас страницы модуля


## 8.1. Desktop layout


| Зона | Содержание | Поведение |
| --- | --- | --- |
| Header | Бренд, Модули, Помощь, баланс запусков, Войти | Sticky; 44 px targets; баланс открывает popover. |
| Left navigation | Конкурс, Пример/Запуск, шаги формы, результат | Sticky; active step highlighted; validation dots; кликабельные завершенные шаги. |
| Main content | Hero модуля, selector, example/start, форма, result | Max width 760–840 px; крупные поля; без длинных intro-дублей. |
| Utility rail (только ≥1280) | Помощь, autosave status, output format, run state | Не дублирует navigation; исчезает на меньших ширинах. |


## 8.2. Mobile layout

- Header компактный: бренд, баланс запусков, menu.
- Вместо постоянной левой панели — строка «Этап 2 из 5» и кнопка «Этапы», открывающая drawer.
- Help и экспертный чат открываются full-screen sheet / bottom sheet.
- Primary CTA закрепляется снизу только на длинных формах и не перекрывает content.
- Карточки повторяемых сущностей — одна колонка, кнопки «Дублировать/Удалить» в overflow menu или отдельной строке.

## 8.3. Порядок экрана

1. Короткий hero: название, promise, время, format, баланс/стоимость.
1. Selector конкурса.
1. Segmented control: «Запустить модуль» / «Посмотреть пример».
1. Форма, разбитая на смысловые секции.
1. Primary CTA и состояние autosave.
1. Результат: download first.
1. Экспертные рекомендации, help, следующий модуль.

## 8.4. Поле формы — обязательный contract


> label
> required | optional | can_skip
> short_helper
> placeholder_example
> question_mark_content: {what, why, examples, mistakes}
> inline_rules
> error_message
> voice_enabled
> save_key
> contest_overrides


## 8.5. Question marks

- Иконка «?» справа от label; aria-label «Зачем нужно это поле».
- Popover содержит максимум 3 коротких блока: что ввести, зачем это нужно, пример.
- Popover не повторяет helper дословно.
- Закрытие по Esc, outside click и повторному нажатию; focus возвращается к иконке.
- На mobile popover превращается в bottom sheet.

# 9. Лендинг и каталог модулей


## 9.1. Изменение брендинга


> Было: Лари — помощник по заявке ПФКИ
> Стало: Лари — AI-помощник по составлению грантовых заявок

Hero должен говорить о задачах и рабочих файлах, а не об одном фонде. ПФКИ появляется только в contest chips и внутри выбранного module profile.


## 9.2. Карточка модуля


> Категория
> Название задачи
> 1–2 предложения: что получится
> Время · формат
> Подходит для: [ПФКИ] [ФПГ] [Росмолодёжь]
> Бесплатный/платный статус
> [Начать] [Посмотреть пример]

Если поддерживается 5+ конкурсов, показывать «5 конкурсов». Popover должен открываться не только hover, но и focus/click, иначе mobile и keyboard-пользователи потеряют информацию.


## 9.3. Индикатор запусков

- В шапке: «Запуски: N».
- При нулевом балансе: «Купить запуск».
- Popover: универсальные запуски, бесплатные попытки по модулям, ссылка на оплату.
- Не показывать пользователю ledger/credits/tokens.

## 9.4. Дополнительные mini-products

- «Не знаете, что выбрать?» — мини-навигатор по задаче.
- «Проверить идею» и «Найти похожие проекты» — будущие отдельные модули/mini-tools, не скрытые функции чужого модуля.
- «Следующий полезный шаг» после каждого результата, основанный на contest + project context.

# 10. Примеры результатов


## 10.1. Архитектура example pack


> example_pack_id
> module_slug
> contest_slug
> version
> input_summary
> preview_sections
> assets: [{format, filename, path, size}]
> notes_for_user
> updated_at


## 10.2. UX примера

- Пример открывается внутри страницы модуля, не уводит в отдельный непонятный flow.
- Сверху: «Так выглядит результат»; ниже download button и preview.
- Кнопка «Запустить модуль» всегда видима.
- Письмо поддержки: preview текста + DOCX с правильным оформлением.
- Презентация: gallery 3–4 слайдов + PPTX.
- Каждый ready module–contest profile обязан иметь хотя бы один example pack перед публикацией.

# 11. Помощь, FAQ и чат помощи


## 11.1. Global help

Текущая страница помощи слишком короткая. Нужен поисковый центр ответов, построенный не на очевидностях, а на реальных затыках CJM.


| Категория | Обязательные вопросы |
| --- | --- |
| Начало | Что выбрать; нужен ли аккаунт; как выбрать конкурс; что делать, если модуль не готов. |
| Формы | Что обязательно; что значит «можно позже»; голос; подсказки; почему поле красное. |
| Результаты | Как скачать; как вернуться; как изменить; срок хранения; как прикрепить к проекту. |
| Запуски и оплата | Что такое запуск; когда списывается; что при технической ошибке; промокод; возврат в форму. |
| Конкурсы | Почему ответы отличаются; как сменить конкурс; где посмотреть поддерживаемые связки. |
| Эксперт | Что анализирует; лимит рекомендаций; что сохраняется; как удалить диалог. |
| Безопасность | Какие данные уходят в AI; срок хранения; как удалить; что не вводить. |
| Ошибки | Результат не создался; файл не скачивается; голос не работает; данные не сохранились. |


## 11.2. Module help modal

- Кнопка «Помощь» в шапке модуля.
- Открывает modal/drawer, не новую страницу.
- Сверху primary action «Задать вопрос».
- Ниже 5–8 module-specific FAQ, example links и contact support.
- FAQ pack versioned per module × contest.

## 11.3. Help chat scope


> Help-chat объясняет интерфейс и содержание полей, но не переписывает готовый результат. Для улучшения результата существует отдельный экспертный диалог.


> Input context:
> module_slug, contest_slug, current_step, field_key,
> FAQ pack, visible form labels, safe project context.
>
> Limits:
> short answers; no result rewriting; no invented contest rules;
> link to official documentation when available.


# 12. Экспертные рекомендации


## 12.1. UX

1. После успешного результата показать кнопку «Рекомендации эксперта».
1. Открыть messenger-like drawer: справа на desktop, full-screen на mobile.
1. До диалога показать уведомление о хранении сообщений 30 дней и кнопку «Продолжить».
1. Верхняя кнопка «Получить рекомендацию эксперта».
1. Первая рекомендация — наиболее критичная. Следующие две не повторяют предыдущие.
1. Пользователь может задать до 5 уточняющих сообщений.
1. Эксперт не меняет результат автоматически. При будущем «Применить» изменение должно быть diff-based и подтверждаться пользователем.

## 12.2. Recommended response schema


```json
{
  "recommendation_id": "uuid",
  "priority": "critical|important|optional",
  "title": "Короткий заголовок",
  "why": "Почему это влияет на критерий конкурса",
  "action": "Что конкретно изменить",
  "example": "Короткий пример формулировки или данных",
  "related_fields": ["..."],
  "criteria_refs": ["..."],
  "fingerprint": "для дедупликации"
}
```


## 12.3. Контекст эксперта

- Текущая форма и input snapshot.
- Сгенерированный результат.
- Contest criteria pack и module instructions.
- Сохраненный project context.
- Связанные разделы проекта, если они есть и пользователь имеет доступ.
- История уже выданных рекомендаций, чтобы не повторяться.

## 12.4. Общий system-prompt template


> Ты — эксперт по грантовым заявкам для конкурса {{contest_name}}.
> Анализируй только модуль {{module_name}} и переданный контекст.
> Выдай одну новую рекомендацию, которая сильнее всего улучшит результат по критериям конкурса.
> Не повторяй fingerprints предыдущих рекомендаций.
> Не выдумывай факты, источники, достижения и требования.
> Не обещай победу.
> Верни строго JSON по схеме ExpertRecommendation.


# 13. Данные, приватность и админ-доступ


## 13.1. Хранение диалогов


| Поле | Правило |
| --- | --- |
| Срок | 30 дней, затем hard delete по scheduled cleanup. |
| Идентификатор | Псевдонимизированный session/thread id. |
| Email/ФИО | Не отображать в админке; не включать как отдельные поля в thread. |
| PII | Перед сохранением выполнять redaction email, phone, passport-like numbers, INN/SNILS patterns where feasible. |
| Consent | consent_at + displayed_notice_version. |
| Удаление | Пользователь может удалить thread раньше 30 дней. |
| Логи приложения | Не писать content prompts/messages в stdout. |


## 13.2. Минимальная admin page

- Internal route, не виден в публичной навигации.
- Доступ только по allowlist account/email или отдельной admin session.
- Фильтры: дата, module, contest, help/expert, status.
- Видны redacted messages и session id, но не user email.
- Export CSV только вручную и с audit log.

# 14. Запуски, оплаты и будущие подписки


## 14.1. Текущая модель main

Коммерческая единица — универсальный запуск: одна генерация/расчет/сборка в любом доступном модуле. Существующий credit_ledger сохраняется как база.

- Первый бесплатный запуск отдельного модуля сохраняется, если это текущее бизнес-правило.
- При технической ошибке запуск не списывается.
- Оплата не сбрасывает форму и возвращает пользователя в тот же module + draft.
- Баланс доступен в header и account.

## 14.2. Будущие сценарии — только feature flags


```text
UNIVERSAL_RUNS_ENABLED=true
MODULE_SPECIFIC_RUNS_ENABLED=false
SUBSCRIPTIONS_ENABLED=false
SUBSCRIPTION_3_DAYS_ENABLED=false
SUBSCRIPTION_7_DAYS_ENABLED=false
SUBSCRIPTION_30_DAYS_ENABLED=false
```


## 14.3. Отдельный документ оплаты

Codex должен создать и поддерживать `docs/product/payment-model.md`. В нем: ledger semantics, порядок списания, payment states, idempotency, возврат в draft, feature flags, будущие 3/7/30-дневные планы. Публичный UI пока показывает только универсальные запуски.


# 15. Документация продукта в репозитории


## 15.1. Обязательная структура


```text
docs/product/
  LARI_MASTER_ARCHITECTURE.md
  implementation-status.md
  architecture-decisions.md
  module-registry.md
  contest-registry.md
  payment-model.md
  data-sources.md
  privacy-and-retention.md
  changelog.md
```


## 15.2. Правило обновления

- Любое изменение registry, API contract, DB schema, prompt pack, template, payment logic или user flow требует обновления соответствующего файла в том же commit.
- `implementation-status.md` содержит таблицу planned / in progress / ready / blocked по фазам и module–contest profiles.
- `architecture-decisions.md` ведется в формате ADR: дата, решение, причины, альтернативы, последствия.
- В корневой AGENTS.md добавить правило: сначала прочитать master architecture и update docs before final report.

# 16. Модуль расчета зарплаты


## 16.1. UX каркас

- Левая навигация перечисляет общие шаги и все должности; по клику переход к карточке без длинного скролла.
- Можно добавить N позиций; внутренние UUID отделяют одинаковые должности.
- Неполные позиции подсвечиваются красным только после submit/touch.
- Если есть хотя бы одна полностью заполненная позиция и есть неполные, показать secondary CTA «Рассчитать только заполненные должности».
- Неполные позиции остаются в draft и не попадают в result.
- Поле функционала поддерживает voice.
- Добавить optional поле «Почему специалист подходит для этой работы».
- В question mark: примеры опыта/званий; компетентность влияет на текст обоснования и expert review, но не автоматически повышает salary value.

## 16.2. Источники

Существующая production-логика ГородРабот + Работа России остается до отдельной достоверной интеграции Росстата. Росстат нельзя просить GigaChat «вспомнить» без подтвержденного web/tool access и backend verification.


### Проверка приложенных файлов

- `tab3-zpl-2025.xlsx` подходит частично: это среднемесячная начисленная зарплата по видам экономической деятельности в РФ за 2017–2025 годы. Есть культура/спорт, образование, информация и связь. Регионального разреза нет, поэтому файл не закрывает требование «регион × сфера».
- `itog_monitor_02-2024.rar` содержит 14 XLSX-файлов `02-24-01.xlsx` … `02-24-14.xlsx`. Содержание не подтверждено; для интеграции нужен распакованный ZIP/XLSX или описание структуры. Не считать базой до проверки заголовков, регионов, отраслей и методики.

## 16.3. Правило Росстата

- Показатель по профессии и официальный отраслевой показатель — разные сущности.
- До окончательного решения не выбирать механически максимум между должностью и отраслью.
- Хранить оба результата: profession_salary и official_industry_salary.
- В формуле по умолчанию использовать подтвержденный показатель по должности; официальный показатель — контроль и усиление обоснования.
- Решение о другом правиле отложено пользователем и не должно быть импровизировано Codex.

## 16.4. Функционал сотрудника

- AI формирует 2–4 предложения, связав обязанности, объем занятости и мероприятия.
- Raw user text никогда не вставляется напрямую.
- Описание должно быть развернутым, но ограниченным, ориентир 500–750 символов в зависимости от позиции.
- Expert recommendation проверяет связь функционала с календарным планом и компетентностью.

# 17. Модуль писем поддержки


## 17.1. Несколько партнеров

1. Общие данные проекта и contest вводятся один раз.
1. Ниже — repeatable partner cards.
1. «Дублировать» копирует карточку с новым UUID.
1. Пользователь меняет partner name, contribution, signatory и иные отличия.
1. Каждая карточка генерирует отдельный DOCX.
1. Result screen: download каждого файла + «Скачать все ZIP».
Рекомендуемый soft limit первой версии — 10 партнеров в одном запуске. Архитектура не должна жестко зависеть от числа 10; лимит конфигурируемый.


## 17.2. Пример

- Example tab показывает текст письма и скачиваемый DOCX с оформлением.
- Example pack зависит от конкурса, потому что адресат, формулировки и реквизиты могут отличаться.

# 18. Модуль актуальности и источников


## 18.1. Требования к источникам

- Дата публикации не ранее 2024 года.
- Sort preference: newest first, затем authority, relevance, geography match.
- Каждый факт с URL, названием источника, датой публикации и кратким объяснением релевантности.
- Backend проверяет URL и не принимает выдуманные ссылки.

## 18.2. Структура результата


```text
Основной ответ
  проблема
  целевая группа
  территория
  доказательства и динамика
  вывод для заявки

Полезные материалы (вне основного ответа)
  1. Опыт реализации смежных проектов
     название · конкурс/организация · регион · ссылка · почему похож
  2. Статистические материалы по теме
     источник · дата · показатель · ссылка
```


## 18.3. База проектов

- Первый источник — `pfki_ALL_WINNERS.xlsx` / локальная копия `~/Downloads/pfki_ALL_WINNERS.xlsx`.
- Не читать production-данные напрямую из Downloads: создать ingest pipeline и хранить нормализованный snapshot/version в data storage.
- База уже содержит названия, регионы, тематики, суммы, обоснование, цель, задачи, актуальность, целевые группы и URL заявки — достаточно для semantic search смежных проектов.
- Позже подключить ФПГ, Росмолодёжь и иные подтвержденные базы через такой же adapter interface.

# 19. Модуль презентаций


## 19.1. Зафиксировано

- Выход — PPTX.
- 8–12 слайдов.
- Без логотипа LARI в пользовательской презентации.
- Узнаваемый стиль, редактируемые элементы, корректная кириллица.

## 19.2. Архитектура до получения шаблона

- Не финализировать дизайн слайдов до передачи пользователем PPTX template и 2–3 эталонов.
- Сейчас подготовить data contract: slide plan, content slots, images, optional charts, theme id.
- Template engine должен уметь заполнять placeholders и не рисовать каждый слайд с нуля в коде.
- Example pack: gallery preview + PPTX download.

# 20. Остальные и новые модули


## 20.1. Действующие модули

- Нормативные акты и программы.
- Сценарный план.
- Проверка готовой заявки — coming soon.
Каждый переносится на common module shell и получает contest profile, example pack, FAQ pack, field help и expert profile. Generic prompt `_build_ai_prompt` должен быть заменен на module–contest prompt packs.


## 20.2. Новые модули

Новый модуль добавляется registry/config, а не копированием page. Минимальный definition of ready: metadata, supported contests, form schema, prompt pack, result schema, template, example, FAQ, expert criteria, tests, documentation.


# 21. Мобильная версия и доступность


## 21.1. Breakpoints QA


```text
390 px   — небольшой телефон
430 px   — крупный телефон
768 px   — планшет
1024 px  — laptop/tablet landscape
1440 px  — desktop
```


## 21.2. Обязательные проверки

- WCAG 2.2 AA contrast, visible focus, keyboard navigation.
- 44×44 px controls; no tiny icon-only actions without label/aria-label.
- Error not communicated only by color.
- Modal/drawer traps focus and restores it after close.
- Reduced motion respected.
- Sidebar/drawer does not cover CTA or input content.
- Long Russian labels wrap without clipping.
- Touch behavior exists for every hover-only interaction.

# 22. Backend/API/DB architecture


## 22.1. API outline


```text
GET  /api/contests
GET  /api/modules
GET  /api/modules/{module}/profiles/{contest}
GET  /api/modules/{module}/examples?contest=...
GET  /api/modules/{module}/faq?contest=...
POST /api/module-runs
GET  /api/module-runs/{run_id}/result
POST /api/module-runs/{run_id}/expert/recommendations
POST /api/module-runs/{run_id}/expert/messages
DELETE /api/expert-threads/{thread_id}
POST /api/help/chat
GET  /api/usage
POST /api/payments/create
```


## 22.2. Module run request


```json
{
  "module_slug": "support-letter",
  "contest_slug": "pfki",
  "project_id": "optional",
  "inputs": {...},
  "profile_version": "..."
}
```


## 22.3. DB migrations


| Таблица/поле | Изменение |
| --- | --- |
| projects | competition string → contest_slug; сохранить legacy migration. |
| module_runs | add contest_slug, profile_version, project_id, error_code. |
| works | add contest_slug; перестать возвращать hardcoded ПФКИ. |
| module_drafts | owner, module_slug, contest_slug, project_id, payload_json, updated_at. |
| expert_threads/messages | run_id, consent, redacted content, sequence, expires_at. |
| help_threads/messages | module/contest/field context, redacted content, expires_at. |
| product_events | Только технические события без текстов заявки: step viewed, help opened, example downloaded, run completed. |


## 22.4. Backward compatibility

- Старые runs/projects со строкой ПФКИ мигрировать в contest_slug=pfki.
- Старые frontend payload без contest_slug временно трактовать как pfki, но помечать legacy; после migration window удалить fallback.
- Старые localStorage drafts мигрировать по version key.

# 23. Prompt architecture


## 23.1. Prompt pack


```text
PromptPack
  system_prompt
  user_prompt_template
  input_schema
  output_schema
  max_lengths
  retry_policy
  forbidden_claims
  evidence_policy
  postprocessors
  version
  tests
```


## 23.2. Правила

- Prompt выбирается backend по module_slug + contest_slug + profile_version.
- Строгий JSON для структурированных блоков; backend валидирует Pydantic schema.
- Никаких точных фактов/URL без supplied data или tool-verified evidence.
- AI не выполняет deterministic calculations, naming, formatting и file assembly.
- Каждый prompt pack имеет golden tests: normal, short, incomplete, contradictory, rude, malicious, exotic.
- Fallback не должен ухудшать официальный документ: безопасный deterministic text лучше raw user input.

# 24. Тестирование и контроль качества


## 24.1. Test layers


| Слой | Что проверять |
| --- | --- |
| Registry | Уникальные slugs, готовые profiles имеют все ids/assets, отсутствует дублирование frontend/backend. |
| Unit | Normalization, validators, prompt parsers, calculations, TTL cleanup, access ledger. |
| Contract | Frontend request соответствует backend schema; legacy migrations. |
| Golden prompt | Структура JSON, ограничения длины, no hallucinated sources, no repeated recommendations. |
| File | DOCX/PPTX открывается, placeholders заменены, кириллица, правильное имя. |
| E2E | Contest selection → example/start → form → result → expert/help → return to draft. |
| Accessibility | Keyboard, focus, contrast, screen-reader names, touch targets. |
| Responsive | 390/430/768/1024/1440 screenshots. |
| Privacy | No user text in logs; redaction; 30-day cleanup; delete thread. |


## 24.2. Обязательные edge cases

- Contest profile preparing.
- Смена конкурса после заполнения части формы.
- Один готовый и несколько неполных repeatable cards.
- AI JSON с markdown/prefix.
- AI timeout; file generation success/failure.
- Payment success, failure, duplicate webhook, return to draft.
- No clipboard API, no microphone permission, expired anonymous work.
- 5+ contest chips on touch device.
- Expert recommendation 2/3 не повторяет первую.

# 25. Этапы реализации


| Фаза | Содержание | Definition of done |
| --- | --- | --- |
| 0. Foundation docs | Master docs, ADR, registry schemas, feature flags, migration plan. | Документы созданы; no code behavior change; tests validate registry shape. |
| 1. Global shell + multi-contest | Branding, landing cards, selector, matrix, unsupported stub, run balance, common module shell, mobile navigation. | 4 contests visible; existing PFKI flows работают; no PFKI in generic branding. |
| 2. Example/help/question marks | Example packs, global help, module modal, contextual question marks. | Каждый ready PFKI module имеет example + FAQ; mobile QA. |
| 3. Expert recommendations | Thread UX, prompts, 3 recommendations, 5 follow-ups, storage/retention/admin. | Consent, redaction, TTL, no repeats, audit tests. |
| 4. Salary | Sidebar positions, partial calculation, competence field, Rosstat adapter after verified DB. | Current sources stable; incomplete cards behavior; expert criteria. |
| 5. Support letters | Multiple partners, duplicate, separate DOCX, ZIP, examples. | 10 partners QA; files correct. |
| 6. Actuality | 2024+ research, evidence URLs, useful materials, PFKI analogs DB. | No unverified URLs; separate materials block. |
| 7. Presentation | Template-driven 8–12 PPTX after user assets. | Visual QA with supplied template. |
| 8. Other/new modules | Move all modules to profiles; add new tasks. | No slug-specific page logic except specialized renderers where justified. |
| 9. Payments/subscriptions | Universal runs hardened; future 3/7/30 plans behind flags. | Payment model doc; no hidden activation. |


> Рекомендуемый следующий шаг
> Следующая практическая задача Codex после этого документа: выполнить только фазу 0 и детальный implementation plan фазы 1. Не начинать salary/support-letter/presentation одновременно.


# 26. Инструкция Codex и acceptance criteria


## 26.1. Как работать с документом

1. Прочитать текущий repository и данный документ полностью.
1. Не повторять в каждом следующем prompt общий контекст продукта; ссылаться на `docs/product/LARI_MASTER_ARCHITECTURE.md`.
1. Перед кодом провести design/impact analysis по реальным файлам.
1. Составить small-step implementation plan с тестами и rollback.
1. Работать только в main, если пользователь не дал другую команду. Не поднимать test environment самостоятельно.
1. Не делать массовый rewrite; сохранять рабочие PFKI flows.
1. После каждой фазы обновить product docs и implementation status.
1. В финальном отчете: commit, changed files, migrations, tests, screenshots, deployment status, known limitations.

## 26.2. Global acceptance criteria

- Публичный бренд не привязан к ПФКИ.
- Contest selection работает и сохраняется в project context.
- Module–contest profile является единственным способом выбрать prompt/template/example/FAQ.
- Неподдерживаемая связка не запускает generic AI prompt.
- Landing cards показывают supported contests и оба действия: start/example.
- Left navigation desktop и mobile drawer работают без horizontal scroll.
- Help modal, question marks и global help не дублируют друг друга.
- Expert recommendations имеют лимиты, consent, TTL и дедупликацию.
- Universal run balance виден и payment flow сохраняет draft.
- Все ready profiles имеют examples and tests.
- В logs нет raw user content.
- Docs обновлены в том же commit.

# 27. Зависимости и данные, которые еще нужны


| Зависимость | Статус | Что нужно от пользователя |
| --- | --- | --- |
| Положения/методички ФПГ, Росмолодёжь, Гранты Первых | Не переданы в текущем наборе | Актуальные PDF/DOCX, формы заявки, критерии и примеры приложений. |
| Росстат регион × отрасль | Не подтверждено | Распаковать `itog_monitor_02-2024.rar` в ZIP/XLSX или дать описание структуры; предоставить стабильную выгрузку региона × ОКВЭД × период. |
| PFKI winners | Доступно | Использовать существующий `pfki_ALL_WINNERS.xlsx`; затем подготовить versioned ingest snapshot. |
| ФПГ/Росмолодёжь winners | Позже | Выгрузки/API/поисковые страницы. |
| Presentation template | Позже | PPTX template, 2–3 сильных референса, цвета/шрифты/изображения. |
| Normal/abnormal inputs | После module architecture | Для каждого приоритетного модуля: полный, короткий, неполный, противоречивый, грубый, ошибочные числа, экзотический кейс, идеальный и недопустимый result. |


# 28. Источники и референсы


## 28.1. Внутренние материалы

- ui ux library lary.docx — accessibility, CJM, forms, microinteractions, navigation, service design, payments and LARI rules.
- repomix-output.xml — snapshot текущего репозитория, routes, services, data contracts and docs.
- tab3-zpl-2025.xlsx — salary by OKVED for Russian Federation, 2017–2025.
- itog_monitor_02-2024.rar — 14 XLSX files; requires unpacking and schema verification.
- pfki_ALL_WINNERS.xlsx — PFKI winner projects and full project fields.

## 28.2. Публичные референсы

- CHECK GRANT: https://checkgrant.ru/
- ГрантоРез: https://grantorez.ru/
- Школа грантов: https://shkolagrantov.ru/
- Legacy LARI: https://lary.pro/
- MPSTATS: https://mpstats.io/
- Current LARI production: https://web-production-532a8.up.railway.app/
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- WAI Older Users: https://www.w3.org/WAI/older-users/
- GOV.UK Service Manual: https://www.gov.uk/service-manual

# Финальная команда для Codex


> Первое действие
> Сохранить этот документ как `docs/product/LARI_MASTER_ARCHITECTURE.md` в текстовой форме, создать остальные product docs из раздела 15 и подготовить implementation plan только для фаз 0–1. Кодовые изменения пользовательского поведения не начинать до утверждения плана.
