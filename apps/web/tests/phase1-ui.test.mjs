import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

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
  for (const banned of ["ledger", "credits", "tokens"]) assert.equal(balance.includes(banned), false);
});
