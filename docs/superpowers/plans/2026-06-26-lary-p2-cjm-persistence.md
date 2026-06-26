# Lary P2 CJM Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the post-P0/P1 blocker list: durable state, correct result states, public UI cleanup, mobile navigation, account/project persistence, ledger-based promos/payments, module form polish, examples, and tests.

**Architecture:** Keep the current FastAPI + Next.js structure. Replace in-memory account/payment/module usage state with SQL-backed persistence: PostgreSQL in production via `DATABASE_URL`, SQLite only for deterministic local restart tests. Keep generated files on filesystem/Railway volume and persist file paths/outputs in SQL so metadata survives restart.

**Tech Stack:** FastAPI, psycopg, sqlite3 for tests, Next.js App Router, Node test runner, python unittest/TestClient.

## Global Constraints

- Priorities: implement P0 first, then P1, then P2.
- Public UI must not expose `MVP`, `P0/P1`, `runtime`, `in-memory`, `placeholder`, `demo`, `AI endpoint`, `webhook`.
- Frontend must not call GigaChat, SaluteSpeech, DB, or payment provider directly.
- Cookies must be httpOnly, SameSite=Lax, Secure in production.
- Backend decides prices and runs; frontend sends only product/package id.
- Paid runs, promos, attempts, works, projects, magic-links, payments and ledger must persist across restart.

---

### Task 1: P0 SQL state source of truth

**Files:**
- Modify: `apps/api/app/services/account_store.py`
- Modify: `apps/api/app/services/run_store.py`
- Modify: `apps/api/app/routers/module_runs.py`
- Modify: `apps/api/tests/test_mvp_contracts.py`

**Interfaces:**
- Consumes: existing FastAPI request/response cookies and `StoredRun`.
- Produces: SQL-backed `get_usage`, `prepare_module_access`, `record_module_run_success`, `apply_promo_code`, `record_payment_created`, `handle_payment_webhook`, `request_magic_link`, `consume_magic_link`, `get_account_works`, `create_project`, `attach_work_to_project`, `delete_work`.

- [x] Add failing restart tests for usage, work, project attach, magic-link and payment ledger.
- [x] Add SQL schema/bootstrap with idempotent migrations.
- [x] Replace memory dictionaries as source of truth with SQL queries.
- [x] Persist module run metadata, inputs, sections and files.
- [x] Rehydrate result/download metadata when `run_store` memory is empty.
- [x] Run backend tests.

### Task 2: P0 public UI and result states

**Files:**
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/components/lary-ui.tsx`
- Modify: `apps/web/app/components/module-runner.tsx`
- Modify: `apps/web/app/components/result-viewer.tsx`
- Modify: `apps/web/app/run/[id]/result/page.tsx`
- Modify: `apps/web/app/components/email-result-form.tsx`
- Modify: `apps/web/tests/modules-data.test.mjs`

**Interfaces:**
- Consumes: existing `ResultPayload` shape.
- Produces: distinct processing/ready/failed states, ready-first download actions, human field labels in launch summary, mobile menu.

- [x] Add failing frontend static tests for banned public terms, mobile menu, email copy, summary labels and result states.
- [x] Remove MVP/P0/P1 markers from public pages/cards.
- [x] Add mobile menu with required links and 44px targets.
- [x] Remove raw input key summary from public form.
- [x] Remove first-submit-only “Проверить данные” gating and separate prelaunch summary per latest user correction; keep inline field hints only.
- [x] Move result download actions above preview.
- [x] Run frontend tests and build.

### Task 3: P1 module forms, cabinet, payment and deletion

**Files:**
- Modify: `apps/web/app/data/modules.json`
- Modify: `apps/web/app/lib/lary-data.ts`
- Modify: `apps/web/app/components/module-runner.tsx`
- Modify: `apps/web/app/components/account-workspace.tsx`
- Modify: `apps/web/app/components/payment-panel.tsx`
- Modify: `apps/api/app/routers/projects.py`
- Modify: `apps/api/app/schemas/modules.py`
- Modify: `apps/api/tests/test_mvp_contracts.py`

**Interfaces:**
- Produces: “не знаю” affordances, long-text voice buttons, salary field split, presentation slide-count choice, scenario chips, empty states, mobile cards, delete work endpoint.

- [x] Add tests for salary validation, magic-link one-time consume, promo messages and delete old result links.
- [x] Update fields and validation hints per module.
- [x] Add delete work API and account UI actions.
- [x] Ensure package 6 copy does not imply discount.
- [x] Run tests.

### Task 4: P2 language/help/examples and final verification

**Files:**
- Modify: `apps/web/app/help/page.tsx`
- Modify: `apps/web/app/security/page.tsx`
- Modify: `apps/web/app/docs/[slug]/page.tsx`
- Modify: `apps/web/app/m/[slug]/page.tsx`
- Modify: `apps/web/tests/modules-data.test.mjs`

**Interfaces:**
- Produces: human security/help copy, example pages/modal links for all modules, no internal legal copy.

- [x] Add frontend static tests for examples and public banned terms.
- [x] Add/verify example routes or existing result example behavior for each module.
- [x] Run full backend/frontend tests, build, py_compile.
- [ ] Deploy API/web, run production smoke and screenshots at 390/768/1024/1440.
