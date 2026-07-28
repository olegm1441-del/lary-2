import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const { buildModuleRoute } = await import("../app/lib/module-route.ts");

test("module card start intent opens the selected contest form directly", () => {
  assert.equal(
    buildModuleRoute(
      {
        moduleSlug: "social-research",
        projectId: "project-1",
        intent: "start",
      },
      "pfki",
    ),
    "/m/social-research?contest=pfki&project_id=project-1&mode=start&intent=start",
  );
});

test("module card example intent opens only a real contest example", () => {
  assert.equal(
    buildModuleRoute(
      {
        moduleSlug: "scenario-plan",
        projectId: "project-1",
        intent: "example",
        realExampleContests: ["pfki"],
      },
      "pfki",
    ),
    "/m/scenario-plan?contest=pfki&project_id=project-1&example=1&intent=example",
  );
});

test("module cards declare explicit start and example intents", () => {
  const source = read("app/components/lary-ui.tsx");
  assert.match(source, /intent: "start"/);
  assert.match(source, /intent: "example"/);
});

test("module page keeps the decision screen for a bare ready contest", () => {
  const source = read("app/m/[slug]/page.tsx");
  assert.match(source, /query\.intent === "start"/);
  assert.match(source, /const showExample = query\.example === "1"/);
  assert.match(source, /!showRunner && !showExample/);
});

test("field assistant uses stable suggestion ids and operations", () => {
  const component = read("app/components/field-assistant-hint.tsx");
  const runner = read("app/components/module-runner.tsx");
  assert.match(component, /suggestions\?:/);
  assert.match(component, /suggestion\.id/);
  assert.match(runner, /suggestion\.operation/);
  assert.equal(runner.includes('chip === "Добавить территорию"'), false);
});

test("completed payload state is fingerprinted and does not clear its result while editing", () => {
  const runner = read("app/components/module-runner.tsx");
  const fingerprint = read("app/lib/submission-fingerprint.ts");
  assert.match(runner, /lastSubmittedFingerprint/);
  assert.match(runner, /Результат сформирован/);
  assert.match(runner, /Обновить результат/);
  assert.match(fingerprint, /stableSubmissionFingerprint/);
  assert.match(fingerprint, /normalizeSubmissionPayload/);
  const updateValueBody = runner.match(/function updateValue[\s\S]+?\n  }\n\n  function markTouched/)?.[0] || "";
  assert.equal(updateValueBody.includes("setResultRunId"), false);
});

test("module navigation exposes sticky scrollspy and data return target", () => {
  const shell = read("app/components/module-shell.tsx");
  const result = read("app/components/result-viewer.tsx");
  assert.match(shell, /aria-current=\{activeId === step\.id \? "step"/);
  assert.match(shell, /sticky/);
  assert.match(shell, /MutationObserver/);
  assert.match(result, /#data/);
});

test("completed result state survives refresh inside the same contest and project draft", () => {
  const drafts = read("app/lib/module-drafts.ts");
  const runner = read("app/components/module-runner.tsx");
  assert.match(drafts, /moduleResultStateKey/);
  assert.match(runner, /savedResult\?\.runId/);
  assert.match(runner, /window\.localStorage\.setItem\(\s*moduleResultStateKey/);
});

test("social research and scenario forms use the playtest field contracts and migrate legacy drafts", () => {
  const data = JSON.parse(read("app/data/modules.json"));
  const fields = read("app/lib/lary-data.ts");
  const runner = read("app/components/module-runner.tsx");
  const social = data.find((item) => item.slug === "social-research");
  const scenario = data.find((item) => item.slug === "scenario-plan");
  assert.deepEqual(
    social.fields.map((field) => field.label),
    ["Регион", "Основное направление", "Целевая группа", "Описание проблемы", "Что изменит проект", "Ограничения и важные условия"],
  );
  assert.deepEqual(
    scenario.fields.map((field) => field.label),
    [
      "Вид сценарного плана",
      "Название мероприятия",
      "Описание идеи",
      "Место проведения",
      "Участники мероприятия",
      "Целевая аудитория проекта",
      "Расписание и продолжительность",
      "Подготовка",
      "Команда, оборудование и ограничения",
    ],
  );
  assert.match(fields, /"project_response", "constraints"/);
  assert.match(fields, /"event_title"/);
  assert.match(runner, /values\.event_idea \|\|= values\.description/);
  assert.match(runner, /values\.schedule \|\|= values\.duration/);
});
