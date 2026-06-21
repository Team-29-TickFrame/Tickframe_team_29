# Reflection

## Learning Points

During Week 3, the team gained practical experience in backlog management, documentation maintenance, MVP delivery, and customer review preparation.

## Key lessons learned:

* Maintaining a structured Product Backlog with stable identifiers and traceability links significantly improves Sprint planning and reporting.
* Creating supporting documentation such as docs/user-stories.md, docs/roadmap.md, docs/definition-of-done.md, CHANGELOG.md, and the updated README.md improves project transparency and onboarding.
* Story point estimation helped prioritize MVP v1 scope and identify higher-risk PBIs such as historical data processing, anomaly detection, and backtesting functionality.
* Sprint Planning was more effective when PBIs were clearly connected to MVP goals, acceptance criteria, and milestones.
* MVP v1 delivery showed that implementation alone is not enough; deployment links, repository visibility, and documentation must also be prepared before customer reviews.
* The Sprint Review highlighted the importance of ensuring that all team members understand the current implementation status and can explain completed work.
* Release preparation requires consistent version control practices, changelog maintenance, and clear mapping between delivered functionality and release artifacts.

# Validated Assumptions

## Confirmed Assumptions

* Documentation-focused PBIs improved project organization and traceability.
* Historical OHLCV data, metrics computation, anomaly detection, and alert generation represent the core functionality required for MVP v1.
* Milestones, releases, and MVP version tracking provide useful visibility into Sprint progress and delivery scope.

## Rejected or Partially Rejected Assumptions

* The assumption that all team members had sufficient visibility into backend implementation was not fully validated during the Sprint Review.
* The assumption that MVP v1 artifacts were fully accessible for review proved incorrect because some deployment and repository materials were unavailable during the meeting.
* The assumption that all planned MVP v1 functionality could be demonstrated was only partially validated, as pattern detection remained unfinished.
* The assumption that requirements interpretation was fully aligned was challenged during discussions about metrics, patterns, and detector functionality.

# Friction and Gaps

## Several challenges and risks were identified during MVP v1 delivery and review:

* MVP v1 source code and deployment artifacts were not fully available during the Sprint Review.
* The project relied heavily on a small number of contributors for backend implementation, creating knowledge-sharing risks.
* Pattern detection functionality remains incomplete and requires further implementation and testing.
* Detector calibration and validation on historical OHLCV data still require additional work.
* Customer feedback revealed uncertainty regarding architecture, framework selection, and implementation status.
* Documentation and implementation progress were occasionally out of sync, making completed work harder to demonstrate.
* Additional testing is required for metrics computation, anomaly detection, breakout alerts, and backtesting functionality.

## Planned Response

During the next Sprint, the team will focus on improving implementation transparency, delivery readiness, and feature completeness.

## Planned actions include:

* Completing the remaining MVP v1 functionality, particularly pattern detection and detector validation.
* Improving repository discipline to ensure that all completed work is committed, reviewed, and accessible before customer meetings.
* Increasing knowledge sharing across the team to reduce dependency on individual contributors.
* Performing additional testing of historical OHLCV coverage, metrics engines, anomaly detectors, breakout alerts, and backtesting modules.
* Improving Sprint Review preparation by validating deployment links, repository access, and demonstration materials before review sessions.
* Continuing Product Backlog refinement and roadmap updates to ensure alignment between customer expectations and planned scope.

The next Sprint will focus on stabilizing MVP v1, improving review readiness, and reducing technical and process-related risks identified during Week 3.
