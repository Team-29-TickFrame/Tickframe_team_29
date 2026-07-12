import assert from "node:assert/strict";
import test from "node:test";
import type { DisplayCandle } from "./types.ts";
import {
  bollingerBands,
  exponentialMovingAverage,
  rollingVwap,
  simpleMovingAverage,
} from "./chart-indicators.ts";

const candles = [1, 2, 3, 4, 5].map((close, index): DisplayCandle => ({
  time: index + 1,
  open: close,
  high: close + 1,
  low: close - 1,
  close,
  volume: 10,
  tradeCount: 1,
}));

test("calculates SMA and EMA from the first complete window", () => {
  assert.deepEqual(simpleMovingAverage(candles, 3).map((item) => item.value), [2, 3, 4]);
  assert.deepEqual(exponentialMovingAverage(candles, 3).map((item) => item.value), [2, 3, 4]);
});

test("calculates ordered Bollinger bands", () => {
  const bands = bollingerBands(candles, 3);
  assert.equal(bands.middle.length, 3);
  for (let index = 0; index < bands.middle.length; index += 1) {
    assert.ok(bands.lower[index].value < bands.middle[index].value);
    assert.ok(bands.middle[index].value < bands.upper[index].value);
  }
});

test("rolling VWAP uses the configured window", () => {
  assert.deepEqual(
    rollingVwap(candles, 3).map((item) => Number(item.value.toFixed(6))),
    [2, 3, 4],
  );
});
