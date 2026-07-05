# Week 5 Public Report

## Sprint 3 Planning

| Artifact | Link |
|---|---|
| Product Backlog board/view | <https://github.com/orgs/Team-29-TickFrame/projects/1> |
| Sprint Backlog platform view | <https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/3> |
| Sprint 3 milestone | <https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/3> |
| Roadmap | [docs/roadmap.md](../../docs/roadmap.md) |

**Sprint dates:** 2026-06-29 to 2026-07-06
**Sprint Goal:** Prepare the MVP v2 increment and Week 5 evidence with customer
feedback traceability, architecture documentation, ADRs, process documentation,
quality evidence, and release documentation.
**Total Sprint size:** 65 Story Points

## MVP v2 Scope

Repository evidence for this Sprint includes:

- Browser alerts for issue [#166](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/166).
- UAT scenarios for pattern-analysis visibility and alerts in
  [docs/user-acceptance-tests.md](../../docs/user-acceptance-tests.md).
- Architecture views and ADRs under [docs/architecture/](../../docs/architecture/).
- Process, configuration-management, quality, testing, and DoD documentation.

## Product Access

| Access item | Link or status |
|---|---|
| Product access URL provided by the team | <http://10.93.26.194:4173/> |
| Run instructions | [README.md - Run the Complete Product](../../README.md#run-the-complete-product) |
| Deployment notes | [README.md - Deployment](../../README.md#deployment) |
| Access note | The IP address must be reachable from the reviewer network. If not, use the run instructions. |

## Customer Feedback Response

Detailed artifact: [reports/week5/customer-feedback-response.md](customer-feedback-response.md)

| Feedback point | Resulting PBI or issue | Status | Response |
|---|---|---|---|
| Complete and up-to-date repository requested. | [#168](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/168) | Partly addressed | Repository documentation was updated. Final release evidence still needs a public release link. |
| Accessible MVP deployment requested for validation. | [#168](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/168), [#155](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/155) | Partly addressed | A team-network product URL and local run instructions are listed above. Public accessibility must be checked before submission. |
| Better visibility of backend architecture requested. | [#152](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/152), [#151](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/151) | Addressed in docs | Static, dynamic, and deployment architecture sources are linked in this report. |
| Clearer mapping between reported and observable components requested. | [#152](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/152), [#163](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/163) | Partly addressed | The report links docs, workflows, and screenshots. Final issue/PR ownership mapping still needs team confirmation. |
| Pattern detection implementation requested after MVP v1. | [#165](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/165), [#156](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/156) | Prepared, not customer-validated in Week 5 | UAT-004 was prepared. It was not executed with the customer during Week 5. |

## Maintained Documentation

| Artifact | Link |
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

Quality requirements are linked to ADRs in
[docs/quality-requirements.md](../../docs/quality-requirements.md) and
[docs/architecture/README.md](../../docs/architecture/README.md).

## Testing, QA, and CI

| Evidence item | Link or status |
|---|---|
| Quality workflow | <https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml> |
| Link-check workflow | <https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml> |
| Latest protected-default-branch CI run | Link must be inserted from GitHub Actions before submission. |
| Testing status document | [docs/testing.md](../../docs/testing.md) |
| Quality requirement tests | [docs/quality-requirement-tests.md](../../docs/quality-requirement-tests.md) |

## Release and Changelog

| Release evidence | Link or status |
|---|---|
| SemVer release mapped to MVP v2 | Release link not confirmed in this report. |
| Release tag | Add the public SemVer tag link before submission. |
| CHANGELOG.md | [CHANGELOG.md](../../CHANGELOG.md) |
| MVP v2 release notes template | [reports/week5/release-notes-template.md](release-notes-template.md) |
| Sprint 3 milestone | <https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/3> |
| Release notes link to Week 5 report | Prepared in [reports/week5/release-notes-template.md](release-notes-template.md) |
| Release notes link to demo video | Not linked in this public report. |
| Release notes link to access/run instructions | Prepared in [reports/week5/release-notes-template.md](release-notes-template.md) |

## Public Sanitized Demo Video

No public demo-video link is included in this report.

## User Acceptance Testing

Maintained UAT scenarios: [docs/user-acceptance-tests.md](../../docs/user-acceptance-tests.md)

| Scenario | Week 5 result | Notes | Resulting PBI or issue |
|---|---|---|---|
| UAT-001 | Passed previously on 2026-06-27 | Existing dashboard scenario. | No new follow-up recorded. |
| UAT-002 | Passed previously on 2026-06-27 | Existing analytics scenario. | No new follow-up recorded. |
| UAT-003 | Passed previously on 2026-06-27 | Existing real-time data scenario. | No new follow-up recorded. |
| UAT-004 | Not executed with customer in Week 5 | Pattern-analysis visibility scenario prepared. | [#165](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/165), [#156](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/156) |
| UAT-005 | Not executed with customer in Week 5 | Alerts and chart scenario prepared. | [#166](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/166), [#167](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/167), [#156](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/156) |

## Sprint Review

| Sprint Review artifact | Link or status |
|---|---|
| Public Sprint Review summary | [reports/week5/sprint-review-summary.md](sprint-review-summary.md) |
| Public Sprint Review transcript | Not published. |
| Public Sprint Review notes | Not published. |
| Private recording link | Not committed publicly. |

## Hosted Documentation

| Hosted artifact | Link |
|---|---|
| Hosted documentation site | <https://team-29-tickframe.github.io/Tickframe_team_29/> |
| Hosted Week 5 evidence page | <https://team-29-tickframe.github.io/Tickframe_team_29/week5/> |
| Documentation site workflow | [docs-site.yml](../../.github/workflows/docs-site.yml) |

## Week 5 Supporting Reports

| Report | Link |
|---|---|
| Sprint Review summary | [reports/week5/sprint-review-summary.md](sprint-review-summary.md) |
| Retrospective | [reports/week5/retrospective.md](retrospective.md) |
| Reflection | [reports/week5/reflection.md](reflection.md) |
| LLM usage report | [reports/week5/llm-report.md](llm-report.md) |
| Customer feedback response | [reports/week5/customer-feedback-response.md](customer-feedback-response.md) |

## Screenshots

| Required screenshot | Embedded evidence |
|---|---|
| Sprint milestone | ![Hosted docs site](reports/week5/images/docs_site.png) |
| Board or project workflow view | ![Sprint board](reports/week5/images/sprint_board.png) |
| Latest protected-default-branch CI run | Not added. |
| SemVer release | ![Hosted docs site](reports/week5/images/docs_site.png)|
| Example reviewed issue-linked PR or MR | ![Hosted docs site](reports/week5/images/docs_site.png) |
| Hosted documentation site | ![Hosted docs site](reports/week5/images/docs_site.png) |
| Product access artifact, if needed | Not added. |


## Contribution Traceability

| Team member / GitHub username | Public evidence currently in this report |
|---|---|
| `IvanGuzhov822` | Local commit history shows repository activity. Sprint 3 issue/PR mapping is not documented here. |
| `DianaSam` | Local commit history shows repository activity. Sprint 3 issue/PR mapping is not documented here. |
| `kayumowanas` | Local commit history shows repository activity. Sprint 3 issue/PR mapping is not documented here. |
| `kristina19-gif` | Local commit history shows repository activity. Sprint 3 issue/PR mapping is not documented here. |
| `z1nny` | Local commit history shows repository activity. Sprint 3 issue/PR mapping is not documented here. |
