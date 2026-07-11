import assert from "node:assert/strict";
import test from "node:test";

import { connectResilientWebSocket } from "./websocket.ts";

type SocketListener = (event: unknown) => void;

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  readonly url: string;
  private readonly listeners = new Map<string, SocketListener[]>();

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type: string, listener: SocketListener): void {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  close(code = 1000): void {
    this.emit("close", { code });
  }

  emit(type: string, event: unknown): void {
    for (const listener of this.listeners.get(type) ?? []) listener(event);
  }
}

interface BrowserHarness {
  online: () => void;
  runNextTimer: () => void;
  timerCount: () => number;
}

function installBrowserHarness(): BrowserHarness {
  FakeWebSocket.instances = [];
  const timers = new Map<number, () => void>();
  const onlineListeners = new Set<() => void>();
  let nextTimerId = 1;
  const fakeWindow = {
    addEventListener(type: string, listener: () => void) {
      if (type === "online") onlineListeners.add(listener);
    },
    clearTimeout(id: number) {
      timers.delete(id);
    },
    removeEventListener(type: string, listener: () => void) {
      if (type === "online") onlineListeners.delete(listener);
    },
    setTimeout(callback: () => void) {
      const id = nextTimerId;
      nextTimerId += 1;
      timers.set(id, callback);
      return id;
    },
  };
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: fakeWindow,
  });
  Object.defineProperty(globalThis, "WebSocket", {
    configurable: true,
    value: FakeWebSocket,
  });
  return {
    online: () => {
      for (const listener of onlineListeners) listener();
    },
    runNextTimer: () => {
      const entry = timers.entries().next().value as
        | [number, () => void]
        | undefined;
      assert.ok(entry, "expected a reconnect timer");
      const [id, callback] = entry;
      timers.delete(id);
      callback();
    },
    timerCount: () => timers.size,
  };
}

test("reconnects after an abnormal close and cleans up timers", () => {
  const harness = installBrowserHarness();
  const attempts: number[] = [];
  const messages: string[] = [];
  const disconnect = connectResilientWebSocket("ws://tickframe.test/markets", {
    onConnecting: (attempt) => attempts.push(attempt),
    onMessage: (event) => messages.push(event.data),
  });

  assert.equal(FakeWebSocket.instances.length, 1);
  FakeWebSocket.instances[0].emit("message", { data: "snapshot" });
  FakeWebSocket.instances[0].emit("close", { code: 1006 });
  assert.deepEqual(messages, ["snapshot"]);
  assert.equal(harness.timerCount(), 1);

  harness.runNextTimer();
  assert.equal(FakeWebSocket.instances.length, 2);
  assert.deepEqual(attempts, [0, 1]);

  disconnect();
  assert.equal(harness.timerCount(), 0);
});

test("does not reconnect after a policy violation", () => {
  const harness = installBrowserHarness();
  const disconnect = connectResilientWebSocket("ws://tickframe.test/markets", {
    onMessage: () => undefined,
  });

  FakeWebSocket.instances[0].emit("close", { code: 1008 });
  harness.online();

  assert.equal(harness.timerCount(), 0);
  assert.equal(FakeWebSocket.instances.length, 1);
  disconnect();
});

test("reconnects immediately when the browser comes back online", () => {
  const harness = installBrowserHarness();
  const disconnect = connectResilientWebSocket("ws://tickframe.test/markets", {
    onMessage: () => undefined,
  });
  FakeWebSocket.instances[0].emit("close", { code: 1006 });

  harness.online();

  assert.equal(harness.timerCount(), 0);
  assert.equal(FakeWebSocket.instances.length, 2);
  disconnect();
});
