### Week 4 Reflection

## Learning points

During Assignment 4, the team learned that customer feedback can significantly influence not only product functionality but also quality priorities and development workflow decisions. Customer discussions highlighted the importance of market data freshness, visibility of synchronization status, and transparency of analytics results.

The team gained practical experience in defining measurable quality requirements using ISO/IEC 25010 quality sub-characteristics and learned how to connect quality requirements to automated quality requirement tests (QRTs). This process demonstrated that quality attributes become significantly more valuable when they are measurable and continuously verified.

The implementation of CI quality gates showed the importance of automated verification. Integrating linting, formatting checks, automated tests, coverage reporting, quality requirement tests, and additional QA checks improved confidence in changes and reduced the risk of regressions.

Running user acceptance testing with the customer reinforced the importance of validating assumptions with real users instead of relying only on internal team expectations. The Sprint Review also demonstrated that customer understanding of system status indicators and analytics output is an important aspect of product usability.

Finally, the team learned that release preparation, changelog maintenance, and evidence preservation require continuous attention throughout the Sprint rather than being postponed until the end of development.

## Validated assumptions

Several assumptions made during earlier development stages were confirmed during Assignment 4:

- Customers value visibility into market data freshness and synchronization status.
- Automated quality gates improve confidence in repository changes and reduce integration risks.
- Maintaining measurable quality requirements simplifies verification and release readiness evaluation.
- User acceptance testing provides valuable feedback even when functionality appears technically complete.
- Real-time market analytics workflows benefit from explicit latency and reliability monitoring.

Some assumptions were partially challenged:

- Certain analytical features required additional explanation during customer demonstrations.
- Quality verification and CI maintenance required more effort than initially estimated.
- Some planned analytical improvements were postponed because quality automation and reliability improvements provided greater short-term value.

## Friction and gaps

Several challenges and open issues were identified during Assignment 4:

- Some quality requirement tests currently rely on simulated environments and will require further refinement using production-like scenarios.
- Coverage requirements for several critical modules remain close to the minimum required threshold and should be expanded during future iterations.
- Additional integration testing is needed for market data synchronization and exchange failure scenarios.
- Maintaining documentation consistency across backlog items, quality requirements, testing documentation, and reports introduced additional coordination overhead.
- CI pipelines increased verification reliability but also introduced additional maintenance requirements.
- Some customer-requested analytical improvements were deferred due to prioritization of quality, automation, and reliability work.

Open technical risks include:

- Exchange API instability and rate limiting.
- Latency variations during periods of increased market activity.
- Potential false positives in anomaly detection and pattern recognition modules.

## Planned response

In the next Sprint, the team plans to:

- Expand automated quality requirement tests and increase coverage for critical modules.
- Improve market data latency monitoring and synchronization visibility.
- Extend integration testing for exchange failures and recovery scenarios.
- Continue refining anomaly detection and advanced market analytics features.
- Maintain and extend CI quality gates introduced during Assignment 4.
- Introduce architecture documentation and architecture decision records (ADRs) required for Assignment 5.
- Continue validating assumptions through customer feedback sessions and user acceptance testing.

The planned work will affect:

- Sprint 3 backlog items and future PBIs.
- Quality requirements QR-001, QR-002, and QR-003.
- Quality requirement tests QRT-001, QRT-002, and QRT-003.
- User acceptance tests UAT-001, UAT-002, and UAT-003.
- CI quality workflows and Definition of Done requirements.
- The maintained project documentation in docs/.
