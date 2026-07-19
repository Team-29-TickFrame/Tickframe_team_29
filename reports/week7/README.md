# Week 7 Report Tickframe
Tickframe is a real-time crypto market pattern recognition and metrics engine that provides honest signals, reproducible analysis, and a clean workflow for team delivery.

## Public Demo Video
You can watch our full product demonstration here:
https://drive.google.com/file/d/1sC_zHEWR8qXjkSKvsInc_yKBgmOq0Ymz/view?usp=sharing

## Sprint Overview
This report summarizes the final activities completed during **Sprint 5 (Week 7)** and serves as the public evidence index for Assignment 6. The sprint focused on final maintenance, customer transition, documentation completion, and preparation of the final MVP v3 release.

| Item | Link |
| --- | --- |
| Previous Week Report | [`../week6/README.md`](../week6/README.md) |
| Product Backlog | GitHub Project Backlog |
| Sprint 5 Board | GitHub Sprint 5 Board |
| Sprint 5 Milestone | GitHub Sprint 5 Milestone |
| Sprint Goal | Complete MVP v3 transition and final public documentation |
| Sprint Dates | Week 7 |
| Total Story Points | Sprint 5 Total |

---

# Final MVP v3
During the final sprint the team focused on stabilization rather than introducing major new features.

Completed work includes:
- Final customer handover documentation.
- Final deployment verification.
- Documentation maintenance.
- Repository cleanup.
- Public demonstration preparation.
- Final Sprint Review documentation.
- Reflection and retrospective.
- Final LLM usage report.
- Final public release preparation.
- Minor maintenance improvements after Week 6.

The resulting MVP v3 represents the final maintained state of Tickframe for Assignment 6.

# Product Access
## Repository
```text
https://github.com/Team-29-TickFrame/Tickframe_team_29
```

## Quick Start

### Clone the repository
```bash
git clone https://github.com/Team-29-TickFrame/Tickframe_team_29.git
cd Tickframe_team_29
```
### Create runtime configuration
```bash
cp .env.example .env
```

### Build and start
```bash
docker compose up -d --build
```

### Frontend
```text
http://127.0.0.1:4173
```

### Backend
```text
http://127.0.0.1:8000
```

### Swagger
```text
http://127.0.0.1:8000/docs
```

## Customer-Facing Documentation

| Documentation | Link |
| --- | --- |
| Customer Handover | [`../../docs/customer-handover.md`](../../docs/customer-handover.md) |
| Roadmap | [`../../docs/roadmap.md`](../../docs/roadmap.md) |
| Architecture | [`../../docs/architecture/README.md`](../../docs/architecture/README.md) |
| Testing | [`../../docs/testing.md`](../../docs/testing.md) |
| User Acceptance Tests | [`../../docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md) |
| Quality Requirements | [`../../docs/quality-requirements.md`](../../docs/quality-requirements.md) |
| Backend Documentation | [`../../backend/README.md`](../../backend/README.md) |
| Runtime Configuration | [`../../.env.example`](../../.env.example) |
| Docker Compose | [`../../docker-compose.yml`](../../docker-compose.yml) |
| Contributing Guide | [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) |
| Repository Guidelines | [`../../AGENTS.md`](../../AGENTS.md) |

---

## Hosted Documentation
The maintained documentation site is available through GitHub Pages.

- Hosted Documentation: https://team-29-tickframe.github.io/Tickframe_team_29/

## Final Handover Status

### Handover Level

**Ready for independent use**
The project repository, deployment instructions, runtime configuration template, and customer documentation are sufficient for another technical user to deploy and evaluate Tickframe MVP v3 independently.

### Customer Confirmation

**Accepted with follow-up items**
During the final Sprint Review the customer confirmed that the current documentation and deployment guidance are sufficient for the achieved transition level.

The remaining work consists of future improvements rather than blockers preventing technical use.


## Follow-up Items

The following items remain for future development:
- Improve the experimental machine learning subsystem.
- Add frontend controls for selecting ML-based and rule-based detection.
- Extend the frontend maintenance interface.
- Continue validating pattern recognition using larger public datasets.

These items do not prevent independent use of the current MVP v3.

## Customer Feedback
During the final Sprint Review the customer evaluated the completed MVP v3 and confirmed that the project reached the expected transition level.

### Customer Requests

Throughout the project the customer requested:
- reliable real-time market monitoring;
- reproducible pattern detection;
- clear deployment documentation;
- maintainable architecture;
- transparent analytics;
- operational monitoring;
- straightforward onboarding for technical users.

### Response

The project currently provides:
- documented Docker deployment;
- public technical documentation;
- monitoring through Prometheus and Grafana;
- historical market data loading;
- rule-based pattern detection;
- experimental machine-learning support;
- maintained repository structure.

The customer accepted the current project state with several future improvements identified for continued development.

## User Acceptance Trial

Maintained UAT scenarios: [`../../docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md)

The final customer review included UAT-related verification of:
- repository accessibility;
- deployment instructions;
- Docker Compose configuration;
- runtime environment and `.env.example`;
- backend API and frontend interface;
- monitoring stack;
- customer documentation;
- remaining limitations.

A separate standalone customer-executed UAT session was not conducted during
Week 7. The final Sprint Review and transition-confirmation discussion covered
the customer-critical UAT areas needed for final transition and product
usefulness evidence.

| Scenario | Result | Public-safe feedback summary | Follow-up issue/PBI |
|---|---|---|---|
| UAT-004 | Passed with follow-up | Improved pattern visualization behavior was reviewed; customer requested clearer ML/rule-based comparison as future work. | [#246](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/246), [#256](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/256) |
| UAT-005 | Passed with follow-up | Pattern-name-without-visualization behavior was addressed; detector comparison remains a future improvement. | [#246](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/246), [#256](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/256) |
| UAT-007 | Passed with follow-up | Repository, README/run instructions, Docker Compose, `.env.example`, and operational documentation were reviewed and considered sufficient for the achieved transition level. | [#212](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/212), [#213](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/213) |
| UAT-008 | Passed with follow-up | Customer confirmed acceptance of the project. Handover status is `Ready for independent use` and `Accepted with follow-up items`. | [#212](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/212), [#216](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/216) |

No critical issue preventing independent technical evaluation was identified.
Remaining items are future improvements and do not block the achieved MVP v3
handover level.


## Final Release

### Public Release
The final MVP v3 release is available through the project's GitHub Releases page.

Related artifacts include:
- Final Release
- CHANGELOG.md
- Public Demo Video

## Public Demo
The final sanitized public demonstration video is available through the project repository.

## Sprint Review Evidence

| Evidence | Link |
| --- | --- |
| Sprint Review Summary | [`sprint-review-summary.md`](sprint-review-summary.md) |
| Sprint Review Transcript | [`sprint-review-transcript.md`](sprint-review-transcript.md) |
| Reflection | [`reflection.md`](reflection.md) |
| Retrospective | [`retrospective.md`](retrospective.md) |
| LLM Report | [`llm-report.md`](llm-report.md) |

## Documentation Updates

The following documentation was reviewed and updated during Week 7:
- customer handover;
- roadmap;
- deployment instructions;
- release documentation;
- hosted documentation;
- Sprint Review report;
- retrospective;
- reflection;
- LLM report;
- README files.

## Contribution Traceability

| Team Member | Main Contribution | Public Evidence |
| --- | --- | --- |
| Ivan Guzov | Backend, ML, pattern, detection, dataset, preparation, backend, technical fixes | Git history, pull requests |
| Roman Mitrofanov | Backend, Core platform, analytics workspace, market data, charts, alerts, deployment and release readiness | Git history, pull requests |
| Kristina Pilipchuk  | Backend, Product, Backlog, sprint planning, user-story traceability, public documentation, customer feedback, UAT planning | Git history, pull requests |
| Diana Samoilova | Frontend, Sprint Review, Sprint Retrospective, customer validation, evidence, public reports, demo materials | Git history, pull requests |
| Anastasia Kaiumova  | Frontend, Evidence, ADRs, UAT, documentation, private, submissions, presentation, customer handover documentation | Git history, pull requests |

## Public Evidence
The following screenshots are stored in `reports/week7/images/` and provide inspectable public evidence.

### Sprint Milestone
![Sprint Milestone](images/sprint5-milestone.png)

### Final Release
![Release](images/release.png)

### Product Deployment
![Deployment](images/deployment.png)

### Reviewed Pull Request
![Reviewed PR](images/reviewed-pr.png)

### Product Dashboard
![Dashboard](images/dashboard.png)

## Current Product Status
Tickframe MVP v3 represents the final maintained version delivered for Assignment 6.

Current project capabilities include:
- Real-time cryptocurrency market monitoring.
- Rule-based pattern detection.
- Machine-learning pattern analysis.
- Historical candle loading.
- REST API with OpenAPI documentation.
- Grafana dashboards.
- Prometheus monitoring.
- Docker Compose deployment.
- Public technical documentation.
- Customer handover documentation.

The project is considered **Ready for independent use** within the documented scope.

## Remaining Limitations
- ML predictions are validated against rule-based labels rather than independently verified market ground truth.
- Some maintenance functionality is currently available only through backend scripts.

## Support Expectations

The public repository contains all documentation required for installation, deployment, and technical evaluation.

Future development may include:
- additional ML model improvements;
- expanded frontend controls;
- extended monitoring capabilities;
- additional supported exchanges;
- further optimization of pattern detection.

No additional private documentation is required for the achieved handover level.

## Assignment 6 Deliverables

The final Assignment 6 public repository includes:
- MVP v3 source code;
- Product documentation;
- Architecture documentation;
- Development process documentation;
- Testing documentation;
- Customer handover guide;
- Sprint Review summary;
- Sprint Review transcript;
- Sprint retrospective;
- Team reflection;
- LLM usage report;
- Public demo video;
- Final release;
- CHANGELOG;
- Hosted documentation;
- Docker deployment configuration.

## Repository Navigation

| Resource | Link |
| --- | --- |
| Project README | [`../../README.md`](../../README.md) |
| Customer Handover | [`../../docs/customer-handover.md`](../../docs/customer-handover.md) |
| Architecture | [`../../docs/architecture/README.md`](../../docs/architecture/README.md) |
| Roadmap | [`../../docs/roadmap.md`](../../docs/roadmap.md) |
| Testing | [`../../docs/testing.md`](../../docs/testing.md) |
| Backend | [`../../backend/README.md`](../../backend/README.md) |
| CHANGELOG | [`../../CHANGELOG.md`](../../CHANGELOG.md) |
| Week 6 Report | [`../week6/README.md`](../week6/README.md) |
