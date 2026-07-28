import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const { buildModuleRoute } = await import("../app/lib/module-route.ts");

test("frontend has one shared registry adapter and generic brand", () => {
  const adapter = read("app/lib/product-registry.ts");
  assert.match(adapter, /product-config\/contests\.json/);
  assert.match(adapter, /getSupportedContests/);
  for (const file of ["app/layout.tsx", "app/page.tsx", "app/components/lary-ui.tsx"]) {
    const source = read(file);
    assert.equal(source.includes("помощник по заявке ПФКИ"), false);
  }
});

test("contest selector and preparing state are explicit", () => {
  const selector = read("app/components/contest-selector.tsx");
  assert.match(selector, /Выберите конкурс/);
  assert.match(selector, /Лари подстроит вопросы, подсказки и результат/);
  const page = read("app/m/[slug]/page.tsx");
  assert.match(page, /Для этого конкурса модуль пока готовится/);
  assert.match(page, /Выбрать другой конкурс/);
  assert.match(page, /profile\?\.status === "ready"/);
});

test("draft keys isolate module contest and project", () => {
  const drafts = read("app/lib/module-drafts.ts");
  const runner = read("app/components/module-runner.tsx");
  assert.match(drafts, /lary:draft:v2:/);
  assert.match(drafts, /projectId \\|\\| "anonymous"/);
  assert.match(runner, /loadedDraftKeyRef/);
  assert.match(runner, /loadedDraftKeyRef\.current !== key/);
});

test("module shell exposes desktop navigation, mobile stages and typed future slots", () => {
  const shell = read("app/components/module-shell.tsx");
  assert.match(shell, /Этап .* из/);
  assert.match(shell, /aria-label="Этапы модуля"/);
  assert.match(shell, /helpSlot\?:/);
  assert.match(shell, /expertSlot\?:/);
});

test("run balance only exposes universal paid runs", () => {
  const balance = read("app/components/run-balance.tsx");
  assert.match(balance, /Запуски:/);
  assert.match(balance, /Купить запуск/);
  assert.equal(balance.includes("md:inline-flex"), false);
  assert.match(balance, /min-h-11/);
  assert.match(balance, /sm:hidden/);
  for (const banned of ["ledger", "credits", "tokens"]) assert.equal(balance.includes(banned), false);
});

test("module routes preserve project context and isolate example intent by contest", () => {
  assert.equal(
    buildModuleRoute({
      moduleSlug: "salary",
      contestSlug: "pfki",
      projectId: "abc",
      mode: "start",
    }),
    "/m/salary?contest=pfki&project_id=abc&mode=start",
  );
  assert.equal(
    buildModuleRoute({
      moduleSlug: "salary",
      projectId: "abc",
      intent: "example",
    }),
    "/m/salary?project_id=abc&intent=example",
  );
  assert.equal(
    buildModuleRoute(
      {
        moduleSlug: "salary",
        projectId: "abc",
        intent: "example",
        realExampleContests: ["pfki"],
      },
      "pfki",
    ),
    "/m/salary?contest=pfki&project_id=abc&example=1",
  );
  assert.equal(
    buildModuleRoute(
      {
        moduleSlug: "salary",
        projectId: "abc",
        intent: "example",
        realExampleContests: ["pfki"],
      },
      "fpg",
    ),
    "/m/salary?contest=fpg&project_id=abc",
  );
});

test("project contest synchronization uses the project API and keeps project id", () => {
  const context = read("app/components/project-contest-sync.tsx");
  const selector = read("app/components/contest-selector.tsx");
  const page = read("app/m/[slug]/page.tsx");

  assert.match(context, /\/api\/projects/);
  assert.match(context, /method: "PATCH"/);
  assert.match(context, /projectId/);
  assert.match(context, /moduleDraftKey\(moduleSlug, project\.contest_slug, stableProjectId\)/);
  assert.match(context, /window\.confirm/);
  assert.doesNotMatch(context, /removeItem/);
  assert.match(selector, /buildModuleRoute/);
  assert.match(page, /ProjectContestSync/);
  assert.match(page, /change_contest/);
});

test("example CTA never hardcodes PFKI for a contestless or FPG project", () => {
  const ui = read("app/components/lary-ui.tsx");
  assert.equal(ui.includes('hasRealExample(module.slug, "pfki")'), false);
  assert.match(ui, /intent: "example"/);
  assert.match(ui, /projectContest/);
});

test("module shell and every runner share one typed result lifecycle", () => {
  const flow = read("app/lib/module-flow.ts");
  const shell = read("app/components/module-shell.tsx");
  const runner = read("app/components/module-runner.tsx");
  const salary = read("app/components/salary-module-runner.tsx");
  const page = read("app/m/[slug]/page.tsx");

  assert.match(flow, /MODULE_RESULT_READY_EVENT/);
  assert.match(flow, /emitModuleResultReady/);
  assert.match(shell, /resultAvailable/);
  assert.match(shell, /scrollIntoView/);
  assert.match(runner, /emitModuleResultReady/);
  assert.match(salary, /emitModuleResultReady/);
  assert.match(salary, /id="result"/);
  assert.equal(page.includes('aria-label="Результат будет доступен после запуска"'), false);
  assert.match(page, /label: "Пример"/);
});

test("catalog recommendations and result return preserve project context", () => {
  const catalog = read("app/modules/page.tsx");
  const result = read("app/components/result-viewer.tsx");
  assert.match(catalog, /buildModuleRoute/);
  assert.match(catalog, /projectId: query\.project_id/);
  assert.match(result, /project_id/);
  assert.match(result, /buildModuleRoute/);
});

test("mobile menu returns focus and keeps its drawer inside the viewport", () => {
  const menu = read("app/components/mobile-menu.tsx");
  const shell = read("app/components/module-shell.tsx");
  assert.match(menu, /triggerRef/);
  assert.match(menu, /triggerRef\.current\?\.focus/);
  assert.match(shell, /max-h-\[calc\(100dvh-1rem\)\]/);
  assert.match(shell, /overflow-y-auto/);
});
