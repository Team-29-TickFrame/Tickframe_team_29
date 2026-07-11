import assert from "node:assert/strict";
import test from "node:test";
import { toDisplayCandles } from "./market-utils.ts";
import type { Candle } from "./types.ts";

function candle(openTime: number, close: string | null = "100"): Candle {
  return {
    exchange: "binance",
    marketType: "spot",
    instrumentId: "BTC-USDT",
    timeframe: "1m",
    openTime,
    closeTime: openTime + 60_000,
    open: close,
    high: close,
    low: close,
    close,
    baseVolume: "1",
    quoteVolume: "100",
    tradeCount: close === null ? 0 : 1,
    status: close === null ? "complete_empty" : "complete",
    revision: 1,
    firstTradeId: null,
    lastTradeId: null,
    finalizedAt: openTime + 60_000,
  };
}

test("bridges a short collection gap", () => {
  const values = toDisplayCandles([candle(0), candle(120_000, "101")]);

  assert.equal(values.length, 3);
  assert.equal(values[1].time, 60);
  assert.equal(values[1].volume, 0);
});

test("does not create thousands of bars across a long outage", () => {
  const values = toDisplayCandles([
    candle(0),
    candle(12 * 60 * 60 * 1000, "101"),
  ]);

  assert.equal(values.length, 2);
});

test("uses the previous close for an explicitly empty candle", () => {
  const values = toDisplayCandles([candle(0), candle(60_000, null)]);

  assert.equal(values.length, 2);
  assert.equal(values[1].close, 100);
  assert.equal(values[1].tradeCount, 0);
});
