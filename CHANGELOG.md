# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/) and the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Pipeline task, malformed-message, in-flight database, and dropped-event
  diagnostics in the health response.
- Functional asset search plus candlestick, line, area, drawing, history, and
  viewport controls in the live chart workspace.

### Changed
- Split the chart engine into a lazy-loaded frontend chunk and debounced
  browser storage writes for faster startup and smoother chart interaction.
- Reduced Docker build context size and hardened the runtime with a non-root
  backend user, frontend healthcheck, graceful shutdown limits, and safer Nginx
  proxy defaults.
- Indexed instrument configuration lookups used by the high-frequency trade
  parsers and added fail-fast validation for invalid market configuration.
- Reworked the analytics workspace into a denser graphite market terminal with
  readable metric states, compact ML context, formatted event values, and
  responsive source navigation.

### Fixed
- Restored the frontend production build after conflicting chart alert-line
  references were merged.
- Reconnected market, candle, and metrics WebSockets automatically after
  transient network failures and bounded stalled REST requests with timeouts.
- Prevented Bybit heartbeat failures, malformed exchange messages, and isolated
  trade/candle processing errors from permanently stopping live-data workers.
- Prevented shutdown hangs and full-queue database writer deadlocks during
  database outages, and stopped counting rolled-back writes as successful.
- Validated ML datasets and model artifacts before training or inference so
  malformed, non-finite, or inconsistent feature vectors fail clearly.
- Fixed collapsed mobile panels, overlapping chart controls, missing dashboard
  alert styles, and long market-data outages creating thousands of empty visual
  candles.

### Removed
- No entries yet.

### Deprecated
- No entries yet.

### Security
- Bounded authentication and telemetry payload sizes, hardened password-hash
  parsing, and moved expensive password hashing off the async event loop.

## [1.2.0] - 2026-07-06

### Added
- User-configurable market alerts with metric presets, level-break rules,
  browser-stored alert state, sound cues, and bottom-right toast notifications
  for issue #166.
- Assignment 5 architecture evidence with static, dynamic, and deployment
  views in PlantUML and Mermaid source formats.
- Public-safe Week 5 evidence index, customer-feedback response, Sprint Review
  summary, reflection, retrospective, LLM usage report, and MVP v2 release
  notes template.

### Changed
- Updated architecture, development-process, quality, testing, UAT, roadmap,
  and hosted-docs links for the Assignment 5 / MVP v2 reporting package.

### Fixed
- Stopped subscribing to unavailable Binance `TONUSDT` and renamed the Bybit
  market to canonical `GRAM-USDT` for issue #178.
- Fixed the Week 5 docs-site customer-feedback link.

### Removed
- No entries yet.

### Deprecated
- No entries yet.

### Security
- No entries yet.

## [1.1.0] - 2026-06-28

### Added
- Dockerized React/TypeScript market terminal with live Binance and Bybit
  instrument selection, candlestick history, health state, metrics, correlations,
  and deterministic event cards.
- Assignment 3 workflow, backlog, and release preparation updates.
- Chart latency diagnostics in candle responses and the terminal footer.
- Persisted metric history tables and a metrics WebSocket for pushed summaries.
- Event-driven market, candle, and metrics WebSocket delivery, including a
  stable candle stream for chart-tail updates.
- Assignment 4 quality requirements, automated quality requirement test
  traceability, maintained testing documentation, and CI quality gates.
- Week 4 customer UAT, customer review summary, reflection, retrospective, and
  Assignment 4 public report evidence.
- Public sanitized Assignment 4 demo video link for issue #111.

### Changed
- Product documentation and repository workflow are aligned with the current
  Assignment 4 / MVP v2 Sprint increment.
- Reduced default short-chart latency settings and polling cadence for issue
  #92.
- Moved live metrics toward backend-owned snapshots with REST fallback polling.
- Replaced chart-tail polling with stable candle WebSocket updates.
- Replaced the organization-licensed Gitleaks action with a reproducible Ruff
  datetime-safety additional QA check.

### Fixed
- Restored passing backend lint and formatting gates required by the Assignment
  4 Quality workflow.
