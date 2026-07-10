# Pattern Real Data v1 Model Card

## Purpose

This artifact is the maintained Tickframe training pipeline result for
geometric chart-pattern recognition on real Binance public market data. It is
an offline experiment artifact, not a production trading signal.

## Supported Scope

- Timeframe: `15m`
- Window size: `96` closed candles
- Intended update cadence: after each newly closed 15m candle
- Supported labels: head_and_shoulders, triangle, flag, double_top, double_bottom, none
- Confidence threshold planned for product integration: `0.65`

## Model

- Model version: `pattern-real-data-v1`
- Model type: `BoostedTreeClassifier`
- Model backend: `lightgbm`
- Feature count: `38`

The classifier uses handcrafted OHLCV shape features learned from weak-labeled
real Binance public market data. `auto` training attempts LightGBM first and
falls back to scikit-learn HistGradientBoosting when LightGBM is unavailable.
Gaussian Naive Bayes remains available as the baseline model.

## Dataset

- Dataset version: `binance-public-spot-1m-weak-labels-v1`
- Dataset path: `data\ml\pattern_recognition\binance-public-spot-1m\prepared\features-15m.jsonl`
- Generated at: `2026-07-10T15:36:32.912856+00:00`
- Total examples: `41200`
- Train examples: `32959`
- Test examples: `8241`

## Evaluation

- Accuracy: `0.667273`
- Macro F1: `0.60591`

See `metrics.json` and `confusion_matrix.json` for the full evaluation output.

## Limitations

- Training labels are weak labels generated from rule-based chart definitions.
- This artifact is trained only for its listed timeframe and 96-candle windows.
- Predictions should be displayed as experimental pattern observations, not as
  buy/sell advice.
- Human review, cross-exchange validation, and backtesting remain required
  before treating the model as product-quality.
