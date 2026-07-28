# Phase 1 Production Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile deployed `main` with the public Railway production site and make Phase 1 ready for a user playtest without marking it `ready`.

**Architecture:** Add one shared build-identity contract across Next.js, FastAPI and the production test; add query-preserving contest/project navigation and typed runner-to-shell result state; keep all non-PFKI profiles fail-closed. Extend existing shell components rather than creating contest- or module-specific forks.

**Tech Stack:** Next.js 16, React 19, TypeScript, Node test runner, FastAPI, Pydantic, Python `unittest`, Railway production.

## Global Constraints

- Work only on `main` and Railway `production`; do not deploy, enable or change a test environment.
- Keep Phase 1 `in_review`; only the user may approve returning it to `ready`.
- Do not start Phase 2, FAQ, help chat, expert recommendations, prompt packs or new contests.
- Use TDD for behavior changes.
- A `preparing` profile cannot run AI, create a run or spend an attempt.
- Preserve `project_id` and contest-specific drafts.
- Minimum touch target is 44×44 px; no horizontal overflow at 390–1440 px.
- Production acceptance must fail rather than skip when required environment values are absent.

---

### Task 1: Build identity and strict production contract

**Files:**
- Modify: `apps/api/app/core/config.py`
- Modify: `apps/api/app/routers/health.py`
- Modify: `apps/api/tests/test_health.py`
- Create: `apps/web/app/lib/build-info.ts`
- Modify: `apps/web/app/layout.tsx`
- Modify: `apps/web/next.config.ts`
- Modify: `apps/web/tests/phase1-production-contract.test.mjs`
- Modify: `apps/web/package.json`

**Interfaces:**
- Produces: `GET /health -> {"status":"ok","build_sha":"<sha>"}`.
- Produces: `<meta name="lari-build-sha">` and `X-Lari-Build-Sha`.
- Produces: `pnpm test:production-contract`.

- [ ] Write failing health and production-contract tests for nonempty matching SHA and required environment variables.
- [ ] Run the targeted tests and confirm the old health/skip behavior fails.
- [ ] Implement build SHA resolution from `RAILWAY_GIT_COMMIT_SHA`, with a safe local fallback only outside production.
- [ ] Add meta/header and strict unique no-store route assertions.
- [ ] Run targeted API and frontend tests.

### Task 2: Project-aware contest routing and draft isolation

**Files:**
- Modify: `apps/web/app/components/contest-selector.tsx`
- Create: `apps/web/app/components/module-contest-context.tsx`
- Modify: `apps/web/app/m/[slug]/page.tsx`
- Modify: `apps/web/app/lib/api.ts`
- Modify: `apps/web/tests/modules-data.test.mjs`
- Modify: `apps/api/app/routers/projects.py` only if the existing update contract is insufficient.

**Interfaces:**
- Consumes: `project_id`, project `contest_slug`, `mode`, `example`, `intent`.
- Produces: contest transitions that retain project context and persist a changed project contest.

- [ ] Add failing tests for automatic project contest, preserved query context, project update and separate PFKI/FPG drafts.
- [ ] Run targeted tests and confirm failures.
- [ ] Implement project loading and query construction through one context component.
- [ ] Keep incompatible-data confirmation scoped to an actual project contest change; retain compatible data and both drafts.
- [ ] Verify a preparing selection never creates a run.

### Task 3: Contest-aware examples

**Files:**
- Modify: `apps/web/app/components/lary-ui.tsx`
- Modify: `apps/web/app/m/[slug]/page.tsx`
- Modify: `apps/web/tests/modules-data.test.mjs`

**Interfaces:**
- Produces: contestless `?intent=example`.
- Produces: selected real example `?contest=<slug>&example=1`.

- [ ] Add failing tests for project-contest examples, contestless intent and preparing profiles.
- [ ] Remove hardcoded PFKI example selection.
- [ ] Require a ready profile and real example pack before rendering an active example CTA.
- [ ] Run targeted frontend tests.

### Task 4: Mobile run balance

**Files:**
- Modify: `apps/web/app/components/run-balance.tsx`
- Modify: `apps/web/app/components/lary-ui.tsx`
- Modify: `apps/web/tests/modules-data.test.mjs`

**Interfaces:**
- Produces: compact visible `/pay` control at 390 and 430 px.

- [ ] Add a failing markup/style contract for mobile visibility and 44 px target.
- [ ] Implement compact count/zero-state copy without technical balance terms.
- [ ] Verify the existing completion event refreshes the count.
- [ ] Run targeted tests and responsive browser checks.

### Task 5: Typed result-step lifecycle

**Files:**
- Create: `apps/web/app/lib/module-flow.ts`
- Modify: `apps/web/app/components/module-shell.tsx`
- Modify: `apps/web/app/components/module-runner.tsx`
- Modify: `apps/web/app/components/salary-module-runner.tsx`
- Modify: `apps/web/app/m/[slug]/page.tsx`
- Modify: `apps/web/tests/modules-data.test.mjs`

**Interfaces:**
- Produces: typed `lari:module-result-ready` contract with `moduleSlug` and result identity.
- Produces: enabled/active Result navigation only after a successful result.

- [ ] Add failing tests for disabled/enabled result, `#result` navigation, mobile drawer and example steps.
- [ ] Implement shared event typing and shell lifecycle.
- [ ] Emit result-ready only after completed generation or restored completed result.
- [ ] Preserve the current result while navigating back to Data; replace it after a new run.
- [ ] Run targeted tests.

### Task 6: Full local verification and production deploy

**Files:**
- Modify: `docs/product/changelog.md`
- Modify: `docs/product/implementation-status.md`
- Modify: `docs/qa/phase-1/README.md`
- Create: `docs/qa/phase-1-final/*`

**Interfaces:**
- Produces: one documented final SHA and user playtest script.

- [ ] Run all backend tests and compileall.
- [ ] Run frontend tests, lint and build.
- [ ] Commit and push only `main`.
- [ ] Wait for both production deployments to reach `SUCCESS` for the same SHA.
- [ ] Run the strict production contract with `EXPECTED_BUILD_SHA`.
- [ ] Run browser CTA/responsive QA and save required screenshots.
- [ ] Generate and read one salary DOCX and one support-letter DOCX; restart API and verify downloads remain identical.
- [ ] Update documentation to one SHA, keep Phase 1 `in_review`, and hand off the manual playtest scenario.

