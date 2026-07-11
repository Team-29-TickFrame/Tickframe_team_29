import type { Candle, DisplayCandle, Timeframe } from "./types";

const TIMEFRAME_SECONDS: Record<Timeframe, number> = {
  "1s": 1,
  "5s": 5,
  "15s": 15,
  "1m": 60,
  "5m": 5 * 60,
  "15m": 15 * 60,
  "1h": 60 * 60,
  "1d": 24 * 60 * 60,
};

export const MAX_VISUAL_BRIDGE_INTERVALS = 3;

function finiteNumber(value: string | null): number | null {
  if (value === null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function toDisplayCandles(candles: Candle[]): DisplayCandle[] {
  const values = [...candles].sort((a, b) => a.openTime - b.openTime);
  const result: DisplayCandle[] = [];
  let previousClose: number | null = null;
  let previousTime: number | null = null;

  for (const candle of values) {
    const intervalSeconds = TIMEFRAME_SECONDS[candle.timeframe];
    if (
      previousClose !== null &&
      previousTime !== null &&
      intervalSeconds !== undefined
    ) {
      const intervalMs = intervalSeconds * 1000;
      const missingIntervals = Math.max(
        0,
        Math.floor((candle.openTime - previousTime) / intervalMs) - 1,
      );

      // Bridge tiny collection gaps so the chart remains continuous. Large
      // outages stay compressed instead of allocating thousands of fake bars.
      if (missingIntervals <= MAX_VISUAL_BRIDGE_INTERVALS) {
        for (let index = 1; index <= missingIntervals; index += 1) {
          result.push({
            time: (previousTime + index * intervalMs) / 1000,
            open: previousClose,
            high: previousClose,
            low: previousClose,
            close: previousClose,
            volume: 0,
            tradeCount: 0,
          });
        }
      }
    }

    const open = finiteNumber(candle.open);
    const high = finiteNumber(candle.high);
    const low = finiteNumber(candle.low);
    const close = finiteNumber(candle.close);
    if (open === null || high === null || low === null || close === null) {
      if (previousClose !== null) {
        result.push({
          time: candle.openTime / 1000,
          open: previousClose,
          high: previousClose,
          low: previousClose,
          close: previousClose,
          volume: 0,
          tradeCount: 0,
        });
        previousTime = candle.openTime;
      }
      continue;
    }

    const volume = Number(candle.baseVolume);
    result.push({
      time: candle.openTime / 1000,
      open,
      high,
      low,
      close,
      volume: Number.isFinite(volume) ? volume : 0,
      tradeCount: candle.tradeCount,
    });
    previousClose = close;
    previousTime = candle.openTime;
  }

  return result;
}
