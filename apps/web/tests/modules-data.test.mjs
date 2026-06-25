import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();
const modulesPath = join(root, "app", "data", "modules.json");
const prohibitedTerms = ["FAQ", "Dashboard", "dashboard", "prompt", "Prompt", "tokens", "Tokens", "credits", "Credits", "кредиты", "токены", "промпт"];
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
  const resultViewer = readFileSync(join(root, "app/components/result-viewer.tsx"), "utf8");
  const resultPage = readFileSync(join(root, "app/run/[id]/result/page.tsx"), "utf8");

  assert.equal(apiClient.includes("NEXT_PUBLIC_API_URL"), true);
  assert.equal(apiClient.includes("startsWith(\"http://\")"), true);
  assert.equal(apiClient.includes("https://"), true);
  assert.equal(runner.includes("FIELD_KEYS_BY_MODULE"), true);
  assert.equal(runner.includes("getFieldKey"), true);
  assert.equal(runner.includes("/api/modules/"), true);
  assert.equal(runner.includes("/validate-inputs"), true);
  assert.equal(runner.includes("Запустить модуль бесплатно"), true);
  assert.equal(runner.includes("за 320 руб / бесплатно"), false);
  assert.equal(runner.includes("Наговорить"), true);
  assert.equal(runner.includes("Записать заново"), false);
  assert.equal(runner.includes("/api/speech/transcribe"), true);
  assert.equal(runner.includes("audio/x-pcm;bit=16;rate=16000"), true);
  assert.equal(runner.includes("/api/module-runs"), true);
  assert.equal(resultViewer.includes("/result"), true);
  assert.equal(resultViewer.includes("Не получилось подготовить ответ"), true);
  assert.equal(resultPage.includes("Если результат еще готовится или произошла ошибка"), false);
  assert.equal(resultPage.includes("Действия"), false);
  assert.equal(resultPage.includes("Сохранить в мои работы"), false);
});

test("web railway workspace file is valid for pnpm auto-detection", () => {
  const workspace = readFileSync(join(root, "pnpm-workspace.yaml"), "utf8");
  assert.equal(workspace.includes("packages:"), true);
  assert.equal(workspace.includes("- \".\""), true);
});
