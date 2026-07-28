# Repository instructions

Before changing product behavior, data contracts, registry files, prompts, templates, payments, storage, or user flows:

1. Read `docs/product/LARI_MASTER_ARCHITECTURE.md`.
2. Read `docs/product/implementation-status.md` and the relevant product document.
3. Work only on the explicitly assigned phase. Do not combine phases in one implementation.
4. Keep existing PFKI flows working until their replacement is verified.
5. Keep prompt packs and provider credentials out of frontend bundles and public registries.
6. Add or update tests before implementation changes.
7. Update the relevant product documentation and `docs/product/changelog.md` in the same commit.
8. Do not deploy or modify a test environment without an explicit user request.
9. Final reports must list commit, changed files, migrations, tests, screenshots, deployment status, and known limitations.
