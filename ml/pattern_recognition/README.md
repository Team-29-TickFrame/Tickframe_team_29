# Tickframe Pattern Recognition Pipeline

This folder contains the first maintained training pipeline for Tickframe ML
chart-pattern recognition. It is intentionally offline and is not integrated
into the live backend/frontend yet.

## Scope

- Dataset type: synthetic OHLCV windows
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

## Model

The baseline model is a dependency-free Gaussian Naive Bayes classifier. The
pipeline converts each 96-candle window into handcrafted OHLCV shape features,
then learns per-class feature means and variances.

This is a small baseline, not a production-quality market model. Its purpose is
to make the ML workflow reproducible:

```text
synthetic candles -> features -> train classifier -> evaluate -> save artifacts
```

## Run

From the repository root:

```bash
python -m ml.pattern_recognition.train_baseline --config ml/pattern_recognition/config.json
```

Fast smoke check:

```bash
python -m ml.pattern_recognition.train_baseline --config ml/pattern_recognition/config.json --smoke
```

The default output directory is:

```text
ml/pattern_recognition/runs/baseline-v0/
```

Generated artifacts:

- `model.json` - trained classifier parameters
- `metrics.json` - accuracy, macro F1, and per-class metrics
- `confusion_matrix.json` - label-vs-prediction table
- `dataset_manifest.json` - dataset version, seed, class counts, split sizes
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
