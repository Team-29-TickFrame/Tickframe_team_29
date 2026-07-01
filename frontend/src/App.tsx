import {
  type FormEvent,
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
import MarketChart from "./components/MarketChart";
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
  const historyLoadingRef = useRef(false);

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
  const backendHealthy = health?.status === "ok";
  const isLive =
    streamStatus === "live" &&
    selectedMarket?.status === "live" &&
    selectedCollector?.connected !== false;

  return (
    <div className="app-shell">
      <aside className="side-rail">
        <div className="brand-mark" aria-label="Tickframe">
          <TickframeLogo />
          <span className="brand-word">TICKFRAME</span>
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          <button className="nav-item active" type="button">
            <span className="nav-index">01</span>
            <span>Dashboard</span>
          </button>
          <button className="nav-item" type="button" disabled>
            <span className="nav-index">02</span>
            <span>Alerts</span>
            <small>soon</small>
          </button>
          <button className="nav-item" type="button" disabled>
            <span className="nav-index">03</span>
            <span>History</span>
            <small>soon</small>
          </button>
        </nav>

        <div className="rail-status">
          <span className={`status-orb ${backendHealthy ? "live" : "warn"}`} />
          <div>
            <span>PIPELINE</span>
            <strong>{health?.status ?? "checking"}</strong>
          </div>
        </div>
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
