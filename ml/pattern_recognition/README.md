# Tickframe Pattern Recognition Pipeline

This folder contains the maintained offline training pipeline for Tickframe ML
chart-pattern recognition on real Binance public market data.

## Scope

- Dataset type: Binance public spot `1m` OHLCV
- Timeframe: `1m` only
- Window size: `96` closed candles
- Intended live cadence: recalculate after each newly closed `1m` candle
- Labels:
  - `head_and_shoulders`
  - `triangle`
  - `flag`
  - `double_top`
  - `double_bottom`
  - `none`

The current product should treat the model as available only for `1m`. Other
timeframes are intentionally unsupported until separate training and validation
artifacts exist.

## Dataset Preparation

The prepared dataset is built from Binance Public Data monthly spot kline
archives. Each configured symbol is downloaded from its first available monthly
archive, normalized into the Tickframe candle shape, scanned with rule-based
weak-label detectors, and converted into feature rows.

From the repository root:

```bash
python -m ml.pattern_recognition.prepare_binance_dataset --config ml/pattern_recognition/config.json
```

Local raw and prepared data are written under:

```text
data/ml/pattern_recognition/binance-public-spot-1m/
```

This directory is intentionally gitignored because it can become large.

## Model

The baseline model is a dependency-free Gaussian Naive Bayes classifier. The
pipeline trains on handcrafted OHLCV shape features generated from real
weak-labeled windows:

```text
Binance public klines -> weak labels -> features -> train classifier -> evaluate -> save artifacts
```

Weak labels are not treated as ground truth. They are reproducible candidate
labels based on classical chart-pattern definitions and should be followed by
manual review, cross-exchange validation, and backtesting.

## Run

Prepare data first, then train:

```bash
python -m ml.pattern_recognition.train_baseline --config ml/pattern_recognition/config.json
```

Fast smoke check after preparing data:

```bash
python -m ml.pattern_recognition.train_baseline --config ml/pattern_recognition/config.json --smoke
```

The default output directory is:

```text
ml/pattern_recognition/runs/real-data-v1/
```

Generated artifacts:

- `model.json` - trained classifier parameters
- `metrics.json` - accuracy, macro F1, and per-class metrics
- `confusion_matrix.json` - label-vs-prediction table
- `dataset_manifest.json` - dataset path, class counts, and split sizes
- `resolved_config.json` - exact config used for the run
- `sample_predictions.json` - small prediction sample for inspection
- `model-card.md` - human-readable model summary and limitations

## Product Integration Plan

Future integration should use only closed `1m` candles:

```text
latest 96 closed 1m candles
        -> same feature extractor
        -> model.predict_proba
        -> pattern label + confidence
```

The frontend should display `No reliable pattern detected` when the best
probability is below the configured confidence threshold.
