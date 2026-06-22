import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { DisplayCandle } from "../types";

interface MarketChartProps {
  candles: DisplayCandle[];
  scopeKey: string;
  loading: boolean;
  historyLoading: boolean;
  hasMore: boolean;
  onLoadEarlier: () => void;
}

const DEFAULT_VISIBLE_BARS = 120;

function pricePrecision(value: number): number {
  if (value >= 1000) return 2;
  if (value >= 1) return 4;
  if (value >= 0.01) return 5;
  return 8;
}

export default function MarketChart({
  candles,
  scopeKey,
  loading,
  historyLoading,
  hasMore,
  onLoadEarlier,
}: MarketChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const lastScopeRef = useRef<string | null>(null);
  const resetPendingRef = useRef(true);
  const previousRangeRef = useRef<{
    first: number;
    last: number;
  } | null>(null);
  const historyStateRef = useRef({
    hasMore,
    historyLoading,
    onLoadEarlier,
  });
  const latestPrice = candles.at(-1)?.close ?? 0;
  const precision = useMemo(() => pricePrecision(latestPrice), [latestPrice]);

  useEffect(() => {
    historyStateRef.current = {
      hasMore,
      historyLoading,
      onLoadEarlier,
    };
  }, [hasMore, historyLoading, onLoadEarlier]);

  const resetViewport = useCallback(() => {
    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    if (!chart || !candleSeries || !volumeSeries || candles.length === 0) {
      return;
    }

    candleSeries.priceScale().setAutoScale(true);
    chart.priceScale("right").setAutoScale(true);
    volumeSeries.priceScale().setAutoScale(true);

    const visibleBars = Math.min(candles.length, DEFAULT_VISIBLE_BARS);
    const lastIndex = candles.length - 1;
    const rangeEnd = lastIndex + 6;
    const rangeWidth = Math.max(visibleBars + 6, 40);
    chart.timeScale().resetTimeScale();
    chart.timeScale().setVisibleLogicalRange({
      from: rangeEnd - rangeWidth,
      to: rangeEnd,
    });
  }, [candles]);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#020916" },
        textColor: "#85889a",
        fontFamily: '"IBM Plex Mono", "SFMono-Regular", Consolas, monospace',
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.045)" },
        horzLines: { color: "rgba(255, 255, 255, 0.045)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: "rgba(124, 77, 255, 0.5)",
          labelBackgroundColor: "#17172a",
        },
        horzLine: {
          color: "rgba(124, 77, 255, 0.5)",
          labelBackgroundColor: "#17172a",
        },
      },
      rightPriceScale: {
        borderColor: "rgba(255, 255, 255, 0.08)",
        scaleMargins: { top: 0.08, bottom: 0.25 },
      },
      timeScale: {
        borderColor: "rgba(255, 255, 255, 0.08)",
        timeVisible: true,
        secondsVisible: true,
        rightOffset: 6,
        barSpacing: 8,
        minBarSpacing: 1.5,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#00c878",
      downColor: "#ff355d",
      wickUpColor: "#35e58a",
      wickDownColor: "#ff4e67",
      borderVisible: false,
      priceLineColor: "#7c4dff",
      priceLineWidth: 1,
      lastValueVisible: true,
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "",
      lastValueVisible: false,
      priceLineVisible: false,
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    const handleVisibleRange = (range: { from: number; to: number } | null) => {
      if (!range || range.from > 15) return;
      const state = historyStateRef.current;
      if (state.hasMore && !state.historyLoading) {
        state.onLoadEarlier();
      }
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleRange);

    const resizeObserver = new ResizeObserver(([entry]) => {
      chart.applyOptions({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleRange);
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    const chart = chartRef.current;
    if (!candleSeries || !volumeSeries || !chart) return;

    const previousRange = previousRangeRef.current;
    const visibleRange = chart.timeScale().getVisibleRange();
    const nextRange =
      candles.length > 0
        ? {
            first: candles[0].time,
            last: candles[candles.length - 1].time,
          }
        : null;
    const historyWasPrepended =
      previousRange !== null &&
      nextRange !== null &&
      nextRange.first < previousRange.first &&
      nextRange.last >= previousRange.last;

    if (lastScopeRef.current !== scopeKey) {
      lastScopeRef.current = scopeKey;
      resetPendingRef.current = true;
      previousRangeRef.current = null;
    }

    const multiplier = 10 ** precision;
    candleSeries.applyOptions({
      priceFormat: {
        type: "price",
        precision,
        minMove: 1 / multiplier,
      },
    });

    candleSeries.setData(
      candles.map((candle) => ({
        time: candle.time as UTCTimestamp,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })),
    );
    volumeSeries.setData(
      candles.map((candle) => ({
        time: candle.time as UTCTimestamp,
        value: candle.volume,
        color:
          candle.close >= candle.open
            ? "rgba(53, 229, 138, 0.26)"
            : "rgba(255, 78, 103, 0.24)",
      })),
    );

    if (resetPendingRef.current && candles.length > 0) {
      resetPendingRef.current = false;
      const frame = window.requestAnimationFrame(resetViewport);
      previousRangeRef.current = nextRange;
      return () => window.cancelAnimationFrame(frame);
    }
    if (historyWasPrepended && visibleRange) {
      const frame = window.requestAnimationFrame(() => {
        chart.timeScale().setVisibleRange(visibleRange);
      });
      previousRangeRef.current = nextRange;
      return () => window.cancelAnimationFrame(frame);
    }
    previousRangeRef.current = nextRange;
  }, [candles, precision, resetViewport, scopeKey]);

  return (
    <div className="chart-stage">
      <div ref={containerRef} className="chart-canvas" />
      <button
        className="chart-reset"
        type="button"
        disabled={candles.length === 0}
        onClick={resetViewport}
      >
        AUTO FIT
      </button>
      {hasMore && (
        <button
          className="chart-history"
          type="button"
          disabled={historyLoading}
          onClick={onLoadEarlier}
        >
          {historyLoading ? "LOADING..." : "LOAD EARLIER"}
        </button>
      )}
      {!loading && candles.length === 0 && (
        <div className="chart-empty">
          <span className="eyebrow">NO COMPLETE CANDLES</span>
          <strong>Waiting for the first finalized interval</strong>
          <p>The live trade stream can be healthy while the 1s candle closes.</p>
        </div>
      )}
      {loading && candles.length === 0 && (
        <div className="chart-empty chart-loading">
          <span className="loading-line" />
          <span className="loading-line short" />
          <span className="loading-line" />
        </div>
      )}
    </div>
  );
}
