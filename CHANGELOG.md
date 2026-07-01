# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/) and the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- No entries yet.

### Changed
- No entries yet.

### Fixed
- Stopped subscribing to unavailable Binance `TONUSDT` and renamed the Bybit
  market to canonical `GRAM-USDT` for issue #178.

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
