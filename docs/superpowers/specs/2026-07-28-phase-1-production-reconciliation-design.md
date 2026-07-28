# Phase 1 Production Reconciliation Design

## Status and scope

Phase 1 remains `in_review` until the production domain, both Railway services, the production contract, responsive browser QA and the user's manual playtest agree. This reconciliation changes only the existing Phase 1 shell and production verification. It does not start Phase 2 or change any test environment.

## Production identity and reconciliation

The deployed web and API expose the same build SHA sourced from Railway's build/runtime environment. The web publishes it as a non-visual meta tag and response header; `/health` publishes only `status` and `build_sha`. The production contract fails closed when its URL or expected SHA is missing, fetches unique no-store URLs, and compares public HTML, web identity, API identity and the expected deployed `main` commit.

Current evidence shows the public domain routed to the production `web` service from `olegm1441-del/lary-2`, branch `main`, root `/apps/web`; API uses `/apps/api`. The latest public HTML already contains the multi-contest shell. The prior mismatch is therefore treated as stale deployment/cache evidence, not as an unresolved UI assertion. The long-lived static response cache and absence of build identity are removed as sources of ambiguity.

## Contest and draft context

Project-bound module pages resolve their project through the existing project API. A saved `contest_slug` becomes the default when the URL has no explicit contest. All contest transitions preserve `project_id` and applicable `mode`, `example`, and `intent`. Changing a project contest updates the project without deleting contest-specific drafts. Draft identity remains `module slug + contest slug + project id`.

Example entry is contest-aware. A project card uses its project contest. A card without contest context links to `intent=example`, then requires an explicit contest. Only an existing example pack for the selected ready profile produces an active example action. Preparing profiles never run AI and never borrow PFKI examples.

## Module flow contract

`ModuleShell` and runners share a typed result event contract. Before generation, Result is disabled. A successful inline or restored result emits the contract event, creates a real `#result` section, enables desktop and mobile navigation and scrolls to it. Returning to Data preserves the result; a later successful run replaces it. Example mode has only Contest and Example steps.

## Mobile shell

The production header always exposes a compact universal run balance at 390 and 430 px. The control is at least 44×44 px, links to `/pay`, does not expose ledger terminology and coexists with the menu without horizontal overflow.

## Verification

Changes are test-first. Unit contracts cover URL preservation, project contest persistence, draft isolation, example routing, preparing guards, result-step state and mobile balance markup. Acceptance adds a strict production contract, fresh no-cache curl evidence, browser QA at 390/430/768/1024/1440, production screenshots, successful salary/support-letter DOCX reads and restart persistence. Documentation records exactly one final production SHA and keeps Phase 1 `in_review`.

