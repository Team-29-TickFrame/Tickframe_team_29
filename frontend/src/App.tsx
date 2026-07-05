import {
  type CSSProperties,
  type FormEvent,
  type PointerEvent as ReactPointerEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  candleWebSocketUrl,
  fetchCandles,
  fetchCurrentUser,
  fetchHealth,
  fetchInstruments,
  fetchMarkets,
  fetchMetrics,
  fetchMlPattern,
  login,
  logout,
  marketWebSocketUrl,
  metricsWebSocketUrl,
  postDisplayTelemetry,
  register,
  stableCandleWebSocketUrl,
} from "./api";
import MarketChart, { type ChartAlertLine } from "./components/MarketChart";
import type {
  AuthResponse,
  AuthUser,
  Candle,
  CandleStreamResponse,
  CandlesResponse,
  DisplayCandle,
  DisplayTelemetrySample,
  Exchange,
  HealthResponse,
  HistorySource,
  Instrument,
  Market,
  MarketsResponse,
  MetricEvent,
  MetricPoint,
  MetricsResponse,
  MlPatternResponse,
  StreamStatus,
  Timeframe,
} from "./types";

const EXCHANGES: Exchange[] = ["binance", "bybit"];
const TIMEFRAMES: Timeframe[] = [
  "1s",
  "5s",
  "15s",
  "1m",
  "5m",
  "15m",
  "1h",
];
const HISTORY_PAGE_SIZE = 1500;
const METRICS_LIMIT = 300;
const STATS_TIMEFRAME: Timeframe = "1m";
const STATS_LIMIT = 24 * 60;
const STATS_WINDOW_MS = 24 * 60 * 60 * 1000;
const METRICS_FALLBACK_POLL_MS = 10_000;
const STATS_FALLBACK_POLL_MS = 60_000;
const AUTH_TOKEN_STORAGE_KEY = "tickframe.authToken";
const GUEST_AUTH_TOKEN = "guest";
const GUEST_AUTH_RESPONSE: AuthResponse = {
  token: GUEST_AUTH_TOKEN,
  tokenType: "bearer",
  expiresAt: "2099-12-31T23:59:59.000Z",
  user: {
    id: "guest",
    email: "guest@tickframe.local",
    displayName: "Guest",
    createdAt: "2026-01-01T00:00:00.000Z",
  },
};
const TIMEFRAME_SECONDS: Record<Timeframe, number> = {
  "1s": 1,
  "5s": 5,
  "15s": 15,
  "1m": 60,
  "5m": 5 * 60,
  "15m": 15 * 60,
  "1h": 60 * 60,
};
const MAX_VISUAL_BRIDGE_CANDLES = 5000;

interface AuthSession {
  token: string;
  user: AuthUser;
}

interface DashboardProps {
  session: AuthSession;
  onLogout: () => void;
}

type ActiveView = "dashboard" | "alerts";
type AlertMetricId =
  | "price"
  | "rsi"
  | "vwapDeviationPct"
  | "shortMomentumPct"
  | "momentumPct"
  | "meanReversionZScore"
  | "realizedVolatilityPct"
  | "volumeSpikeRatio"
  | "priceVolumeDivergencePct";
type AlertCondition = "above" | "below" | "crosses_above" | "crosses_below";
type AlertSeverity = "medium" | "high";

interface UserAlert {
  id: string;
  label: string;
  exchange: Exchange;
  instrumentId: string;
  instrumentBase: string;
  timeframe: Timeframe;
  metric: AlertMetricId;
  condition: AlertCondition;
  threshold: number;
  cooldownMs: number;
  once: boolean;
  enabled: boolean;
  createdAt: number;
  lastTriggeredAt: number | null;
}

interface AlertDraft {
  label: string;
  metric: AlertMetricId;
  condition: AlertCondition;
  threshold: string;
  cooldownSeconds: string;
  once: boolean;
}

interface AlertToast {
  id: string;
  title: string;
  body: string;
  severity: AlertSeverity;
  createdAt: number;
}

interface AlertPreset {
  label: string;
  description: string;
  metric: AlertMetricId;
  condition: AlertCondition;
  threshold: number | ((livePrice: number | null) => number | null);
  cooldownSeconds: number;
  once?: boolean;
}

const USER_ALERTS_STORAGE_KEY = "tickframe.userAlerts.v1";
const ALERT_TOAST_TTL_MS = 8_000;
const ALERT_TOAST_EXIT_MS = 260;
const ALERT_BEEP_DATA_URI =
  "data:audio/wav;base64,UklGRuQDAABXQVZFZm10IBAAAAABAAEAoA8AAEAfAAACABAAZGF0YcADAAAAAIIBIQEc/Mv7hARXCFP9vfNE/pwOJAjM8Z3wXArpFev88eUg+WgaDhLs6XjjAQ02JAAAxti88FAkfh7q5E/Wdgv9LcYFLdTN6YEjgSPN6S3UxgX9LXYLT9bq5Isf6CYK773SAABDLfYQGNl14BYbsSmK9APSOvrTKzMWf9x/3DMW0ys6+gPSivSxKRYbdeAY2fYQQy0AAL3SCu/oJosf6uRP1nYL/S3GBS3UzemBI4Ejzekt1MYF/S12C0/W6uSLH+gmCu+90gAAQy32EBjZdeAWG7EpivQD0jr60yszFn/cf9wzFtMrOvoD0or0sSkWG3XgGNn2EEMtAAC90grv6CaLH+rkT9Z2C/0txgUt1M3pgSOBI83pLdTGBf0tdgtP1urkix/oJgrvvdIAAEMt9hAY2XXgFhuxKYr0A9I6+tMrMxZ/3H/cMxbTKzr6A9KK9LEpFht14BjZ9hBDLQAAvdIK7+gmix/q5E/Wdgv9LcYFLdTN6YEjgSPN6S3UxgX9LXYLT9bq5Isf6CYK773SAABDLfYQGNl14BYbsSmK9APSOvrTKzMWf9x/3DMW0ys6+gPSivSxKRYbdeAY2fYQQy0AAL3SCu/oJosf6uRP1nYL/S3GBS3UzemBI4Ejzekt1MYF/S12C0/W6uSLH+gmCu+90gAAQy32EBjZdeAWG7EpivQD0jr60yszFn/cf9wzFtMrOvoD0or0sSkWG3XgGNn2EEMtAAC90grv6CaLH+rkT9Z2C/0txgUt1M3pgSOBI83pLdTGBf0tdgtP1urkix/oJgrvvdIAAEMt9hAY2XXgFhuxKYr0A9I6+tMrMxZ/3H/cMxbTKzr6A9KK9LEpFht14BjZ9hBDLQAAvdIK7+gmix/q5E/Wdgv9LcYFLdTN6YEjgSPN6S3UxgX9LXYLT9bq5Isf6CYK773SAABDLfYQGNl14BYbsSmK9APSOvrTKzMWf9x/3DMW0ys6+gPSivSxKRYbdeAY2fYQQy0AAL3SCu/oJosf6uRP1nYL/S3GBS3UzemBI4Ejzekt1MYF/S12C0/W6uSLH+gmCu+90gAAQy32EBjZdeAWG7EpivQD0jr60yszFn/cf9wzFtMrOvoD0or0sSkWG3XgGNn2EEMtAAC90grv6CaLH+rkT9Z2C/0txgUt1M3pgSOBI83pLdTGBf0tdgtP1urkix/oJgrvvdIAAEMt9hAY2XXgFhuxKYr0A9I6+tMrMxZ/3H/cMxbTKzr6A9KK9LEpFht14BjZ9hBDLQAAvdIK7+gmix/q5E/Wdgv9LcYFLdTN6YEjgSPN6S3UxgX9LXYLT9bq5Isf6CYK773SAABDLfYQGNl14BYbsSmK9APSOvrTKzMWf9x/3DMW0ys6+gPSivSxKRYbdeAY2fYQQy0AAL3SCu/oJosf6uRP1nYL/S3GBS3UzemBI4Ejzekt1MYF/S12C0/W6uSLH+gmCu+90gAAsiyKEI7aCeJkGZEmi/Wc1uD6WCYlE9LhROJQEpsjYfvJ2x73yx9QFL3oy+MWDK8fAABz4cP0ShkcFBPvd+bgBgUbUgNZ58rzFROkEqD0F+rRAtgVTQU97Sf0aA0MEDf5du4AAGgQ8AXf8sD1dwiCDLX8WvN8/vUKRgUD+HX4cQQ4CP3+h/hI/rwFYwN0/Bz8fAFlAwAAvf1d//kAZQA=";

const ALERT_METRICS: Array<{
  id: AlertMetricId;
  label: string;
  shortLabel: string;
  unit: "price" | "percent" | "ratio" | "number";
}> = [
  { id: "price", label: "Last trade price", shortLabel: "Price", unit: "price" },
  { id: "rsi", label: "RSI", shortLabel: "RSI", unit: "number" },
  { id: "vwapDeviationPct", label: "VWAP deviation", shortLabel: "VWAP dev", unit: "percent" },
  { id: "shortMomentumPct", label: "Short momentum", shortLabel: "Short mom", unit: "percent" },
  { id: "momentumPct", label: "Long momentum", shortLabel: "Momentum", unit: "percent" },
  { id: "meanReversionZScore", label: "Mean reversion Z-score", shortLabel: "Z-score", unit: "number" },
  { id: "realizedVolatilityPct", label: "Realized volatility", shortLabel: "Volatility", unit: "percent" },
  { id: "volumeSpikeRatio", label: "Volume spike ratio", shortLabel: "Volume spike", unit: "ratio" },
  { id: "priceVolumeDivergencePct", label: "Price / volume divergence", shortLabel: "Divergence", unit: "percent" },
];

const ALERT_CONDITIONS: Array<{ id: AlertCondition; label: string }> = [
  { id: "above", label: "Moves above" },
  { id: "below", label: "Moves below" },
  { id: "crosses_above", label: "Breaks above" },
  { id: "crosses_below", label: "Breaks below" },
];

const ALERT_PRESETS: AlertPreset[] = [
  {
    label: "Price +1%",
    description: "Notify when price trades 1% above now.",
    metric: "price",
    condition: "crosses_above",
    threshold: (price) => (price === null ? null : price * 1.01),
    cooldownSeconds: 120,
  },
  {
    label: "Price -1%",
    description: "Notify when price trades 1% below now.",
    metric: "price",
    condition: "crosses_below",
    threshold: (price) => (price === null ? null : price * 0.99),
    cooldownSeconds: 120,
  },
  {
    label: "RSI high",
    description: "Notify when RSI moves above 70.",
    metric: "rsi",
    condition: "above",
    threshold: 70,
    cooldownSeconds: 180,
  },
  {
    label: "RSI low",
    description: "Notify when RSI moves below 30.",
    metric: "rsi",
    condition: "below",
    threshold: 30,
    cooldownSeconds: 180,
  },
  {
    label: "Volume spike",
    description: "Notify when volume is 2x baseline.",
    metric: "volumeSpikeRatio",
    condition: "above",
    threshold: 2,
    cooldownSeconds: 180,
  },
];

const DEFAULT_ALERT_DRAFT: AlertDraft = {
  label: "",
  metric: "price",
  condition: "crosses_above",
  threshold: "",
  cooldownSeconds: "120",
  once: false,
};

function TickframeLogo({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`brand-logo ${className}`.trim()}
      viewBox="0 0 96 96"
      role="img"
      aria-label="Tickframe logo"
    >
      <defs>
        <linearGradient id="tickframeLogoStroke" x1="12" x2="84" y1="76" y2="20">
          <stop offset="0%" stopColor="#35a7ff" />
          <stop offset="52%" stopColor="#6f6bff" />
          <stop offset="100%" stopColor="#8b3dff" />
        </linearGradient>
        <linearGradient id="tickframeLogoT" x1="30" x2="66" y1="24" y2="72">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="58%" stopColor="#eef2ff" />
          <stop offset="100%" stopColor="#9aa7ff" />
        </linearGradient>
      </defs>
      <path
        className="logo-hex-fill"
        d="M48 7.5 83 27.8v40.4L48 88.5 13 68.2V27.8L48 7.5Z"
      />
      <path
        className="logo-hex-outline"
        d="M48 7.5 83 27.8v40.4L48 88.5 13 68.2V27.8L48 7.5Z"
      />
      <path className="logo-t-mark" d="M25.5 26.5h45L64 39H55v31H41V39h-9L25.5 26.5Z" />
    </svg>
  );
}

const COIN_LOGO_SYMBOLS = new Set([
  "BTC",
  "ETH",
  "SOL",
  "XRP",
  "AVAX",
  "TON",
  "TRX",
  "BONK",
  "PENGU",
  "FLOKI",
]);

function CoinLogo({
  base,
  className = "",
}: {
  base: string | undefined;
  className?: string;
}) {
  const symbol = (base ?? "?").toUpperCase();
  const fileName = COIN_LOGO_SYMBOLS.has(symbol)
    ? symbol.toLowerCase()
    : "unknown";

  return (
    <span
      className={`coin-logo coin-${fileName} ${className}`.trim()}
      title={`${symbol} logo`}
    >
      <img
        src={`/assets/coins/${fileName}.png`}
        alt=""
        aria-hidden="true"
        draggable={false}
      />
    </span>
  );
}

function HeroBrandPoster() {
  return (
    <div className="hero-brand-poster">
      <svg
        className="hero-poster-chart"
        viewBox="0 0 720 560"
        aria-hidden="true"
      >
        <g className="poster-grid">
          <path d="M24 42H696M24 138H696M24 234H696M24 330H696M24 426H696M24 522H696" />
          <path d="M78 28V538M190 28V538M302 28V538M414 28V538M526 28V538M638 28V538" />
        </g>
        <path
          className="poster-ma-line"
          d="M52 530 C112 528 134 492 174 436 C206 390 242 356 294 350 C356 344 390 378 430 308 C456 260 488 230 538 222 C582 214 604 172 640 116 C664 78 688 62 710 52"
        />
        <g className="poster-candles">
          <path className="violet" d="M38 378v128" />
          <rect className="violet" x="26" y="406" width="24" height="56" rx="4" />
          <path className="violet" d="M70 394v96" />
          <rect className="violet" x="58" y="424" width="24" height="32" rx="4" />
          <path className="green" d="M102 338v146" />
          <rect className="green" x="90" y="378" width="24" height="92" rx="4" />
          <path className="green" d="M134 250v170" />
          <rect className="green" x="122" y="292" width="24" height="88" rx="4" />
          <path className="violet light" d="M166 228v126" />
          <rect className="violet light" x="154" y="268" width="24" height="72" rx="4" />
          <path className="violet" d="M198 214v106" />
          <rect className="violet" x="186" y="276" width="24" height="32" rx="4" />
          <path className="green" d="M230 112v206" />
          <rect className="green" x="218" y="202" width="24" height="106" rx="4" />
          <path className="violet" d="M262 140v154" />
          <rect className="violet" x="250" y="188" width="24" height="80" rx="4" />
          <path className="violet" d="M294 174v154" />
          <rect className="violet" x="282" y="242" width="24" height="62" rx="4" />
          <path className="violet" d="M326 202v142" />
          <rect className="violet" x="314" y="268" width="24" height="58" rx="4" />
          <path className="violet" d="M358 242v134" />
          <rect className="violet" x="346" y="298" width="24" height="60" rx="4" />
          <path className="violet" d="M390 286v126" />
          <rect className="violet" x="378" y="336" width="24" height="66" rx="4" />
          <path className="violet" d="M422 318v120" />
          <rect className="violet" x="410" y="364" width="24" height="52" rx="4" />
          <path className="green" d="M454 286v92" />
          <rect className="green" x="442" y="326" width="24" height="42" rx="4" />
          <path className="green" d="M486 226v142" />
          <rect className="green" x="474" y="278" width="24" height="82" rx="4" />
          <path className="green" d="M518 198v122" />
          <rect className="green" x="506" y="248" width="24" height="64" rx="4" />
          <path className="green" d="M550 136v134" />
          <rect className="green" x="538" y="194" width="24" height="74" rx="4" />
          <path className="green" d="M582 118v104" />
          <rect className="green" x="570" y="162" width="24" height="48" rx="4" />
          <path className="violet" d="M614 58v132" />
          <rect className="violet" x="602" y="104" width="24" height="60" rx="4" />
          <path className="violet" d="M646 104v126" />
          <rect className="violet" x="634" y="150" width="24" height="44" rx="4" />
          <path className="green" d="M678 56v164" />
          <rect className="green" x="666" y="94" width="24" height="86" rx="4" />
        </g>
      </svg>
    </div>
  );
}

function coerceNumber(value: string | null): number | null {
  if (value === null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function toDisplayCandles(candles: Candle[]): DisplayCandle[] {
  const values = [...candles].sort((a, b) => a.openTime - b.openTime);
  const result: DisplayCandle[] = [];
  let previousClose: number | null = null;
  let previousTime: number | null = null;
  let bridgeCount = 0;

  for (const candle of values) {
    const intervalSeconds = TIMEFRAME_SECONDS[candle.timeframe] ?? null;
    if (
      previousClose !== null &&
      previousTime !== null &&
      intervalSeconds !== null
    ) {
      const intervalMs = intervalSeconds * 1000;
      for (
        let openTime = previousTime + intervalMs;
        openTime < candle.openTime && bridgeCount < MAX_VISUAL_BRIDGE_CANDLES;
        openTime += intervalMs
      ) {
        result.push({
          time: openTime / 1000,
          open: previousClose,
          high: previousClose,
          low: previousClose,
          close: previousClose,
          volume: 0,
          tradeCount: 0,
        });
        bridgeCount += 1;
      }
    }

    const open = coerceNumber(candle.open);
    const high = coerceNumber(candle.high);
    const low = coerceNumber(candle.low);
    const close = coerceNumber(candle.close);
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
    result.push({
      time: candle.openTime / 1000,
      open,
      high,
      low,
      close,
      volume: Number(candle.baseVolume),
      tradeCount: candle.tradeCount,
    });
    previousClose = close;
    previousTime = candle.openTime;
  }
  return result;
}

function mergeCandles(current: Candle[], incoming: Candle[]): Candle[] {
  const merged = new Map(
    current.map((candle) => [candle.openTime, candle]),
  );
  for (const candle of incoming) {
    merged.set(candle.openTime, candle);
  }
  return [...merged.values()].sort((a, b) => a.openTime - b.openTime);
}

function formatPrice(value: number | null): string {
  if (value === null) return "--";
  if (value >= 1_000) {
    return value.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  if (value >= 1) return value.toFixed(4);
  if (value >= 0.01) return value.toFixed(5);
  return value.toFixed(8);
}

function formatCompact(value: number | null, digits = 2): string {
  if (value === null || !Number.isFinite(value)) return "--";
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: digits,
  }).format(value);
}

function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "--";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatMetricPercent(value: number | null, signed = false): string {
  if (value === null || !Number.isFinite(value)) return "--";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)}%`;
}

function formatRatio(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "--";
  return `${value.toFixed(2)}x`;
}

function formatSignedNumber(value: number | null, digits = 2): string {
  if (value === null || !Number.isFinite(value)) return "--";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}`;
}

function formatCorrelation(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "--";
  return formatSignedNumber(value, 3);
}

function metricTone(value: number | null | undefined): "positive" | "negative" | "" {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "";
  }
  return value < 0 ? "negative" : "positive";
}

function formatConfidence(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "--";
  return `${Math.round(value * 100)}%`;
}

function patternLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function formatAge(value: number | null | undefined): string {
  if (value === null || value === undefined) return "no data";
  if (value < 1_000) return `${Math.round(value)} ms`;
  return `${(value / 1_000).toFixed(1)} s`;
}

function formatClock(value: number | null | undefined): string {
  if (!value) return "--";
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(value);
}

function formatEndpointHost(value: string | null | undefined): string {
  if (!value) return "--";
  try {
    return new URL(value).host;
  } catch {
    return value.replace(/^wss?:\/\//, "").split("/")[0] || value;
  }
}

function rejectedTopicReason(
  collector: HealthResponse["collectors"][Exchange] | undefined,
  market: Market | null,
): string | null {
  if (!collector?.rejectedTopics || !market) return null;
  return collector.rejectedTopics[`publicTrade.${market.exchangeSymbol}`] ?? null;
}

function exchangeLabel(exchange: Exchange): string {
  return exchange[0].toUpperCase() + exchange.slice(1);
}

function eventLabel(event: MetricEvent): string {
  return event.type
    .split("_")
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function alertMetricDefinition(metric: AlertMetricId) {
  return ALERT_METRICS.find((item) => item.id === metric) ?? ALERT_METRICS[0];
}

function conditionLabel(condition: AlertCondition): string {
  return ALERT_CONDITIONS.find((item) => item.id === condition)?.label ?? condition;
}

function createAlertId(prefix = "alert"): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function safeStoredAlerts(): UserAlert[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(USER_ALERTS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as UserAlert[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (alert) =>
        typeof alert.id === "string" &&
        typeof alert.label === "string" &&
        typeof alert.threshold === "number" &&
        typeof alert.enabled === "boolean",
    );
  } catch {
    return [];
  }
}

function alertMetricValue(
  metric: AlertMetricId,
  livePrice: number | null,
  latestMetrics: MetricPoint | null,
): number | null {
  if (metric === "price") return livePrice;
  const value = latestMetrics?.[metric];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatAlertValue(metric: AlertMetricId, value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "--";
  const definition = alertMetricDefinition(metric);
  if (definition.unit === "price") return formatPrice(value);
  if (definition.unit === "percent") return formatMetricPercent(value, true);
  if (definition.unit === "ratio") return formatRatio(value);
  return formatSignedNumber(value, 2);
}

function alertConditionMet(
  condition: AlertCondition,
  currentValue: number,
  previousValue: number | null,
  threshold: number,
): boolean {
  if (condition === "above") return currentValue > threshold;
  if (condition === "below") return currentValue < threshold;
  if (previousValue === null) return false;
  if (condition === "crosses_above") {
    return previousValue <= threshold && currentValue > threshold;
  }
  return previousValue >= threshold && currentValue < threshold;
}

function alertSeverity(alert: UserAlert, currentValue: number): AlertSeverity {
  const distance =
    alert.threshold === 0
      ? Math.abs(currentValue)
      : Math.abs((currentValue - alert.threshold) / alert.threshold);
  return distance > 0.05 || alert.metric === "price" ? "high" : "medium";
}

function marketKey(market: Market): string {
  return `${market.exchange}:${market.instrumentId}`;
}

type PendingDisplayTelemetrySample = Omit<
  DisplayTelemetrySample,
  "displayedAt"
>;

const displayTelemetryLastSentAt = new Map<string, number>();
const DISPLAY_TELEMETRY_MIN_INTERVAL_MS = 1_000;

function scheduleDisplayTelemetry(
  key: string,
  samples: PendingDisplayTelemetrySample[],
) {
  if (samples.length === 0) return;
  const now = Date.now();
  const previous = displayTelemetryLastSentAt.get(key) ?? 0;
  if (now - previous < DISPLAY_TELEMETRY_MIN_INTERVAL_MS) return;
  displayTelemetryLastSentAt.set(key, now);

  const send = () => {
    const displayedAt = Date.now();
    void postDisplayTelemetry(
      samples.map((sample) => ({ ...sample, displayedAt })),
    ).catch(() => undefined);
  };

  if (document.visibilityState === "hidden") {
    window.setTimeout(send, 0);
    return;
  }
  window.requestAnimationFrame(() => window.requestAnimationFrame(send));
}

function marketDisplaySamples(
  snapshot: MarketsResponse,
  frontendReceivedAt: number,
): PendingDisplayTelemetrySample[] {
  return snapshot.markets.map((market) => ({
    channel: "markets",
    exchange: market.exchange,
    instrumentId: market.instrumentId,
    price: market.price,
    exchangeTimestamp: market.exchangeTimestamp,
    backendReceivedAt: market.receivedTimestamp,
    backendGeneratedAt: snapshot.generatedAt,
    frontendReceivedAt,
  }));
}

function candleDisplaySample(
  channel: "stable_candles" | "provisional_candles",
  snapshot: CandlesResponse | CandleStreamResponse,
  frontendReceivedAt: number,
): PendingDisplayTelemetrySample | null {
  const latest = snapshot.candles.at(-1);
  if (!latest) return null;
  return {
    channel,
    exchange: snapshot.exchange,
    instrumentId: snapshot.instrumentId,
    timeframe: snapshot.timeframe,
    price: latest.close,
    backendGeneratedAt:
      snapshot.chartLatency?.generatedAt ??
      ("generatedAt" in snapshot ? snapshot.generatedAt : null),
    dataTimestamp: snapshot.chartLatency?.dataTo ?? latest.closeTime,
    frontendReceivedAt,
  };
}

function metricsDisplaySample(
  channel: "metrics" | "stats",
  snapshot: MetricsResponse,
  frontendReceivedAt: number,
): PendingDisplayTelemetrySample {
  return {
    channel,
    exchange: snapshot.exchange,
    instrumentId: snapshot.instrumentId,
    timeframe: snapshot.timeframe,
    price:
      snapshot.latest?.close === null || snapshot.latest?.close === undefined
        ? null
        : String(snapshot.latest.close),
    backendGeneratedAt: snapshot.metricsLatency.generatedAt,
    dataTimestamp: snapshot.metricsLatency.dataTo,
    frontendReceivedAt,
  };
}

function useMarketFeed() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [streamStatus, setStreamStatus] =
    useState<StreamStatus>("connecting");
  const [error, setError] = useState<string | null>(null);
  const reconnectAttempt = useRef(0);

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([
      fetchInstruments(controller.signal),
      fetchMarkets(controller.signal),
      fetchHealth(controller.signal),
    ])
      .then(([instrumentData, marketData, healthData]) => {
        const frontendReceivedAt = Date.now();
        setInstruments(instrumentData.instruments);
        setMarkets(marketData.markets);
        setHealth(healthData);
        setError(null);
        scheduleDisplayTelemetry(
          "markets:initial",
          marketDisplaySamples(marketData, frontendReceivedAt),
        );
      })
      .catch((requestError: Error) => {
        if (requestError.name !== "AbortError") {
          setError("Backend is unreachable. Live values are intentionally hidden.");
        }
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let closed = false;

    const connect = () => {
      if (closed) return;
      setStreamStatus(reconnectAttempt.current ? "reconnecting" : "connecting");
      socket = new WebSocket(marketWebSocketUrl());

      socket.addEventListener("open", () => {
        reconnectAttempt.current = 0;
        setStreamStatus("live");
        setError(null);
      });

      socket.addEventListener("message", (event) => {
        try {
          const frontendReceivedAt = Date.now();
          const snapshot = JSON.parse(event.data) as MarketsResponse;
          setMarkets(snapshot.markets);
          scheduleDisplayTelemetry(
            "markets:stream",
            marketDisplaySamples(snapshot, frontendReceivedAt),
          );
        } catch {
          setError("A malformed market snapshot was ignored.");
        }
      });

      socket.addEventListener("close", () => {
        if (closed) return;
        reconnectAttempt.current += 1;
        setStreamStatus("reconnecting");
        const delay = Math.min(1_000 * 2 ** reconnectAttempt.current, 10_000);
        retryTimer = window.setTimeout(connect, delay);
      });

      socket.addEventListener("error", () => {
        socket?.close();
      });
    };

    connect();
    return () => {
      closed = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      socket?.close();
      setStreamStatus("offline");
    };
  }, []);

  useEffect(() => {
    const loadHealth = () => {
      fetchHealth()
        .then(setHealth)
        .catch(() => setHealth(null));
    };
    const interval = window.setInterval(loadHealth, 5_000);
    return () => window.clearInterval(interval);
  }, []);

  return { instruments, markets, health, streamStatus, error };
}

function Dashboard({ session, onLogout }: DashboardProps) {
  const { instruments, markets, health, streamStatus, error } = useMarketFeed();
  const [activeView, setActiveView] = useState<ActiveView>("dashboard");
  const [exchange, setExchange] = useState<Exchange>("binance");
  const [instrumentId, setInstrumentId] = useState("BTC-USDT");
  const [timeframe, setTimeframe] = useState<Timeframe>("5s");
  const [candleData, setCandleData] = useState<{
    scope: string;
    values: Candle[];
    hasMore: boolean;
    source: HistorySource | null;
    latency: CandlesResponse["chartLatency"] | null;
  }>({ scope: "", values: [], hasMore: false, source: null, latency: null });
  const [provisionalData, setProvisionalData] = useState<{
    scope: string;
    values: Candle[];
  }>({ scope: "", values: [] });
  const [metricsData, setMetricsData] = useState<{
    scope: string;
    value: MetricsResponse | null;
  }>({ scope: "", value: null });
  const [statsData, setStatsData] = useState<{
    scope: string;
    value: MetricsResponse | null;
  }>({ scope: "", value: null });
  const [mlPatternData, setMlPatternData] = useState<{
    scope: string;
    value: MlPatternResponse | null;
  }>({ scope: "", value: null });
  const [candlesLoading, setCandlesLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [mlPatternLoading, setMlPatternLoading] = useState(false);
  const [candleError, setCandleError] = useState<string | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [mlPatternError, setMlPatternError] = useState<string | null>(null);
  const [instrumentMenuOpen, setInstrumentMenuOpen] = useState(false);
  const [userAlerts, setUserAlerts] = useState<UserAlert[]>(safeStoredAlerts);
  const [alertDraft, setAlertDraft] =
    useState<AlertDraft>(DEFAULT_ALERT_DRAFT);
  const [dashboardAlertComposerOpen, setDashboardAlertComposerOpen] =
    useState(false);
  const [alertFormError, setAlertFormError] = useState<string | null>(null);
  const [alertToasts, setAlertToasts] = useState<AlertToast[]>([]);
  const [dismissingToastIds, setDismissingToastIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [toastDragOffsets, setToastDragOffsets] = useState<Record<string, number>>(
    {},
  );
  const [alertSoundReady, setAlertSoundReady] = useState(false);
  const historyLoadingRef = useRef(false);
  const alertAudioRef = useRef<AudioContext | null>(null);
  const previousAlertValuesRef = useRef<Record<string, number | null>>({});
  const toastDragStartRef = useRef<Record<string, number>>({});

  useEffect(() => {
    window.localStorage.setItem(
      USER_ALERTS_STORAGE_KEY,
      JSON.stringify(userAlerts),
    );
  }, [userAlerts]);

  const dismissAlertToast = useCallback((id: string) => {
    setDismissingToastIds((current) => {
      if (current.has(id)) return current;
      const next = new Set(current);
      next.add(id);
      return next;
    });
    window.setTimeout(() => {
      setAlertToasts((current) => current.filter((item) => item.id !== id));
      setDismissingToastIds((current) => {
        if (!current.has(id)) return current;
        const next = new Set(current);
        next.delete(id);
        return next;
      });
      setToastDragOffsets((current) => {
        if (!(id in current)) return current;
        const next = { ...current };
        delete next[id];
        return next;
      });
    }, ALERT_TOAST_EXIT_MS);
  }, []);

  const pushAlertToast = useCallback(
    (toast: Omit<AlertToast, "id" | "createdAt">) => {
      const id = createAlertId("toast");
      setAlertToasts((current) =>
        [{ ...toast, id, createdAt: Date.now() }, ...current].slice(0, 5),
      );
      window.setTimeout(() => dismissAlertToast(id), ALERT_TOAST_TTL_MS);
    },
    [dismissAlertToast],
  );

  const startAlertToastDrag = useCallback(
    (id: string, event: ReactPointerEvent<HTMLElement>) => {
      if (dismissingToastIds.has(id)) return;
      toastDragStartRef.current[id] = event.clientX;
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [dismissingToastIds],
  );

  const moveAlertToastDrag = useCallback(
    (id: string, event: ReactPointerEvent<HTMLElement>) => {
      const startX = toastDragStartRef.current[id];
      if (startX === undefined) return;
      const offset = Math.max(0, event.clientX - startX);
      setToastDragOffsets((current) =>
        current[id] === offset ? current : { ...current, [id]: offset },
      );
    },
    [],
  );

  const clearAlertToastDrag = useCallback((id: string) => {
    delete toastDragStartRef.current[id];
    setToastDragOffsets((current) => {
      if (!(id in current)) return current;
      const next = { ...current };
      delete next[id];
      return next;
    });
  }, []);

  const finishAlertToastDrag = useCallback(
    (id: string, event: ReactPointerEvent<HTMLElement>) => {
      const startX = toastDragStartRef.current[id];
      const offset = startX === undefined ? 0 : Math.max(0, event.clientX - startX);
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
      if (offset > 86) {
        delete toastDragStartRef.current[id];
        dismissAlertToast(id);
        return;
      }
      clearAlertToastDrag(id);
    },
    [clearAlertToastDrag, dismissAlertToast],
  );

  const playAlertSound = useCallback(async () => {
    try {
      const audioWindow = window as typeof window & {
        webkitAudioContext?: typeof AudioContext;
      };
      const AudioContextConstructor =
        window.AudioContext ?? audioWindow.webkitAudioContext;
      if (!AudioContextConstructor) {
        if (typeof Audio === "undefined") return;
        const audio = new Audio(ALERT_BEEP_DATA_URI);
        await audio.play();
        setAlertSoundReady(true);
        return;
      }
      const context =
        alertAudioRef.current ?? new AudioContextConstructor();
      alertAudioRef.current = context;
      if (context.state === "suspended") {
        await context.resume();
      }
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      const now = context.currentTime;
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(880, now);
      oscillator.frequency.exponentialRampToValueAtTime(1320, now + 0.12);
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.18, now + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.24);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start(now);
      oscillator.stop(now + 0.26);
      setAlertSoundReady(true);
    } catch {
      setAlertSoundReady(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    let initialController: AbortController | null = null;
    const scope = `${exchange}:${instrumentId}:${timeframe}`;

    const loadInitial = async () => {
      initialController = new AbortController();
      setCandlesLoading(true);
      try {
        const response = await fetchCandles(
          exchange,
          instrumentId,
          { timeframe, limit: HISTORY_PAGE_SIZE },
          initialController.signal,
        );
        const frontendReceivedAt = Date.now();
        if (!active) return;
        setCandleData({
          scope,
          values: response.candles,
          hasMore: response.hasMore,
          source: response.source,
          latency: response.chartLatency,
        });
        setCandleError(null);
        const sample = candleDisplaySample(
          "stable_candles",
          response,
          frontendReceivedAt,
        );
        if (sample) {
          scheduleDisplayTelemetry(`stable:${scope}:initial`, [sample]);
        }
      } catch (requestError) {
        if (!active || (requestError as Error).name === "AbortError") return;
        setCandleError("Candle history is temporarily unavailable.");
      } finally {
        if (active) setCandlesLoading(false);
      }
    };

    setCandleData({
      scope,
      values: [],
      hasMore: false,
      source: null,
      latency: null,
    });
    setHistoryLoading(false);
    historyLoadingRef.current = false;
    void loadInitial();

    return () => {
      active = false;
      initialController?.abort();
    };
  }, [exchange, instrumentId, timeframe]);

  useEffect(() => {
    const scope = `${exchange}:${instrumentId}:${timeframe}`;
    let closed = false;
    const socket = new WebSocket(
      stableCandleWebSocketUrl(exchange, instrumentId, timeframe, 20),
    );

    socket.addEventListener("message", (event) => {
      if (closed) return;
      try {
        const frontendReceivedAt = Date.now();
        const snapshot = JSON.parse(event.data) as CandlesResponse;
        setCandleData((current) =>
          current.scope === scope
            ? {
                ...current,
                values: mergeCandles(current.values, snapshot.candles),
                source: current.source ?? snapshot.source,
                latency: snapshot.chartLatency,
              }
            : current,
        );
        setCandleError(null);
        const sample = candleDisplaySample(
          "stable_candles",
          snapshot,
          frontendReceivedAt,
        );
        if (sample) {
          scheduleDisplayTelemetry(`stable:${scope}:stream`, [sample]);
        }
      } catch {
        setCandleError("A malformed stable candle snapshot was ignored.");
      }
    });

    return () => {
      closed = true;
      socket.close();
    };
  }, [exchange, instrumentId, timeframe]);

  useEffect(() => {
    const scope = `${exchange}:${instrumentId}:${timeframe}`;
    let closed = false;
    const socket = new WebSocket(
      candleWebSocketUrl(exchange, instrumentId, timeframe),
    );

    setProvisionalData({ scope, values: [] });
    socket.addEventListener("message", (event) => {
      if (closed) return;
      try {
        const frontendReceivedAt = Date.now();
        const snapshot = JSON.parse(event.data) as CandleStreamResponse;
        setProvisionalData({ scope, values: snapshot.candles });
        setCandleError(null);
        const sample = candleDisplaySample(
          "provisional_candles",
          snapshot,
          frontendReceivedAt,
        );
        if (sample) {
          scheduleDisplayTelemetry(`provisional:${scope}:stream`, [sample]);
        }
      } catch {
        setCandleError("A malformed live candle snapshot was ignored.");
      }
    });

    return () => {
      closed = true;
      socket.close();
    };
  }, [exchange, instrumentId, timeframe]);

  useEffect(() => {
    let active = true;
    let controller: AbortController | null = null;
    const scope = `${exchange}:${instrumentId}:${timeframe}`;

    const loadMetrics = async () => {
      controller?.abort();
      controller = new AbortController();
      setMetricsLoading(true);
      try {
        const response = await fetchMetrics(
          exchange,
          instrumentId,
          { timeframe, limit: METRICS_LIMIT },
          controller.signal,
        );
        const frontendReceivedAt = Date.now();
        if (!active) return;
        setMetricsData({ scope, value: response });
        setMetricsError(null);
        scheduleDisplayTelemetry(`metrics:${scope}:rest`, [
          metricsDisplaySample("metrics", response, frontendReceivedAt),
        ]);
      } catch (requestError) {
        if (!active || (requestError as Error).name === "AbortError") return;
        setMetricsError("Metrics are temporarily unavailable.");
      } finally {
        if (active) setMetricsLoading(false);
      }
    };

    setMetricsData({ scope, value: null });
    void loadMetrics();
    const interval = window.setInterval(
      () => void loadMetrics(),
      METRICS_FALLBACK_POLL_MS,
    );

    return () => {
      active = false;
      controller?.abort();
      window.clearInterval(interval);
    };
  }, [exchange, instrumentId, timeframe]);

  useEffect(() => {
    let active = true;
    let controller: AbortController | null = null;
    const scope = `${exchange}:${instrumentId}:24h`;

    const loadStats = async () => {
      controller?.abort();
      controller = new AbortController();
      setStatsLoading(true);
      try {
        const now = Date.now();
        const response = await fetchMetrics(
          exchange,
          instrumentId,
          {
            timeframe: STATS_TIMEFRAME,
            from: now - STATS_WINDOW_MS,
            to: now,
            limit: STATS_LIMIT,
          },
          controller.signal,
        );
        const frontendReceivedAt = Date.now();
        if (!active) return;
        setStatsData({ scope, value: response });
        setStatsError(null);
        scheduleDisplayTelemetry(`stats:${scope}:rest`, [
          metricsDisplaySample("stats", response, frontendReceivedAt),
        ]);
      } catch (requestError) {
        if (!active || (requestError as Error).name === "AbortError") return;
        setStatsError("24h statistics are temporarily unavailable.");
      } finally {
        if (active) setStatsLoading(false);
      }
    };

    setStatsData({ scope, value: null });
    void loadStats();
    const interval = window.setInterval(
      () => void loadStats(),
      STATS_FALLBACK_POLL_MS,
    );

    return () => {
      active = false;
      controller?.abort();
      window.clearInterval(interval);
    };
  }, [exchange, instrumentId]);

  useEffect(() => {
    const scope = `${exchange}:${instrumentId}:${timeframe}`;
    let closed = false;
    const socket = new WebSocket(
      metricsWebSocketUrl(exchange, instrumentId, timeframe, "default"),
    );

    socket.addEventListener("message", (event) => {
      if (closed) return;
      try {
        const frontendReceivedAt = Date.now();
        const snapshot = JSON.parse(event.data) as MetricsResponse;
        setMetricsData({ scope, value: snapshot });
        setMetricsLoading(false);
        setMetricsError(null);
        scheduleDisplayTelemetry(`metrics:${scope}:stream`, [
          metricsDisplaySample("metrics", snapshot, frontendReceivedAt),
        ]);
      } catch {
        setMetricsError("A malformed metrics snapshot was ignored.");
      }
    });

    return () => {
      closed = true;
      socket.close();
    };
  }, [exchange, instrumentId, timeframe]);

  useEffect(() => {
    const scope = `${exchange}:${instrumentId}:24h`;
    let closed = false;
    const socket = new WebSocket(
      metricsWebSocketUrl(exchange, instrumentId, STATS_TIMEFRAME, "24h"),
    );

    socket.addEventListener("message", (event) => {
      if (closed) return;
      try {
        const frontendReceivedAt = Date.now();
        const snapshot = JSON.parse(event.data) as MetricsResponse;
        setStatsData({ scope, value: snapshot });
        setStatsLoading(false);
        setStatsError(null);
        scheduleDisplayTelemetry(`stats:${scope}:stream`, [
          metricsDisplaySample("stats", snapshot, frontendReceivedAt),
        ]);
      } catch {
        setStatsError("A malformed 24h statistics snapshot was ignored.");
      }
    });

    return () => {
      closed = true;
      socket.close();
    };
  }, [exchange, instrumentId]);

  const candleScope = `${exchange}:${instrumentId}:${timeframe}`;
  const statsScope = `${exchange}:${instrumentId}:24h`;
  const candles =
    candleData.scope === candleScope ? candleData.values : [];
  const provisionalCandles =
    provisionalData.scope === candleScope ? provisionalData.values : [];
  const chartCandles = useMemo(
    () => mergeCandles(candles, provisionalCandles),
    [candles, provisionalCandles],
  );
  const hasMoreHistory =
    candleData.scope === candleScope && candleData.hasMore;
  const metrics =
    metricsData.scope === candleScope ? metricsData.value : null;
  const statsMetrics =
    statsData.scope === statsScope ? statsData.value : null;
  const latestClosedCandleTime = candles.at(-1)?.closeTime ?? null;
  const mlPatternScope = `${exchange}:${instrumentId}:${timeframe}:${latestClosedCandleTime ?? "none"}`;
  const mlPattern =
    mlPatternData.scope === mlPatternScope ? mlPatternData.value : null;

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const scope = mlPatternScope;

    const loadPattern = async () => {
      setMlPatternLoading(true);
      try {
        const response = await fetchMlPattern(
          exchange,
          instrumentId,
          timeframe,
          controller.signal,
        );
        if (!active) return;
        setMlPatternData({ scope, value: response });
        setMlPatternError(null);
      } catch (requestError) {
        if (!active || (requestError as Error).name === "AbortError") return;
        setMlPatternError("ML pattern recognition is temporarily unavailable.");
        setMlPatternData({ scope, value: null });
      } finally {
        if (active) setMlPatternLoading(false);
      }
    };

    void loadPattern();
    return () => {
      active = false;
      controller.abort();
    };
  }, [exchange, instrumentId, timeframe, latestClosedCandleTime, mlPatternScope]);

  const latestMetrics = statsMetrics?.latest ?? null;
  const statsSummary = statsMetrics?.summary ?? null;
  const metricEvents = metrics?.events ?? [];
  const correlations = statsMetrics?.crossPairCorrelations ?? [];
  const topCorrelations = correlations.slice(0, 4);

  const loadEarlier = useCallback(async () => {
    if (
      historyLoadingRef.current ||
      !hasMoreHistory ||
      candles.length === 0
    ) {
      return;
    }

    historyLoadingRef.current = true;
    setHistoryLoading(true);
    const before = candles[0].openTime;
    try {
      const response = await fetchCandles(exchange, instrumentId, {
        timeframe,
        limit: HISTORY_PAGE_SIZE,
        to: before,
      });
      setCandleData((current) =>
        current.scope === candleScope
          ? {
              ...current,
              values: mergeCandles(response.candles, current.values),
              hasMore: response.hasMore,
              source: response.source,
            }
          : current,
      );
      setCandleError(null);
    } catch {
      setCandleError("Older candle history could not be loaded.");
    } finally {
      historyLoadingRef.current = false;
      setHistoryLoading(false);
    }
  }, [
    candleScope,
    candles,
    exchange,
    hasMoreHistory,
    instrumentId,
    timeframe,
  ]);

  const availableInstruments = useMemo(
    () => instruments.filter((item) => item.symbols[exchange]),
    [exchange, instruments],
  );
  const selectedInstrument = availableInstruments.find(
    (item) => item.instrumentId === instrumentId,
  );
  const instrument =
    selectedInstrument ?? availableInstruments[0] ?? instruments[0];

  useEffect(() => {
    if (availableInstruments.length > 0 && !selectedInstrument) {
      setInstrumentId(availableInstruments[0].instrumentId);
    }
  }, [availableInstruments, selectedInstrument]);

  const marketMap = useMemo(
    () => new Map(markets.map((market) => [marketKey(market), market])),
    [markets],
  );
  const selectedMarket =
    marketMap.get(`${exchange}:${instrumentId}`) ?? null;
  const sourceMarkets = EXCHANGES.map(
    (source) => marketMap.get(`${source}:${instrumentId}`) ?? null,
  );
  const displayCandles = useMemo(
    () => toDisplayCandles(chartCandles),
    [chartCandles],
  );

  const gapCount = candles.filter(
    (candle) => candle.status === "incomplete",
  ).length;
  const latestClose = displayCandles.at(-1)?.close ?? null;
  const livePrice = coerceNumber(selectedMarket?.price ?? null) ?? latestClose;
  const firstClose = displayCandles[0]?.close ?? null;
  const viewportChange =
    firstClose && livePrice ? ((livePrice - firstClose) / firstClose) * 100 : null;
  const high = statsSummary?.high ?? null;
  const low = statsSummary?.low ?? null;
  const volume = statsSummary?.baseVolume ?? null;
  const trades = statsSummary?.tradeCount ?? null;
  const binancePrice = coerceNumber(sourceMarkets[0]?.price ?? null);
  const bybitPrice = coerceNumber(sourceMarkets[1]?.price ?? null);
  const spreadBps =
    binancePrice && bybitPrice
      ? ((binancePrice - bybitPrice) / ((binancePrice + bybitPrice) / 2)) *
        10_000
      : null;
  const selectedCollector = health?.collectors[exchange];
  const isLive =
    streamStatus === "live" &&
    selectedMarket?.status === "live" &&
    selectedCollector?.connected !== false;
  const alertMetrics = metrics?.latest ?? latestMetrics;
  const currentScopeAlerts = userAlerts.filter(
    (alert) =>
      alert.exchange === exchange &&
      alert.instrumentId === instrumentId &&
      alert.timeframe === timeframe,
  );
  const activeCurrentScopeAlerts = currentScopeAlerts.filter(
    (alert) => alert.enabled,
  );
  const chartAlertLines: ChartAlertLine[] = currentScopeAlerts
    .filter(
      (alert) =>
        alert.enabled &&
        alert.metric === "price" &&
        Number.isFinite(alert.threshold),
    )
    .map((alert) => ({
      id: alert.id,
      label: `${conditionLabel(alert.condition)} ${formatAlertValue(
        alert.metric,
        alert.threshold,
      )}`,
      price: alert.threshold,
      tone:
        alert.condition === "below" || alert.condition === "crosses_below"
          ? "below"
          : "above",
    }));
  const dashboardAlertPresets = ALERT_PRESETS.slice(0, 4);
  const enabledAlertCount = userAlerts.filter((alert) => alert.enabled).length;

  const createAlert = useCallback(
    (draft: AlertDraft) => {
      const threshold = Number(draft.threshold);
      const cooldownSeconds = Number(draft.cooldownSeconds);
      if (!Number.isFinite(threshold)) {
        setAlertFormError("Enter a numeric threshold.");
        return;
      }
      if (!Number.isFinite(cooldownSeconds) || cooldownSeconds < 5) {
        setAlertFormError("Cooldown must be at least 5 seconds.");
        return;
      }

      const definition = alertMetricDefinition(draft.metric);
      const label =
        draft.label.trim() ||
        `${definition.shortLabel} ${conditionLabel(draft.condition)} ${formatAlertValue(
          draft.metric,
          threshold,
        )}`;
      const nextAlert: UserAlert = {
        id: createAlertId(),
        label,
        exchange,
        instrumentId,
        instrumentBase: instrument?.base ?? instrumentId,
        timeframe,
        metric: draft.metric,
        condition: draft.condition,
        threshold,
        cooldownMs: cooldownSeconds * 1000,
        once: draft.once,
        enabled: true,
        createdAt: Date.now(),
        lastTriggeredAt: null,
      };
      setUserAlerts((current) => [nextAlert, ...current]);
      setAlertDraft(DEFAULT_ALERT_DRAFT);
      setAlertFormError(null);
      setDashboardAlertComposerOpen(false);
      pushAlertToast({
        title: "Alert armed",
        body: `${nextAlert.label} on ${exchangeLabel(exchange)} ${
          nextAlert.instrumentBase
        }`,
        severity: "medium",
      });
    },
    [exchange, instrument?.base, instrumentId, pushAlertToast, timeframe],
  );

  const createPresetAlert = useCallback(
    (preset: AlertPreset) => {
      const threshold =
        typeof preset.threshold === "function"
          ? preset.threshold(livePrice)
          : preset.threshold;
      if (threshold === null || !Number.isFinite(threshold)) {
        setAlertFormError("This preset needs a live price first.");
        return;
      }
      createAlert({
        label: preset.label,
        metric: preset.metric,
        condition: preset.condition,
        threshold: String(threshold),
        cooldownSeconds: String(preset.cooldownSeconds),
        once: Boolean(preset.once),
      });
    },
    [createAlert, livePrice],
  );

  const toggleAlert = useCallback((id: string) => {
    setUserAlerts((current) =>
      current.map((alert) =>
        alert.id === id ? { ...alert, enabled: !alert.enabled } : alert,
      ),
    );
  }, []);

  const removeAlert = useCallback((id: string) => {
    setUserAlerts((current) => current.filter((alert) => alert.id !== id));
    delete previousAlertValuesRef.current[id];
  }, []);

  useEffect(() => {
    const now = Date.now();
    const nextPrevious = { ...previousAlertValuesRef.current };
    const triggered: Array<{
      alert: UserAlert;
      value: number;
      severity: AlertSeverity;
    }> = [];

    for (const alert of userAlerts) {
      if (
        !alert.enabled ||
        alert.exchange !== exchange ||
        alert.instrumentId !== instrumentId ||
        alert.timeframe !== timeframe
      ) {
        continue;
      }

      const currentValue = alertMetricValue(alert.metric, livePrice, alertMetrics);
      if (currentValue === null) continue;
      const previousValue = nextPrevious[alert.id] ?? null;
      nextPrevious[alert.id] = currentValue;

      const cooledDown =
        alert.lastTriggeredAt === null ||
        now - alert.lastTriggeredAt >= alert.cooldownMs;
      if (
        cooledDown &&
        alertConditionMet(
          alert.condition,
          currentValue,
          previousValue,
          alert.threshold,
        )
      ) {
        triggered.push({
          alert,
          value: currentValue,
          severity: alertSeverity(alert, currentValue),
        });
      }
    }

    previousAlertValuesRef.current = nextPrevious;
    if (triggered.length === 0) return;

    const triggeredIds = new Set(triggered.map(({ alert }) => alert.id));
    setUserAlerts((current) =>
      current.map((alert) =>
        triggeredIds.has(alert.id)
          ? {
              ...alert,
              enabled: alert.once ? false : alert.enabled,
              lastTriggeredAt: now,
            }
          : alert,
      ),
    );

    for (const { alert, value, severity } of triggered) {
      pushAlertToast({
        title: alert.label,
        body: `${exchangeLabel(alert.exchange)} ${alert.instrumentBase} ${alertMetricDefinition(
          alert.metric,
        ).shortLabel}: ${formatAlertValue(alert.metric, value)} (${conditionLabel(
          alert.condition,
        ).toLowerCase()} ${formatAlertValue(alert.metric, alert.threshold)})`,
        severity,
      });
    }
    void playAlertSound();
  }, [
    alertMetrics,
    exchange,
    instrumentId,
    livePrice,
    playAlertSound,
    pushAlertToast,
    timeframe,
    userAlerts,
  ]);

  return (
    <div className="app-shell">
      <aside className="side-rail">
        <div className="brand-mark" aria-label="Tickframe">
          <TickframeLogo />
          <span className="brand-word">TICKFRAME</span>
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          <button
            className={`nav-item ${activeView === "dashboard" ? "active" : ""}`}
            type="button"
            onClick={() => setActiveView("dashboard")}
          >
            <span className="nav-index">01</span>
            <span>Dashboard</span>
          </button>
          <button
            className={`nav-item ${activeView === "alerts" ? "active" : ""}`}
            type="button"
            onClick={() => setActiveView("alerts")}
          >
            <span className="nav-index">02</span>
            <span>Alerts</span>
          </button>
          <button className="nav-item" type="button" disabled>
            <span className="nav-index">03</span>
            <span>History</span>
            <small>soon</small>
          </button>
        </nav>

      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <span className="product-kicker">TICKFRAME ANALYTICS</span>
            <p>Crypto pattern analytics - public market data</p>
          </div>
          <div className="topbar-search" aria-hidden="true">
            Search assets
          </div>
          <div className="topbar-meta">
            <span className="user-chip">
              {session.user.displayName}
              <small>{session.user.email}</small>
            </span>
            <span>CFG {health?.configVersion ?? "--"}</span>
            <span className={`stream-pill ${streamStatus}`}>
              <span />
              {streamStatus}
            </span>
            <button className="logout-button" type="button" onClick={onLogout}>
              Log out
            </button>
          </div>
        </header>

        {(error || candleError || metricsError || statsError || mlPatternError) && (
          <div className="system-notice" role="status">
            <span>DATA NOTICE</span>
            <p>
              {error ??
                candleError ??
                statsError ??
                metricsError ??
                mlPatternError}
            </p>
          </div>
        )}

        <section className="source-rail" aria-label="Market data sources">
          <div className="source-instrument">
            <button
              className="source-instrument-trigger"
              type="button"
              aria-expanded={instrumentMenuOpen}
              onClick={() => setInstrumentMenuOpen((open) => !open)}
            >
              <CoinLogo base={instrument?.base} />
              <span>
                <small>{instrument?.name ?? "Loading instruments"}</small>
                <strong>
                  {instrument?.base ?? "--"}
                  <i>/</i>
                  {instrument?.quote ?? "USDT"}
                </strong>
              </span>
              <span className="chevron">v</span>
            </button>

            {instrumentMenuOpen && (
              <div className="instrument-menu source-instrument-menu">
                {availableInstruments.map((item) => {
                  const itemMarket = marketMap.get(
                    `${exchange}:${item.instrumentId}`,
                  );
                  return (
                    <button
                      key={item.instrumentId}
                      type="button"
                      className={
                        item.instrumentId === instrumentId ? "selected" : ""
                      }
                      onClick={() => {
                        setInstrumentId(item.instrumentId);
                        setInstrumentMenuOpen(false);
                      }}
                    >
                      <span className="instrument-token">
                        <CoinLogo base={item.base} className="coin-logo-sm" />
                        <b>{item.base}</b>
                      </span>
                      <small>{item.name}</small>
                      <strong>{formatPrice(coerceNumber(itemMarket?.price ?? null))}</strong>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="source-last-trade">
            <span className="eyebrow">LAST TRADE - {exchange.toUpperCase()}</span>
            <strong>{formatPrice(livePrice)}</strong>
            <span className={viewportChange !== null && viewportChange < 0 ? "negative" : "positive"}>
              {formatPercent(viewportChange)} viewport
            </span>
          </div>

          {sourceMarkets.map((market, index) => {
            const source = EXCHANGES[index];
            const collector = health?.collectors[source];
            const subscriptionError = rejectedTopicReason(collector, market);
            return (
              <button
                className={`source-node ${exchange === source ? "active" : ""}`}
                type="button"
                key={source}
                onClick={() => setExchange(source)}
              >
                <span className={`source-line ${market?.status ?? "waiting"}`} />
                <span>
                  <small>{exchangeLabel(source)}</small>
                  <strong>{formatPrice(coerceNumber(market?.price ?? null))}</strong>
                </span>
                <span className="source-stats">
                  <small>{subscriptionError ? "unsupported" : market?.status ?? "waiting"}</small>
                  <b>
                    {subscriptionError
                      ? "rejected by exchange"
                      : formatAge(collector?.messageAgeMs ?? market?.ageMs)}
                  </b>
                  <em>{formatEndpointHost(collector?.endpoint)}</em>
                </span>
              </button>
            );
          })}
          <div className="venue-spread">
            <small>VENUE DELTA</small>
            <strong>{spreadBps === null ? "--" : `${spreadBps.toFixed(2)} bps`}</strong>
          </div>
        </section>

        {activeView === "dashboard" ? (
        <section className="terminal-grid">
          <div className="market-stack">
            <article className="chart-panel panel">
              <div className="panel-head">
                <div className="chart-title">
                  <CoinLogo base={instrument?.base} className="coin-logo-sm" />
                  <span className="eyebrow">PRICE / VOLUME</span>
                  <strong>{instrumentId} - SPOT</strong>
                </div>
                <div className="timeframe-tabs" aria-label="Timeframe">
                  {TIMEFRAMES.map((item) => (
                    <button
                      key={item}
                      type="button"
                      className={timeframe === item ? "active" : ""}
                      onClick={() => setTimeframe(item)}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>
              <MarketChart
                candles={displayCandles}
                scopeKey={candleScope}
                loading={candlesLoading}
                historyLoading={historyLoading}
                hasMore={hasMoreHistory}
                onLoadEarlier={loadEarlier}
                alertLines={chartAlertLines}
              />
              <div className="chart-foot">
                <span>
                  <i className="legend-box up" /> Up
                </span>
                <span>
                  <i className="legend-box down" /> Down
                </span>
                <span>{displayCandles.length} bars</span>
                <span>{gapCount} gaps</span>
                <span>{candleData.source ?? "loading"} history</span>
                {provisionalCandles.length > 0 && <span>live overlay</span>}
                <span>chart lag {formatAge(candleData.latency?.effectiveLagMs)}</span>
                <span>late window {formatAge(health?.chart.allowedLatenessMs)}</span>
                <span>updated {formatClock(selectedMarket?.receivedTimestamp)}</span>
              </div>
            </article>

            <article className="panel metrics-panel">
              <div className="panel-head compact">
                <div className="panel-title-with-logo">
                  <CoinLogo base={instrument?.base} className="coin-logo-xs" />
                  <div>
                    <span className="eyebrow">METRICS ENGINE</span>
                    <strong>{statsMetrics?.version ?? "calculating"}</strong>
                  </div>
                </div>
                <span className={`quality-badge ${statsLoading ? "warn" : "good"}`}>
                  {statsLoading ? "CALC" : statsMetrics?.source.toUpperCase() ?? "WAIT"}
                </span>
              </div>
              <div className="metrics-dashboard">
                <div className="metric-window-strip">
                  <span>24h statistics</span>
                  <strong>{STATS_TIMEFRAME} candles</strong>
                </div>

                <div className="metric-hero-grid">
                  <div className="metric-card metric-card-wide">
                    <span>VWAP</span>
                    <strong>{formatPrice(latestMetrics?.vwap ?? null)}</strong>
                    <small
                      className={metricTone(latestMetrics?.vwapDeviationPct)}
                    >
                      {formatMetricPercent(
                        latestMetrics?.vwapDeviationPct ?? null,
                        true,
                      )}{" "}
                      deviation
                    </small>
                  </div>
                  <div className="metric-card">
                    <span>RSI</span>
                    <strong>
                      {latestMetrics?.rsi === null ||
                      latestMetrics?.rsi === undefined
                        ? "--"
                        : latestMetrics.rsi.toFixed(1)}
                    </strong>
                    <small>momentum state</small>
                  </div>
                  <div className="metric-card">
                    <span>Short momentum</span>
                    <strong className={metricTone(latestMetrics?.shortMomentumPct)}>
                      {formatMetricPercent(
                        latestMetrics?.shortMomentumPct ?? null,
                        true,
                      )}
                    </strong>
                    <small>{statsMetrics?.windows.momentum ?? "--"} bar window</small>
                  </div>
                  <div className="metric-card">
                    <span>Volume spike</span>
                    <strong>{formatRatio(latestMetrics?.volumeSpikeRatio ?? null)}</strong>
                    <small>{metricEvents.length} live events</small>
                  </div>
                </div>

                <section className="metric-section">
                  <header>
                    <span>Volatility estimators</span>
                  </header>
                  <div className="metric-row-grid">
                    <div>
                      <span>Realized</span>
                      <strong>
                        {formatMetricPercent(
                          latestMetrics?.realizedVolatilityPct ?? null,
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>Parkinson</span>
                      <strong>
                        {formatMetricPercent(
                          latestMetrics?.parkinsonVolatilityPct ?? null,
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>Garman-Klass</span>
                      <strong>
                        {formatMetricPercent(
                          latestMetrics?.garmanKlassVolatilityPct ?? null,
                        )}
                      </strong>
                    </div>
                  </div>
                </section>

                <section className="metric-section">
                  <header>
                    <span>Momentum & mean reversion</span>
                  </header>
                  <div className="metric-row-list">
                    <div>
                      <span>Long momentum</span>
                      <strong className={metricTone(latestMetrics?.momentumPct)}>
                        {formatMetricPercent(
                          latestMetrics?.momentumPct ?? null,
                          true,
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>Z-score</span>
                      <strong
                        className={metricTone(
                          latestMetrics?.meanReversionZScore,
                        )}
                      >
                        {formatSignedNumber(
                          latestMetrics?.meanReversionZScore ?? null,
                          2,
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>Distance to mean</span>
                      <strong
                        className={metricTone(latestMetrics?.distanceToMeanPct)}
                      >
                        {formatMetricPercent(
                          latestMetrics?.distanceToMeanPct ?? null,
                          true,
                        )}
                      </strong>
                    </div>
                  </div>
                </section>

                <section className="metric-section">
                  <header>
                    <span>Anomalies & 24h market</span>
                  </header>
                  <div className="metric-row-list compact">
                    <div>
                      <span>Price / volume divergence</span>
                      <strong
                        className={metricTone(
                          latestMetrics?.priceVolumeDivergencePct,
                        )}
                      >
                        {formatMetricPercent(
                          latestMetrics?.priceVolumeDivergencePct ?? null,
                          true,
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>High / low</span>
                      <strong>{formatPrice(high)} / {formatPrice(low)}</strong>
                    </div>
                    <div>
                      <span>Volume / trades</span>
                      <strong>
                        {formatCompact(volume)} {instrument?.base} /{" "}
                        {formatCompact(trades, 1)}
                      </strong>
                    </div>
                  </div>
                </section>
              </div>

              <div className="correlation-list" aria-label="Cross-pair correlations">
                {topCorrelations.length > 0 ? (
                  topCorrelations.map((item) => (
                    <div className="correlation-card" key={item.instrumentId}>
                      <span className="correlation-asset">
                        <CoinLogo base={item.base} className="coin-logo-xs" />
                        {item.base}
                      </span>
                      <strong>{formatCorrelation(item.correlation)}</strong>
                      <small>{item.sampleSize} returns</small>
                    </div>
                  ))
                ) : (
                  <div className="correlation-empty">
                    Correlations need overlapping return history.
                  </div>
                )}
              </div>
            </article>
          </div>

          <aside className="events-column">
            <article className="panel ml-pattern-panel">
              <div className="panel-head compact">
                <div className="panel-title-with-logo">
                  <CoinLogo base={instrument?.base} className="coin-logo-xs" />
                  <div>
                    <span className="eyebrow">ML PATTERN</span>
                    <strong>{mlPattern?.modelVersion ?? "pattern-baseline-v0"}</strong>
                  </div>
                </div>
                <span
                  className={`quality-badge ${
                    mlPatternLoading
                      ? "warn"
                      : mlPattern?.status === "pattern_detected"
                        ? "good"
                        : "neutral"
                  }`}
                >
                  {mlPatternLoading
                    ? "CALC"
                    : timeframe === "1m"
                      ? "ML ON"
                      : "LOCKED"}
                </span>
              </div>
              <div className="ml-pattern-body">
                <div className="ml-pattern-result">
                  <span>
                    {mlPattern?.status === "pattern_detected"
                      ? "Detected pattern"
                      : "Current state"}
                  </span>
                  <strong>
                    {mlPattern?.prediction &&
                    mlPattern.status === "pattern_detected"
                      ? patternLabel(mlPattern.prediction.label)
                      : mlPattern?.status === "unsupported_timeframe"
                        ? "Switch to 1m"
                        : mlPattern?.status === "insufficient_data"
                          ? "Collecting candles"
                          : "No reliable pattern"}
                  </strong>
                  <small>
                    {mlPattern?.message ??
                      "Waiting for the ML detector response."}
                  </small>
                </div>

                <div className="ml-pattern-stats">
                  <div>
                    <span>Confidence</span>
                    <strong>
                      {mlPattern?.prediction
                        ? formatConfidence(mlPattern.prediction.confidence)
                        : "--"}
                    </strong>
                  </div>
                  <div>
                    <span>Window</span>
                    <strong>{mlPattern?.windowSize ?? 96} candles</strong>
                  </div>
                  <div>
                    <span>Source</span>
                    <strong>{mlPattern?.source ?? "--"}</strong>
                  </div>
                </div>

                {mlPattern?.alternatives && mlPattern.alternatives.length > 0 && (
                  <div className="ml-alternatives">
                    {mlPattern.alternatives.slice(0, 3).map((item) => (
                      <span key={item.label}>
                        {patternLabel(item.label)}
                        <b>{formatConfidence(item.confidence)}</b>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </article>

            <article className="panel dashboard-alert-panel">
              <div className="panel-head compact">
                <div className="panel-title-with-logo">
                  <CoinLogo base={instrument?.base} className="coin-logo-xs" />
                  <div>
                    <span className="eyebrow">ALERTS</span>
                    <strong>
                      {activeCurrentScopeAlerts.length
                        ? `${activeCurrentScopeAlerts.length} watching`
                        : "No active alerts"}
                    </strong>
                  </div>
                </div>
                <button
                  className="alert-add-button"
                  type="button"
                  onClick={() => {
                    if (dashboardAlertComposerOpen) {
                      setDashboardAlertComposerOpen(false);
                      return;
                    }
                    setAlertFormError(null);
                    setAlertDraft({
                      label: "Price above level",
                      metric: "price",
                      condition: "crosses_above",
                      threshold:
                        livePrice === null
                          ? ""
                          : livePrice.toFixed(livePrice >= 1 ? 2 : 6),
                      cooldownSeconds: "120",
                      once: false,
                    });
                    setDashboardAlertComposerOpen(true);
                  }}
                >
                  {dashboardAlertComposerOpen ? "Close" : "Price level"}
                </button>
              </div>

              {currentScopeAlerts.length > 0 ? (
                <div className="dashboard-alert-list">
                  {currentScopeAlerts.slice(0, 4).map((alert) => (
                    <article
                      className={`dashboard-alert-row ${
                        alert.enabled ? "enabled" : "disabled"
                      }`}
                      key={alert.id}
                    >
                      <div>
                        <strong>{alert.label}</strong>
                        <span>
                          {alertMetricDefinition(alert.metric).shortLabel}{" "}
                          {conditionLabel(alert.condition)}{" "}
                          {formatAlertValue(alert.metric, alert.threshold)}
                        </span>
                      </div>
                      <button type="button" onClick={() => toggleAlert(alert.id)}>
                        {alert.enabled ? "Pause" : "Resume"}
                      </button>
                      <button type="button" onClick={() => removeAlert(alert.id)}>
                        Remove
                      </button>
                    </article>
                  ))}
                  {currentScopeAlerts.length > 4 && (
                    <button
                      className="dashboard-alert-more"
                      type="button"
                      onClick={() => setActiveView("alerts")}
                    >
                      View {currentScopeAlerts.length - 4} more
                    </button>
                  )}
                </div>
              ) : null}

              <div className="dashboard-alert-templates">
                <span>Quick templates</span>
                <div className="dashboard-alert-presets">
                  {dashboardAlertPresets.map((preset) => (
                    <button
                      key={preset.label}
                      type="button"
                      onClick={() => createPresetAlert(preset)}
                    >
                      <strong>{preset.label}</strong>
                      <span>{preset.description}</span>
                    </button>
                  ))}
                </div>
              </div>

              {dashboardAlertComposerOpen && (
                <form
                  className="dashboard-alert-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    createAlert({
                      ...alertDraft,
                      label:
                        alertDraft.condition === "crosses_below"
                          ? "Price below level"
                          : "Price above level",
                      metric: "price",
                      cooldownSeconds: "120",
                      once: false,
                    });
                  }}
                >
                  <div className="dashboard-level-toggle">
                    <button
                      className={
                        alertDraft.condition === "crosses_above" ? "active" : ""
                      }
                      type="button"
                      onClick={() =>
                        setAlertDraft((draft) => ({
                          ...draft,
                          label: "Price above level",
                          condition: "crosses_above",
                        }))
                      }
                    >
                      Above
                    </button>
                    <button
                      className={
                        alertDraft.condition === "crosses_below" ? "active" : ""
                      }
                      type="button"
                      onClick={() =>
                        setAlertDraft((draft) => ({
                          ...draft,
                          label: "Price below level",
                          condition: "crosses_below",
                        }))
                      }
                    >
                      Below
                    </button>
                  </div>
                  <label>
                    <span>Price level</span>
                    <input
                      inputMode="decimal"
                      value={alertDraft.threshold}
                      onChange={(event) =>
                        setAlertDraft((draft) => ({
                          ...draft,
                          threshold: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <button type="submit">Save level alert</button>
                </form>
              )}
              {alertFormError && (
                <p className="dashboard-alert-error">{alertFormError}</p>
              )}
            </article>
            <article className="panel signal-panel">
              <div className="panel-head compact">
                <div className="panel-title-with-logo">
                  <CoinLogo base={instrument?.base} className="coin-logo-xs" />
                  <div>
                    <span className="eyebrow">METRIC EVENTS</span>
                    <strong>Signals without trade advice</strong>
                  </div>
                </div>
                <span className={`quality-badge ${metricEvents.length ? "good" : "neutral"}`}>
                  {metricEvents.length ? `${metricEvents.length} LIVE` : "QUIET"}
                </span>
              </div>
              {metricEvents.length > 0 ? (
                <div className="signal-list">
                  {metricEvents.map((event) => (
                    <article
                      className={`signal-card ${event.severity}`}
                      key={`${event.type}:${event.openTime}:${event.metric}`}
                    >
                      <div>
                        <strong>{eventLabel(event)}</strong>
                        <span>{formatClock(event.openTime)}</span>
                      </div>
                      <p>{event.description}</p>
                      <footer>
                        <span>{event.metric}</span>
                        <b>{event.value === null ? "--" : event.value.toFixed(2)}</b>
                        <span>{formatConfidence(event.confidence)}</span>
                      </footer>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="signal-empty">
                  <span className="signal-crosshair" />
                  <strong>No metric events</strong>
                  <p>
                    Tickframe is calculating deterministic metrics, but the
                    current window has not crossed any event threshold.
                  </p>
                </div>
              )}
            </article>
          </aside>
        </section>
        ) : (
        <section className="alerts-workspace" aria-label="User alerts">
          <div className="alerts-main">
            <article className="panel alert-builder-panel">
              <div className="panel-head compact">
                <div className="panel-title-with-logo">
                  <CoinLogo base={instrument?.base} className="coin-logo-xs" />
                  <div>
                    <span className="eyebrow">USER ALERTS</span>
                    <strong>{exchangeLabel(exchange)} {instrumentId}</strong>
                  </div>
                </div>
                <span className={`quality-badge ${isLive ? "good" : "warn"}`}>
                  {isLive ? "ARMED" : "WAITING"}
                </span>
              </div>

              <div className="alert-reading-grid">
                <div>
                  <span>Last price</span>
                  <strong>{formatPrice(livePrice)}</strong>
                </div>
                <div>
                  <span>RSI</span>
                  <strong>
                    {alertMetrics?.rsi === null || alertMetrics?.rsi === undefined
                      ? "--"
                      : alertMetrics.rsi.toFixed(1)}
                  </strong>
                </div>
                <div>
                  <span>Volume spike</span>
                  <strong>{formatRatio(alertMetrics?.volumeSpikeRatio ?? null)}</strong>
                </div>
                <div>
                  <span>Events</span>
                  <strong>{metricEvents.length}</strong>
                </div>
              </div>

              <form
                className="alert-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  createAlert(alertDraft);
                }}
              >
                <label className="alert-field alert-field-wide">
                  <span>Alert name</span>
                  <input
                    value={alertDraft.label}
                    onChange={(event) =>
                      setAlertDraft((draft) => ({
                        ...draft,
                        label: event.target.value,
                      }))
                    }
                    placeholder="Resistance break"
                  />
                </label>

                <div className="alert-form-grid">
                  <label className="alert-field">
                    <span>Metric</span>
                    <select
                      value={alertDraft.metric}
                      onChange={(event) =>
                        setAlertDraft((draft) => ({
                          ...draft,
                          metric: event.target.value as AlertMetricId,
                        }))
                      }
                    >
                      {ALERT_METRICS.map((metric) => (
                        <option key={metric.id} value={metric.id}>
                          {metric.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="alert-field">
                    <span>Condition</span>
                    <select
                      value={alertDraft.condition}
                      onChange={(event) =>
                        setAlertDraft((draft) => ({
                          ...draft,
                          condition: event.target.value as AlertCondition,
                        }))
                      }
                    >
                      {ALERT_CONDITIONS.map((condition) => (
                        <option key={condition.id} value={condition.id}>
                          {condition.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="alert-field">
                    <span>Threshold</span>
                    <input
                      inputMode="decimal"
                      value={alertDraft.threshold}
                      onChange={(event) =>
                        setAlertDraft((draft) => ({
                          ...draft,
                          threshold: event.target.value,
                        }))
                      }
                      placeholder="0.00"
                    />
                  </label>

                  <label className="alert-field">
                    <span>Cooldown, sec</span>
                    <input
                      inputMode="numeric"
                      value={alertDraft.cooldownSeconds}
                      onChange={(event) =>
                        setAlertDraft((draft) => ({
                          ...draft,
                          cooldownSeconds: event.target.value,
                        }))
                      }
                    />
                  </label>
                </div>

                <label className="alert-checkbox">
                  <input
                    type="checkbox"
                    checked={alertDraft.once}
                    onChange={(event) =>
                      setAlertDraft((draft) => ({
                        ...draft,
                        once: event.target.checked,
                      }))
                    }
                  />
                  <span>Disable after first trigger</span>
                </label>

                {alertFormError && (
                  <div className="alert-form-error" role="alert">
                    {alertFormError}
                  </div>
                )}

                <div className="alert-actions">
                  <button type="submit">Save alert</button>
                  <button
                    type="button"
                    className={alertSoundReady ? "sound-ready" : ""}
                    onClick={() => void playAlertSound()}
                  >
                    {alertSoundReady ? "Sound ready" : "Test sound"}
                  </button>
                </div>
              </form>
            </article>

            <article className="panel alert-presets-panel">
              <div className="panel-head compact">
                <div>
                  <span className="eyebrow">METRIC PRESETS</span>
                  <strong>Common market alerts</strong>
                </div>
              </div>
              <div className="alert-preset-grid">
                {ALERT_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => createPresetAlert(preset)}
                  >
                    <strong>{preset.label}</strong>
                    <span>{preset.description}</span>
                    <b>
                      {alertMetricDefinition(preset.metric).shortLabel}{" "}
                      {conditionLabel(preset.condition).toLowerCase()}
                    </b>
                  </button>
                ))}
              </div>
            </article>
          </div>

          <aside className="alerts-side">
            <article className="panel alert-rules-panel">
              <div className="panel-head compact">
                <div>
                  <span className="eyebrow">ACTIVE RULES</span>
                  <strong>{currentScopeAlerts.length} for current scope</strong>
                </div>
                <span className={`quality-badge ${enabledAlertCount ? "good" : "neutral"}`}>
                  {enabledAlertCount ? `${enabledAlertCount} ON` : "EMPTY"}
                </span>
              </div>

              {userAlerts.length > 0 ? (
                <div className="alert-rule-list">
                  {userAlerts.map((alert) => (
                    <article
                      className={`alert-rule-card ${alert.enabled ? "enabled" : ""}`}
                      key={alert.id}
                    >
                      <div>
                        <strong>{alert.label}</strong>
                        <span>
                          {exchangeLabel(alert.exchange)} {alert.instrumentBase}{" "}
                          {alert.timeframe}
                        </span>
                      </div>
                      <p>
                        {alertMetricDefinition(alert.metric).shortLabel}{" "}
                        {conditionLabel(alert.condition).toLowerCase()}{" "}
                        {formatAlertValue(alert.metric, alert.threshold)}
                      </p>
                      <footer>
                        <span>
                          Last {alert.lastTriggeredAt ? formatClock(alert.lastTriggeredAt) : "--"}
                        </span>
                        <button type="button" onClick={() => toggleAlert(alert.id)}>
                          {alert.enabled ? "On" : "Off"}
                        </button>
                        <button type="button" onClick={() => removeAlert(alert.id)}>
                          Remove
                        </button>
                      </footer>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="signal-empty">
                  <span className="signal-crosshair" />
                  <strong>No user alerts</strong>
                  <p>
                    Save a price level or metric threshold to monitor this
                    market while you work.
                  </p>
                </div>
              )}
            </article>

            <article className="panel signal-panel alert-engine-panel">
              <div className="panel-head compact">
                <div>
                  <span className="eyebrow">ENGINE EVENTS</span>
                  <strong>Built-in metric signals</strong>
                </div>
                <span className={`quality-badge ${metricEvents.length ? "good" : "neutral"}`}>
                  {metricEvents.length ? `${metricEvents.length} LIVE` : "QUIET"}
                </span>
              </div>
              {metricEvents.length > 0 ? (
                <div className="signal-list">
                  {metricEvents.map((event) => (
                    <article
                      className={`signal-card ${event.severity}`}
                      key={`${event.type}:${event.openTime}:${event.metric}`}
                    >
                      <div>
                        <strong>{eventLabel(event)}</strong>
                        <span>{formatClock(event.openTime)}</span>
                      </div>
                      <p>{event.description}</p>
                      <footer>
                        <span>{event.metric}</span>
                        <b>{event.value === null ? "--" : event.value.toFixed(2)}</b>
                        <span>{formatConfidence(event.confidence)}</span>
                      </footer>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="signal-empty">
                  <span className="signal-crosshair" />
                  <strong>No engine events</strong>
                  <p>Built-in metrics are quiet for the selected market window.</p>
                </div>
              )}
            </article>
          </aside>
        </section>
        )}

        <footer className="system-footer">
          <span>
            <b className={`status-orb ${isLive ? "live" : "warn"}`} />
            {exchangeLabel(exchange)} {selectedMarket?.status ?? "waiting"}
          </span>
          <span>PIPE Q {health?.pipeline.queueSize ?? "--"}</span>
          <span>TRADES {formatCompact(health?.pipeline.processedTrades ?? null, 1)}</span>
          <span>DB {health?.database.status ?? "--"}</span>
          <span className="footer-time">{formatClock(Date.now())} MSK</span>
        </footer>

        <div className="alert-toast-stack" aria-live="assertive">
          {alertToasts.map((toast) => {
            const dragOffset = toastDragOffsets[toast.id] ?? 0;
            const isDismissing = dismissingToastIds.has(toast.id);
            return (
              <article
                className={`alert-toast ${toast.severity} ${
                  dragOffset > 0 ? "dragging" : ""
                } ${isDismissing ? "dismissing" : ""}`}
                key={toast.id}
                onPointerDown={(event) => startAlertToastDrag(toast.id, event)}
                onPointerMove={(event) => moveAlertToastDrag(toast.id, event)}
                onPointerUp={(event) => finishAlertToastDrag(toast.id, event)}
                onPointerCancel={() => clearAlertToastDrag(toast.id)}
                style={
                  {
                    "--toast-drag-x": `${dragOffset}px`,
                  } as CSSProperties
                }
              >
                <div className="alert-toast-head">
                  <strong>{toast.title}</strong>
                  <span>{formatClock(toast.createdAt)}</span>
                  <button
                    aria-label="Close notification"
                    className="alert-toast-close"
                    type="button"
                    onClick={() => dismissAlertToast(toast.id)}
                    onPointerDown={(event) => event.stopPropagation()}
                  >
                    x
                  </button>
                </div>
                <p>{toast.body}</p>
              </article>
            );
          })}
        </div>
      </main>
    </div>
  );
}

function readableError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  try {
    const parsed = JSON.parse(message) as { detail?: string };
    return parsed.detail ?? message;
  } catch {
    return message;
  }
}

function AuthScreen({
  onAuthenticated,
}: {
  onAuthenticated: (response: AuthResponse) => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isRegister = mode === "register";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = isRegister
        ? await register({
            email,
            password,
            displayName: displayName.trim() || undefined,
          })
        : await login({ email, password });
      window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, response.token);
      onAuthenticated(response);
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setLoading(false);
    }
  };

  const handleGuest = () => {
    setError(null);
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, GUEST_AUTH_TOKEN);
    onAuthenticated(GUEST_AUTH_RESPONSE);
  };

  return (
    <main className="auth-shell">
      <section className="auth-frame">
        <div className="auth-showcase" aria-hidden="true">
          <div className="auth-brand auth-brand-showcase">
            <TickframeLogo />
            <div>
              <strong>TICKFRAME</strong>
              <small>Crypto Pattern Analytics</small>
            </div>
          </div>
          <HeroBrandPoster />
        </div>

        <section className="auth-card">
          <div className="auth-brand">
            <TickframeLogo />
            <div>
              <span className="product-kicker">TICKFRAME ACCESS</span>
              <h1>{isRegister ? "Create account" : "Welcome back"}</h1>
            </div>
          </div>

          <p className="auth-copy">
            Sign in to open live market analytics, pattern signals, and
            quantitative metrics in one workspace.
          </p>

          <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
            <button
              type="button"
              className={!isRegister ? "active" : ""}
              onClick={() => {
                setMode("login");
                setError(null);
              }}
            >
              Login
            </button>
            <button
              type="button"
              className={isRegister ? "active" : ""}
              onClick={() => {
                setMode("register");
                setError(null);
              }}
            >
              Register
            </button>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            {isRegister && (
              <label>
                Display name
                <input
                  autoComplete="name"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Roman"
                />
              </label>
            )}

            <label>
              Email
              <input
                autoComplete="email"
                inputMode="email"
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
              />
            </label>

            <label>
              Password
              <input
                autoComplete={isRegister ? "new-password" : "current-password"}
                minLength={8}
                required
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 8 characters"
              />
            </label>

            {error && (
              <div className="auth-error" role="alert">
                {error}
              </div>
            )}

            <button className="auth-submit" type="submit" disabled={loading}>
              {loading
                ? "Please wait..."
                : isRegister
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>

          <button
            className="guest-submit"
            type="button"
            disabled={loading}
            onClick={handleGuest}
          >
            Continue as guest
          </button>
        </section>
      </section>
    </main>
  );
}

export default function App() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
    if (!token) {
      setAuthLoading(false);
      return;
    }
    if (token === GUEST_AUTH_TOKEN) {
      setSession({ token, user: GUEST_AUTH_RESPONSE.user });
      setAuthLoading(false);
      return;
    }

    const controller = new AbortController();
    fetchCurrentUser(token, controller.signal)
      .then((response) => {
        setSession({ token, user: response.user });
      })
      .catch(() => {
        window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
        setSession(null);
      })
      .finally(() => setAuthLoading(false));

    return () => controller.abort();
  }, []);

  const handleAuthenticated = useCallback((response: AuthResponse) => {
    setSession({ token: response.token, user: response.user });
  }, []);

  const handleLogout = useCallback(() => {
    const token = session?.token;
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    setSession(null);
    if (token && token !== GUEST_AUTH_TOKEN) {
      void logout(token).catch(() => undefined);
    }
  }, [session]);

  if (authLoading) {
    return (
      <main className="auth-shell">
        <section className="auth-card auth-loading">
          <TickframeLogo />
          <strong>Restoring session</strong>
          <div className="loading-line short" />
        </section>
      </main>
    );
  }

  if (!session) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  return <Dashboard session={session} onLogout={handleLogout} />;
}
