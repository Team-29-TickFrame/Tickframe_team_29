# Week 4 Report


### CI Links

| Evidence item | Link or location | Status |
|---|---|---|
| Quality CI pipeline | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) | Runs on pull requests, pushes to `main`, and manual dispatch |
| Link-check CI pipeline | [Links workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml) | Runs on Markdown/link-check changes in pull requests and pushes to `main` |
| CI configuration | [`.github/workflows/quality.yml`](../../.github/workflows/quality.yml) | Backend lint/format/tests/coverage, frontend typecheck/build, Gitleaks secret scan |
| Link-check configuration | [`.github/workflows/links.yml`](../../.github/workflows/links.yml) and [`lychee.toml`](../../lychee.toml) | Lychee checks repository Markdown links |
| Testing documentation | [`docs/testing.md`](../../docs/testing.md) | Maintained testing status and quality-gate summary |
| Link-check exclusions | [`docs/link-check-exclusions.md`](../../docs/link-check-exclusions.md) | Documents local URL exclusions for Lychee |



### Quality Gates That Continue Later

For now, all quality gated will be continued later:

- Backend linting with `ruff check backend ml`.
- Backend formatting with `ruff format --check backend ml`.
- Backend unit and integration tests under [`backend/tests`](../../backend/tests).
- Coverage reporting for `backend.app` and `ml.pattern_recognition`.
- Critical-module coverage gate at 30% minimum per listed module.
- Frontend TypeScript type checking with `npm run typecheck`.
- Frontend build verification with `npm run build`.
- Gitleaks secret scanning as the Assignment 4 additional QA check.
- Lychee Markdown link checking for repository documentation.
- Automated quality requirement tests linked from `docs/quality-requirement-tests.md` once the QRT traceability document is finalized.
- Definition of Done evidence requirements for passing CI checks, tests, coverage gates, and preserved verification evidence.

If later work changes the product stack, critical modules, quality
requirements, or CI configuration, the team must update the gates and
documentation instead of bypassing or disabling the Assignment 4 checks.
