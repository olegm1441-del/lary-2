# Lary UI/UX P0/P1 Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring Lary 2.0 MVP 0.1 in line with the attached UI/UX revision DOCX: implement P0 before P1, verify working flows, deploy, and report in section 17 format.

**Architecture:** Keep the current Next.js + FastAPI split. Move trust-critical state from localStorage-only behavior into backend services with cookie/session, usage ledger, promo/payment ledger, and account/project endpoints. Keep user-facing copy data-driven from module configuration.

**Tech Stack:** Next.js app router, TypeScript, Tailwind, FastAPI, PostgreSQL-compatible schema with in-memory test fallback, python-docx/python-pptx, Railway.

## Global Constraints

- Do not require registration before the first free result.
- Each active module has one separate free attempt.
- Commercial unit is "запуск модуля".
- Frontend must not know AI/payment/database secrets.
- Public copy must be Russian, calm, predictable, and suitable for users 45-65+.
- No internal legal TODO, technical stack errors, prompts, tokens, raw provider failures, or unmarked demo data on public pages.
- Implement P0 first, then P1.

---

### Task 1: P0 public UI and routes

**Files:**
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/modules/page.tsx`
- Modify: `apps/web/app/components/lary-ui.tsx`
- Modify: `apps/web/app/data/modules.json`
- Modify: `apps/web/app/account/page.tsx`
- Modify: `apps/web/app/pay/page.tsx`
- Modify: `apps/web/app/help/page.tsx`
- Modify: `apps/web/app/security/page.tsx`
- Modify: `apps/web/app/docs/[slug]/page.tsx`
- Test: `apps/web/tests/modules-data.test.mjs`

**Acceptance:**
- Guest `/account` shows email login, not fake works.
- Catalog title is "Что нужно подготовить для заявки ПФКИ?"
- Main CTA says "Выбрать задачу".
- Future check module is "Скоро" and CTA says "Сообщить, когда модуль будет готов".
- `/pay` has working promo form UI copy.

### Task 2: P1 backend state

**Files:**
- Modify: `apps/api/app/services/account_store.py`
- Create: `apps/api/app/services/session_store.py`
- Modify: `apps/api/app/routers/module_runs.py`
- Modify: `apps/api/app/routers/payments.py`
- Create: `apps/api/app/routers/auth.py`
- Create: `apps/api/app/routers/account.py`
- Create: `apps/api/app/routers/projects.py`
- Modify: `apps/api/app/schemas/modules.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_mvp_contracts.py`

**Acceptance:**
- Backend creates `anon_session_id` httpOnly cookie.
- `GET /api/usage` reports per-module free attempts and paid balance.
- Re-running the same module from the same session requires paid run/promo.
- Promo redemption is one-time per session/email.
- Payment webhook is idempotent by `provider_payment_id`.
- Magic-link request/consume attaches temporary works to an account.
- Account works include `project` column data and usable actions.

### Task 3: P1 frontend flows

**Files:**
- Modify: `apps/web/app/components/module-runner.tsx`
- Modify: `apps/web/app/components/module-attempt-status.tsx`
- Modify: `apps/web/app/lib/module-attempts.ts`
- Modify: `apps/web/app/components/result-viewer.tsx`
- Modify: `apps/web/app/components/email-result-form.tsx`
- Modify: `apps/web/app/account/page.tsx`
- Modify: `apps/web/app/pay/page.tsx`

**Acceptance:**
- UI reads usage from backend, localStorage is only draft convenience.
- Module form opens summary before run.
- Paid repeat shows "Использовать 1 запуск" and promo option.
- Pay flow preserves return module and form draft.
- Account login and work list use API state.

### Task 4: Tests, Figma, deploy

**Files:**
- Create/Modify: Playwright tests under `apps/web/tests` if dependency already exists; otherwise add deterministic Node smoke tests without new deps.
- Modify: Figma file `viyK3LkFkzxo6P1dcc9lrv`.

**Acceptance:**
- Backend unit tests pass.
- Frontend tests/build pass.
- Production smoke covers public routes, module run, download, account, pay, promo, webhook.
- Figma has key frames for main/catalog/module/result/account/pay/mobile.
