# Tickframe Pattern Recognition Pipeline

This folder contains the maintained offline training pipeline for Tickframe ML
chart-pattern recognition on real Binance public market data.

## Scope

- Dataset type: Binance public spot `1m` OHLCV
- Source timeframe: `1m`
- Prepared dataset timeframes: `1m`, `5m`, `15m`, `1h`, `1d`
- Window size: `96` closed candles
- Intended live cadence: recalculate after each newly closed `1m` candle
- Labels:
  - `head_and_shoulders`
  - `triangle`
  - `flag`
  - `double_top`
  - `double_bottom`
  - `none`

The current product model artifact is still wired to the `1m` training file.
The preparation pipeline can now produce additional timeframe datasets for
separate training and validation artifacts.

## Dataset Preparation

The prepared dataset is built from Binance Public Data monthly and daily spot
kline archives. Each configured symbol is normalized into the Tickframe candle
shape, sorted by `openTime`, scanned with rule-based weak-label detectors, and
converted into feature rows.

The cleaner enforces:

- all `openTime` / `closeTime` values are normalized to milliseconds;
- candles are sorted chronologically after monthly and daily archives are merged;
- generated windows must be contiguous, with no gap, duplicate, or backward jump;
- examples are sampled more evenly by year per symbol and label;
- hard negatives are retained as `label=none` rows with `hardNegativeFor`;
- each row stores `labelScores` and flat `softScores` such as
  `double_top_score` and `triangle_score`;
- extra prepared files are emitted for configured timeframes, e.g.
  `features-5m.jsonl`, `features-15m.jsonl`, `features-1h.jsonl`, and
  `features-1d.jsonl`.

From the repository root:

```bash
python -m ml.pattern_recognition.prepare_binance_dataset --config ml/pattern_recognition/config.json
```

Rebuild prepared datasets from already downloaded local normalized files without
network access:

```bash
python -m ml.pattern_recognition.prepare_binance_dataset --config ml/pattern_recognition/config.json --offline-normalized
```

Rewrite normalized CSV files into sorted millisecond timestamps while rebuilding:

```bash
python -m ml.pattern_recognition.prepare_binance_dataset --config ml/pattern_recognition/config.json --offline-normalized --rebuild-normalized
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
