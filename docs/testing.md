# Testing

This document is the maintained testing status artifact for Assignment 4.
It records the automated tests, critical-module coverage gate, CI checks,
additional QA check, and the quality gates that must remain active in later
project work.

## Critical Modules and Coverage

Critical modules are the parts of Tickframe where defects would materially
affect market data correctness, analytics output, external exchange ingestion,
authentication, or pattern-recognition behavior.

The CI coverage gate requires every listed critical module to have at least
30% line coverage. The threshold is enforced by
[`backend/scripts/check_critical_coverage.py`](../backend/scripts/check_critical_coverage.py)
after the backend test suite creates `coverage.json`.

| Critical module | Why critical | Required line coverage | Current line coverage | Evidence |
|---|---|---:|---:|---|
| [`backend/app/aggregation.py`](../backend/app/aggregation.py) | Builds canonical `1s` OHLCV candles from exchange trades. Incorrect behavior would corrupt the main market-data workflow. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |
| [`backend/app/auth.py`](../backend/app/auth.py) | Handles registration, login, password hashing, and token-based user lookup. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |
| [`backend/app/exchanges/binance.py`](../backend/app/exchanges/binance.py) | Parses Binance trade messages and normalizes external exchange data. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |
| [`backend/app/exchanges/bybit.py`](../backend/app/exchanges/bybit.py) | Parses Bybit trade messages and manages Bybit subscriptions/rejected topics. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |
| [`backend/app/history.py`](../backend/app/history.py) | Aggregates and pages candle history for the chart and metrics workflows. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |
| [`backend/app/metrics.py`](../backend/app/metrics.py) | Computes VWAP, volatility, RSI, momentum, divergence, anomaly, and correlation metrics. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |
| [`backend/app/pattern_ml.py`](../backend/app/pattern_ml.py) | Loads the maintained pattern-recognition artifact and returns safe prediction statuses. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |
| [`ml/pattern_recognition/dataset.py`](../ml/pattern_recognition/dataset.py) | Generates reproducible training and test windows for the maintained baseline model. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |
| [`ml/pattern_recognition/features.py`](../ml/pattern_recognition/features.py) | Extracts model features used by the pattern detector. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |
| [`ml/pattern_recognition/model.py`](../ml/pattern_recognition/model.py) | Contains the baseline model logic used by the product pattern endpoint. | 30% | CI-enforced >= 30%; exact latest value from coverage artifact | Latest `Quality` workflow coverage artifact |

Before submission, the Week 4 public report must link the latest protected
default-branch CI run and include the coverage/test screenshot or artifact link
showing the exact latest per-module coverage evidence.

## Automated Test Status

| Test type | Scope | Command or CI check | Latest result | Evidence |
|---|---|---|---|---|
| Unit tests | Critical product logic: aggregation, metrics, history helpers, auth, config, exchange parsers, historical candle parsers, and ML detector behavior | `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests` | Must pass in `Quality` CI before merge/submission | [`backend/tests`](../backend/tests) and latest `Quality` workflow run |
| Integration tests | Important interactions between product components: service history fallback, service metrics snapshots, database-history conversion helpers, exchange subscription handling, and the ML API function using history plus detector logic | `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests` | Must pass in `Quality` CI before merge/submission | [`backend/tests/test_service_history.py`](../backend/tests/test_service_history.py), [`backend/tests/test_database_history.py`](../backend/tests/test_database_history.py), [`backend/tests/test_api_patterns.py`](../backend/tests/test_api_patterns.py), [`backend/tests/test_exchange_parsers.py`](../backend/tests/test_exchange_parsers.py) |
| Automated QRTs | Assignment 4 quality requirements and quality requirement tests | Same CI checks and test commands once linked from `docs/quality-requirement-tests.md` | Pending QRT traceability document | `docs/quality-requirement-tests.md` must link the relevant automated checks |
| Critical-module coverage | All critical modules listed above | `python backend/scripts/check_critical_coverage.py coverage.json` | Must pass in `Quality` CI before merge/submission | [`backend/scripts/check_critical_coverage.py`](../backend/scripts/check_critical_coverage.py) and latest `Quality` workflow run |

## Test Scope

| Test file | What it verifies | Data strategy |
|---|---|---|
| [`test_aggregation.py`](../backend/tests/test_aggregation.py) | Event-time candle aggregation, duplicate trade handling, empty candles, late-trade revisions, disconnected gaps, recovered trades, numeric trade ID ordering, and OHLC invariants. | Controlled synthetic trades passed into the real `CandleAggregator`; Hypothesis generates additional price sequences for invariant testing. |
| [`test_metrics.py`](../backend/tests/test_metrics.py) | VWAP, RSI, momentum, volatility estimators, mean reversion, volume spike events, double-top events, RSI divergence, price-volume divergence, and cross-pair return correlation. | Controlled synthetic candles passed into the real metrics functions. |
| [`test_history.py`](../backend/tests/test_history.py) | Memory rollups, incomplete source candles, pagination, default time windows, and invalid range rejection. | Controlled synthetic candle dictionaries passed into real history helpers. |
| [`test_database_history.py`](../backend/tests/test_database_history.py) | Raw-trade history conversion, empty-second filling, latest-limit trimming, repair no-op behavior without a DB engine, and history-source priority. | Controlled rows shaped like database output passed into real `DatabaseWriter` conversion helpers. |
| [`test_service_history.py`](../backend/tests/test_service_history.py) | Service-level history fallback, metrics reuse of memory history, stable-candle latency window, cross-pair correlations, raw-trade preference for recent second charts, historical-source behavior, and recovery duration parsing. | Real `MarketDataService` and in-memory store with controlled candles; small fake database objects are used only to isolate database boundary behavior. |
| [`test_exchange_parsers.py`](../backend/tests/test_exchange_parsers.py) | Binance and Bybit trade normalization, Bybit one-topic subscription behavior, rejected topic tracking, and active-instrument status. | Representative exchange message fixtures passed into real parser/collector methods; fake websocket records outgoing subscription payloads without opening a network connection. |
| [`test_backfill_candles.py`](../backend/tests/test_backfill_candles.py) | Binance and Bybit kline mapping, Binance `1s` support, Bybit `1s` unsupported behavior, closed interval alignment, and REST URL environment overrides. | Representative REST kline fixtures passed into real parser/config helper functions. |
| [`test_auth.py`](../backend/tests/test_auth.py) | Password hash verification, in-memory registration/login/current-user lookup, duplicate registration rejection, and wrong-password rejection. | Real `AuthService` with `database_url=None` to exercise the maintained in-memory fallback rather than an external database. |
| [`test_config.py`](../backend/tests/test_config.py) | Exchange support matrix, default websocket endpoint fallbacks, and environment override parsing. | Real config loader with temporary environment overrides. |
| [`test_pattern_ml.py`](../backend/tests/test_pattern_ml.py) | Unsupported timeframe status, insufficient-data status, maintained model loading, synthetic pattern detection, missing-model safety, confidence threshold clamping, and model artifact size. | Real `PatternMLDetector` and committed baseline model artifact; synthetic candles generated by the maintained ML dataset generator. |
| [`test_api_patterns.py`](../backend/tests/test_api_patterns.py) | ML pattern API function behavior for unsupported and supported timeframes, including history-service call shape and detector output. | Real `ml_patterns` function with the history service mocked to avoid a live DB/network dependency and to verify the service boundary contract. |

## Test Data and Mock Use

The automated tests do not depend on live Binance, Bybit, Docker, TimescaleDB,
or network access. They use controlled test data so the expected outcomes are
deterministic and repeatable in CI.

The tests still exercise real application code. They import production modules
from `backend.app`, `backend.scripts`, and `ml.pattern_recognition`; they do not
replace the candle aggregation, metrics, history, parser, auth, or detector
logic with mocks.

Mocks and fakes are used only at external or unstable boundaries:

- fake websocket objects record subscription payloads without opening a real
  WebSocket connection;
- fake database objects verify service routing without requiring TimescaleDB;
- `AsyncMock` replaces the history service in the ML API test so the endpoint
  contract can be checked without live persistence;
- temporary environment overrides verify config behavior without changing the
  real deployment environment.

This strategy is intentional: CI should verify product logic with deterministic
inputs while avoiding flaky tests that depend on live exchanges, external
network timing, or a mutable database.

## CI and QA Check Status

| Gate or check | Required for Done? | Command or CI check | Latest protected-branch status | Evidence |
|---|---|---|---|---|
| Backend linting | Yes | `ruff check backend ml` | Must pass before submission | `Quality` workflow |
| Backend formatting | Yes | `ruff format --check backend ml` | Must pass before submission | `Quality` workflow |
| Backend tests and coverage | Yes | `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests` | Must pass before submission | `Quality` workflow and `backend-coverage` artifact |
| Critical-module coverage | Yes | `python backend/scripts/check_critical_coverage.py coverage.json` | Must pass before submission | `Quality` workflow |
| Frontend type checking | Yes | `npm run typecheck` | Must pass before submission | `Quality` workflow |
| Frontend build | Yes | `npm run build` | Must pass before submission | `Quality` workflow |
| Additional QA check | Yes | `gitleaks/gitleaks-action@v2` | Must pass before submission | `Quality` workflow, `Additional QA - secret scan` job |
| Markdown link checking | Yes for repository documentation hygiene; does not count as the Assignment 4 additional QA check | Lychee link check over repository Markdown files | Must pass before submission when Markdown changes affect the workflow | `Links` workflow |

## Additional QA Check Rationale

| QA objective or risk | Additional QA check | Scope | Latest result | Evidence | Limitations or follow-up |
|---|---|---|---|---|---|
| Tickframe is a public repository and may contain deployment instructions, environment examples, or integration code. Accidentally committed credentials, tokens, private keys, or API secrets would create a security and privacy risk. | Gitleaks secret scan. | Repository content and git history available to the action checkout. | Must pass in the latest protected-branch `Quality` workflow before submission. | `Additional QA - secret scan` job in the `Quality` workflow. | Secret scanning may produce false positives or miss unusual secret formats. If a real secret is found, it must be revoked, removed from current files and history, and documented privately according to the incident-response process. |

Other QA options considered for Assignment 4 were dependency vulnerability
scanning, deeper static analysis, accessibility checks, API contract checks,
and performance checks. The team selected secret scanning because public
repository hygiene and credential leakage are immediate risks for a project
with `.env`-based configuration, deployment documentation, and public evidence.

## Manual Evidence That Does Not Count as QRT

| Evidence | Scope | Result | Follow-up PBI or issue |
|---|---|---|---|
| Customer UAT observation | End-user ability to open the dashboard, inspect analytics, and review latency/health information. | To be completed during the Week 4 customer session. | Add or link follow-up PBIs after UAT execution. |
| Deployment smoke check | Product starts through Docker Compose and exposes frontend/API endpoints. | To be completed for the Week 4 release/deployment evidence. | Add or link follow-up PBIs for any deployment issues. |

Manual observations support release confidence, but they do not count as
automated quality requirement tests.

## Gates Maintained After Assignment 4

The following gates remain active for later project work and must not be
removed, disabled, or narrowed only because Assignment 4 has been submitted:

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

If later product changes make a check obsolete, the team must replace it with
an equivalent or stronger documented gate and update this document, the
Definition of Done, and the Week/Sprint evidence accordingly.
