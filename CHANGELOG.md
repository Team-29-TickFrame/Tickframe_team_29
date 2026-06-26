# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/) and the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Dockerized React/TypeScript market terminal with live Binance and Bybit
  instrument selection, candlestick history, health state, metrics, correlations,
  and deterministic event cards.
- Assignment 3 workflow, backlog, and release preparation updates.
- Chart latency diagnostics in candle responses and the terminal footer.
- Persisted metric history tables and a metrics WebSocket for pushed summaries.
- Event-driven market, candle, and metrics WebSocket delivery, including a
  stable candle stream for chart-tail updates.

### Changed
- Product documentation and repository workflow are being aligned with the
  current MVP v1 delivery.
- Reduced default short-chart latency settings and polling cadence for issue #92.
- Moved live metrics toward backend-owned snapshots with REST fallback polling.
- Replaced chart-tail polling with stable candle WebSocket updates.

### Fixed
- No entries yet.

### Removed
- No entries yet.

### Deprecated
- No entries yet.

### Security
- No entries yet.
