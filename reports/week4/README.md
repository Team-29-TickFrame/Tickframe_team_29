# Week 4 Report

Tickframe is a real-time crypto market analytics product for inspecting live
Binance and Bybit data, chart history, market metrics, pattern observations,
and operational latency/status signals.

This report is the public Assignment 4 submission index. Private recordings,
exact timecodes, credentials, university emails, and customer-identifying
evidence are intentionally excluded from the public repository and must be
submitted only through Moodle/private instructor channels.

## Sprint Scope

| Item | Evidence |
|---|---|
| Product Backlog board/view | [Team project board](https://github.com/orgs/Team-29-TickFrame/projects/1) |
| Sprint Backlog board/table | [Sprint 2 milestone scope](https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/2) |
| Assignment 4 Sprint milestone | [Sprint 2](https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/2) |
| MVP v2 filtered view | [Issues labeled `mvp-v2`](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues?q=is%3Aissue%20label%3Amvp-v2) |
| Backlog and Sprint evidence | [`reports/week4/backlog-sprint-evidence.md`](backlog-sprint-evidence.md) |

- Sprint dates: 2026-06-22 to 2026-06-28.
- Sprint Goal: improve the MVP v1 market analytics increment based on customer
  feedback by reducing and measuring data latency, starting the
  pattern-detection model training direction, and establishing maintained
  Assignment 4 quality gates, CI evidence, UAT, release, and reporting assets.
- Total Sprint size: 47 Story Points.
- Scope summary: latency reduction and observability, metric and candle
  WebSocket delivery, persisted metric history, ML pattern baseline work, UAT,
  testing/coverage/CI gates, release evidence, and Week 4 reporting assets.

## Delivered Increment

Delivered product changes include:

- Reduced short-chart latency and replaced chart-tail polling with stable candle
  WebSocket updates.
- Added chart latency diagnostics and frontend display telemetry.
- Added persisted metric history plus WebSocket pushed metric snapshots.
- Added Prometheus latency metrics and a Grafana latency dashboard.
- Added the first maintained offline ML pattern-recognition training baseline
  and product endpoint integration for supported `1m` windows.
- Added maintained quality requirements, QRT traceability, testing evidence,
  critical-module coverage gates, and CI quality gates.

Access and run evidence:

- Current run instructions: [`README.md`](../../README.md#run-the-complete-product)
- Docker Compose deployment instructions: [`README.md`](../../README.md#deployment)
- Historical public MVP v0 deployment: <https://tickframe.h1n.ru/>
- Current product is runnable through Docker Compose; public deployment access
  details that contain credentials or private host information must be supplied
  only through Moodle/private submission.

## Customer Feedback Response

| Feedback point | Resulting PBI or issue | Status | Response |
|---|---|---|---|
| MVP v1 review needed clearer live-data availability and deployment evidence. | [#92](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/92), [#93](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/93) | Done in Sprint 2 | Reduced chart latency, added latency diagnostics, and exposed observability metrics/dashboard evidence. |
| Customer/stakeholder needed the analytics flow to remain understandable during review. | [#100](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/100), [#101](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/101) | Done in Sprint 2 | Executed and summarized UAT/customer review evidence with sanitized public results. |
| Pattern detection direction remained important but needed a safer foundation. | [#94](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/94) | Done in Sprint 2 | Added a synthetic baseline training pipeline and safe experimental ML endpoint behavior. |
| Public sanitized demo video is required for Assignment 4 release evidence. | [#111](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/111) | Tracked separately | Demo video will be added later by the owner of #111 and is not included in this release-evidence PR. |

No additional public follow-up PBI was required from the three passed UAT
scenarios. Private access details, recordings, and timecodes are Moodle-only.

## Maintained Project Assets

| Asset | Link |
|---|---|
| Roadmap | [`docs/roadmap.md`](../../docs/roadmap.md) |
| Definition of Done | [`docs/definition-of-done.md`](../../docs/definition-of-done.md) |
| Quality requirements | [`docs/quality-requirements.md`](../../docs/quality-requirements.md) |
| Quality requirement tests | [`docs/quality-requirement-tests.md`](../../docs/quality-requirement-tests.md) |
| Testing status | [`docs/testing.md`](../../docs/testing.md) |
| User acceptance tests | [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md) |
| Changelog | [`CHANGELOG.md`](../../CHANGELOG.md) |

The quality model used is ISO/IEC 25010. The selected Assignment 4
sub-characteristics are Time behaviour (`QR-001`), Fault tolerance (`QR-002`),
and Testability (`QR-003`).

## Testing and CI

| Evidence item | Link or location | Status |
|---|---|---|
| Unit tests | [`backend/tests`](../../backend/tests) | 69 tests passing locally on 2026-06-28 |
| Integration tests | [`backend/tests/test_service_history.py`](../../backend/tests/test_service_history.py), [`backend/tests/test_database_history.py`](../../backend/tests/test_database_history.py), [`backend/tests/test_api_patterns.py`](../../backend/tests/test_api_patterns.py) | Passing locally on 2026-06-28 |
| Automated QRTs | [`docs/quality-requirement-tests.md`](../../docs/quality-requirement-tests.md) and [`backend/tests/test_quality_requirements.py`](../../backend/tests/test_quality_requirements.py) | Passing locally through backend tests and coverage gate |
| Critical-module coverage | [`docs/testing.md`](../../docs/testing.md#critical-modules-and-coverage-status) | All 10 critical modules pass the 30% gate; global measured coverage is 66% |
| Quality CI pipeline | [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) | Runs on pull requests, pushes to `main`, and manual dispatch |
| Latest protected-branch quality run | [Quality workflow runs](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml) | Must be green after the release-evidence PR merges |
| Link-check CI pipeline | [Links workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml) | Runs on Markdown/link-check changes in pull requests and pushes to `main` |
| CI configuration | [`.github/workflows/quality.yml`](../../.github/workflows/quality.yml) | Backend lint/format/tests/coverage, frontend typecheck/build, and datetime-safety additional QA |
| Link-check configuration | [`.github/workflows/links.yml`](../../.github/workflows/links.yml), [`github/workflows/links.yml`](../../github/workflows/links.yml), and [`lychee.toml`](../../lychee.toml) | Lychee checks repository Markdown links |
| Link-check exclusions | [`docs/link-check-exclusions.md`](../../docs/link-check-exclusions.md) | Documents local URL exclusions for Lychee |
| Branch protection or rules evidence | `reports/week4/images/` or Moodle screenshots | Store screenshots privately/publicly according to sensitivity |
| Additional QA check | `ruff check --select DTZ backend/app ml/pattern_recognition` | Passing locally on 2026-06-28; runs in the Quality workflow |

The additional QA check protects timestamp handling by detecting naive datetime
anti-patterns in backend and ML source. This risk matters because Tickframe's
latency, history windows, observability evidence, and market-data correctness
depend on consistent time handling.

The Assignment 4 tests, CI checks, QRTs, coverage gate, and Definition of Done
remain active project assets. Later work must keep them passing or replace them
with documented equivalent-or-stronger checks.

## Release Evidence

| Item | Evidence |
|---|---|
| Assignment 4 SemVer release | Planned mapped release: `v1.1.0` from protected `main` after the release PR is merged |
| Release PBI | [#103](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/103) |
| Changelog release section | [`CHANGELOG.md`](../../CHANGELOG.md#110---2026-06-28) |
| Public sanitized demo video | Tracked separately by [#111](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/111) |

The final `v1.1.0` release description must identify the Assignment 4 Sprint
increment, link [Sprint 2](https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/2),
and link current run instructions.

## UAT and Customer Review

| Item | Evidence |
|---|---|
| UAT scenarios and execution summary | [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md) |
| Public sanitized UAT result | UAT-001, UAT-002, and UAT-003 passed on 2026-06-27 |
| Customer review summary | [`reports/week4/customer-review-summary.md`](customer-review-summary.md) |
| Public transcript or notes | No public transcript is committed; private recording/timecode evidence is Moodle-only |

## Reflection, Retro, and LLM Use

| Artifact | Link |
|---|---|
| Week 4 reflection | [`reports/week4/reflection.md`](reflection.md) |
| Week 4 retrospective | [`reports/week4/retrospective.md`](retrospective.md) |
| Week 4 LLM report | [`reports/week4/llm-report.md`](llm-report.md) |

## Contribution Traceability

| Team member | Issues / PBIs | PRs or evidence | Activity |
|---|---|---|---|
| `kayumowanas` | [#103](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/103), [#104](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/104) | This release-evidence branch/PR | Changelog, release evidence, report alignment, and presentation-material planning |
| `dianasamojlova5947-cmyk` | [#100](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/100), [#101](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/101), [#109](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/109), [#111](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/111) | [#114](https://github.com/Team-29-TickFrame/Tickframe_team_29/pull/114), [#116](https://github.com/Team-29-TickFrame/Tickframe_team_29/pull/116), [#120](https://github.com/Team-29-TickFrame/Tickframe_team_29/pull/120), [#121](https://github.com/Team-29-TickFrame/Tickframe_team_29/pull/121), [#129](https://github.com/Team-29-TickFrame/Tickframe_team_29/pull/129) | UAT, customer review, LLM report, retrospective, and demo-video task ownership |
| `IvanGuzhov822` | [#94](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/94), [#97](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/97), [#98](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/98) | [#113](https://github.com/Team-29-TickFrame/Tickframe_team_29/pull/113), [#123](https://github.com/Team-29-TickFrame/Tickframe_team_29/pull/123), [#124](https://github.com/Team-29-TickFrame/Tickframe_team_29/pull/124) | ML baseline, tests, coverage, and CI quality gates |
| `z1nnyy` | [#99](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/99), [#107](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/107) | [#132](https://github.com/Team-29-TickFrame/Tickframe_team_29/pull/132) and [quality requirement test work](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/107) | Quality requirements, QRT automation, and link-check/quality traceability work |

## Screenshots and Public Evidence

Screenshots for Sprint milestone, latest protected-default-branch CI run,
branch protection/rules evidence, coverage/test report, additional QA result,
SemVer release, and an example reviewed issue-linked PR should be stored under
[`reports/week4/images/`](images/) or submitted privately when the screenshot
contains instructor-only information. Product Backlog, Sprint Backlog, deployed
product, or runnable artifact screenshots should be added there when public
links may not be inspectable by graders.

## Current Product Status and Next Steps

Tickframe has a runnable Docker Compose product foundation with live exchange
collectors, persisted candles and metrics, real-time analytics UI,
observability, and an experimental ML pattern baseline.

Next steps:

- Merge the release-evidence PR after review and confirm the protected
  default-branch Quality run is green.
- Publish `v1.1.0` from protected `main`.
- Add the public sanitized demo video link later through the separate #111
  evidence flow.
- Submit private Sprint Review/UAT recording links, timecodes, credentials, and
  rehearsed presentation video through Moodle only.
