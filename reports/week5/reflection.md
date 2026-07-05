# Week 5 Reflection

## Learning points

During Assignment 5, the team learned that architecture documentation is most useful when it is connected to maintained project evidence instead of being written as a separate explanation. The new [architecture landing page](../../docs/architecture/README.md) and ADR set helped connect exchange-source separation, time-series storage, WebSocket-driven updates, and Docker Compose observability to the existing quality model.

The ADR work also showed that quality requirements are easier to defend when the implementation rationale is explicit. Linking [QR-001](../../docs/quality-requirements.md#qr-001-market-data-update-latency), [QR-002](../../docs/quality-requirements.md#qr-002-exchange-data-failure-visibility), and [QR-003](../../docs/quality-requirements.md#qr-003-critical-module-test-coverage) to the ADRs made the relationship between product risks, quality gates, and design decisions clearer.

The team also gained experience maintaining workflow and configuration-management evidence. The [development process document](../../docs/development-process.md) made branch naming, PR review, CI checks, and secrets handling more visible, which is important for keeping Assignment 5 evidence public-safe and reproducible.

Hosted documentation preparation showed that documentation needs its own delivery workflow and verification path. A maintained documentation site can make project evidence easier to review, but it also requires the repository settings, CI workflow, and report links to stay aligned.

Finally, Week 5 reinforced that UAT and Sprint Review evidence must be planned early. The [UAT scenarios](../../docs/user-acceptance-tests.md) were maintained for Sprint 3, but the planned Week 5 customer session did not take place, so the team had to clearly separate previous customer-validated evidence from internal preparation and postponed customer execution.

## Validated assumptions

Several assumptions made earlier in the project were confirmed during Assignment 5:

- Architecture decisions are easier to review when they are linked to quality requirements and quality requirement tests.
- The Assignment 4 quality gates remain relevant for Assignment 5 because MVP v2 still depends on market-data latency, exchange failure visibility, and testable critical modules.
- Public reports are more reliable when links point to maintained source documents instead of duplicating the same evidence in many places.
- Configuration and secrets handling must be documented explicitly because public repository evidence cannot include private credentials or private access details.
- A concise [LLM usage report](llm-report.md) is enough when the team clearly explains limited use, human review, and boundaries.

Some assumptions were partially challenged:

- Hosted documentation is not only a content task; it also depends on repository-level GitHub Pages configuration and workflow execution.
- Final Week 5 reporting depends on many parallel artifacts, so small delays in UAT, Sprint Review, demo, or release evidence can affect the public report index.
- Customer-facing validation cannot be replaced by internal checks. When a customer session is missed, the report must state that honestly and preserve the follow-up work.

## Friction and gaps

Several challenges and open gaps were identified during Assignment 5:

- Week 5 evidence was distributed across architecture docs, quality docs, testing docs, UAT, hosted documentation, LLM reporting, and issue-level tracking.
- Some Sprint 3 implementation and release-readiness issues remained open while the reflection was prepared, so the reflection needed careful wording around MVP v2 delivery status.
- The Week 5 customer UAT session did not take place, leaving UAT-004 and UAT-005 as maintained scenarios with internal preparation only.
- Sprint Review evidence depends on the same public-safe discipline as UAT: no private recordings, exact timecodes, credentials, university emails, or customer-identifying details should be committed.
- Documentation links need continued maintenance as the Week 5 report, demo evidence, release evidence, and Moodle/private submission package are finalized.

Open project risks include:

- Product and documentation evidence may drift if MVP v2 implementation changes are merged without updating related ADR, QR, QRT, UAT, or testing notes.
- Release and deployment evidence may be incomplete if final configuration details are kept only in private channels and not summarized safely in public docs.
- UAT feedback for Sprint 3 scenarios may remain incomplete until the next available customer session.

## Planned response

For the next project steps, the team plans to:

- Keep the ADR map and quality requirement links current when implementation or deployment behavior changes.
- Continue using the [Quality workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/quality.yml), [Links workflow](https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/workflows/links.yml), and documented Definition of Done as merge readiness evidence.
- Complete the remaining Week 5 Sprint Review, demo, release, and submission-package evidence with public-safe wording.
- Execute postponed customer UAT for UAT-004 and UAT-005 when a customer session is available, then update [docs/user-acceptance-tests.md](../../docs/user-acceptance-tests.md).
- Use the Week 5 report as the public evidence index and keep private credentials, access details, recordings, and exact timecodes only in the private submission context.

The planned work will affect:

- Sprint 3 backlog and final Assignment 5 support issues.
- Architecture decision records under [docs/architecture/adr/](../../docs/architecture/adr/).
- Quality requirements, QRTs, testing status, and Definition of Done.
- UAT scenarios UAT-004 and UAT-005.
- Hosted documentation, release evidence, and final Moodle/private submission materials.
