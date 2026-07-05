# Quality Requirement Tests

This document defines maintained automated quality requirement tests (QRTs) for
Tickframe. The QRT set verifies the quality requirements in
[`docs/quality-requirements.md`](quality-requirements.md) using the ISO/IEC
25010 quality model selected for Sprint 2 / MVP v2.

## Navigation

- [Traceability summary](#traceability-summary)
- [Sprint scope and quality model](#sprint-scope-and-quality-model)
- [Assignment 5 / Sprint 3 continuity](#assignment-5--sprint-3-continuity)
- [QRT-001: Market Data Update Latency](#qrt-001-market-data-update-latency)
- [QRT-002: Exchange Data Failure Visibility](#qrt-002-exchange-data-failure-visibility)
- [QRT-003: Critical Module Test Coverage](#qrt-003-critical-module-test-coverage)

## Traceability Summary

| Quality requirement | ISO/IEC 25010 sub-characteristic | Automated QRT | Repository test or gate | CI execution |
|---|---|---|---|---|
| [QR-001: Market data update latency](quality-requirements.md#qr-001-market-data-update-latency) | Time behaviour | [QRT-001](#qrt-001-market-data-update-latency) | [`backend/tests/test_quality_requirements.py`](../backend/tests/test_quality_requirements.py) | `Quality` workflow backend job |
| [QR-002: Exchange data failure visibility](quality-requirements.md#qr-002-exchange-data-failure-visibility) | Fault tolerance | [QRT-002](#qrt-002-exchange-data-failure-visibility) | [`backend/tests/test_quality_requirements.py`](../backend/tests/test_quality_requirements.py) | `Quality` workflow backend job |
| [QR-003: Critical module test coverage](quality-requirements.md#qr-003-critical-module-test-coverage) | Testability | [QRT-003](#qrt-003-critical-module-test-coverage) | [`backend/tests/test_quality_requirements.py`](../backend/tests/test_quality_requirements.py) and [`backend/scripts/check_critical_coverage.py`](../backend/scripts/check_critical_coverage.py) | `Quality` workflow backend job |

## Sprint Scope and Quality Model

- Sprint scope: Sprint 2 / MVP v2, PB-29 / issue #107, Assignment 4 Part 4.
- Selected quality model: ISO/IEC 25010.
- Selected sub-characteristics: Time behaviour, Fault tolerance, and
  Testability.
- Automated CI entry point: the
  [`Quality` workflow](../.github/workflows/quality.yml) runs
  `coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests`,
  then generates `coverage.json` and runs
  `python backend/scripts/check_critical_coverage.py coverage.json`.
- Evidence location: latest protected-branch or pull-request run of the
  [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml),
  with the `backend-coverage` artifact when coverage evidence is needed.

## Assignment 5 / Sprint 3 Continuity

The Assignment 4 QRTs remain the maintained automated quality evidence for
Assignment 5. The A5-P05 ADRs do not replace the QRTs; they explain why the
same checks are still relevant for MVP v2:

| QRT | Assignment 5 architecture relevance | Evidence to cite in Week 5 |
|---|---|---|
| [QRT-001](#qrt-001-market-data-update-latency) | Supports WebSocket-driven market updates, exchange-specific streams, TimescaleDB-backed history, and observability latency evidence. | Backend quality tests, [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml), and [ADR-003](architecture/adr/ADR-003-websocket-driven-market-updates.md). |
| [QRT-002](#qrt-002-exchange-data-failure-visibility) | Supports independent exchange-source status and visible stale-data behavior. | Backend quality tests, [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml), [ADR-001](architecture/adr/ADR-001-independent-exchange-sources.md), and [ADR-004](architecture/adr/ADR-004-dockerized-local-deployment-and-observability.md). |
| [QRT-003](#qrt-003-critical-module-test-coverage) | Supports the maintained testability gate for critical analytics, history, storage, exchange parsing, and ML modules. | `backend-coverage` artifact, `check_critical_coverage.py`, [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml), and [ADR-002](architecture/adr/ADR-002-timescaledb-time-series-storage.md). |

If Sprint 3 product implementation changes the measured latency path, stale
status behavior, critical-module list, or coverage threshold, the same PR
should update this file and [`docs/testing.md`](testing.md).

## QRT-001: Market Data Update Latency

**Stable ID:** QRT-001

**Linked quality requirement:** [QR-001](quality-requirements.md#qr-001-market-data-update-latency)

**ISO/IEC 25010 sub-characteristic:** Time behaviour

**Verification method:** Automated backend test of the market-data latency
telemetry path. The test records deterministic trade samples through
`LatencyObservability` and checks the `exchange_to_backend` p95 latency.

**Test data, setup, or environment:** Twenty deterministic Binance `BTC-USDT`
trade samples in the standard Python test environment. Nineteen samples are
within the 1 second latency budget and one sample is above the budget to verify
the 95% threshold.

**Automated command or CI check:**
`coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests`
in the `Quality` workflow backend job. For a focused local run:
`python -m unittest backend.tests.test_quality_requirements.QualityRequirementLatencyTests`.

**Expected measurable result:** The `exchange_to_backend` latency series has
p95 latency of `1000ms` or less, and at least 95% of tested updates are within
the `1000ms` budget.

**Evidence location:** [`backend/tests/test_quality_requirements.py`](../backend/tests/test_quality_requirements.py),
the latest `Quality` workflow backend job, and the generated coverage evidence
from that job.

## QRT-002: Exchange Data Failure Visibility

**Stable ID:** QRT-002

**Linked quality requirement:** [QR-002](quality-requirements.md#qr-002-exchange-data-failure-visibility)

**ISO/IEC 25010 sub-characteristic:** Fault tolerance

**Verification method:** Automated backend test of market freshness status in
`LiveStore.market_snapshot`. The test simulates a market that stops receiving
new exchange data after the latest trade.

**Test data, setup, or environment:** Standard repository market configuration
loaded by `load_config()`, one deterministic Binance `BTC-USDT` trade, and
snapshot timestamps immediately before and at the 10 second stale-data budget.

**Automated command or CI check:**
`coverage run --source=backend.app,ml.pattern_recognition -m unittest discover -s backend/tests`
in the `Quality` workflow backend job. For a focused local run:
`python -m unittest backend.tests.test_quality_requirements.QualityRequirementFailureVisibilityTests`.

**Expected measurable result:** The market remains `live` before the 10 second
budget and becomes `stale` at `10000ms`, with the `ageMs` field exposed in the
API snapshot that the UI consumes.

**Evidence location:** [`backend/tests/test_quality_requirements.py`](../backend/tests/test_quality_requirements.py)
and the latest `Quality` workflow backend job.

## QRT-003: Critical Module Test Coverage

**Stable ID:** QRT-003

**Linked quality requirement:** [QR-003](quality-requirements.md#qr-003-critical-module-test-coverage)

**ISO/IEC 25010 sub-characteristic:** Testability

**Verification method:** Automated test of the maintained critical-module
coverage gate plus the CI coverage check itself. The unit test verifies that
the gate accepts coverage at the required threshold and fails when a critical
module drops below it.

**Test data, setup, or environment:** Synthetic `coverage.json` payloads that
include every module listed in `backend/scripts/check_critical_coverage.py`,
plus the real CI-generated `coverage.json` from backend test execution.

**Automated command or CI check:** The `Quality` workflow backend job runs
`coverage json -o coverage.json` and
`python backend/scripts/check_critical_coverage.py coverage.json`. For a
focused local run:
`python -m unittest backend.tests.test_quality_requirements.QualityRequirementCoverageGateTests`.

**Expected measurable result:** Every listed critical module is present in the
coverage report and has line coverage of at least `30%`. The CI job fails if a
critical module is missing or below `30%`.

**Evidence location:** [`backend/scripts/check_critical_coverage.py`](../backend/scripts/check_critical_coverage.py),
[`backend/tests/test_quality_requirements.py`](../backend/tests/test_quality_requirements.py),
the latest `Quality` workflow backend job, and the `backend-coverage` artifact.
