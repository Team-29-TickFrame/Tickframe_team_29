import type {
  AuthResponse,
  CandlesResponse,
  CurrentUserResponse,
  Exchange,
  HealthResponse,
  InstrumentsResponse,
  MarketsResponse,
  MetricsResponse,
  MlPatternResponse,
  Timeframe,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

interface RequestOptions {
  signal?: AbortSignal;
  method?: "GET" | "POST";
  body?: unknown;
  token?: string;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }

  return (await response.json()) as T;
}

export function fetchInstruments(signal?: AbortSignal) {
  return request<InstrumentsResponse>("/api/v1/instruments", { signal });
}

export function fetchMarkets(signal?: AbortSignal) {
  return request<MarketsResponse>("/api/v1/markets", { signal });
}

export function fetchHealth(signal?: AbortSignal) {
  return request<HealthResponse>("/health", { signal });
}

export function register(
  payload: { email: string; password: string; displayName?: string },
  signal?: AbortSignal,
) {
  return request<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: payload,
    signal,
  });
}

export function login(
  payload: { email: string; password: string },
  signal?: AbortSignal,
) {
  return request<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: payload,
    signal,
  });
}

export function fetchCurrentUser(token: string, signal?: AbortSignal) {
  return request<CurrentUserResponse>("/api/v1/auth/me", {
    token,
    signal,
  });
}

export function logout(token: string, signal?: AbortSignal) {
  return request<{ status: "ok" }>("/api/v1/auth/logout", {
    method: "POST",
    token,
    signal,
  });
}

export function fetchCandles(
  exchange: Exchange,
  instrumentId: string,
  options: {
    timeframe: Timeframe;
    limit?: number;
    from?: number;
    to?: number;
  },
  signal?: AbortSignal,
) {
  const query = new URLSearchParams({
    exchange,
    instrumentId,
    timeframe: options.timeframe,
    limit: String(options.limit ?? 1000),
  });
  if (options.from !== undefined) query.set("from", String(options.from));
  if (options.to !== undefined) query.set("to", String(options.to));
  return request<CandlesResponse>(`/api/v1/candles?${query}`, { signal });
}

export function fetchMetrics(
  exchange: Exchange,
  instrumentId: string,
  options: {
    timeframe: Timeframe;
    limit?: number;
    from?: number;
    to?: number;
  },
  signal?: AbortSignal,
) {
  const query = new URLSearchParams({
    exchange,
    instrumentId,
    timeframe: options.timeframe,
    limit: String(options.limit ?? 300),
  });
  if (options.from !== undefined) query.set("from", String(options.from));
  if (options.to !== undefined) query.set("to", String(options.to));
  return request<MetricsResponse>(`/api/v1/metrics?${query}`, { signal });
}

export function fetchMlPattern(
  exchange: Exchange,
  instrumentId: string,
  timeframe: Timeframe,
  signal?: AbortSignal,
) {
  const query = new URLSearchParams({
    exchange,
    instrumentId,
    timeframe,
  });
  return request<MlPatternResponse>(`/api/v1/patterns/ml?${query}`, { signal });
}

export function marketWebSocketUrl(): string {
  const configured = import.meta.env.VITE_WS_URL as string | undefined;
  if (configured) {
    return configured;
  }

  const url = new URL("/ws/v1/markets", window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function metricsWebSocketUrl(
  exchange: Exchange,
  instrumentId: string,
  timeframe: Timeframe,
  windowName: "default" | "24h",
): string {
  const configured = import.meta.env.VITE_METRICS_WS_URL as string | undefined;
  const base = configured || "/ws/v1/metrics";
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("exchange", exchange);
  url.searchParams.set("instrumentId", instrumentId);
  url.searchParams.set("timeframe", timeframe);
  url.searchParams.set("window", windowName);
  return url.toString();
}

export function candleWebSocketUrl(
  exchange: Exchange,
  instrumentId: string,
  timeframe: Timeframe,
): string {
  const configured = import.meta.env.VITE_CANDLES_WS_URL as string | undefined;
  const base = configured || "/ws/v1/candles";
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("exchange", exchange);
  url.searchParams.set("instrumentId", instrumentId);
  url.searchParams.set("timeframe", timeframe);
  return url.toString();
}

export function stableCandleWebSocketUrl(
  exchange: Exchange,
  instrumentId: string,
  timeframe: Timeframe,
  limit = 20,
): string {
  const configured = import.meta.env.VITE_STABLE_CANDLES_WS_URL as
    | string
    | undefined;
  const base = configured || "/ws/v1/candles/stable";
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("exchange", exchange);
  url.searchParams.set("instrumentId", instrumentId);
  url.searchParams.set("timeframe", timeframe);
  url.searchParams.set("limit", String(limit));
  return url.toString();
}
