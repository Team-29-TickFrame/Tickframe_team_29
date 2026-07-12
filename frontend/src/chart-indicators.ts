import type { UTCTimestamp } from "lightweight-charts";
import type { DisplayCandle } from "./types";

export interface IndicatorPoint {
  time: UTCTimestamp;
  value: number;
}

export interface BollingerPointSet {
  lower: IndicatorPoint[];
  middle: IndicatorPoint[];
  upper: IndicatorPoint[];
}

const point = (candle: DisplayCandle, value: number): IndicatorPoint => ({
  time: candle.time as UTCTimestamp,
  value,
});

export function simpleMovingAverage(
  candles: DisplayCandle[],
  period: number,
): IndicatorPoint[] {
  if (period < 1) return [];
  const result: IndicatorPoint[] = [];
  let sum = 0;
  for (let index = 0; index < candles.length; index += 1) {
    sum += candles[index].close;
    if (index >= period) sum -= candles[index - period].close;
    if (index >= period - 1) result.push(point(candles[index], sum / period));
  }
  return result;
}

export function exponentialMovingAverage(
  candles: DisplayCandle[],
  period: number,
): IndicatorPoint[] {
  if (period < 1 || candles.length < period) return [];
  const result: IndicatorPoint[] = [];
  let average =
    candles.slice(0, period).reduce((sum, candle) => sum + candle.close, 0) /
    period;
  result.push(point(candles[period - 1], average));
  const multiplier = 2 / (period + 1);
  for (let index = period; index < candles.length; index += 1) {
    average += (candles[index].close - average) * multiplier;
    result.push(point(candles[index], average));
  }
  return result;
}

export function bollingerBands(
  candles: DisplayCandle[],
  period: number,
  deviations = 2,
): BollingerPointSet {
  const lower: IndicatorPoint[] = [];
  const middle: IndicatorPoint[] = [];
  const upper: IndicatorPoint[] = [];
  if (period < 1) return { lower, middle, upper };

  let sum = 0;
  let sumSquares = 0;
  for (let index = 0; index < candles.length; index += 1) {
    const close = candles[index].close;
    sum += close;
    sumSquares += close * close;
    if (index >= period) {
      const removed = candles[index - period].close;
      sum -= removed;
      sumSquares -= removed * removed;
    }
    if (index < period - 1) continue;
    const mean = sum / period;
    const variance = Math.max(0, sumSquares / period - mean * mean);
    const spread = Math.sqrt(variance) * deviations;
    middle.push(point(candles[index], mean));
    upper.push(point(candles[index], mean + spread));
    lower.push(point(candles[index], mean - spread));
  }
  return { lower, middle, upper };
}

export function rollingVwap(
  candles: DisplayCandle[],
  period: number,
): IndicatorPoint[] {
  if (period < 1) return [];
  const result: IndicatorPoint[] = [];
  let priceVolume = 0;
  let volume = 0;
  for (let index = 0; index < candles.length; index += 1) {
    const candle = candles[index];
    const typicalPrice = (candle.high + candle.low + candle.close) / 3;
    priceVolume += typicalPrice * candle.volume;
    volume += candle.volume;
    if (index >= period) {
      const removed = candles[index - period];
      const removedTypical = (removed.high + removed.low + removed.close) / 3;
      priceVolume -= removedTypical * removed.volume;
      volume -= removed.volume;
    }
    if (index >= period - 1 && volume > 0) {
      result.push(point(candle, priceVolume / volume));
    }
  }
  return result;
}
