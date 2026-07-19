# User Acceptance Tests

## Purpose

This document maintains end-user-facing UAT scenarios for Tickframe across the
maintained MVP increments through Assignment 6.

Week 6 customer-facing UAT was executed during the guided customer trial,
Sprint Review discussion, repository inspection, and transition-readiness
conversation on 2026-07-12.

Week 7 final transition and usefulness verification was completed during the
final customer review on 2026-07-19. The final review included product,
repository, deployment, documentation, and limitation inspection. A separate
standalone customer-executed UAT session was not conducted during Week 7.

Private recording links, exact timecodes, credentials, and customer-identifying details must not be committed to the public repository.

## UAT Scenario Index

| ID | Scenario | Status | Related scope | Last execution |
|---|---|---|---|---|
| UAT-001 | Open the product and inspect the main dashboard | Active | MVP v2 / Sprint 2 | Passed on 2026-06-27 |
| UAT-002 | Inspect market metrics and analytics output | Active | MVP v2 / Sprint 2 | Passed on 2026-06-27 |
| UAT-003 | Check latency or system health information | Active | MVP v2 / Sprint 2 | Passed on 2026-06-27 |
| UAT-004 | Validate pattern-analysis progress visibility | Active | MVP v2 / MVP v3 | Passed with follow-up on 2026-07-12 and 2026-07-19 |
| UAT-005 | Validate simple alerts and chart experience | Active | MVP v2 / MVP v3 | Passed with follow-up on 2026-07-19 |
| UAT-006 | Inspect MVP v3 trial release and product access | Active | MVP v3 / Sprint 4 | Passed with follow-up on 2026-07-12 |
| UAT-007 | Validate customer handover and deployment readiness | Active | MVP v3 / Sprint 4-5 | Passed with follow-up on 2026-07-12 and 2026-07-19 |
| UAT-008 | Confirm final transition and product usefulness | Active | MVP v3 / Sprint 5 | Passed with follow-up on 2026-07-19 |

## UAT-001: Open the product and inspect the main dashboard

**Status:** Active  
**Related scope:** MVP v2 / Sprint 2  
**Traceability:** Sprint 2 milestone and MVP v2 backlog items

### Steps
1. Open the delivered Tickframe product.
2. Confirm that the main dashboard loads.
3. Inspect the visible market or instrument information.
4. Confirm that the page is understandable for a customer user.

### Expected result
The customer can open the product and understand the main dashboard without developer assistance.

### Execution history
| Date | Executor | Result | Notes |
|---|---|---|---|
| 2026-06-27 | Customer/stakeholder with team guidance | Passed | The main Tickframe Analytics dashboard opened successfully and was understandable during the demonstration. |

## UAT-002: Inspect market metrics and analytics output

**Status:** Active  
**Related scope:** MVP v2 / Sprint 2  
**Traceability:** MVP v2 analytics and market data backlog items

### Steps
1. Open the product dashboard.
2. Locate the market metrics or analytics section.
3. Review the displayed values, charts, or signals.
4. Confirm whether the information is useful and understandable.

### Expected result
The customer can inspect the analytics output and provide feedback on usefulness, clarity, and missing information.

### Execution history
| Date | Executor | Result | Notes |
|---|---|---|---|
| 2026-06-27 | Customer/stakeholder with team guidance | Passed | Market data, chart output, ML pattern panel, and metric events were demonstrated successfully. The customer/stakeholder approved the flow. |

## UAT-003: Check real-time data availability

**Status:** Active  
**Related scope:** MVP v2 / Sprint 2  
**Traceability:** Sprint 2 real-time market data availability scope

### Steps
1. Open the product dashboard.
2. Locate live market data, exchange values, data age, venue delta, or other real-time data indicators.
3. Confirm whether the displayed data appears available and up to date.
4. Record whether the availability/status is clear for the customer.

### Expected result
The customer can understand whether real-time market data is available and sufficiently up to date for using the product.

### Execution history
| Date | Executor | Result | Notes |
|---|---|---|---|
| 2026-06-27 | Customer/stakeholder with team guidance | Passed | Real-time data availability was demonstrated through live exchange values, data age/status indicators, and venue delta. The customer approved the demonstrated flow. |

## UAT-004: Validate pattern-analysis progress visibility

**Status:** Active  
**Related scope:** MVP v2 / MVP v3
**Traceability:** [#165](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/165), [#156](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/156), [#219](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/219), [#221](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/221), [#224](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/224), [#246](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/246), [#256](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/256)

### Steps
1. Open the product and select a supported instrument/timeframe.
2. Open the pattern-analysis or ML-related section in the UI.
3. Confirm that pattern-analysis output/progress is visible and understandable.
4. Ask the customer whether this information is clear and useful.

### Expected result
The customer can see pattern-analysis progress/output and understand what functionality is currently supported in MVP v2.

### Execution history
| Date | Executor | Result | Notes |
|---|---|---|---|
| 2026-07-05 | Team (internal pre-check only) | Not executed with customer | Week 5 customer session did not take place; formal customer UAT postponed to next available session. |
| 2026-07-12 | Customer/stakeholder with team guidance | Passed with follow-up | Customer reviewed current pattern-detection behavior, supported pattern types, chart-line behavior, and the ML/rule-based validation flow. Customer requested stronger validation and manual checking of detected patterns before relying on the model as production-level evidence. |
| 2026-07-19 | Customer/stakeholder with team guidance | Passed with follow-up | Final review confirmed the improved ML visualization behavior and clarified that unconfirmed patterns should not be shown without matching validation. Customer requested a frontend switch between ML-based and rule-based detection as a future improvement. |

## UAT-005: Validate simple alerts and chart experience

**Status:** Active  
**Related scope:** MVP v2 / MVP v3
**Traceability:** [#166](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/166), [#167](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/167), [#156](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/156), [#219](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/219), [#224](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/224), [#246](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/246)

### Steps
1. Open the product and navigate to chart/market monitoring view.
2. Trigger or observe available simple alert behavior in the UI.
3. Review chart readability and interaction flow.
4. Ask the customer whether alerts and chart behavior are clear and useful.

### Expected result
The customer confirms that simple alerts and the updated chart experience are understandable and provide useful user-facing behavior.

### Execution history
| Date | Executor | Result | Notes |
|---|---|---|---|
| 2026-07-05 | Team (internal pre-check only) | Not executed with customer | Week 5 customer session did not take place; formal customer UAT postponed to next available session. |
| 2026-07-12 | Customer/stakeholder with team guidance | Partially passed with follow-up | Customer reviewed the chart-focused interface and pattern visualization behavior. Pattern visualization was useful for review, but some visualization behavior remained inconsistent; alert behavior was not the main customer-executed focus of this Week 6 session. |
| 2026-07-19 | Customer/stakeholder with team guidance | Passed with follow-up | Final review confirmed that inconsistent pattern-name-without-visualization behavior was addressed. Further detector-comparison controls remain a future improvement. |

## UAT-006: Inspect MVP v3 trial release and product access

**Status:** Active

**Related scope:** MVP v3 / Sprint 4

**Traceability:** [#200](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/200), [#202](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/202), [#204](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/204), [#218](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/218)

### Steps
1. Open the latest MVP v3 trial release or deployed trial instance.
2. Confirm that the customer can inspect the product entry point.
3. Review dashboard, chart, and market-analysis behavior that is critical for the trial release.
4. Confirm whether product access is sufficient for customer/TA review.

### Expected result
The customer can inspect the MVP v3 trial release and identify whether any
access, availability, or release-readiness blockers remain.

### Execution history
| Date | Executor | Result | Notes |
|---|---|---|---|
| 2026-07-12 | Customer/stakeholder with team guidance | Passed with follow-up | Customer reviewed the deployed trial version and repository access path. No hard access blocker was recorded; follow-up work remained for final release/readiness confirmation. |

## UAT-007: Validate customer handover and deployment readiness

**Status:** Active

**Related scope:** MVP v3 / Sprint 4-5

**Traceability:** [#203](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/203), [#204](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/204), [#212](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/212), [#218](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/218), [#219](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/219)

### Steps
1. Review the repository, README, and customer handover documentation.
2. Confirm that the Docker-based run/deployment path is documented.
3. Review database and configuration expectations at a customer-facing level.
4. Ask the customer whether the handover path is understandable and sufficient for transition.

### Expected result
The customer can understand how to clone, inspect, and run the product from the
repository and can identify remaining transition-readiness gaps.

### Execution history
| Date | Executor | Result | Notes |
|---|---|---|---|
| 2026-07-12 | Customer/stakeholder with team guidance | Passed with follow-up | Customer confirmed that the repository had already been provided and that cloning it is enough for handover. Docker deployment, TimescaleDB, and ENV configuration were discussed; moving additional port configuration into ENV variables remained a follow-up item. |
| 2026-07-19 | Customer/stakeholder with team guidance | Passed with follow-up | Customer reviewed the repository, README/run instructions, Docker Compose setup, `.env.example`, operational documentation, and current limitations. The achieved handover level is ready for independent technical use with follow-up items. |

## UAT-008: Confirm final transition and product usefulness

**Status:** Active

**Related scope:** MVP v3 / Sprint 5

**Traceability:** [#206](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/206), [#207](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/207), [#212](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/212), [#213](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/213), [#216](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/216)

### Steps
1. Review the final MVP v3 release and customer-facing documentation.
2. Confirm the final customer use/operation level.
3. Record whether the product is accepted, conditionally accepted, or not accepted.
4. Store any private customer confirmation evidence only in the private submission channel.

### Expected result
The final Week 7 report and private submission can state the final transition
outcome, product usefulness status, and any remaining handover limitations.

### Execution history
| Date | Executor | Result | Notes |
|---|---|---|---|
| 2026-07-19 | Customer/stakeholder with team guidance and private written confirmation | Passed with follow-up | The customer confirmed project acceptance. Public status is `Ready for independent use` and `Accepted with follow-up items`; private proof is stored only in the Moodle/private submission package. |

## Week 5 Execution Summary

The planned Week 5 customer UAT session did not take place.  
Only scenario maintenance and internal preparation were completed in this iteration.

Private recording links and exact timecodes are not included in the public repository and are reserved for Moodle/private submission.

| Scenario | Result | Customer feedback | Follow-up issue/PBI |
|---|---|---|---|
| UAT-001 | Passed (previous customer execution on 2026-06-27) | Previously approved in customer session. | No follow-up required from this scenario |
| UAT-002 | Passed (previous customer execution on 2026-06-27) | Previously approved in customer session. | No follow-up required from this scenario |
| UAT-003 | Passed (previous customer execution on 2026-06-27) | Previously approved in customer session. | No follow-up required from this scenario |
| UAT-004 | Not executed with customer | Customer feedback unavailable in Week 5 because the session was not held. | Next customer session |
| UAT-005 | Not executed with customer | Customer feedback unavailable in Week 5 because the session was not held. | Next customer session |

## Week 6 Execution Summary

Week 6 customer-facing UAT was executed during the guided customer trial,
Sprint Review discussion, repository inspection, and transition-readiness
conversation on 2026-07-12.

Private recording links, exact timecodes, credentials, and
customer-identifying details are not included in this public repository and are
reserved for the Moodle/private submission package.

| Scenario | Result | Customer feedback | Follow-up issue/PBI |
|---|---|---|---|
| UAT-004 | Passed with follow-up | Pattern-analysis behavior was visible, but the customer asked for stronger validation and manual checking of detected patterns. | [#219](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/219), [#221](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/221), [#224](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/224) |
| UAT-005 | Partially passed with follow-up | Chart and pattern visualization were reviewed, but some pattern visualization behavior remained inconsistent and alerts were not the main UAT focus of this session. | [#219](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/219), [#224](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/224) |
| UAT-006 | Passed with follow-up | MVP v3 trial access was reviewed; no hard customer-access blocker was recorded. | [#218](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/218) |
| UAT-007 | Passed with follow-up | Repository and Docker-based handover path were understandable; additional port configuration should be moved into ENV variables. | [#212](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/212), [#218](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/218), [#219](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/219) |

No failed Week 6 UAT scenario was recorded. The main gaps were converted into
traceable follow-up PBIs/issues rather than private-only notes.

## Week 7 Execution Summary

Week 7 final transition and usefulness verification was completed during the
final customer review on 2026-07-19. A separate standalone customer-executed
UAT session was not conducted during Week 7, but the final review verified the
customer-critical transition and product-usefulness areas required for
Assignment 6.

Private written confirmation and any customer-identifying proof remain in the
Moodle/private submission package.

| Scenario | Result | Customer feedback | Follow-up issue/PBI |
|---|---|---|---|
| UAT-004 | Passed with follow-up | Improved pattern visualization behavior was reviewed; customer requested clearer ML/rule-based comparison as future work. | [#246](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/246), [#256](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/256) |
| UAT-005 | Passed with follow-up | Pattern-name-without-visualization behavior was addressed; detector comparison remains a future improvement. | [#246](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/246), [#256](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/256) |
| UAT-007 | Passed with follow-up | Repository, README/run instructions, Docker Compose, `.env.example`, and operational documentation were reviewed and considered sufficient for the achieved transition level. | [#212](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/212), [#213](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/213) |
| UAT-008 | Passed with follow-up | Customer confirmed acceptance of the project. Handover status is `Ready for independent use` and `Accepted with follow-up items`. | [#212](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/212), [#216](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/216) |

No critical issue preventing independent technical evaluation was identified.
Remaining items are future improvements and do not block the achieved MVP v3
handover level.
