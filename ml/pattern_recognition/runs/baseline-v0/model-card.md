# Pattern Baseline v0 Model Card

## Purpose

This artifact is the first maintained Tickframe training pipeline result for
geometric chart-pattern recognition. It is an offline experiment artifact, not
a production trading signal.

## Supported Scope

- Timeframe: `1m` only
- Window size: `96` closed candles
- Intended update cadence: after each newly closed 1m candle
- Supported labels: head_and_shoulders, triangle, flag, double_top, double_bottom, none
- Confidence threshold planned for product integration: `0.65`

## Model

- Model version: `pattern-baseline-v0`
- Model type: `GaussianNaiveBayesClassifier`
- Feature count: `38`

The classifier uses handcrafted OHLCV shape features and a Gaussian Naive Bayes
decision rule. Each label is represented by per-feature means and variances
learned from the synthetic training split.

## Dataset

- Dataset version: `synthetic-patterns-1m-v0`
- Generated at: `2026-06-26T11:18:15.923982+00:00`
- Seed: `42`
- Total examples: `5400`
- Train examples: `4320`
- Test examples: `1080`

## Evaluation

- Accuracy: `1.0`
- Macro F1: `1.0`

See `metrics.json` and `confusion_matrix.json` for the full evaluation output.

## Limitations

- Training data is synthetic and does not prove real-market pattern quality.
- The model is maintained only for 1m candles and 96-candle windows.
- Predictions should be displayed as experimental pattern observations, not as
  buy/sell advice.
- Real-data validation, weak labeling, human labeling, and backtesting are
  planned follow-up work.
