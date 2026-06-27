export type Exchange = "binance" | "bybit";
export type MarketStatus = "live" | "stale" | "waiting";
export type StreamStatus = "connecting" | "live" | "reconnecting" | "offline";
export type HistorySource =
  | "timescaledb"
  | "memory"
  | "raw_trades"
  | "historical_candles"
  | "binance_proxy_1s"
  | "provisional";
export type Timeframe =
  | "1s"
  | "5s"
  | "15s"
  | "1m"
  | "5m"
  | "15m"
  | "1h";

export interface Instrument {
  instrumentId: string;
  name: string;
  base: string;
  quote: string;
  symbols: Partial<Record<Exchange, string>>;
}

export interface InstrumentsResponse {
  configVersion: string;
  marketType: string;
  instruments: Instrument[];
}

export interface Market {
  exchange: Exchange;
  marketType: string;
  instrumentId: string;
  name: string;
  base: string;
  quote: string;
  exchangeSymbol: string;
  price: string | null;
  lastTradeSize: string | null;
  lastTradeSide: "buy" | "sell" | null;
  exchangeTimestamp: number | null;
  receivedTimestamp: number | null;
  latencyMs: number | null;
  ageMs: number | null;
  status: MarketStatus;
}

export interface MarketsResponse {
  configVersion: string;
  revision: number;
  generatedAt: number;
  markets: Market[];
}

export interface Candle {
  exchange: Exchange;
  marketType: string;
  instrumentId: string;
  timeframe: Timeframe;
  openTime: number;
  closeTime: number;
  open: string | null;
  high: string | null;
  low: string | null;
  close: string | null;
  baseVolume: string;
  quoteVolume: string;
  tradeCount: number;
  status:
    | "complete"
    | "complete_empty"
    | "incomplete"
    | "recovered"
    | "provisional";
  revision: number;
  firstTradeId: string | null;
  lastTradeId: string | null;
  finalizedAt: number;
  source?: HistorySource | string | null;
}

export interface CandlesResponse {
  exchange: Exchange;
  instrumentId: string;
  timeframe: Timeframe;
  source: HistorySource;
  from: number;
  to: number;
  count: number;
  hasMore: boolean;
  nextBefore: number | null;
  chartLatency: {
    generatedAt: number;
    dataTo: number;
    effectiveLagMs: number;
    stableDelayMs: number;
    allowedLatenessMs: number;
  };
  candles: Candle[];
}

export interface CandleStreamResponse {
  exchange: Exchange;
  instrumentId: string;
  timeframe: Timeframe;
  source: "provisional";
  generatedAt: number;
  revision: number;
  chartLatency?: CandlesResponse["chartLatency"];
  candles: Candle[];
}

export interface MetricPoint {
  openTime: number;
  closeTime: number;
  close: number | null;
  vwap: number | null;
  vwapDeviationPct: number | null;
  realizedVolatilityPct: number | null;
  parkinsonVolatilityPct: number | null;
  garmanKlassVolatilityPct: number | null;
  rsi: number | null;
  shortMomentumPct: number | null;
  momentumPct: number | null;
  meanReversionZScore: number | null;
  distanceToMeanPct: number | null;
  priceVolumeDivergencePct: number | null;
  volumeSpikeRatio: number | null;
  baseVolume: number | null;
  tradeCount: number;
  status: Candle["status"];
}

export interface MetricEvent {
  type: string;
  metric: keyof MetricPoint | string;
  openTime: number;
  closeTime: number;
  severity: "medium" | "high";
  confidence: number | null;
  value: number | null;
  threshold: number | null;
  description: string;
}

export interface MetricsResponse {
  exchange: Exchange;
  marketType: string;
  instrumentId: string;
  timeframe: Timeframe;
  source: HistorySource;
  from: number;
  to: number;
  hasMore: boolean;
  nextBefore: number | null;
  version: string;
  windows: {
    rsi: number;
    shortMomentum: number;
    momentum: number;
    realizedVolatility: number;
    rangeVolatility: number;
    meanReversion: number;
    priceVolumeDivergence: number;
    volumeSpike: number;
  };
  count: number;
  latest: MetricPoint | null;
  summary: {
    high: number | null;
    low: number | null;
    baseVolume: number | null;
    tradeCount: number;
  };
  events: MetricEvent[];
  crossPairCorrelations: Array<{
    instrumentId: string;
    name: string;
    base: string;
    correlation: number | null;
    sampleSize: number;
    source: HistorySource | string;
  }>;
  points: MetricPoint[];
  metricsLatency: {
    generatedAt: number;
    dataTo: number;
    effectiveLagMs: number;
    calculatedAt: number;
    computeDurationMs: number;
    windowName: string;
  };
}

export type MlPatternStatus =
  | "pattern_detected"
  | "no_reliable_pattern"
  | "unsupported_timeframe"
  | "insufficient_data"
  | "model_unavailable";

export interface MlPatternResponse {
  status: MlPatternStatus;
  message: string;
  modelVersion: string;
  modelType?: string;
  supportedTimeframes: Timeframe[];
  exchange: Exchange;
  instrumentId: string;
  timeframe: Timeframe;
  windowSize: number;
  source: HistorySource | string;
  generatedAt: number;
  confidenceThreshold?: number;
  prediction: {
    label: string;
    confidence: number;
  } | null;
  alternatives: Array<{
    label: string;
    confidence: number;
  }>;
  dataFrom?: number | null;
  dataTo?: number | null;
  candleCount?: number;
  experimental?: boolean;
}

export interface CollectorHealth {
  exchange: Exchange;
  connected: boolean;
  lastMessageAt: number | null;
  messageAgeMs: number | null;
  reconnects: number;
  endpoint: string | null;
  endpointFailures: number;
  acceptedTopics?: string[];
  pendingTopics?: string[];
  rejectedTopics?: Record<string, string>;
  lastError: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  configVersion: string;
  collectors: Record<Exchange, CollectorHealth>;
  pipeline: {
    queueSize: number;
    queueCapacity: number;
    processedTrades: number;
    revisedCandles: number;
  };
  streams: {
    marketRevision: number;
    provisionalCandleRevision: number;
    stableCandleRevision: number;
    metricRevision: number;
  };
  metrics: {
    queueSize: number;
    queueCapacity: number;
    pendingScopes: number;
    computedSnapshots: number;
    cachedScopes: number;
    cachedCorrelations: number;
    correlationRefreshMs: number;
    lastError: string | null;
  };
  chart: {
    stableDelayMs: number;
    allowedLatenessMs: number;
    rawTradeTimeframes: Timeframe[];
    rawTradeRetentionHours: number;
    secondRepairHours: number;
    binanceSecondBackfillHours: number;
  };
  database: {
    status: "ok" | "degraded" | "disabled";
    queueSize: number;
    queueCapacity: number;
    writtenTrades: number;
    writtenCandles: number;
    writtenMetricPoints: number;
    writtenMetricEvents: number;
    writtenMetricSummaries: number;
    lastError: string | null;
  };
  recovery: {
    enabled: boolean;
    running: boolean;
    lookbackHours: number;
    secondRepairHours: number;
    binanceSecondBackfillHours: number;
    lastReason: string | null;
    lastStartedAt: number | null;
    lastFinishedAt: number | null;
    insertedCandles: number;
    insertedHistoricalSecondCandles: number;
    repairedSecondCandles: number;
    failedMarkets: Record<string, string>;
    lastError: string | null;
  };
  observability?: {
    latencySeries: number;
    latestMarkets: number;
    latestDisplays: number;
    frontendSamples: number;
    prometheusPath: string;
    latencyApiPath: string;
  };
}

export interface DisplayTelemetrySample {
  channel: "markets" | "stable_candles" | "provisional_candles" | "metrics" | "stats";
  exchange: Exchange;
  instrumentId: string;
  timeframe?: Timeframe;
  price?: string | null;
  exchangeTimestamp?: number | null;
  backendReceivedAt?: number | null;
  backendGeneratedAt?: number | null;
  dataTimestamp?: number | null;
  frontendReceivedAt: number;
  displayedAt: number;
}

export interface DisplayCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  tradeCount: number;
}

export interface AuthUser {
  id: string;
  email: string;
  displayName: string;
  createdAt: string;
}

export interface AuthResponse {
  token: string;
  tokenType: "bearer";
  expiresAt: string;
  user: AuthUser;
}

export interface CurrentUserResponse {
  user: AuthUser;
}
