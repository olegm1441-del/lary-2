import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();
const modulesPath = join(root, "app", "data", "modules.json");
const prohibitedTerms = ["FAQ", "Dashboard", "dashboard", "prompt", "Prompt", "tokens", "Tokens", "credits", "Credits", "кредиты", "токены", "промпт", "MVP", "P0/P1", "in-memory", "runtime", "demo"];
const requiredActiveSlugs = [
  "social-research",
  "legal-acts",
  "salary",
  "support-letter",
  "presentation",
  "scenario-plan",
];

function readModules() {
  const raw = readFileSync(modulesPath, "utf8");
  return JSON.parse(raw);
}

function flattenStrings(value) {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(flattenStrings);
  if (value && typeof value === "object") return Object.values(value).flatMap(flattenStrings);
  return [];
}

test("module data file exists", () => {
  assert.equal(existsSync(modulesPath), true);
});

test("six MVP modules are active and application check is coming soon", () => {
  const modules = readModules();
  const active = modules.filter((module) => module.status === "active");
  const comingSoon = modules.filter((module) => module.status === "coming_soon");

  assert.equal(active.length, 6);
  assert.deepEqual(active.map((module) => module.slug), requiredActiveSlugs);
  assert.equal(comingSoon.length, 1);
  assert.equal(comingSoon[0].slug, "check-application");
});

test("each module has enough UI metadata for first MVP screens", () => {
  const modules = readModules();

  for (const laryModule of modules) {
    assert.match(laryModule.title, /\S/);
    assert.match(laryModule.shortTitle, /\S/);
    assert.match(laryModule.promise, /\S/);
    assert.match(laryModule.duration, /\S/);
    assert.ok(Array.isArray(laryModule.outputFormats));
    assert.ok(laryModule.outputFormats.length >= 1);
    assert.ok(Array.isArray(laryModule.fields));
    assert.ok(laryModule.fields.length >= 4);
    assert.ok(Array.isArray(laryModule.resultActions));
    assert.ok(laryModule.resultActions.length >= 3);
  }
});

test("user-facing content avoids technical jargon banned by the product spec", () => {
  const modules = readModules();
  const allCopy = flattenStrings(modules).join("\n");

  for (const term of prohibitedTerms) {
    assert.equal(allCopy.includes(term), false, `Found prohibited user-facing term: ${term}`);
  }
});

test("required MVP routes exist", () => {
  const requiredFiles = [
    "app/page.tsx",
    "app/modules/page.tsx",
    "app/m/[slug]/page.tsx",
    "app/run/[id]/result/page.tsx",
    "app/pay/page.tsx",
    "app/account/page.tsx",
    "app/help/page.tsx",
    "app/security/page.tsx",
    "app/contacts/page.tsx",
    "app/docs/[slug]/page.tsx",
  ];

  for (const file of requiredFiles) {
    assert.equal(existsSync(join(root, file)), true, `${file} should exist`);
  }
});

test("routes do not expose raw technical errors to users", () => {
  const routeFiles = [
    "app/page.tsx",
    "app/modules/page.tsx",
    "app/m/[slug]/page.tsx",
    "app/run/[id]/result/page.tsx",
    "app/pay/page.tsx",
    "app/account/page.tsx",
    "app/help/page.tsx",
    "app/security/page.tsx",
    "app/contacts/page.tsx",
    "app/docs/[slug]/page.tsx",
  ];

  for (const file of routeFiles) {
    if (!existsSync(join(root, file))) continue;
    const source = readFileSync(join(root, file), "utf8");
    assert.equal(source.includes("500 Internal Server Error"), false, `${file} exposes raw 500 copy`);
    assert.equal(source.includes("GigaChat request failed"), false, `${file} exposes provider failure copy`);
  }
});

test("frontend has API client and voice-enabled module runner", () => {
  const requiredFiles = [
    "app/lib/api-client.ts",
    "app/components/module-runner.tsx",
    "app/components/result-viewer.tsx",
  ];

  for (const file of requiredFiles) {
    assert.equal(existsSync(join(root, file)), true, `${file} should exist`);
  }

  const apiClient = readFileSync(join(root, "app/lib/api-client.ts"), "utf8");
  const runner = readFileSync(join(root, "app/components/module-runner.tsx"), "utf8");
  const laryUi = readFileSync(join(root, "app/components/lary-ui.tsx"), "utf8");
  const mobileMenuPath = join(root, "app/components/mobile-menu.tsx");
  const mobileMenu = existsSync(mobileMenuPath) ? readFileSync(mobileMenuPath, "utf8") : "";
  const fieldAssistantHint = readFileSync(join(root, "app/components/field-assistant-hint.tsx"), "utf8");
  const attemptStatus = readFileSync(join(root, "app/components/module-attempt-status.tsx"), "utf8");
  const moduleAttempts = readFileSync(join(root, "app/lib/module-attempts.ts"), "utf8");
  const resultViewer = readFileSync(join(root, "app/components/result-viewer.tsx"), "utf8");
  const resultPage = readFileSync(join(root, "app/run/[id]/result/page.tsx"), "utf8");
  const modulePage = readFileSync(join(root, "app/m/[slug]/page.tsx"), "utf8");
  const homePage = readFileSync(join(root, "app/page.tsx"), "utf8");
  const emailResultForm = readFileSync(join(root, "app/components/email-result-form.tsx"), "utf8");
  const paymentPanel = readFileSync(join(root, "app/components/payment-panel.tsx"), "utf8");
  const accountWorkspace = readFileSync(join(root, "app/components/account-workspace.tsx"), "utf8");

  assert.equal(apiClient.includes("NEXT_PUBLIC_API_URL"), true);
  assert.equal(apiClient.includes("startsWith(\"http://\")"), true);
  assert.equal(apiClient.includes("https://"), true);
  assert.equal(runner.includes("FIELD_KEYS_BY_MODULE"), false);
  assert.equal(runner.includes("getFieldKey"), true);
  assert.equal(runner.includes("FieldAssistantHint"), true);
  assert.equal(runner.includes("getFieldQualityHint"), true);
  assert.equal(runner.includes("setTimeout"), true);
  assert.equal(runner.includes("1000"), true);
  assert.equal(runner.includes("/api/field-assistant/analyze"), true);
  assert.equal(runner.includes("Сделать бесплатный запуск"), false);
  assert.equal(runner.includes("Запустить бесплатно"), true);
  assert.equal(runner.includes("Запустить модуль"), false);
  assert.equal(runner.includes("за 320 руб / бесплатно"), false);
  assert.equal(runner.includes("Наговорить ответ"), true);
  assert.equal(runner.includes("Наговорить описание"), true);
  assert.equal(runner.includes("Записать заново"), false);
  assert.equal(runner.includes("/api/speech/transcribe"), true);
  assert.equal(runner.includes("audio/x-pcm;bit=16;rate=16000"), true);
  assert.equal(runner.includes("/api/module-runs"), true);
  assert.equal(runner.includes("/api/usage"), true);
  assert.equal(runner.includes("credentials: \"include\""), true);
  assert.equal(runner.includes("Проверить данные"), false);
  assert.equal(runner.includes("Проверка перед запуском"), false);
  assert.equal(runner.includes("Проверьте основные данные"), false);
  assert.equal(runner.includes("Не знаю"), true);
  assert.equal(runner.includes("fillUnknownField"), true);
  assert.equal(runner.includes("Все обязательные поля заполнены."), true);
  assert.equal(runner.includes("Можно запускать. Есть подсказки, которые улучшат результат."), true);
  assert.equal(runner.includes("Заполните обязательные поля, чтобы запустить."), true);
  assert.equal(runner.includes("{key}:"), false);
  assert.equal(runner.includes("Использовать 1 запуск"), true);
  assert.equal(laryUi.includes("<details"), false);
  assert.equal(laryUi.includes("MobileMenu"), true);
  assert.equal(mobileMenu.includes("fixed"), true);
  assert.equal(mobileMenu.includes("z-[100]"), true);
  assert.equal(mobileMenu.includes("overflow = \"hidden\""), true);
  assert.equal(mobileMenu.includes("Escape"), true);
  assert.equal(mobileMenu.includes("Начать"), true);
  assert.equal(fieldAssistantHint.includes("max-w-full"), true);
  assert.equal(fieldAssistantHint.includes("overflow-wrap:anywhere"), true);
  assert.equal(fieldAssistantHint.includes("flex-wrap"), true);
  assert.equal(laryUi.includes("Запуски и промокод"), false);
  assert.equal(laryUi.includes("Попытка"), false);
  assert.equal(attemptStatus.includes("1 бесплатный запуск для этой задачи"), true);
  assert.equal(attemptStatus.includes("1 бесплатный запуск в этом модуле"), false);
  assert.equal(attemptStatus.includes("необходимо купить запуск модуля"), true);
  assert.equal(attemptStatus.includes("/api/usage"), true);
  assert.equal(moduleAttempts.includes("localStorage"), true);
  assert.equal(resultViewer.includes("/result"), true);
  assert.equal(resultViewer.includes("Не получилось подготовить результат"), true);
  assert.equal(resultViewer.includes("Результат готов"), true);
  assert.equal(resultViewer.includes("Скачать файл"), true);
  assert.equal(resultViewer.includes("Отправить на email"), true);
  assert.equal(resultViewer.includes("Прикрепить к проекту"), true);
  assert.equal(resultViewer.includes("Не закрывайте страницу."), true);
  assert.equal(resultViewer.includes("Скопировать"), true);
  assert.equal(resultViewer.includes("Улучшить"), true);
  assert.equal(resultViewer.includes("Попробовать еще раз"), true);
  assert.equal(resultViewer.includes("Вернуться к форме"), true);
  assert.equal(resultViewer.includes("Написать в поддержку"), true);
  assert.equal(resultViewer.includes("Лари готовит результат"), true);
  assert.equal(resultPage.includes("Если результат еще готовится или произошла ошибка"), false);
  assert.equal(resultPage.includes("Результат готов к скачиванию"), false);
  assert.equal(resultPage.includes("Действия"), false);
  assert.equal(resultPage.includes("Сохранить в мои работы"), false);
  assert.equal(resultPage.includes("Чтобы сохранить надолго, отправьте файл на почту."), true);
  assert.equal(emailResultForm.includes("Сохранить и отправить ссылку на результат"), true);
  assert.equal(emailResultForm.includes("Лари сохранит работу в личном кабинете и отправит ссылку для входа. Пароль не нужен."), true);
  assert.equal(emailResultForm.includes("id=\"email-result\""), true);
  assert.equal(emailResultForm.includes("type=\"email\""), true);
  assert.equal(emailResultForm.includes("type=\"password\""), false);
  assert.equal(emailResultForm.includes("/api/auth/magic-link/request"), true);
  assert.equal(paymentPanel.includes("credentials: \"include\""), true);
  assert.equal(accountWorkspace.includes("/api/account/works"), true);
  assert.equal(accountWorkspace.includes("/api/projects"), true);
  assert.equal(accountWorkspace.includes("/api/auth/magic-link/request"), true);
  assert.equal(accountWorkspace.includes("/api/account/works/${runId}"), true);
  assert.equal(accountWorkspace.includes("Пока нет работ. Выберите задачу и запустите любой модуль"), true);
  assert.equal(accountWorkspace.includes("Прикрепить к проекту"), true);
  assert.equal(accountWorkspace.includes("Удалить"), true);
  assert.equal(modulePage.includes("Поля собраны по ТЗ"), false);
  assert.equal(modulePage.includes("Форма модуля"), false);
  assert.equal(modulePage.includes("Ответьте на вопросы"), true);
  assert.equal(modulePage.includes("Лари обработает ответы и подготовит рабочий файл для скачивания."), true);
  assert.equal(modulePage.includes("При запуске нейросеть проанализирует задачу и подготовит файл для скачивания."), false);
  assert.equal(modulePage.includes("ApiStatePanel"), false);
  assert.equal(modulePage.includes("Если что-то идет не так"), false);
  assert.equal(homePage.includes("DOCX/PDF"), false);
  assert.equal(homePage.includes("DOCX/PDF/PPTX"), false);
  assert.equal(homePage.includes("рабочий редактируемый файл"), true);
});

test("presentation form avoids duplicated type and manual slide count", () => {
  const modules = readModules();
  const presentation = modules.find((module) => module.slug === "presentation");
  const fieldLabels = presentation.fields.map((field) => field.label);
  const laryData = readFileSync(join(root, "app/lib/lary-data.ts"), "utf8");

  assert.equal(fieldLabels.includes("Тип презентации"), false);
  assert.equal(fieldLabels.includes("Количество слайдов"), true);
  assert.equal(fieldLabels.includes("Шаблон"), true);
  assert.equal(laryData.includes("Официальный"), true);
  assert.equal(laryData.includes("Минималистичный"), true);
  assert.equal(laryData.includes("10–12 рекомендуется"), true);
});

test("P1 module forms include split salary fields and scenario helper choices", () => {
  const modules = readModules();
  const salary = modules.find((module) => module.slug === "salary");
  const supportLetter = modules.find((module) => module.slug === "support-letter");
  const scenario = modules.find((module) => module.slug === "scenario-plan");
  const laryData = readFileSync(join(root, "app/lib/lary-data.ts"), "utf8");

  const salaryLabels = salary.fields.map((field) => field.label);
  assert.equal(salaryLabels.includes("Количество сотрудников в этой роли"), true);
  assert.equal(salaryLabels.includes("Занятость одного сотрудника, %"), true);
  assert.equal(salaryLabels.includes("Занятость и количество людей"), false);

  const supportLabels = supportLetter.fields.map((field) => field.label);
  assert.equal(supportLabels.includes("Тип поддержки"), true);
  assert.equal(supportLabels.includes("Вклад в рублях"), true);
  assert.equal(supportLabels.includes("Стиль письма"), true);

  assert.equal(scenario.fields[0].type, "chips");
  assert.equal(laryData.includes("Документальный фильм"), true);
  assert.equal(laryData.includes("Спортивно-культурное событие"), true);
});

test("P0 public copy and account gate match revision spec", () => {
  const homePage = readFileSync(join(root, "app/page.tsx"), "utf8");
  const modulesPage = readFileSync(join(root, "app/modules/page.tsx"), "utf8");
  const accountPage = readFileSync(join(root, "app/account/page.tsx"), "utf8");
  const accountWorkspace = readFileSync(join(root, "app/components/account-workspace.tsx"), "utf8");
  const payPage = readFileSync(join(root, "app/pay/page.tsx"), "utf8");
  const paymentPanel = readFileSync(join(root, "app/components/payment-panel.tsx"), "utf8");
  const laryUi = readFileSync(join(root, "app/components/lary-ui.tsx"), "utf8");
  const mobileMenu = readFileSync(join(root, "app/components/mobile-menu.tsx"), "utf8");
  const docsPage = readFileSync(join(root, "app/docs/[slug]/page.tsx"), "utf8");
  const securityPage = readFileSync(join(root, "app/security/page.tsx"), "utf8");
  const helpPage = readFileSync(join(root, "app/help/page.tsx"), "utf8");

  assert.equal(homePage.includes("Помощник для документов заявки ПФКИ"), true);
  assert.equal(homePage.includes("Модульный помощник для заявки ПФКИ"), false);
  assert.equal(homePage.includes("Лари 2.0 MVP 0.1"), false);
  assert.equal(homePage.includes("Соберите рабочие документы для заявки ПФКИ быстрее и без лишних ошибок"), true);
  assert.equal(homePage.includes("Выберите задачу"), true);
  assert.equal(homePage.includes("По одному бесплатному запуску для каждой задачи"), true);
  assert.equal(homePage.includes("По одному бесплатному запуску в каждом модуле"), false);
  assert.equal(homePage.includes("Показать все задачи"), true);
  assert.equal(homePage.includes("Выбрать модуль"), false);
  assert.equal(homePage.includes("Что нужно сделать сегодня?"), true);
  assert.equal(homePage.includes("text-[44px]"), true);

  assert.equal(modulesPage.includes("Что нужно подготовить для заявки ПФКИ?"), true);
  assert.equal(modulesPage.includes("Выберите задачу. Каждый запуск дает один рабочий файл или разбор."), true);
  assert.equal(modulesPage.includes("фильтр по конкурсам"), false);

  assert.equal(laryUi.includes("Посмотреть пример"), true);
  assert.equal(laryUi.includes("Сообщить, когда модуль будет готов"), true);
  assert.equal(laryUi.includes("Результат можно скачать и доработать вручную."), true);
  assert.equal(laryUi.includes("Закройте одну задачу по заявке."), false);
  assert.equal(laryUi.includes("MVP"), false);
  assert.equal(laryUi.includes("Доступно"), true);
  assert.equal(laryUi.includes("MobileMenu"), true);
  for (const navLabel of ["Модули", "Как работает", "Цены", "Безопасность", "Помощь", "Войти"]) {
    assert.equal(`${laryUi}\n${mobileMenu}`.includes(navLabel), true, `mobile menu should include ${navLabel}`);
  }

  assert.equal(accountPage.includes("Войти в личный кабинет"), true);
  assert.equal(accountPage.includes("Вход без пароля"), false);
  assert.equal(accountWorkspace.includes("Вход без пароля"), true);
  assert.equal(accountWorkspace.includes("Войти в личный кабинет"), false);
  assert.equal(accountWorkspace.includes("Укажите email, чтобы получить ссылку для входа. Пароль не нужен."), true);
  assert.equal(accountWorkspace.includes("placeholder=\"name@example.ru\""), true);
  assert.equal(accountWorkspace.includes("projectMessage"), true);
  assert.equal(accountWorkspace.includes("Проект создан. Его можно использовать для новых работ."), true);
  assert.equal(accountWorkspace.includes("type=\"email\""), true);
  assert.equal(accountWorkspace.includes("Социальная значимость"), false);
  assert.equal(accountWorkspace.includes("Сегодня"), false);

  assert.equal(payPage.includes("PaymentPanel"), true);
  assert.equal(paymentPanel.includes("Промокод"), true);
  assert.equal(paymentPanel.includes("Введите код, если он у вас есть."), true);
  assert.equal(paymentPanel.includes("Например: LARY-START"), true);
  assert.equal(paymentPanel.includes("Применить"), true);

  assert.equal(docsPage.includes("Юридическая проверка"), false);
  assert.equal(docsPage.includes("Текст адаптирован под MVP"), false);
  assert.equal(docsPage.includes("проверить с юристом"), false);
  assert.equal(securityPage.includes("Нельзя обещать абсолютную безопасность"), false);
  assert.equal(securityPage.toLowerCase().includes("что собираем"), true);
  assert.equal(helpPage.includes("Что хотите узнать?"), true);
  assert.equal(helpPage.includes("Оплата и промокоды"), true);
});

test("P2 public screens do not expose internal development markers", () => {
  const publicFiles = [
    "app/page.tsx",
    "app/modules/page.tsx",
    "app/m/[slug]/page.tsx",
    "app/run/[id]/result/page.tsx",
    "app/pay/page.tsx",
    "app/account/page.tsx",
    "app/help/page.tsx",
    "app/security/page.tsx",
    "app/docs/[slug]/page.tsx",
    "app/components/lary-ui.tsx",
    "app/components/payment-panel.tsx",
    "app/components/email-result-form.tsx",
    "app/components/account-workspace.tsx",
    "app/data/modules.json",
  ];
  const banned = ["MVP", "P0/P1", "in-memory", "runtime", "AI endpoint"];

  for (const file of publicFiles) {
    const source = readFileSync(join(root, file), "utf8");
    for (const term of banned) {
      assert.equal(source.includes(term), false, `${file} exposes ${term}`);
    }
  }
});

test("P2 example result links render a non-real-application warning", () => {
  const modulePage = readFileSync(join(root, "app/m/[slug]/page.tsx"), "utf8");
  const laryUi = readFileSync(join(root, "app/components/lary-ui.tsx"), "utf8");

  assert.equal(laryUi.includes("?example=1"), true);
  assert.equal(modulePage.includes("пример, не настоящая заявка"), true);
  for (const slug of requiredActiveSlugs) {
    assert.equal(modulePage.includes(`"${slug}"`) || modulePage.includes(`${slug}:`), true, `example should include ${slug}`);
  }
});

test("web railway workspace file is valid for pnpm auto-detection", () => {
  const workspace = readFileSync(join(root, "pnpm-workspace.yaml"), "utf8");
  assert.equal(workspace.includes("packages:"), true);
  assert.equal(workspace.includes("- \".\""), true);
});
