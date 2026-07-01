# Quality Requirements

Tickframe uses maintained ISO/IEC 25010 quality requirements for the MVP v2
market analytics scope. Assignment 5 keeps these requirements active and links
them to architecture decisions.

## Active Quality Requirements

| Requirement | Focus | Evidence |
|---|---|---|
| QR-001 | Market data update latency | QRT-001 and latency observability evidence. |
| QR-002 | Exchange data failure visibility | QRT-002 and visible stale-market status. |
| QR-003 | Critical module test coverage | QRT-003 and the critical-module coverage gate. |

## Assignment 5 Traceability

- ADR-001 supports exchange-specific latency and failure visibility.
- ADR-002 supports time-series history, rollups, repair, and testability.
- ADR-003 supports event-driven update latency and stale-state handling.
- ADR-004 supports runtime observability and CI-aligned delivery evidence.

## Key Source Documents

- [Quality requirements](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/quality-requirements.md)
- [Quality requirement tests](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/quality-requirement-tests.md)
- [Architecture decision map](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/architecture/README.md)
