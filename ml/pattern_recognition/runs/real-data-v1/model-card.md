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
- Model type: `GaussianNaiveBayesClassifier`
- Feature count: `38`

The classifier uses handcrafted OHLCV shape features and a Gaussian Naive Bayes
decision rule. Each label is represented by per-feature means and variances
learned from weak-labeled real Binance public market data.

## Dataset

- Dataset version: `binance-public-spot-1m-weak-labels-v1`
- Dataset path: `data/ml/pattern_recognition/binance-public-spot-1m/prepared/features.jsonl`
- Generated at: `2026-07-03T10:55:29.841673+00:00`
- Total examples: `18000`
- Train examples: `14400`
- Test examples: `3600`

## Evaluation

- Accuracy: `0.503611`
- Macro F1: `0.431362`

See `metrics.json` and `confusion_matrix.json` for the full evaluation output.

## Limitations

- Training labels are weak labels generated from rule-based chart definitions.
- The model is maintained only for 1m candles and 96-candle windows.
- Predictions should be displayed as experimental pattern observations, not as
  buy/sell advice.
- Human review, cross-exchange validation, and backtesting remain required
  before treating the model as product-quality.
