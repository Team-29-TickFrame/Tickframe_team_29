# Week 5 Public Report - Assignment 5

## Project

**Project name:** Tickframe
**Team:** Team 29


## Sprint 3 Planning

| Artifact | Link |
|---|---|
| Product Backlog board/view | <https://github.com/orgs/Team-29-TickFrame/projects/1> |
| Sprint Backlog platform view | <https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/3> |
| Sprint 3 milestone | <https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/3> |
| Roadmap | [docs/roadmap.md](../../docs/roadmap.md) |

**Sprint dates:** 2026-06-29 to 2026-07-06
**Sprint Goal:** Deliver MVP v2 planning and execution scope with clear
customer-feedback traceability, quality evidence, maintained architecture and
workflow documentation, and release readiness.
**Total Sprint size:** 65 Story Points
**Scope summary:** Sprint 3 focused on MVP v2 product improvements, customer
feedback response, maintained architecture documentation, ADRs, development
process and configuration-management documentation, QA/DoD evidence, hosted
documentation, UAT preparation, and Week 5 reporting.

## MVP v2 Increment

### Delivered or prepared changes

- User-configurable browser alerts with metric presets, price-level rules,
  browser-stored alert state, sound cues, and toast notifications for issue
  [#166](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/166).
- Experimental ML pattern-recognition visibility remains documented and linked
  to Sprint 3 UAT preparation through
  [docs/user-acceptance-tests.md](../../docs/user-acceptance-tests.md).
- Maintained architecture documentation and ADR traceability were added or
  updated for the current backend, frontend, storage, WebSocket, and
  observability structure.
- Development process, configuration-management, quality, testing, and
  Definition of Done documentation were updated for Assignment 5.

### Product access

| Access item | Link |
|---|---|
| Current product access artifact | ... |
| Current run instructions | [README.md - Run the Complete Product](../../README.md#run-the-complete-product) |
| Deployment notes | [README.md - Deployment](../../README.md#deployment) |
| Product access screenshot, if public link is not inspectable | ... |

## Customer Feedback Response

Detailed supporting artifact:
[reports/week5/customer-feedback-response.md](customer-feedback-response.md)

| Feedback point | Resulting PBI or issue | Status | Response |
|---|---|---|---|
| Complete and up-to-date repository requested. | [#168](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/168) | Planned / needs final evidence | Sprint 3 includes release/readiness packaging so public artifacts remain complete and inspectable. Final release evidence link: ... |
| Accessible MVP deployment requested for validation. | [#168](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/168), [#155](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/155) | Planned / needs final evidence | Deployment and release tracking are included in Sprint 3 scope. Product access link: ... |
| Better visibility of backend architecture requested. | [#152](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/152), [#151](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/151) | Partially addressed | Architecture and development-process documentation were updated. Remaining architecture diagram links: ... |
| Clearer mapping between reported and observable components requested. | [#152](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/152), [#163](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/163) | Partially addressed | The Week 5 report and maintained docs now index the major product, quality, and architecture evidence. Screenshot evidence still to insert: ... |
| Pattern detection implementation requested after MVP v1. | [#165](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/165), [#156](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/156) | Planned / needs customer validation | Sprint 3 UAT scenarios were prepared for pattern-analysis visibility. Customer-executed result link or issue update: ... |

### Feedback not addressed

Some Week 5 feedback response items remain marked as planned or partially
addressed because the final Sprint Review, customer-executed UAT, release, and
product access evidence still need to be completed or linked. Follow-up issue
or backlog view for deferred feedback: ...

## Maintained Documentation

| Maintained artifact | Link |
|---|---|
| Root README and run instructions | [README.md](../../README.md) |
| Roadmap | [docs/roadmap.md](../../docs/roadmap.md) |
| Definition of Done | [docs/definition-of-done.md](../../docs/definition-of-done.md) |
| Testing status | [docs/testing.md](../../docs/testing.md) |
| Quality requirements | [docs/quality-requirements.md](../../docs/quality-requirements.md) |
| Quality requirement tests | [docs/quality-requirement-tests.md](../../docs/quality-requirement-tests.md) |
| User acceptance tests | [docs/user-acceptance-tests.md](../../docs/user-acceptance-tests.md) |
| Development process and configuration management | [docs/development-process.md](../../docs/development-process.md) |
| Architecture documentation and ADR index | [docs/architecture/README.md](../../docs/architecture/README.md) |
| ADR directory | [docs/architecture/adr/](../../docs/architecture/adr/) |
| Changelog | [CHANGELOG.md](../../CHANGELOG.md) |

## Architecture Evidence

Tickframe's current architecture keeps public exchange streams separate,
normalizes market data into canonical trades, builds delayed and
revision-aware candles, persists time-series history in TimescaleDB, exposes
REST and WebSocket interfaces from FastAPI, renders market analytics in a React
terminal, and exports observability data through Prometheus and Grafana.

| Architecture view | Artifact |
|---|---|
| Static component view | [docs/architecture/README.md - Static View](../../docs/architecture/README.md#static-view---component-diagram) |
| Static component view PlantUML source | [docs/architecture/static-view/component-diagram.puml](../../docs/architecture/static-view/component-diagram.puml) |
| Static component view Mermaid source | [docs/architecture/static-view/component-diagram.mmd](../../docs/architecture/static-view/component-diagram.mmd) |
| Dynamic sequence view | [docs/architecture/README.md - Dynamic View](../../docs/architecture/README.md#dynamic-view---live-market-update-sequence) |
| Dynamic sequence view PlantUML source | [docs/architecture/dynamic-view/live-market-update-sequence.puml](../../docs/architecture/dynamic-view/live-market-update-sequence.puml) |
| Dynamic sequence view Mermaid source | [docs/architecture/dynamic-view/live-market-update-sequence.mmd](../../docs/architecture/dynamic-view/live-market-update-sequence.mmd) |
| Deployment view | [docs/architecture/README.md - Deployment View](../../docs/architecture/README.md#deployment-view---docker-compose-runtime) |
| Deployment view PlantUML source | [docs/architecture/deployment-view/docker-compose-deployment.puml](../../docs/architecture/deployment-view/docker-compose-deployment.puml) |
| Deployment view Mermaid source | [docs/architecture/deployment-view/docker-compose-deployment.mmd](../../docs/architecture/deployment-view/docker-compose-deployment.mmd) |
| Maintained architecture README | [docs/architecture/README.md](../../docs/architecture/README.md) |

Quality requirements are linked to architecture decisions in
[docs/quality-requirements.md](../../docs/quality-requirements.md) and
[docs/architecture/README.md](../../docs/architecture/README.md). The current
ADR set explains why the product keeps independent exchange sources, uses
TimescaleDB for time-series storage, uses WebSockets for live updates, and
keeps the runnable product stack in Docker Compose with Prometheus and Grafana.

## Testing, QA, and CI

| Evidence item | Link or status |
|---|---|
| Quality workflow | <https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml> |
| Link-check workflow | <https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml> |
| Latest protected-default-branch CI run | ... |
| Testing status document | [docs/testing.md](../../docs/testing.md) |
| Quality requirement tests | [docs/quality-requirement-tests.md](../../docs/quality-requirement-tests.md) |



## Release and Changelog

| Release evidence | Link |
|---|---|
| SemVer release mapped to MVP v2 | ... |
| Release tag | ... |
| CHANGELOG.md | [CHANGELOG.md](../../CHANGELOG.md) |
| Sprint 3 milestone linked from release | <https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/3> |
| Release notes link to Week 5 report | ... |
| Release notes link to demo video | ... |
| Release notes link to access/run instructions | ... |



## Public Sanitized Demo Video

| Demo artifact | Link |
|---|---|
| Public sanitized MVP v2 demo video, under two minutes | ... |
| Demo video linked from MVP v2 release | ... |

The public demo must use sanitized demo data and must not expose private
recordings, private credentials, customer-identifying details, or exact private
timecodes.

## User Acceptance Testing

Maintained UAT scenarios:
[docs/user-acceptance-tests.md](../../docs/user-acceptance-tests.md)

| Scenario | Week 5 result | Notes | Resulting PBI or issue |
|---|---|---|---|
| UAT-001 | Passed previously on 2026-06-27 | Existing dashboard opening scenario remains active. | No new follow-up recorded. |
| UAT-002 | Passed previously on 2026-06-27 | Existing analytics output scenario remains active. | No new follow-up recorded. |
| UAT-003 | Passed previously on 2026-06-27 | Existing real-time data availability scenario remains active. | No new follow-up recorded. |
| UAT-004 | Not yet customer-executed for Week 5 | Pattern-analysis progress visibility scenario prepared for Sprint 3. | ... |
| UAT-005 | Not yet customer-executed for Week 5 | Alerts and chart experience scenario prepared for Sprint 3. | ... |

Private UAT recording link and exact timecodes must be submitted through
Moodle only. Public summary of the customer-executed Week 5 UAT, when
completed: ...

## Sprint Review

| Sprint Review artifact | Link or status |
|---|---|
| Public Sprint Review summary | [reports/week5/sprint-review-summary.md](sprint-review-summary.md) |
| Public Sprint Review transcript, if publication was permitted | ... |
| Public Sprint Review notes, if notes were used instead of transcript | ... |
| Private recording link, Moodle only | Not committed publicly |

The current public summary states that the planned Week 5 Sprint Review was
postponed. If the review is completed before submission, update the summary,
add or link the sanitized transcript or notes, and insert the public artifact
links above. Private recording links and exact private timecodes must remain in
the Moodle submission only.

## Hosted Documentation

| Hosted artifact | Link |
|---|---|
| Hosted documentation site | <https://team-29-tickframe.github.io/Tickframe_team_29/> |
| Hosted Week 5 evidence page | <https://team-29-tickframe.github.io/Tickframe_team_29/week5/> |
| Documentation site workflow | [docs-site.yml](../../.github/workflows/docs-site.yml) |

The hosted documentation site is deployed from the maintained documentation
through the `Documentation Site` GitHub Actions workflow. Insert the latest
successful documentation deployment run here: ...

## Week 5 Supporting Reports

| Report | Link |
|---|---|
| Sprint Review summary | [reports/week5/sprint-review-summary.md](sprint-review-summary.md) |
| Retrospective | [reports/week5/retrospective.md](retrospective.md) |
| Reflection | [reports/week5/reflection.md](reflection.md) |
| LLM usage report | [reports/week5/llm-report.md](llm-report.md) |
| Customer feedback response | [reports/week5/customer-feedback-response.md](customer-feedback-response.md) |

## Screenshots

Add sanitized screenshots under `reports/week5/images/` and embed them here
before submission.

| Required screenshot | Embedded evidence |
|---|---|
| Sprint milestone | ... |
| Board or project workflow view | ... |
| Latest protected-default-branch CI run | ... |
| SemVer release | ... |
| Example reviewed issue-linked PR or MR | ... |
| Hosted documentation site | ... |
| Product access artifact, if needed | ... |

## Current Product Status

Tickframe currently has a runnable Docker Compose product stack, maintained
backend and frontend source, market-data collectors, TimescaleDB persistence,
WebSocket and REST APIs, observability, ML pattern endpoint documentation, and
an alerts-oriented Sprint 3 frontend increment. The public Week 5 evidence
still needs the final MVP v2 release link, current product access link, public
demo video link, latest protected-branch CI run link, and completed
customer-facing UAT/Sprint Review evidence where available.

## Next Steps

1. Insert the current product access artifact link.
2. Create or link the MVP v2 SemVer release.
3. Insert the latest protected-default-branch CI run.
4. Add public sanitized demo video link.
5. Add Week 5 screenshots under `reports/week5/images/` and embed them above.
6. Complete or update customer UAT and Sprint Review evidence.
7. Ensure architecture view artifacts are linked once the static, dynamic, and
   deployment diagrams are added.
8. Prepare the Moodle PDF with private-only links, credentials, timecodes,
   team identity details, and commit-hash permalinks.

## Contribution Traceability

Replace the `...` placeholders with the final team evidence before submission.

| Team member / GitHub username | Sprint role or responsibility | Issues or PBIs | PRs or MRs | Review / testing / QA / docs contribution |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |
