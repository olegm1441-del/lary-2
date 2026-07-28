import assert from "node:assert/strict";
import test from "node:test";

const baseUrl = process.env.PRODUCTION_BASE_URL?.replace(/\/$/, "");
const routes = ["/", "/modules", "/m/salary", "/m/support-letter", "/pay", "/account"];
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

test("production Phase 1 public contract", { skip: !baseUrl }, async () => {
  const pages = new Map();
  for (const route of routes) {
    const response = await fetch(`${baseUrl}${route}`, { redirect: "follow" });
    assert.equal(response.status, 200, `${route} should return 200`);
    pages.set(route, await response.text());
  }

  assert.match(pages.get("/"), /Лари — AI-помощник по составлению грантовых заявок/);
  assert.match(pages.get("/modules"), /Что нужно подготовить для грантовой заявки/);
  for (const contest of [
    "Президентский фонд культурных инициатив",
    "Фонд президентских грантов",
    "Росмолодёжь.Гранты",
    "Гранты Первых",
  ]) {
    assert.match(pages.get("/m/salary"), new RegExp(contest));
  }

  for (const [route, html] of pages) {
    for (const banned of bannedPublicText) {
      assert.equal(html.toLowerCase().includes(banned.toLowerCase()), false, `${route} exposes ${banned}`);
    }
  }
});
