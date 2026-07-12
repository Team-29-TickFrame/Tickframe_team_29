# Changelog

All notable changes to Tickframe MVP releases are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/), the project
uses [Semantic Versioning](https://semver.org/), and the release baseline is
generated with [git-cliff](https://git-cliff.org/) using `cliff.toml`. The final
entries are curated so the upgrade notes stay straightforward for the team and
customer reviewers.

## [3.0.0] - 2026-07-12

MVP v3 is the Week 6 handover-candidate release. It turns the analytics screen
into a configurable working environment, expands the chart from a passive
viewer into an interactive analysis tool, and hardens the real-data ML path.
Upgrade by rebuilding the Docker Compose stack so the frontend, backend, and ML
dependencies are refreshed together.

### Added

- Add an advanced market chart with Candles, Line, Area, Heikin-Ashi, and
  Baseline views; crosshair and OHLC inspection; zoom, pan, fit, latest, and
  history navigation; indicator overlays; and compact timeframe controls.
- Add persistent chart drawings for trend lines, horizontal and vertical
  levels, rectangles, Fibonacci retracements, and measurements, including
  selection, movement, duplication, deletion, visibility, locking, and style
  controls.
- Add a configurable dashboard workspace with balanced, chart-focused, and
  signal-focused presets, drag-and-drop panel placement, horizontal and
  vertical resizing, sensible per-panel limits, and saved browser preferences.
- Add responsive metrics layouts for VWAP, RSI, momentum, volume activity,
  volatility estimators, mean-reversion statistics, market anomalies, and
  cross-pair correlations.
- Add real-market-data ML pattern inference backed by LightGBM, including
  probability calibration, supported-pattern metadata, progress states, chart
  overlays, and explicit non-trading-advice presentation.
- Add scrollable alert and metric-event panels with pinned quick templates,
  compact states, browser notifications, audio cues, and persistent rules.
- Add Week 6 customer handover, transition-readiness, Sprint Review, reflection,
  and release evidence.

### Changed

- Refine the dashboard density, typography, panel headers, resize handles, and
  responsive breakpoints so the chart keeps useful height on laptop displays
  while narrow panels reflow instead of clipping information.
- Make panel dimensions follow the panel type rather than its current slot, so
  moving the chart, metrics, ML, alerts, or signals preserves appropriate size
  constraints and interaction behavior.
- Keep alert templates fixed at the top while active alerts appear in a
  separately scrollable region; keep the ML panel vertically stable while
  retaining drag-and-drop placement.
- Improve Binance dataset preparation, weak labeling, model training, artifact
  loading, and backend inference behavior for repeatable real-data ML runs.
- Harden Docker, Vite, Nginx, environment defaults, service health checks, and
  customer-facing run/deployment documentation for a more predictable local
  startup.

### Fixed

- Fix chart toolbar and OHLC readout overlap, drawing selection and movement,
  duplicated interactions, stale pointer state, and drawing persistence edge
  cases.
- Fix metrics cards and market statistics being clipped or disappearing when
  the panel is narrowed; the panel now grows to fit reflowed content within a
  bounded maximum size.
- Fix oversized empty metric areas, malformed text wrapping, horizontal data
  overflow, and inconsistent panel minimum sizes.
- Fix alerts, metric events, and compact right-rail panels so they can be made
  smaller without losing access to content; overflow is handled by internal
  scrolling.
- Fix Binance training-data defects and ML model-loading failures, with clearer
  fallback and progress states when insufficient candles are available.
- Fix critical-coverage and quality checks for the updated backend and ML paths.

## [2.0.0] - 2026-07-05

MVP v2 release. Upgrade from MVP v1 by rebuilding the Docker Compose stack,
refreshing the local environment against the current README, running the backend
and frontend quality checks, and verifying the new ML pattern panel,
observability endpoints, WebSocket streams, and chart workspace after startup.

### Added

- TICKFRAME-0092 MINOR Add stable and provisional candle WebSocket delivery to
  reduce chart latency and keep live chart updates event-driven.
- TICKFRAME-0093 MINOR Add latency observability through a backend endpoint,
  Prometheus metrics, and a provisioned Grafana dashboard.
- TICKFRAME-0094 MINOR Add the first maintained ML pattern-recognition training
  baseline with dataset preparation, weak-label generation, reproducible model
  artifacts, saved metrics, and backend API integration.
- TICKFRAME-0165 MINOR Extend the ML workflow from synthetic experiments toward
  real market data by adding resolved training configuration, dataset manifest,
  model card, sample predictions, confusion matrix, and reusable training
  outputs.
- TICKFRAME-0165 MINOR Expose ML pattern-analysis progress in the product so
  reviewers can inspect supported timeframes, confidence output, and current
  validation limits without treating the model as trading advice.
- TICKFRAME-0166 MINOR Add user-configurable market alerts with metric presets,
  price-level rules, browser-stored alert state, sound cues, and toast
  notifications.
- TICKFRAME-0167 MINOR Add TradingView-style chart controls with Candles, Line,
  and Area modes, OHLC readout, drawing tools, Fibonacci levels, measurement,
  fit/latest/history actions, and persisted drawing state.
- TICKFRAME-0159 MINOR Add a hosted documentation site for product, quality,
  testing, process, and architecture evidence.
- TICKFRAME-0152 PATCH Add Tickframe architecture views and ADR traceability.
- TICKFRAME-0107 PATCH Add automated quality requirement tests and traceability.
- TICKFRAME-0100 PATCH Add Week 4 UAT scenarios and execution results.
- TICKFRAME-0101 PATCH Add Week 4 customer review summary and transcript
  evidence.
- TICKFRAME-0157 PATCH Add the Week 5 Sprint Review summary.
- TICKFRAME-0162 PATCH Add the Assignment 5 LLM usage report.

### Changed

- TICKFRAME-0095 PATCH Update the roadmap and Definition of Done for Assignment
  4 quality expectations.
- TICKFRAME-0149 PATCH Update the Sprint 3 roadmap and MVP v2 scope rationale.
- TICKFRAME-0150 PATCH Map MVP v1 customer feedback to MVP v2 response items.
- TICKFRAME-0151 PATCH Add development process and configuration management
  documentation.
- TICKFRAME-0163 PATCH Refresh the README with current product scope, endpoints,
  run instructions, and deployment notes.
- TICKFRAME-0156 PATCH Record Week 5 UAT status when the customer session was
  postponed.
- TICKFRAME-0154 PATCH Align MVP v2 quality evidence with the maintained
  architecture, testing, CI, and release-readiness documentation.

### Fixed

- TICKFRAME-0097 PATCH Restore passing backend lint, formatting, tests, and
  critical coverage evidence.
- TICKFRAME-0099 PATCH Update the markdown link-check baseline and public link
  exclusions.
- TICKFRAME-0111 PATCH Add public sanitized demo-video evidence for release
  review.
- TICKFRAME-0178 PATCH Fix market subscription edge cases so unavailable data
  sources are skipped cleanly instead of creating noisy collector failures.
- TICKFRAME-0187 PATCH Rename the Week 5 customer feedback response file so
  documentation links remain stable.
- TICKFRAME-0193 PATCH Fix several chart-workspace regressions found during MVP
  v2 stabilization, including debug leftovers, drawing-tool state, and layout
  polish.

## [1.0.0] - 2026-06-22

MVP v1 release. Upgrade from the static MVP v0 prototype by using the repository
source and local runtime instructions as the canonical product path; the old
public MVP v0 deployment remains historical evidence only.

### Added

- TICKFRAME-0050 MINOR Implement the MVP v1 backend analytics engine with OHLCV
  history, market metrics, correlations, and deterministic event output.
- TICKFRAME-0057 MINOR Wire the MVP v1 analytics UI with candlestick
  visualization, market metrics, and product navigation.
- TICKFRAME-0043 PATCH Add MVP v1 release/demo evidence and local runtime notes.
- TICKFRAME-0030 PATCH Add normalized GitHub issue forms and the pull request
  template for team workflow.
- TICKFRAME-0062 PATCH Restore the Week 3 report structure and screenshots.

### Changed

- TICKFRAME-0035 PATCH Refresh the README, project setup, navigation, and Week 2
  references.
- TICKFRAME-0034 PATCH Create and maintain the Definition of Done, roadmap,
  Process Requirements, and Week 3 reporting artifacts.

### Fixed

- TICKFRAME-0011 PATCH Fix public MVP v0 video playback as baseline evidence.
- TICKFRAME-0064 PATCH Remove the duplicate uppercase pull request template.

[3.0.0]: https://github.com/Team-29-TickFrame/Tickframe_team_29/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/Team-29-TickFrame/Tickframe_team_29/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/Team-29-TickFrame/Tickframe_team_29/releases/tag/v1.0.0
