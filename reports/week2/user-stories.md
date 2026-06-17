## US-01: Log In to the Platform

**Requirement status:** Active
**MoSCoW priority:** Must Have

As a Market Analyst,
I want to securely log in to the platform,
so that I can access market analytics, alerts, and personalized settings.

### Notes and constraints
 • User authentication must be required before accessing protected features.
 • Email and password authentication is sufficient for MVP.
 • Invalid credentials should display an error message.
 • User sessions should remain active until logout or session expiration.


## US-02: Access Platform as Guest

**Requirement status:** Active
**MoSCoW priority:** Could Have

As a Visitor,
I want to access the platform without creating an account,
so that I can explore available features before signing up.

### Notes and constraints
 • Guest users have read-only access.
 • Alert creation and personalized settings are unavailable.
 • Guest sessions are temporary and not persisted.


## US-03: View live market data

**Requirement status:** Active
**MoSCoW priority:** Must Have

As a Market Analyst,
I want to view live normalized OHLCV data from multiple exchanges,
so that I can monitor the current market state in real time.

### Notes and constraints
 • Data should be aggregated into a common format.
 • Support at least two exchanges.
 • Initial MVP supports certain trading pairs.


## US-04: Detect chart patterns

**Requirement status:** Active
**MoSCoW priority:** Must Have

As a Market Analyst,
I want the system to automatically detect chart patterns,
so that I can identify significant market structures without manually inspecting charts.

### Notes and constraints
Initial patterns include:
 • Head and Shoulders
 • Double Top
 • Double Bottom
 • Triangles
 • Flags
 • Each detected pattern must include a confidence score.


## US-05: View detected signals

**Requirement status:** Active
**MoSCoW priority:** Must Have

As a Market Analyst,
I want to see detected signals in a live feed,
so that I can quickly identify important market events.

### Notes and constraints
Signals must include:
 • Timestamp
 • Trading pair
 • Pattern type
 • Confidence score


## US-06: Analyze quantitative metrics

**Requirement status:** Active
**MoSCoW priority:** Must Have

As a Market Analyst,
I want to view calculated market metrics,
so that I can better understand market conditions and market behavior.

### Notes and constraints
Initial metrics include:
 • Realized volatility
 • VWAP
 • Momentum indicators
 • Mean-reversion indicators


## US-07: Visualize patterns on charts

**Requirement status:** Active
**MoSCoW priority:** Should Have
As a Market Analyst,
I want detected patterns to be displayed directly on charts,
so that I can visually validate generated signals.

### Notes and constraints
 • Pattern annotations should be clearly visible.
 • Chart updates should occur in real time.


## US-08: Evaluate historical signal performance

**Requirement status:** Active
**MoSCoW priority:** Should Have

As a Quant Researcher,
I want to backtest detected signals against historical market data,
so that I can evaluate the effectiveness and reliability of detection algorithms.

### Notes and constraints
 • Backtests should provide hit rate statistics.
 • Historical results must be reproducible.


## US-09: Compare cross-pair correlations

**Requirement status:** Active
**MoSCoW priority:** Should Have

As a Market Analyst,
I want to analyze correlations between cryptocurrency trading pairs, so that I can identify broader market relationships and dependencies.

### Notes and constraints
 • Correlations should be computed using historical price data.
 • Correlation windows should be configurable.


## US-10: Monitor system health

**Requirement status:** Active
**MoSCoW priority:** Should Have

As a System Administrator,
I want to monitor exchange connections and data ingestion status,
so that I can quickly identify and resolve operational issues.

### Notes and constraints
 • Display connection status.
 • Display reconnection attempts.
 • Display data lag indicators.

 
## US-11: Detect previously unseen market behavior

**Requirement status:** Active
**MoSCoW priority:** Could Have

As a Market Analyst,
I want the system to identify anomalous market behavior,
so that I can investigate events that are not explained by existing pattern detectors.

### Notes and constraints
 • Anomalies should be flagged separately from known patterns.
 • False positives are acceptable in early versions.


## US-12: Export signal history

**Requirement status:** Active
**MoSCoW priority:** Could Have

As a Quant Researcher,
I want to export signal history and calculated metrics,
so that I can perform further analysis using external research tools.

### Notes and constraints
 • CSV export is sufficient for MVP.
 • Exported data should include timestamps and confidence scores.
