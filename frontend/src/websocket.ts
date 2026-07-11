interface ResilientWebSocketOptions {
  onConnecting?: (attempt: number) => void;
  onOpen?: () => void;
  onMessage: (event: MessageEvent<string>) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: () => void;
  minReconnectDelayMs?: number;
  maxReconnectDelayMs?: number;
}

export function connectResilientWebSocket(
  url: string,
  options: ResilientWebSocketOptions,
): () => void {
  const minDelay = Math.max(250, options.minReconnectDelayMs ?? 1_000);
  const maxDelay = Math.max(minDelay, options.maxReconnectDelayMs ?? 15_000);
  let socket: WebSocket | null = null;
  let retryTimer: number | null = null;
  let retryAttempt = 0;
  let stopped = false;

  const scheduleReconnect = () => {
    if (stopped || retryTimer !== null) return;
    const delay = Math.min(minDelay * 2 ** retryAttempt, maxDelay);
    retryAttempt += 1;
    retryTimer = window.setTimeout(() => {
      retryTimer = null;
      connect();
    }, delay);
  };

  const connect = () => {
    if (stopped || socket !== null) return;
    options.onConnecting?.(retryAttempt);

    let current: WebSocket;
    try {
      current = new WebSocket(url);
    } catch {
      options.onError?.();
      scheduleReconnect();
      return;
    }
    socket = current;

    current.addEventListener("open", () => {
      if (stopped || socket !== current) return;
      options.onOpen?.();
    });
    current.addEventListener("message", (event: MessageEvent<string>) => {
      if (stopped || socket !== current) return;
      retryAttempt = 0;
      options.onMessage(event);
    });
    current.addEventListener("error", () => {
      if (stopped || socket !== current) return;
      options.onError?.();
      current.close();
    });
    current.addEventListener("close", (event) => {
      if (socket === current) socket = null;
      if (stopped) return;
      options.onClose?.(event);
      if (event.code === 1008) {
        stopped = true;
        return;
      }
      scheduleReconnect();
    });
  };

  const reconnectWhenOnline = () => {
    if (stopped || socket !== null) return;
    if (retryTimer !== null) {
      window.clearTimeout(retryTimer);
      retryTimer = null;
    }
    connect();
  };

  window.addEventListener("online", reconnectWhenOnline);
  connect();

  return () => {
    stopped = true;
    window.removeEventListener("online", reconnectWhenOnline);
    if (retryTimer !== null) window.clearTimeout(retryTimer);
    retryTimer = null;
    const current = socket;
    socket = null;
    current?.close(1000, "component unmounted");
  };
}
