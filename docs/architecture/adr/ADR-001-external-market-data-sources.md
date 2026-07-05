# ADR-001: Use External Exchange APIs as Market Data Sources

## Status
Accepted

## Context
TickFrame provides market analytics and pattern detection functionality for cryptocurrency markets. The system requires reliable access to live and historical OHLCV data from multiple exchanges.

## Decision
The system will use external cryptocurrency exchange APIs (Binance and Bybit) as the primary source of market data.

## Consequences
Positive
 • Access to real-time and historical market information.
 • Support for multiple exchanges.

Negative
 • Potential rate limits and temporary service interruptions.

## Related Quality Requirements
 • QR-01 Performance
 • QR-03 Reliability
 • QR-05 Scalability
