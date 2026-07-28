import assert from "node:assert/strict";
import test from "node:test";

const baseUrl = process.env.PRODUCTION_BASE_URL?.replace(/\/$/, "");
const expectedBuildSha = process.env.EXPECTED_BUILD_SHA?.trim();
const apiUrl = (process.env.PRODUCTION_API_URL || "https://api-production-d1a9.up.railway.app").replace(/\/$/, "");
const routes = [
  "/",
  "/modules",
  "/m/salary",
  "/m/salary?contest=pfki",
  "/m/salary?contest=pfki&mode=start",
  "/m/salary?contest=fpg",
];
const bannedPublicText = [
  "помощник по заявке ПФКИ",
  "prompt_pack",
  "profile_version",
  "provider error",
  "blocked",
  "unavailable",
  "ledger",
  "credits",
  "tokens",
];

test("production Phase 1 public contract", async () => {
  assert.ok(baseUrl, "PRODUCTION_BASE_URL is required");
  assert.ok(expectedBuildSha, "EXPECTED_BUILD_SHA is required");
  const pages = new Map();
  for (const route of routes) {
    const separator = route.includes("?") ? "&" : "?";
    const response = await fetch(`${baseUrl}${route}${separator}qa=${Date.now()}-${Math.random()}`, {
      redirect: "follow",
      cache: "no-store",
      headers: {
        "Cache-Control": "no-cache",
        Pragma: "no-cache",
      },
    });
    assert.equal(response.status, 200, `${route} should return 200`);
    pages.set(route, {
      html: await response.text(),
      buildSha: response.headers.get("x-lari-build-sha"),
    });
  }

  assert.match(pages.get("/").html, /Лари — AI-помощник по составлению грантовых заявок/);
  assert.match(pages.get("/").html, /Подготовьте рабочие документы для грантовой заявки/);
  assert.doesNotMatch(pages.get("/").html, /помощник по заявке ПФКИ/i);
  assert.doesNotMatch(pages.get("/").html, /Помощник для документов заявки ПФКИ/i);

  assert.match(pages.get("/modules").html, /Что нужно подготовить для грантовой заявки\?/);
  assert.match(pages.get("/modules").html, /Подходит для/);
  assert.doesNotMatch(pages.get("/modules").html, /Что нужно подготовить для заявки ПФКИ\?/);

  for (const contest of [
    "Президентский фонд культурных инициатив",
    "Фонд президентских грантов",
    "Росмолодёжь.Гранты",
    "Гранты Первых",
  ]) {
    assert.match(pages.get("/m/salary").html, new RegExp(contest));
  }
  assert.doesNotMatch(pages.get("/m/salary").html, /Позиции расчета/);

  assert.match(pages.get("/m/salary?contest=pfki").html, /Запустить модуль/);
  assert.match(pages.get("/m/salary?contest=pfki").html, /Посмотреть пример/);
  assert.match(pages.get("/m/salary?contest=pfki&mode=start").html, /Позиции расчета/);

  assert.match(pages.get("/m/salary?contest=fpg").html, /Для этого конкурса модуль пока готовится\./);
  assert.match(pages.get("/m/salary?contest=fpg").html, /Выбрать другой конкурс/);
  assert.match(pages.get("/m/salary?contest=fpg").html, /Вернуться к модулям/);
  assert.doesNotMatch(pages.get("/m/salary?contest=fpg").html, /Позиции расчета/);
  assert.doesNotMatch(pages.get("/m/salary?contest=fpg").html, /Купить запуск/);

  for (const [route, page] of pages) {
    assert.equal(page.buildSha, expectedBuildSha, `${route} web header SHA mismatch`);
    const metaMatch = page.html.match(/<meta[^>]+name=["']lari-build-sha["'][^>]+content=["']([^"']+)["']/i);
    assert.ok(metaMatch, `${route} is missing lari-build-sha meta`);
    assert.equal(metaMatch[1], expectedBuildSha, `${route} web meta SHA mismatch`);
    for (const banned of bannedPublicText) {
      assert.equal(page.html.toLowerCase().includes(banned.toLowerCase()), false, `${route} exposes ${banned}`);
    }
  }

  const healthResponse = await fetch(`${apiUrl}/health?qa=${Date.now()}`, {
    cache: "no-store",
    headers: {
      "Cache-Control": "no-cache",
      Pragma: "no-cache",
    },
  });
  assert.equal(healthResponse.status, 200, "API health should return 200");
  const health = await healthResponse.json();
  assert.deepEqual(Object.keys(health).sort(), ["build_sha", "status"]);
  assert.equal(health.status, "ok");
  assert.equal(health.build_sha, expectedBuildSha, "API build SHA mismatch");
});
