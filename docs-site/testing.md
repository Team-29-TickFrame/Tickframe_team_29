# Testing and QA

Assignment 5 keeps the Assignment 4 quality gates active. The maintained
testing evidence covers backend linting, backend formatting, automated backend
tests, coverage generation, critical-module coverage validation, frontend
typechecking, frontend build verification, QRTs, datetime-safety QA, and
Markdown link checking.

## Active CI Gates

| Gate | Maintained evidence |
|---|---|
| Backend linting and formatting | Quality workflow backend job. |
| Backend tests and coverage | Quality workflow backend job and coverage artifact. |
| Critical-module coverage | `backend/scripts/check_critical_coverage.py`. |
| Frontend typecheck and build | Quality workflow frontend job. |
| Additional QA | Ruff datetime-safety check. |
| Markdown link health | Links workflow with Lychee. |

## Week 5 Evidence Use

Week 5 report notes can cite the maintained workflow runs, this documentation
site, QRTs, ADRs, and Definition of Done artifacts. Private access details and
recording links must stay outside the public repository.

## Key Source Documents

- [Testing and quality gate status](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/testing.md)
- [Definition of Done](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/definition-of-done.md)
- [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml)
- [Links workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml)
