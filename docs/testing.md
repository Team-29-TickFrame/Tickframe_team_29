# Testing and Quality Gate Status

This document is the maintained testing status artifact for Tickframe starting
from Assignment 4. It records critical-module coverage, automated test status,
quality requirement tests, CI gates, and the additional QA check that remains
part of the Definition of Done for later work.

## Critical Modules and Coverage Status

Latest local verification: 2026-06-28 using
`coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests`,
`coverage report --show-missing`, and
`python backend/scripts/check_critical_coverage.py coverage.json`.

| Critical module | Why critical | Required line coverage | Current line coverage | Evidence |
|---|---|---:|---:|---|
| [`backend/app/aggregation.py`](../backend/app/aggregation.py) | Builds canonical OHLCV candles from exchange trades. Incorrect behavior would corrupt the main market-data workflow. | 30% | 88% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| [`backend/app/auth.py`](../backend/app/auth.py) | Handles registration, login, password hashing, and token-based user lookup. | 30% | 70% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| [`backend/app/exchanges/binance.py`](../backend/app/exchanges/binance.py) | Parses Binance trade messages and normalizes exchange data. | 30% | 50% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| [`backend/app/exchanges/bybit.py`](../backend/app/exchanges/bybit.py) | Parses Bybit trade messages and manages Bybit subscriptions and rejected topics. | 30% | 57% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| [`backend/app/history.py`](../backend/app/history.py) | Aggregates and pages candle history for chart and metrics workflows. | 30% | 92% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| [`backend/app/metrics.py`](../backend/app/metrics.py) | Computes VWAP, volatility, RSI, momentum, divergence, anomaly, and correlation metrics. | 30% | 89% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| [`backend/app/pattern_ml.py`](../backend/app/pattern_ml.py) | Loads the maintained pattern-recognition artifact and returns safe prediction statuses. | 30% | 98% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| [`ml/pattern_recognition/dataset.py`](../ml/pattern_recognition/dataset.py) | Generates reproducible training and test windows for the baseline model. | 30% | 73% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| [`ml/pattern_recognition/features.py`](../ml/pattern_recognition/features.py) | Extracts model features used by the pattern detector. | 30% | 92% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| [`ml/pattern_recognition/model.py`](../ml/pattern_recognition/model.py) | Contains the baseline model logic used by the product pattern endpoint. | 30% | 59% | Local coverage run and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |

The global measured coverage for `backend.app` and `ml.pattern_recognition` is
66%. Global coverage is lower than some critical modules because migration,
database-adapter, deployment, and training-script paths are tested less heavily
than the core analytics, history, observability, and model-serving logic.

## Automated Test Status

| Test type | Scope | Command or CI check | Latest result | Evidence |
|---|---|---|---|---|
| Unit tests | Aggregation, metrics, auth, config, exchange parsers, observability, and ML detector behavior. | `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests` | Passing locally on 2026-06-28; 69 tests OK. | [`backend/tests`](../backend/tests) and [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Integration tests | Service history fallback, metrics snapshots, database-history conversion helpers, exchange subscription handling, and ML API function using history plus detector logic. | Same backend test command. | Passing locally on 2026-06-28. | [`backend/tests/test_service_history.py`](../backend/tests/test_service_history.py), [`backend/tests/test_database_history.py`](../backend/tests/test_database_history.py), [`backend/tests/test_api_patterns.py`](../backend/tests/test_api_patterns.py) |
| Automated QRTs | QR-001 latency, QR-002 failure visibility, and QR-003 critical-module testability. | Backend tests and critical coverage gate. | Passing locally on 2026-06-28. | [`docs/quality-requirement-tests.md`](quality-requirement-tests.md) and [`backend/tests/test_quality_requirements.py`](../backend/tests/test_quality_requirements.py) |
| Critical-module coverage | All critical modules listed above. | `python backend/scripts/check_critical_coverage.py coverage.json` | Passing locally on 2026-06-28 for 10 modules at >= 30%. | [`backend/scripts/check_critical_coverage.py`](../backend/scripts/check_critical_coverage.py) |

## CI and QA Check Status

| Gate or check | Required for Done? | Command or CI check | Latest status | Evidence |
|---|---|---|---|---|
| Backend linting | Yes | `ruff check backend ml` | Passing locally on 2026-06-28. | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Backend formatting | Yes | `ruff format --check backend ml` | Passing locally on 2026-06-28 after applying Ruff formatting. | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Backend tests and coverage | Yes | `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests` | Passing locally on 2026-06-28. | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) and `backend-coverage` artifact |
| Critical-module coverage | Yes | `python backend/scripts/check_critical_coverage.py coverage.json` | Passing locally on 2026-06-28. | [`backend/scripts/check_critical_coverage.py`](../backend/scripts/check_critical_coverage.py) |
| Frontend type checking | Yes | `npm run typecheck` | Required in CI before merge and release. | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Frontend build | Yes | `npm run build` | Required in CI before merge and release. | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Additional QA check | Yes | `ruff check --select DTZ backend/app ml/pattern_recognition` | Passing locally on 2026-06-28. | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml), `Additional QA - datetime safety analysis` job |
| Markdown link checking | Yes for repository documentation hygiene; it does not count as the Assignment 4 additional QA check. | Lychee over repository Markdown files. | Latest checked `main` run passed on 2026-06-28. | [Links workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml) |

## Additional QA Check Rationale

| QA objective or risk | Additional QA check | Scope | Latest result | Evidence | Limitations or follow-up |
|---|---|---|---|---|---|
| Market analytics and release evidence depend on correct timestamp handling. Naive datetime usage can make latency, history windows, and deployment evidence misleading across environments. | Ruff datetime-safety rules (`DTZ`). | Product backend and ML source under `backend/app` and `ml/pattern_recognition`. | Passing locally on 2026-06-28. | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) | The check detects known datetime anti-patterns; it does not replace runtime latency monitoring or customer UAT. |

## CI Links and Protected Branch Evidence

| Evidence item | Location | Notes |
|---|---|---|
| Quality CI pipeline | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) | Runs on pull requests, pushes to `main`, and manual dispatch. |
| Markdown link-check pipeline | [Links workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml) | Runs on Markdown/link-check changes in pull requests and pushes to `main`. |
| CI configuration | [`.github/workflows/quality.yml`](../.github/workflows/quality.yml) | Defines backend lint, formatting, tests, coverage, frontend typecheck/build, and additional QA. |
| Link-check configuration | [`.github/workflows/links.yml`](../.github/workflows/links.yml), [`github/workflows/links.yml`](../github/workflows/links.yml), and [`lychee.toml`](../lychee.toml) | Defines Lychee link checking for repository Markdown. |
| Branch protection or rules evidence | Week 4 report screenshots or GitHub branch settings | Public screenshots should be stored under `reports/week4/images/` when captured. |

## Manual Evidence That Does Not Count as QRT

| Evidence | Scope | Result | Follow-up PBI or issue |
|---|---|---|---|
| Customer UAT observation | End-user ability to open the dashboard, inspect analytics, and review real-time data availability. | Passed during the Week 4 customer session. | [`docs/user-acceptance-tests.md`](user-acceptance-tests.md) |

## Gates Maintained After Assignment 4

These gates remain active project assets for later work:

- Backend linting with `ruff check backend ml`.
- Backend formatting with `ruff format --check backend ml`.
- Backend automated tests under [`backend/tests`](../backend/tests).
- Coverage reporting for `backend.app` and `ml.pattern_recognition`.
- Critical-module coverage gate at 30% minimum per listed module.
- Frontend TypeScript type checking.
- Frontend build verification.
- Automated QRTs introduced in [`docs/quality-requirement-tests.md`](quality-requirement-tests.md).
- Additional QA datetime-safety analysis.
- Lychee Markdown link checking.
- Definition of Done requirements for passing relevant checks, tests, coverage
  gates, and preserved verification evidence.
