# Pattern Real Data v1 Model Card

## Purpose

This artifact is the maintained Tickframe training pipeline result for
geometric chart-pattern recognition on real Binance public market data. It is
an offline experiment artifact, not a production trading signal.

## Supported Scope

- Timeframe: `1m` only
- Window size: `96` closed candles
- Intended update cadence: after each newly closed 1m candle
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
- Dataset path: `data/ml/pattern_recognition/binance-public-spot-1m/prepared/features.jsonl`
- Generated at: `2026-07-10T14:39:47.721129+00:00`
- Total examples: `49403`
- Train examples: `39523`
- Test examples: `9880`

## Evaluation

- Accuracy: `0.750911`
- Macro F1: `0.768031`

See `metrics.json` and `confusion_matrix.json` for the full evaluation output.

## Limitations

- Training labels are weak labels generated from rule-based chart definitions.
- The model is maintained only for 1m candles and 96-candle windows.
- Predictions should be displayed as experimental pattern observations, not as
  buy/sell advice.
- Human review, cross-exchange validation, and backtesting remain required
  before treating the model as product-quality.
