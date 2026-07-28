# LARI 2 Phases 0–1 Multi-Contest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Зафиксировать foundation architecture и затем перевести global shell на четыре конкурса без поломки действующих PFKI-модулей.

**Architecture:** Один public registry в `config/product` описывает contests, modules и module–contest profiles; backend держит закрытые prompt packs и разрешает запуск только `ready` profile. Phase 1 использует additive DB migration, legacy PFKI fallback и общий frontend shell, чтобы новая архитектура могла быть отключена одним feature flag без потери черновиков.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS, FastAPI, Pydantic, PostgreSQL/SQLite compatibility layer, Python `unittest`, Node test runner.

## Global Constraints

- Работать только в `main`; test environment не разворачивать и не изменять.
- Не начинать salary, support-letter, actuality, presentation, expert chat или subscriptions в рамках Phase 1.
- Сохранять рабочими все существующие PFKI flows, downloads, free attempts, promo и payments.
- Не отправлять prompt packs в frontend bundle.
- Неподдерживаемый profile не вызывает AI, не создает run и не списывает запуск.
- Payload без `contest_slug` временно трактовать как legacy `pfki`.
- Минимальный обычный текст — 16 px; основной текст форм — 18 px; touch target — минимум 44×44 px.
- Не показывать публично prompt, backend, endpoint, JSON, provider error, blocked, unavailable, ledger, credits или tokens.
- Любое изменение registry, API, DB, payment или flow обновляет product docs в том же commit.
- Rollback выполняется через `PRODUCT_REGISTRY_RUNTIME_ENABLED=false`; additive DB columns не удаляются при rollback.

---

### Task 1: Phase 0 Foundation Registry and Documentation

**Files:**
- Create: `config/product/contests.json`
- Create: `config/product/modules.json`
- Create: `config/product/module-contest-profiles.json`
- Create: `config/product/examples-manifest.json`
- Create: `config/product/faq-manifest.json`
- Create: `config/product/feature-flags.json`
- Create: `config/product/schemas/*.schema.json`
- Create: `apps/api/tests/test_product_registry.py`
- Create: `docs/product/*.md`
- Create: `AGENTS.md`

**Interfaces:**
- Produces: stable public registry keyed by `module_slug + contest_slug`.
- Produces: feature flag defaults and versioned pack identifiers used by later tasks.

- [x] **Step 1: Write registry tests before creating config**

The tests require four contest slugs, seven unique module slugs, a complete 7×4 profile matrix, required ids for `ready` profiles, manifest references and exact feature flag values.

- [x] **Step 2: Run the test and verify RED**

Run:

```bash
PYTHONPATH=apps/api python3 -m unittest apps/api/tests/test_product_registry.py
```

Expected: `FileNotFoundError` for `config/product/contests.json` and the other not-yet-created registry files.

- [x] **Step 3: Add the minimal registry, schemas and docs**

The public matrix contains six ready PFKI profiles, one preparing PFKI profile and all seven profiles in preparing state for each of the other three contests.

- [x] **Step 4: Run the registry test and verify GREEN**

Run:

```bash
PYTHONPATH=apps/api python3 -m unittest apps/api/tests/test_product_registry.py
```

Expected: seven tests run and the suite ends with `OK`.

- [x] **Step 5: Commit Phase 0**

```bash
git add AGENTS.md config/product docs/product docs/superpowers/plans apps/api/tests/test_product_registry.py
git commit -m "Add LARI multi-contest architecture foundation"
```

---

### Task 2: Backend Product Registry Loader

**Files:**
- Create: `apps/api/app/services/product_registry.py`
- Create: `apps/api/app/schemas/product.py`
- Modify: `apps/api/app/core/config.py`
- Test: `apps/api/tests/test_product_registry_runtime.py`

**Interfaces:**
- Consumes: JSON files in `config/product`.
- Produces: `ProductRegistry.load(config_dir: Path) -> ProductRegistry`.
- Produces: `get_contests()`, `get_modules()`, `get_profile(module_slug, contest_slug)`.
- Produces: `ProfileNotReadyError` for `preparing` and `disabled` profiles.

- [x] **Step 1: Write failing loader tests**

```python
class ProductRegistryRuntimeTest(unittest.TestCase):
    def test_loads_the_shared_registry(self):
        registry = ProductRegistry.load(PRODUCT_CONFIG)
        self.assertEqual([item.slug for item in registry.contests], ["pfki", "fpg", "rosmolodezh", "first_grants"])

    def test_ready_profile_resolves_all_pack_ids(self):
        registry = ProductRegistry.load(PRODUCT_CONFIG)
        profile = registry.require_ready_profile("salary", "pfki")
        self.assertEqual(profile.prompt_pack_id, "prompt.pfki.salary.v1")

    def test_preparing_profile_is_not_runnable(self):
        registry = ProductRegistry.load(PRODUCT_CONFIG)
        with self.assertRaises(ProfileNotReadyError):
            registry.require_ready_profile("salary", "fpg")

    def test_duplicate_or_broken_references_fail_startup_validation(self):
        broken = copy_registry_fixture(PRODUCT_CONFIG)
        append_duplicate_profile(broken)
        with self.assertRaises(ProductRegistryError):
            ProductRegistry.load(broken)
```

- [x] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=apps/api python3 -m unittest apps/api/tests/test_product_registry_runtime.py
```

Expected: import failure because `app.services.product_registry` does not exist.

- [x] **Step 3: Implement typed loader and settings**

Add:

```python
class ProductRegistry:
    @classmethod
    def load(cls, config_dir: Path) -> "ProductRegistry":
        contests = TypeAdapter(list[Contest]).validate_python(read_json(config_dir / "contests.json"))
        modules = TypeAdapter(list[ProductModule]).validate_python(read_json(config_dir / "modules.json"))
        profiles = TypeAdapter(list[ModuleContestProfile]).validate_python(
            read_json(config_dir / "module-contest-profiles.json")
        )
        registry = cls(contests=contests, modules=modules, profiles=profiles)
        registry.validate_references()
        return registry

    def get_profile(self, module_slug: str, contest_slug: str) -> ModuleContestProfile | None:
        return self.profiles_by_key.get((module_slug, contest_slug))

    def require_ready_profile(self, module_slug: str, contest_slug: str) -> ModuleContestProfile:
        profile = self.get_profile(module_slug, contest_slug)
        if profile is None:
            raise ProductRegistryError("Unknown module-contest profile")
        if profile.status != "ready":
            raise ProfileNotReadyError(profile.status)
        return profile
```

Add settings:

```python
product_registry_runtime_enabled = env_bool("PRODUCT_REGISTRY_RUNTIME_ENABLED", False)
product_config_dir = os.getenv("PRODUCT_CONFIG_DIR")
```

The default config path resolves from repository root. Startup validation rejects duplicate slugs, duplicate profile pairs, missing references and secrets/prompt text in public JSON.

- [x] **Step 4: Run targeted and full backend tests**

```bash
PYTHONPATH=apps/api python3 -m unittest apps/api/tests/test_product_registry.py apps/api/tests/test_product_registry_runtime.py
PYTHONPATH=apps/api python3 -m unittest discover -s apps/api/tests
```

Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add apps/api/app/core/config.py apps/api/app/schemas/product.py apps/api/app/services/product_registry.py apps/api/tests/test_product_registry_runtime.py
git commit -m "Add validated product registry loader"
```

---

### Task 3: Read-Only Product API

**Files:**
- Create: `apps/api/app/routers/product.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_product_api.py`

**Interfaces:**
- Consumes: `ProductRegistry`.
- Produces:
  - `GET /api/contests`
  - `GET /api/modules`
  - `GET /api/modules/{module}/profiles/{contest}`
- Preserves: legacy `GET /api/modules/{slug}/schema`.

- [x] **Step 1: Write failing API contract tests**

```python
def test_contests_endpoint_returns_four_public_choices(self):
    response = client.get("/api/contests")
    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["pfki", "fpg", "rosmolodezh", "first_grants"]

def test_profile_endpoint_returns_preparing_without_private_prompt(self):
    response = client.get("/api/modules/salary/profiles/fpg")
    assert response.status_code == 200
    assert response.json()["status"] == "preparing"
    assert "system_prompt" not in response.text

def test_unknown_profile_is_404_with_safe_message(self):
    response = client.get("/api/modules/unknown/profiles/pfki")
    assert response.status_code == 404
    assert response.json()["detail"]["message"] == "Такая задача не найдена."
```

- [x] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=apps/api python3 -m unittest apps/api/tests/test_product_api.py
```

Expected: `/api/contests` returns 404.

- [x] **Step 3: Implement router and response schemas**

Only public metadata and pack ids are returned. No prompt text, provider settings, credentials, template filesystem path or internal source failure is serialized.

- [x] **Step 4: Verify targeted and existing module contracts**

```bash
PYTHONPATH=apps/api python3 -m unittest apps/api/tests/test_product_api.py apps/api/tests/test_mvp_contracts.py
```

Expected: both suites pass; legacy module catalog remains compatible.

- [x] **Step 5: Commit**

```bash
git add apps/api/app/main.py apps/api/app/routers/product.py apps/api/tests/test_product_api.py
git commit -m "Expose public contest and profile registry"
```

---

### Task 4: Additive Contest Context Migration

**Files:**
- Modify: `apps/api/app/services/account_store.py`
- Modify: `apps/api/app/schemas/modules.py`
- Modify: `apps/api/app/routers/projects.py`
- Modify: `apps/api/app/routers/module_runs.py`
- Test: `apps/api/tests/test_contest_migration.py`

**Interfaces:**
- Adds nullable DB fields:
  - `projects.contest_slug`
  - `module_runs.contest_slug`
  - `module_runs.profile_version`
  - `module_runs.project_id`
  - `module_runs.error_code`
  - `works.contest_slug`
- Adds `contest_slug: str = "pfki"` to legacy-compatible requests.
- Preserves `competition` during migration window.

- [x] **Step 1: Write migration and compatibility tests**

```python
def test_legacy_project_is_backfilled_to_pfki(self):
    insert_legacy_project(competition="ПФКИ")
    ensure_account_schema()
    assert read_project()["contest_slug"] == "pfki"

def test_new_project_accepts_contest_slug_and_keeps_display_name(self):
    response = client.post("/api/projects", json={"title": "Музей", "contest_slug": "fpg"})
    assert response.status_code == 200
    assert response.json()["contest_slug"] == "fpg"
    assert response.json()["competition"] == "Фонд президентских грантов"

def test_legacy_run_payload_defaults_to_pfki(self):
    response = create_legacy_module_run()
    assert response.status_code == 200
    assert persisted_run(response.json()["run_id"])["contest_slug"] == "pfki"
```

- [x] **Step 2: Verify RED**

Expected failures: missing `contest_slug` columns and response fields.

- [x] **Step 3: Implement idempotent additive migration**

Use the existing `_column_exists` compatibility layer. Backfill only recognized legacy value `ПФКИ`; unknown legacy strings remain unchanged and receive no runnable profile until manually mapped.

Write both `competition` and `contest_slug` during migration. Never drop or rename a column in Phase 1.

- [x] **Step 4: Verify restart and backward compatibility**

```bash
PYTHONPATH=apps/api python3 -m unittest apps/api/tests/test_contest_migration.py apps/api/tests/test_mvp_contracts.py
```

Expected: schema initialization is idempotent for SQLite and PostgreSQL query paths; existing account/project tests pass.

- [x] **Step 5: Commit**

```bash
git add apps/api/app/services/account_store.py apps/api/app/schemas/modules.py apps/api/app/routers/projects.py apps/api/app/routers/module_runs.py apps/api/tests/test_contest_migration.py
git commit -m "Add backward-compatible contest context"
```

---

### Task 5: Profile-Gated Run Creation

**Files:**
- Modify: `apps/api/app/schemas/modules.py`
- Modify: `apps/api/app/routers/module_runs.py`
- Modify: `apps/api/app/routers/modules.py`
- Modify: `apps/api/app/services/module_engine.py`
- Modify: `apps/api/app/services/account_store.py`
- Test: `apps/api/tests/test_profile_gated_runs.py`

**Interfaces:**
- Request:

```json
{
  "module_slug": "support-letter",
  "contest_slug": "pfki",
  "project_id": null,
  "inputs": {},
  "profile_version": "1.0.0"
}
```

- Safe preparing response: HTTP 409 with code `MODULE_CONTEST_PROFILE_PREPARING` and message `Для этого конкурса модуль пока готовится.`

- [x] **Step 1: Write failing gate and ledger tests**

```python
def test_ready_pfki_profile_runs_existing_engine(self):
    response = client.post(
        "/api/module-runs",
        json={
            "module_slug": "social-research",
            "contest_slug": "pfki",
            "inputs": {
                "region": "Москва",
                "direction": "театр",
                "target_group": "подростки 14–17 лет",
                "problem": "мало доступных занятий",
            },
        },
    )
    assert response.status_code == 200
    stored = load_persisted_run(response.json()["run_id"])
    assert stored is not None

def test_preparing_profile_does_not_call_ai(self):
    with patch("app.services.module_engine.generate_with_gigachat") as ai:
        response = client.post("/api/module-runs", json={"module_slug": "salary", "contest_slug": "fpg", "inputs": {}})
    assert response.status_code == 409
    ai.assert_not_called()

def test_preparing_profile_does_not_spend_free_or_paid_run(self):
    before = client.get("/api/usage").json()
    client.post("/api/module-runs", json={"module_slug": "salary", "contest_slug": "fpg", "inputs": {}})
    assert client.get("/api/usage").json() == before

def test_mismatched_profile_version_is_rejected_without_spend(self):
    before = client.get("/api/usage").json()
    response = client.post(
        "/api/module-runs",
        json={
            "module_slug": "social-research",
            "contest_slug": "pfki",
            "profile_version": "0.0.1",
            "inputs": {"region": "Москва"},
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "PROFILE_VERSION_MISMATCH"
    assert client.get("/api/usage").json() == before
```

- [x] **Step 2: Verify RED**

Expected: current endpoint ignores `contest_slug` and attempts legacy generation.

- [x] **Step 3: Add profile resolution before access reservation**

Resolve and validate profile before `prepare_module_access`. Legacy request without contest selects `pfki` and server-owned current `profile_version`. Client cannot select an arbitrary prompt/template id.

- [x] **Step 4: Run profile, salary, support-letter and ledger regression tests**

```bash
PYTHONPATH=apps/api python3 -m unittest \
  apps/api/tests/test_profile_gated_runs.py \
  apps/api/tests/test_salary_generate.py \
  apps/api/tests/test_support_letter.py \
  apps/api/tests/test_mvp_contracts.py
```

Expected: all pass; provider or file errors still do not spend a run.

- [x] **Step 5: Commit**

```bash
git add apps/api/app/schemas/modules.py apps/api/app/routers/module_runs.py apps/api/app/routers/modules.py apps/api/app/services/module_engine.py apps/api/app/services/account_store.py apps/api/tests/test_profile_gated_runs.py
git commit -m "Gate module runs by contest profile"
```

---

### Task 6: Typed Frontend Registry Adapter and Brand Copy

**Files:**
- Create: `apps/web/app/lib/product-registry.ts`
- Modify: `apps/web/app/lib/lary-data.ts`
- Modify: `apps/web/app/components/lary-ui.tsx`
- Modify: `apps/web/app/layout.tsx`
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/modules/page.tsx`
- Test: `apps/web/tests/product-registry.test.mjs`
- Test: `apps/web/tests/modules-data.test.mjs`

**Interfaces:**
- Consumes: shared JSON imports from `config/product`.
- Produces:

```ts
getPublicContests(): Contest[]
getPublicModules(): ProductModule[]
getModuleProfile(moduleSlug: string, contestSlug: string): ModuleContestProfile | undefined
getSupportedContests(moduleSlug: string): Contest[]
```

- [x] **Step 1: Write failing frontend registry and copy tests**

```js
test("public registry exposes four contests and no private prompts", () => {
  assert.deepEqual(contests.map((item) => item.slug), ["pfki", "fpg", "rosmolodezh", "first_grants"]);
  assert.equal(JSON.stringify(productConfig).includes("system_prompt"), false);
});

test("generic brand is not tied to PFKI", () => {
  for (const file of ["app/layout.tsx", "app/page.tsx", "app/components/lary-ui.tsx"]) {
    assert.equal(read(file).includes("помощник по заявке ПФКИ"), false);
  }
});
```

- [x] **Step 2: Verify RED**

Expected: adapter file is missing and current header/footer contain PFKI-specific generic branding.

- [x] **Step 3: Implement shared typed adapter and copy**

Use brand exactly: `Лари — AI-помощник по составлению грантовых заявок`.

Landing cards show `Подходит для` chips and actions `Начать` / `Посмотреть пример`. Current PFKI module details remain available through the profile adapter.

- [x] **Step 4: Verify frontend tests, lint and build**

```bash
cd apps/web
pnpm test
pnpm lint
pnpm build
```

Expected: all pass. Build must prove cross-root JSON imports are bundled in Railway-compatible output. If cross-root import fails, stop and resolve packaging without copying a second registry.

- [x] **Step 5: Commit**

```bash
git add apps/web/app/lib/product-registry.ts apps/web/app/lib/lary-data.ts apps/web/app/components/lary-ui.tsx apps/web/app/layout.tsx apps/web/app/page.tsx apps/web/app/modules/page.tsx apps/web/tests
git commit -m "Use multi-contest product registry in public shell"
```

---

### Task 7: Contest Selector and Draft-Safe Unsupported State

**Files:**
- Create: `apps/web/app/components/contest-selector.tsx`
- Create: `apps/web/app/lib/module-drafts.ts`
- Modify: `apps/web/app/m/[slug]/page.tsx`
- Modify: `apps/web/app/components/module-runner.tsx`
- Modify: `apps/web/app/components/salary-module-runner.tsx`
- Test: `apps/web/tests/contest-selector.test.mjs`
- Test: `apps/web/tests/module-drafts.test.mjs`

**Interfaces:**
- Draft key: `lary:draft:v2:{module_slug}:{contest_slug}:{project_id|anonymous}`.
- Selector emits `onSelect(contestSlug)`.
- Preparing state contains two actions: `Выбрать другой конкурс` and `Вернуться к модулям`.

- [x] **Step 1: Write failing state transition tests**

```js
test("legacy draft migrates to pfki without losing fields", () => {
  const migrated = migrateLegacyDraft({ moduleSlug: "salary", payload: { region: "Москва" } });
  assert.equal(migrated.contestSlug, "pfki");
  assert.equal(migrated.payload.region, "Москва");
});

test("preparing profile never renders the module runner", () => {
  const source = read("app/m/[slug]/page.tsx");
  assert.match(source, /Для этого конкурса модуль пока готовится/);
  assert.match(source, /profile\\.status === "ready"/);
});
```

- [x] **Step 2: Verify RED**

Expected: v2 draft adapter and selector are absent.

- [x] **Step 3: Implement selector and draft migration**

When a project has `contest_slug`, select it initially. Otherwise show four radio cards. Changing contest preserves compatible field keys; if schemas differ, show confirmation before discarding only incompatible values.

Preparing profile renders no form CTA and no generic prompt path.

- [x] **Step 4: Verify frontend tests and build**

```bash
cd apps/web
pnpm test
pnpm lint
pnpm build
```

Expected: all pass.

- [x] **Step 5: Commit**

```bash
git add apps/web/app/components/contest-selector.tsx apps/web/app/lib/module-drafts.ts apps/web/app/m/'[slug]'/page.tsx apps/web/app/components/module-runner.tsx apps/web/app/components/salary-module-runner.tsx apps/web/tests
git commit -m "Add draft-safe contest selection"
```

---

### Task 8: Common Module Shell, Mobile Steps and Run Balance

**Files:**
- Create: `apps/web/app/components/module-shell.tsx`
- Create: `apps/web/app/components/module-step-navigation.tsx`
- Create: `apps/web/app/components/run-balance.tsx`
- Modify: `apps/web/app/components/lary-ui.tsx`
- Modify: `apps/web/app/components/mobile-menu.tsx`
- Modify: `apps/web/app/m/[slug]/page.tsx`
- Modify: `apps/web/app/globals.css`
- Test: `apps/web/tests/module-shell.test.mjs`

**Interfaces:**
- `ModuleShell` accepts profile, module, contest, steps, active step and utility content.
- `ModuleStepNavigation` renders sticky desktop navigation and mobile drawer.
- `RunBalance` consumes existing `/api/usage` and links to `/pay` at zero paid balance.

- [x] **Step 1: Write failing structural/accessibility tests**

```js
test("module shell exposes desktop navigation and mobile stages", () => {
  const shell = read("app/components/module-shell.tsx");
  assert.match(shell, /Этап .* из/);
  assert.match(shell, /aria-label="Этапы модуля"/);
});

test("run balance uses user-facing terms", () => {
  const balance = read("app/components/run-balance.tsx");
  assert.match(balance, /Запуски:/);
  for (const banned of ["ledger", "credits", "tokens"]) assert.equal(balance.includes(banned), false);
});
```

- [x] **Step 2: Verify RED**

Expected: new components are missing.

- [x] **Step 3: Implement common shell**

Desktop layout: sticky header, left navigation, 760–840 px main content, utility rail only at ≥1280 px. Mobile layout: compact header, `Этап N из M`, `Этапы` drawer, no permanent sidebar and no covered CTA.

Run balance preserves existing cookie credentials and payment route. It does not expose technical ledger terms.

- [x] **Step 4: Run tests, lint and build**

```bash
cd apps/web
pnpm test
pnpm lint
pnpm build
```

Expected: all pass.

- [x] **Step 5: Commit**

```bash
git add apps/web/app/components/module-shell.tsx apps/web/app/components/module-step-navigation.tsx apps/web/app/components/run-balance.tsx apps/web/app/components/lary-ui.tsx apps/web/app/components/mobile-menu.tsx apps/web/app/m/'[slug]'/page.tsx apps/web/app/globals.css apps/web/tests
git commit -m "Add accessible common module shell"
```

---

### Task 9: Phase 1 E2E, Responsive QA and Documentation

**Files:**
- Create: `apps/web/tests/phase1-production-contract.test.mjs`
- Modify: `docs/product/implementation-status.md`
- Modify: `docs/product/architecture-decisions.md`
- Modify: `docs/product/module-registry.md`
- Modify: `docs/product/contest-registry.md`
- Modify: `docs/product/migration-plan.md`
- Modify: `docs/product/changelog.md`
- Create: `docs/qa/phase-1/README.md`
- Create: `docs/qa/phase-1/*.png`

**Interfaces:**
- QA widths: 390, 430, 768, 1024, 1440 px.
- Critical flow: contest selection → ready/preparing state → form/draft → PFKI result → return to draft.

- [x] **Step 1: Add production contract test**

The test fetches production HTML after deploy for `/`, `/modules`, `/m/salary`, `/m/support-letter`, `/pay`, `/account`, confirms generic branding, four contest labels, no banned technical text and no PFKI-specific generic subtitle.

- [x] **Step 2: Run complete local verification**

```bash
PYTHONPATH=apps/api python3 -m unittest discover -s apps/api/tests
python3 -m compileall -q apps/api/app
cd apps/web
pnpm test
pnpm lint
pnpm build
```

Expected: zero failures.

- [x] **Step 3: Run local browser QA and capture screenshots**

Capture `/`, `/modules`, ready PFKI salary module and preparing FPG salary state at 390, 430, 768, 1024 and 1440 px. Verify keyboard focus, Esc close, focus restoration, 44×44 targets, Russian label wrapping and absence of horizontal scroll.

- [ ] **Step 4: Update docs and Phase 1 status**

Set Phase 1 to `ready` only after all local and production checks pass. Record migrations, rollback flag, screenshots and known limitations.

- [ ] **Step 5: Commit**

```bash
git add apps/web/tests/phase1-production-contract.test.mjs docs/product docs/qa/phase-1
git commit -m "Verify and document multi-contest shell"
```

- [ ] **Step 6: Push main and verify production only**

```bash
git push origin main
railway deployment list --service api --environment production --limit 2 --json
railway deployment list --service web --environment production --limit 2 --json
```

Do not run Railway commands without `--environment production`. Wait for `SUCCESS` for the pushed commit, then run health/API/public HTML smoke tests.

- [ ] **Step 7: Rollback if production smoke fails**

Set `PRODUCT_REGISTRY_RUNTIME_ENABLED=false` in production or revert the Phase 1 commits. Do not drop additive columns. Confirm legacy PFKI routes, payments and downloads before closing the incident.
