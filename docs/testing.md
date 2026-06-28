## Critical Modules and Coverage Status

| Critical module | Why critical | Required line coverage | Current line coverage | Evidence |
|---|---|---:|---:|---|
| [`backend/app/aggregation.py`](../backend/app/aggregation.py) | Builds canonical `1s` OHLCV candles from exchange trades. Incorrect behavior would corrupt the main market-data workflow. | 30% | data from latest creen with last ci-check in github actions quality| screen with last ci-check in github actions quality |
| [`backend/app/auth.py`](../backend/app/auth.py) | Handles registration, login, password hashing, and token-based user lookup. | 30% | data from latest creen with last ci-check in github actions quality |  screen with last ci-check in github |
| [`backend/app/exchanges/binance.py`](../backend/app/exchanges/binance.py) | Parses Binance trade messages and normalizes external exchange data. | 30% | data from latest creen with last ci-check in github actions quality | screen with last ci-check in github actions quality|
| [`backend/app/exchanges/bybit.py`](../backend/app/exchanges/bybit.py) | Parses Bybit trade messages and manages Bybit subscriptions/rejected topics. | 30% | data from latest creen with last ci-check in github actions quality | screen with last ci-check in github actions quality |
| [`backend/app/history.py`](../backend/app/history.py) | Aggregates and pages candle history for the chart and metrics workflows. | 30% |data from latest creen with last ci-check in github actions quality | screen with last ci-check in github actions quality |
| [`backend/app/metrics.py`](../backend/app/metrics.py) | Computes VWAP, volatility, RSI, momentum, divergence, anomaly, and correlation metrics. | 30% | data from latest screen with last ci-check in github actions quality | screen with last ci-check in github actions quality |
| [`backend/app/pattern_ml.py`](../backend/app/pattern_ml.py) | Loads the maintained pattern-recognition artifact and returns safe prediction statuses. | 30% | data from latest creen with last ci-check in github actions quality | screen with last ci-check in github actions quality |
| [`ml/pattern_recognition/dataset.py`](../ml/pattern_recognition/dataset.py) | Generates reproducible training and test windows for the maintained baseline model. | 30% | data from latest creen with last ci-check in github actions quality| screen with last ci-check in github actions quality |
| [`ml/pattern_recognition/features.py`](../ml/pattern_recognition/features.py) | Extracts model features used by the pattern detector. | 30% |data from latest creen with last ci-check in github actions quality | screen with last ci-check in github actions quality |
| [`ml/pattern_recognition/model.py`](../ml/pattern_recognition/model.py) | Contains the baseline model logic used by the product pattern endpoint. | 30% |data from latest creen with last ci-check in github actions quality |screen with last ci-check in github actions quality |


## Automated Test Status

| Test type | Scope | Command or CI check | Latest result | Evidence |
|---|---|---|---|---|
| Unit tests | Critical product logic: aggregation, metrics, history helpers, auth, config, exchange parsers, historical candle parsers, observability latency snapshots/Prometheus export, and ML detector behavior | `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests` | github quality actions |qithub quality actions |
| Integration tests | Important interactions between product components: service history fallback, service metrics snapshots, database-history conversion helpers, exchange subscription handling, and the ML API function using history plus detector logic | `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests` | github quality actions | github quality actions |
| Automated QRTs | QR-001 latency, QR-002 failure visibility, and QR-003 critical-module testability | `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests` and `python backend/scripts/check_critical_coverage.py coverage.json` | Must pass in `Quality` CI before merge/submission | [`docs/quality-requirement-tests.md`](quality-requirement-tests.md) and [`backend/tests/test_quality_requirements.py`](../backend/tests/test_quality_requirements.py) |
| Critical-module coverage | All critical modules listed above | `python backend/scripts/check_critical_coverage.py coverage.json` | Must pass in `Quality` CI before merge/submission | [`backend/scripts/check_critical_coverage.py`](../backend/scripts/check_critical_coverage.py) and latest `Quality` workflow run |


## CI and QA Check Status

| Gate or check | Required for Done | Command or CI check | Latest protected-branch status | Evidence |
|---|---|---|---|---|
| Backend linting | Yes | `ruff check backend ml` | Must pass before submission | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Backend formatting | Yes | `ruff format --check backend ml` | Must pass before submission | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Backend tests and coverage | Yes | `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests` | Must pass before submission | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) and `backend-coverage` artifact |
| Critical-module coverage | Yes | `python backend/scripts/check_critical_coverage.py coverage.json` | Must pass before submission | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Frontend type checking | Yes | `npm run typecheck` | Must pass before submission | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Frontend build | Yes | `npm run build` | Must pass before submission | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) |
| Additional QA check | Yes | `gitleaks/gitleaks-action@v2` | Must pass before submission | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml), `Additional QA - secret scan` job |
| Markdown link checking | Yes for repository documentation hygiene; does not count as the Assignment 4 additional QA check | Lychee link check over repository Markdown files | Must pass before submission | [Links workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml) |

## CI Links and Protected Branch Evidence

| Evidence item | Location | Latest status |
|---|---|---|
| CI pipeline for quality gates | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) | from screen |
| CI pipeline for Markdown link checking | [Links workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml) | from screen |
| Latest protected-default-branch CI result | Link the final successful `Quality` run on `main` after the last Assignment 4 PR is merged | from screen|
| Latest protected-default-branch link-check result | screen|github quality 
| Branch protection or rules evidence | screenshot of main protection evidence |

## Additional QA Check

| QA objective or risk | Additional QA check | Scope | Latest result | Evidence | Limitations|
|---|---|---|---|---|---|
| Tickframe is a public repository and may contain deployment instructions, environment examples, or integration code. Accidentally committed credentials, tokens, private keys, or API secrets would create a security and privacy risk. | Gitleaks secret scan. | Repository content and git history available to the action checkout. | github quality check | github quality check |Secret scanning may produce false positives or miss unusual secret formats. If a real secret is found, it must be revoked, removed from current files and history, and documented privately according to the incident-response process. |


## Manual Evidence That Does Not Count as QRT

| Evidence | Scope | Result | Follow-up PBI or issue |
|---|---|---|---|
| Customer UAT observation | End-user ability to open the dashboard, inspect analytics, and review real-time data availability. |Was done with the customer|[`docs/user-acceptance-tests.md`](user-acceptance-tests.md)


## Gates Maintained After Assignment 4

For now, all the gates remain active:

- backend linting with `ruff check backend ml`;
- backend formatting with `ruff format --check backend ml`;
- backend unit and integration tests under [`backend/tests`](../backend/tests);
- coverage reporting for `backend.app` and `ml.pattern_recognition`;
- critical-module coverage gate at 30% minimum per listed module;
- frontend TypeScript type checking;
- frontend build verification;
- Gitleaks secret scanning as the additional QA check;
- Lychee Markdown link checking;
- automated QRTs introduced in `docs/quality-requirement-tests.md`;
- Definition of Done requirements for passing relevant CI checks, tests,
  coverage gates, and preserved evidence.
