import type {
  AuthResponse,
  CandlesResponse,
  CurrentUserResponse,
  DisplayTelemetrySample,
  Exchange,
  HealthResponse,
  InstrumentsResponse,
  MarketsResponse,
  MetricsResponse,
  MlPatternResponse,
  PatternDetectorMode,
  ScriptDefinition,
  ScriptRun,
  Timeframe,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;

interface RequestOptions {
  signal?: AbortSignal;
  method?: "GET" | "POST";
  body?: unknown;
  token?: string;
  timeoutMs?: number;
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

  const controller = new AbortController();
  const abortFromCaller = () => controller.abort(options.signal?.reason);
  if (options.signal?.aborted) {
    abortFromCaller();
  } else {
    options.signal?.addEventListener("abort", abortFromCaller, { once: true });
  }
  const timeout = window.setTimeout(
    () => controller.abort(new DOMException("Request timed out", "TimeoutError")),
    Math.max(1, options.timeoutMs ?? DEFAULT_REQUEST_TIMEOUT_MS),
  );

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    });

    if (!response.ok) {
      const body = await response.text();
      let message = body;
      try {
        const parsed = JSON.parse(body) as { detail?: string };
        if (typeof parsed.detail === "string") message = parsed.detail;
      } catch {
        // Non-JSON errors are already suitable for display.
      }
      throw new Error(message || `Request failed with ${response.status}`);
    }

    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeout);
    options.signal?.removeEventListener("abort", abortFromCaller);
  }
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

export function postDisplayTelemetry(samples: DisplayTelemetrySample[]) {
  if (samples.length === 0) {
    return Promise.resolve({ accepted: 0 });
  }
  return request<{ accepted: number }>("/api/v1/telemetry/display-latency", {
    method: "POST",
    body: { samples },
  });
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

export function fetchScripts(token: string, signal?: AbortSignal) {
  return request<{ scripts: ScriptDefinition[] }>("/api/v1/scripts", {
    token,
    signal,
  });
}

export function fetchScriptAccess(token: string, signal?: AbortSignal) {
  return request<{ allowed: boolean }>("/api/v1/scripts/access", {
    token,
    signal,
  });
}

export function startScript(
  scriptId: string,
  parameters: Record<string, string | number | boolean>,
  token: string,
  signal?: AbortSignal,
) {
  return request<{ run: ScriptRun }>(`/api/v1/scripts/${scriptId}/runs`, {
    method: "POST",
    body: { parameters },
    token,
    signal,
    timeoutMs: 30_000,
  });
}

export function fetchScriptRun(runId: string, token: string, signal?: AbortSignal) {
  return request<{ run: ScriptRun }>(`/api/v1/scripts/runs/${runId}`, {
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
  mode: PatternDetectorMode = "ml",
  signal?: AbortSignal,
) {
  const query = new URLSearchParams({
    exchange,
    instrumentId,
    timeframe,
    mode,
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
