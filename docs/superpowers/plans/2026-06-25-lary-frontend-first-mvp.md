# Lary Frontend-First MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the frontend-first Lary 2.0 MVP shell: home page, module catalog, six module flows, result screens, and API-loading/error states.

**Architecture:** Keep the first slice frontend-focused and data-driven. Shared module metadata lives in `apps/web/app/data/modules.json`; pages consume small helpers and reusable components so future backend endpoints can replace local fixtures without redesigning the UI.

**Tech Stack:** Next.js 16 App Router, React 19, Tailwind CSS 4, built-in Node test runner for deterministic content/route checks.

## Global Constraints

- Lary is a modular web platform, not an AI chat.
- PFKI is a grant competition/context, not a module.
- MVP includes six active modules: social research, legal acts, salary, support letter, presentation, scenario plan.
- Future application check is shown as a coming-soon module, not implemented as core MVP.
- UX is optimized for users 45-65+: large text, clear buttons, calm state messages, no technical jargon.
- Do not use "credits", "tokens", "dashboard", "FAQ", or "prompt" in user-facing copy.
- Frontend must not call GigaChat, SaluteSpeech, database, or payment providers directly.
- API loading/error states must be understandable: no raw "500 Internal Server Error" to users.
- No new runtime dependencies for this frontend slice.

---

## File Structure

- `apps/web/app/data/modules.json`: source of truth for module cards, route slugs, fields, output formats, hints, and result actions.
- `apps/web/app/lib/lary-data.ts`: typed loader/helpers around module metadata.
- `apps/web/app/components/lary-ui.tsx`: shared header, footer, cards, callouts, loading/error blocks, form preview components.
- `apps/web/app/page.tsx`: homepage with hero, module cards, trust, how-it-works, pricing teaser.
- `apps/web/app/modules/page.tsx`: full catalog page.
- `apps/web/app/m/[slug]/page.tsx`: module form shell for all six active modules and coming-soon check module.
- `apps/web/app/run/[id]/result/page.tsx`: result screen with API-loading, download actions, improve/save/email/project actions.
- `apps/web/app/pay/page.tsx`: payment/promo shell for launches.
- `apps/web/app/account/page.tsx`: light personal cabinet shell.
- `apps/web/app/help/page.tsx`: help page.
- `apps/web/app/security/page.tsx`: security page.
- `apps/web/app/contacts/page.tsx`: contacts page.
- `apps/web/app/docs/[slug]/page.tsx`: legal-document placeholders with correct product framing.
- `apps/web/tests/modules-data.test.mjs`: Node tests that enforce MVP module count, route coverage, and prohibited jargon.
- `apps/web/package.json`: add `test` script only.

## Task 1: Data Contract and Tests

**Files:**
- Create: `apps/web/tests/modules-data.test.mjs`
- Modify: `apps/web/package.json`

**Interfaces:**
- Produces test expectations for `apps/web/app/data/modules.json`.

- [ ] **Step 1: Write failing tests**

Create tests that read `app/data/modules.json`, assert six active modules, one coming-soon check module, required slugs, non-empty fields/actions, and no prohibited terms in user-facing strings.

- [ ] **Step 2: Run tests to verify RED**

Run: `pnpm test`

Expected: FAIL because `app/data/modules.json` does not exist yet.

- [ ] **Step 3: Implement data JSON and typed helper**

Create `modules.json` and `lary-data.ts` matching the tests.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pnpm test`

Expected: PASS.

## Task 2: Shared UI and Homepage

**Files:**
- Create: `apps/web/app/components/lary-ui.tsx`
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/app/layout.tsx`

**Interfaces:**
- Consumes `getActiveModules()` and `getComingSoonModules()`.
- Produces reusable shell components for later pages.

- [ ] **Step 1: Add homepage route assertions to tests**

Extend test to assert homepage source includes all six active slugs and the key promise.

- [ ] **Step 2: Run tests to verify RED**

Run: `pnpm test`

Expected: FAIL until the homepage renders module links.

- [ ] **Step 3: Implement shared components and homepage**

Build top nav, hero, module cards, trust block, how-it-works, pricing teaser, and footer.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pnpm test`

Expected: PASS.

## Task 3: Catalog and Module Pages

**Files:**
- Create: `apps/web/app/modules/page.tsx`
- Create: `apps/web/app/m/[slug]/page.tsx`

**Interfaces:**
- Consumes module metadata by slug.
- Produces per-module UI shells with fields, AI-hints, right sticky "Моя работа" panel, loading/error state copy.

- [ ] **Step 1: Add route file assertions**

Extend tests to assert `app/modules/page.tsx` and `app/m/[slug]/page.tsx` exist and reference data helpers.

- [ ] **Step 2: Run tests to verify RED**

Run: `pnpm test`

Expected: FAIL until route files exist.

- [ ] **Step 3: Implement catalog and module shell**

Build catalog cards and dynamic module page with active/coming-soon behavior.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pnpm test`

Expected: PASS.

## Task 4: Result, Payment, Account, Help, Security, Legal Pages

**Files:**
- Create: `apps/web/app/run/[id]/result/page.tsx`
- Create: `apps/web/app/pay/page.tsx`
- Create: `apps/web/app/account/page.tsx`
- Create: `apps/web/app/help/page.tsx`
- Create: `apps/web/app/security/page.tsx`
- Create: `apps/web/app/contacts/page.tsx`
- Create: `apps/web/app/docs/[slug]/page.tsx`

**Interfaces:**
- Consumes module metadata and shared UI states.
- Produces CJM continuation screens and API-loading shells.

- [ ] **Step 1: Add route coverage assertions**

Extend tests to assert all required MVP route files exist and avoid raw technical error copy.

- [ ] **Step 2: Run tests to verify RED**

Run: `pnpm test`

Expected: FAIL until route files exist.

- [ ] **Step 3: Implement remaining pages**

Build result state, payment/promo shell, account light shell, help/security/contact/legal pages.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pnpm test`

Expected: PASS.

## Task 5: Build Verification

**Files:**
- No new files.

**Interfaces:**
- Verifies the frontend slice compiles.

- [ ] **Step 1: Run deterministic frontend checks**

Run:

```bash
pnpm test
pnpm lint
pnpm build
```

Expected: all pass.

- [ ] **Step 2: Report exact changed files and risks**

Run: `git status --short`.

Expected: only frontend MVP files and this plan are changed.
