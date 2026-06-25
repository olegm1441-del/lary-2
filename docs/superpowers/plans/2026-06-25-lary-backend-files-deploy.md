# Lary Backend, File Generation, and Deploy Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real backend contracts, AI-backed/fallback module runs, DOCX/PDF/PPTX generation, frontend API calls, and Railway deployment readiness.

**Architecture:** Keep backend MVP deterministic and safe: module schemas are data-driven, runs are stored in an in-process repository with generated files on disk, GigaChat is used only when env is configured, and fallback content keeps the site testable without secrets. Frontend submits module input to the API and shows loading/error/result states in language suitable for the 45+ audience.

**Tech Stack:** FastAPI, Pydantic, python-docx, reportlab, python-pptx, Next.js 16, React 19, Tailwind CSS 4.

## Global Constraints

- Frontend does not call GigaChat, SaluteSpeech, database, or payment providers directly.
- No raw provider errors or raw HTTP 500 messages in the user UI.
- One launch costs 320 RUB in MVP copy and payment placeholder.
- Presentation module creates a real PPTX with 8-12 slides.
- Presentation has two variants: grant-defense presentation and calendar-plan demonstration.
- Voice input buttons are visible in long text fields; speech API is exposed by backend and returns a friendly unavailable state when SaluteSpeech env is missing.
- Email login is visual-only for first deploy unless backend auth is explicitly requested.
- Railway deployment requires authenticated Railway CLI or GitHub-linked auto-deploy.

---

## Task 1: Backend Contracts and Tests

- [ ] Add unittest coverage for module catalog, module run lifecycle, download endpoints, payment placeholder, promo placeholder, and speech unavailable state.
- [ ] Verify RED before implementation.
- [ ] Implement schemas, module metadata, run repository, routers, and main app registration.
- [ ] Verify GREEN.

## Task 2: File Generators

- [ ] Add tests asserting generated DOCX/PDF/PPTX files exist and are non-empty.
- [ ] Implement DOCX generator with project sections and manual-check notes.
- [ ] Implement PDF generator with Cyrillic font fallback.
- [ ] Implement PPTX generator with 10 branded slides and two presentation variants.
- [ ] Verify generated files through tests.

## Task 3: Frontend API Integration

- [ ] Add client module runner with real form input, voice buttons, API loading, friendly error messages, and redirect to result.
- [ ] Add result client that fetches `/api/module-runs/{id}/result` and exposes download links.
- [ ] Update tests to enforce API URL handling and voice button copy.
- [ ] Verify Next lint/build.

## Task 4: Railway Readiness and Deployment

- [ ] Add or verify `railway.json` for api and web services.
- [ ] Verify local API starts and `/api/health`, `/api/modules`, module run, and download endpoints work.
- [ ] Commit only approved files, excluding unrelated `.DS_Store` and `.Rhistory`.
- [ ] Push branch or main per owner instruction.
- [ ] Deploy via Railway CLI if authenticated, otherwise provide exact user action required.
