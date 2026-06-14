const DEMO_USER = {
  id: "demo",
  name: "Demo Analyst",
  email: "demo@tickframe.local",
  password: "demo123",
};

const DEFAULT_ALERTS = [
  {
    id: "seed-btc-triangle",
    asset: "BTC/USDT",
    type: "Triangle detected",
    threshold: 84,
    method: "In-App Notification",
    status: "Active",
    createdAt: Date.now() - 2 * 60 * 1000,
  },
  {
    id: "seed-eth-confidence",
    asset: "BTC/USDT",
    type: "Confidence > 80%",
    threshold: 80,
    method: "In-App Notification",
    status: "Active",
    createdAt: Date.now() - 15 * 60 * 1000,
  },
  {
    id: "seed-xrp-rsi",
    asset: "BTC/USDT",
    type: "RSI Oversold",
    threshold: 35,
    method: "Email",
    status: "Inactive",
    createdAt: Date.now() - 3 * 60 * 60 * 1000,
  },
];

const ASSETS = [
  {
    symbol: "BTC/USDT",
    name: "Bitcoin / Tether",
    icon: "B",
    basePrice: 108250,
    minPrice: 90000,
    maxPrice: 120000,
    marketCap: "$2.14T",
    supply: "19.68M BTC",
    pattern: "Ascending Triangle",
    confidence: 84,
    hitRate: 72,
    volatility: "Medium",
    volume: "High",
  },
];

const TIMEFRAMES = [
  { id: "1s", label: "1s", ms: 1000, visibleCandles: 58, btcPriceStep: 50 },
  { id: "5s", label: "5s", ms: 5000, visibleCandles: 64, btcPriceStep: 100 },
  { id: "15s", label: "15s", ms: 15000, visibleCandles: 68, btcPriceStep: 250 },
  { id: "1m", label: "1m", ms: 60000, visibleCandles: 72, btcPriceStep: 500 },
  { id: "5m", label: "5m", ms: 300000, visibleCandles: 72, btcPriceStep: 1000 },
  { id: "15m", label: "15m", ms: 900000, visibleCandles: 48, btcPriceStep: 500 },
  { id: "1h", label: "1h", ms: 3600000, visibleCandles: 48, btcPriceStep: 1000 },
  { id: "4h", label: "4h", ms: 14400000, visibleCandles: 42, btcPriceStep: 2000 },
  { id: "1D", label: "1D", ms: 86400000, visibleCandles: 30, btcPriceStep: 5000 },
];

const HISTORY_MS = 30 * 24 * 60 * 60 * 1000;
const BASE_TICK_MS = 1000;
const RECENT_FINE_HISTORY_MS = 2 * 60 * 60 * 1000;
const MID_HISTORY_MS = 3 * 24 * 60 * 60 * 1000;
const MID_TICK_MS = 60 * 1000;
const FAR_TICK_MS = 5 * 60 * 1000;

const state = {
  route: "login",
  user: readSession(),
  selectedAsset: "BTC/USDT",
  selectedTimeframe: "1m",
  markets: createMarkets(),
  lastError: "",
  successMessage: "",
};

if (state.user) {
  state.route = "dashboard";
  seedAlerts(state.user.id);
}

setInterval(() => {
  if (!state.user) return;
  advanceMarkets();
  if (state.route === "dashboard") {
    render();
  }
}, BASE_TICK_MS);

function readSession() {
  try {
    return JSON.parse(localStorage.getItem("tickframe.session"));
  } catch {
    return null;
  }
}

function writeSession(user) {
  localStorage.setItem("tickframe.session", JSON.stringify(user));
}

function alertsKey(userId) {
  return `tickframe.alerts.${userId}`;
}

function readAlerts() {
  if (!state.user) return [];
  try {
    return JSON.parse(localStorage.getItem(alertsKey(state.user.id))) || [];
  } catch {
    return [];
  }
}

function writeAlerts(alerts) {
  localStorage.setItem(alertsKey(state.user.id), JSON.stringify(alerts));
}

function seedAlerts(userId) {
  const key = alertsKey(userId);
  if (!localStorage.getItem(key)) {
    const seeded = userId === "guest" ? DEFAULT_ALERTS.slice(0, 1) : DEFAULT_ALERTS;
    localStorage.setItem(key, JSON.stringify(seeded));
  }
}

function createMarkets() {
  return ASSETS.reduce((markets, asset, assetIndex) => {
    const ticks = seedTicks(asset, assetIndex);
    markets[asset.symbol] = {
      asset,
      assetIndex,
      ticks,
      step: ticks.length,
    };
    return markets;
  }, {});
}

function seedTicks(asset, assetIndex) {
  const ticks = [];
  const now = floorToSecond(Date.now());
  const startTime = now - HISTORY_MS;
  const midStartTime = now - MID_HISTORY_MS;
  const fineStartTime = now - RECENT_FINE_HISTORY_MS;
  let price = asset.basePrice * (0.972 + assetIndex * 0.003);
  let index = 0;

  for (let time = startTime; time < midStartTime; time += FAR_TICK_MS) {
    price = nextMockPrice(asset, assetIndex, price, index, HISTORY_MS / FAR_TICK_MS);
    ticks.push(createSyntheticTick(asset, assetIndex, index, time, price));
    index += 1;
  }

  for (let time = midStartTime; time < fineStartTime; time += MID_TICK_MS) {
    price = nextMockPrice(asset, assetIndex, price, index, HISTORY_MS / MID_TICK_MS);
    ticks.push(createSyntheticTick(asset, assetIndex, index, time, price));
    index += 1;
  }

  for (let time = fineStartTime; time <= now; time += BASE_TICK_MS) {
    price = nextMockPrice(asset, assetIndex, price, index, HISTORY_MS / BASE_TICK_MS);
    ticks.push(createSyntheticTick(asset, assetIndex, index, time, price));
    index += 1;
  }

  return ticks;
}

function nextMockPrice(asset, assetIndex, previousPrice, index, total) {
  const progress = index / Math.max(1, total);
  const base = asset.basePrice;
  const macroTrend = Math.sin(progress * Math.PI * 7.5 + assetIndex) * base * 0.000028;
  const intradayWave = Math.sin(index / 2300 + assetIndex * 0.9) * base * 0.000052;
  const microWave = Math.sin(index / 67 + assetIndex * 1.7) * base * 0.000026;
  const patternBias = getPatternBias(asset.pattern, progress, index, base);
  const meanReversion = (base - previousPrice) * 0.000012;
  const noise = (Math.random() - 0.5) * base * 0.00008;
  const next = previousPrice + macroTrend + intradayWave + microWave + patternBias + meanReversion + noise;

  return clampAssetPrice(asset, next, index);
}

function clampAssetPrice(asset, price, index) {
  const minPrice = asset.minPrice || asset.basePrice * 0.04;
  const maxPrice = asset.maxPrice || asset.basePrice * 25;

  if (price > maxPrice) {
    return maxPrice - Math.abs(Math.sin(index * 0.19)) * asset.basePrice * 0.0016;
  }

  if (price < minPrice) {
    return minPrice + Math.abs(Math.cos(index * 0.17)) * asset.basePrice * 0.0016;
  }

  return price;
}

function nextMockVolume(asset, assetIndex, index) {
  const baseVolume = asset.basePrice > 1000 ? 0.6 : 1200;
  const pulse = Math.abs(Math.sin(index / 600 + assetIndex)) * baseVolume * 1.6;
  const spike = asset.pattern === "Volume Spike" && index % 1800 > 1680 ? baseVolume * 4 : 0;
  return baseVolume + pulse + spike + Math.random() * baseVolume;
}

function createSyntheticTick(asset, assetIndex, index, time, price) {
  const base = asset.basePrice;
  const volatilityWave = 0.75 + Math.abs(Math.sin(index / 37 + assetIndex)) * 1.55;
  const localRange = base * (0.00058 + (index % 11) * 0.000026) * volatilityWave;
  const upperWick = localRange * (0.9 + Math.abs(Math.sin(index / 13)) * 1.8);
  const lowerWick = localRange * (0.9 + Math.abs(Math.cos(index / 17)) * 1.8);
  const shadowBias = Math.sin(index / 29 + assetIndex) * localRange * 0.28;
  const high = clampAssetPrice(asset, price + upperWick + Math.max(0, shadowBias), index);
  const low = clampAssetPrice(asset, price - lowerWick + Math.min(0, shadowBias), index);

  return {
    time,
    price,
    high: Math.max(price, high),
    low: Math.min(price, low),
    volume: nextMockVolume(asset, assetIndex, index),
  };
}

function getPatternBias(pattern, progress, index, basePrice) {
  if (pattern === "Ascending Triangle") {
    const lateCompression = progress > 0.55 ? basePrice * 0.000025 : basePrice * 0.000008;
    return lateCompression + Math.max(0, Math.sin(index / 210)) * basePrice * 0.00002;
  }

  if (pattern === "Bull Flag") {
    const impulse = progress < 0.34 ? basePrice * 0.00005 : 0;
    const channel = progress >= 0.34 && progress < 0.72 ? -basePrice * 0.000012 : basePrice * 0.000018;
    return impulse + channel;
  }

  if (pattern === "Double Bottom") {
    const leftDip = -Math.exp(-Math.pow((progress - 0.32) / 0.08, 2)) * basePrice * 0.00016;
    const rightRecovery = progress > 0.68 ? basePrice * 0.00006 : 0;
    return leftDip + rightRecovery;
  }

  if (pattern === "Head and Shoulders") {
    return progress > 0.76 ? -basePrice * 0.00006 : Math.sin(index / 700) * basePrice * 0.000018;
  }

  if (pattern === "Volume Spike") {
    return index % 1800 > 1680 ? basePrice * 0.00012 : Math.sin(index / 440) * basePrice * 0.000015;
  }

  return Math.sin(index / 500) * basePrice * 0.000025;
}

function advanceMarkets() {
  Object.values(state.markets).forEach((market) => {
    const previous = market.ticks[market.ticks.length - 1];
    const nextTime = previous.time + BASE_TICK_MS;
    const nextPrice = nextMockPrice(market.asset, market.assetIndex, previous.price, market.step, market.step + 1);
    market.ticks.push(createSyntheticTick(market.asset, market.assetIndex, market.step, nextTime, nextPrice));

    market.step += 1;
    pruneOldTicks(market);
  });
}

function pruneOldTicks(market) {
  const newest = market.ticks[market.ticks.length - 1].time;
  const cutoff = newest - HISTORY_MS;
  while (market.ticks.length > 0 && market.ticks[0].time < cutoff) {
    market.ticks.shift();
  }
}

function buildCandlesFromTicks(market, timeframe) {
  const latest = market.ticks[market.ticks.length - 1];
  const visibleCandles = getVisibleCandleCount(timeframe);
  const lookback = Math.min(HISTORY_MS, timeframe.ms * visibleCandles);
  const startTime = latest.time - lookback;
  const startIndex = findFirstTickIndex(market.ticks, startTime);
  const candles = [];
  let current = null;

  for (let index = startIndex; index < market.ticks.length; index += 1) {
    const tick = market.ticks[index];
    const bucket = Math.floor(tick.time / timeframe.ms) * timeframe.ms;

    if (!current || current.time !== bucket) {
      current = {
        time: bucket,
        open: tick.price,
        high: tick.high,
        low: tick.low,
        close: tick.price,
        volume: tick.volume,
        final: latest.time >= bucket + timeframe.ms,
      };
      candles.push(current);
    } else {
      current.high = Math.max(current.high, tick.high);
      current.low = Math.min(current.low, tick.low);
      current.close = tick.price;
      current.volume += tick.volume;
      current.final = latest.time >= current.time + timeframe.ms;
    }
  }

  if (candles.length > visibleCandles) {
    return candles.slice(-visibleCandles);
  }

  return candles;
}

function getVisibleCandleCount(timeframe) {
  return Math.min(timeframe.visibleCandles || 72, Math.ceil(HISTORY_MS / timeframe.ms));
}

function findFirstTickIndex(ticks, startTime) {
  let low = 0;
  let high = ticks.length;

  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (ticks[mid].time < startTime) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }

  return low;
}

function floorToSecond(timestamp) {
  return Math.floor(timestamp / BASE_TICK_MS) * BASE_TICK_MS;
}

function formatPrice(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function relativeTime(timestamp) {
  const diff = Math.max(1, Date.now() - timestamp);
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.floor(hours / 24)} day ago`;
}

function getSelectedMarket() {
  return state.markets[state.selectedAsset];
}

function getSelectedTimeframe() {
  return TIMEFRAMES.find((timeframe) => timeframe.id === state.selectedTimeframe) || TIMEFRAMES[3];
}

function getCurrentCandles() {
  return buildCandlesFromTicks(getSelectedMarket(), getSelectedTimeframe());
}

function routeTo(route) {
  state.route = route;
  state.lastError = "";
  state.successMessage = "";
  render();
}

function loginAsGuest() {
  const user = { id: "guest", name: "Guest User", email: "guest@tickframe.local" };
  state.user = user;
  writeSession(user);
  seedAlerts(user.id);
  state.route = "dashboard";
  render();
}

function loginWithDemo(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const email = String(form.get("email") || "").trim();
  const password = String(form.get("password") || "");

  if (email === DEMO_USER.email && password === DEMO_USER.password) {
    const user = { id: DEMO_USER.id, name: DEMO_USER.name, email: DEMO_USER.email };
    state.user = user;
    writeSession(user);
    seedAlerts(user.id);
    state.route = "dashboard";
    state.lastError = "";
    render();
    return;
  }

  state.lastError = "Invalid demo credentials. Use demo@tickframe.local / demo123.";
  render();
}

function logout() {
  localStorage.removeItem("tickframe.session");
  state.user = null;
  state.route = "login";
  render();
}

function createAlert(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const threshold = Number(form.get("threshold"));
  const methods = form.getAll("methods").map(String);

  if (!Number.isFinite(threshold) || threshold < 1 || threshold > 100) {
    state.lastError = "Confidence threshold must be between 1 and 100.";
    render();
    return;
  }

  if (methods.length === 0) {
    state.lastError = "Choose at least one notification method.";
    render();
    return;
  }

  const alert = {
    id: `alert-${Date.now()}`,
    asset: String(form.get("asset")),
    type: String(form.get("type")),
    threshold,
    method: methods.join(", "),
    status: "Active",
    createdAt: Date.now(),
  };

  writeAlerts([alert, ...readAlerts()]);
  state.successMessage = "Pattern alert was created and saved to this user profile.";
  state.route = "success";
  render();
}

function deleteAlert(alertId) {
  writeAlerts(readAlerts().filter((alert) => alert.id !== alertId));
  render();
}

function render() {
  const app = document.querySelector("#app");
  if (state.route === "login") {
    app.innerHTML = renderLogin();
    document.querySelector("#login-form").addEventListener("submit", loginWithDemo);
    document.querySelector("#guest-button").addEventListener("click", loginAsGuest);
    return;
  }

  if (state.route === "success") {
    app.innerHTML = renderShell(renderSuccess());
    bindShellEvents();
    document.querySelector("#continue-button").addEventListener("click", () => routeTo("alerts"));
    return;
  }

  app.innerHTML = renderShell(state.route === "alerts" ? renderAlerts() : state.route === "create-alert" ? renderCreateAlert() : renderDashboard());
  bindShellEvents();

  if (state.route === "create-alert") {
    document.querySelector("#create-alert-form").addEventListener("submit", createAlert);
    const confidenceInput = document.querySelector("#confidence-range");
    const confidenceValue = document.querySelector("#confidence-value");
    confidenceInput.addEventListener("input", () => {
      confidenceValue.textContent = `${confidenceInput.value}%`;
    });
  }
}

function bindShellEvents() {
  document.querySelectorAll("[data-route]").forEach((element) => {
    element.addEventListener("click", () => routeTo(element.dataset.route));
  });
  document.querySelectorAll("[data-timeframe]").forEach((element) => {
    element.addEventListener("click", () => {
      state.selectedTimeframe = element.dataset.timeframe;
      render();
    });
  });
  document.querySelectorAll("[data-delete-alert]").forEach((element) => {
    element.addEventListener("click", () => {
      deleteAlert(element.dataset.deleteAlert);
    });
  });
  document.querySelector("#logout-button").addEventListener("click", logout);
}

function renderLogin() {
  return `
    <main class="login-page">
      <section class="brand-panel">
        <div class="logo-mark">T</div>
        <div>
          <h1>TICKFRAME</h1>
          <p>Crypto Pattern Analytics</p>
        </div>
        <div class="hero-chart">${renderMiniChart(getCurrentCandles().map((candle) => candle.close).slice(-34), "large")}</div>
      </section>
      <section class="login-card">
        <h2>Welcome Back</h2>
        <p>Sign in to continue to Tickframe</p>
        <form id="login-form">
          <label>Email
            <input name="email" value="demo@tickframe.local" autocomplete="username" />
          </label>
          <label>Password
            <input name="password" type="password" value="demo123" autocomplete="current-password" />
          </label>
          ${state.lastError ? `<div class="error-message">${state.lastError}</div>` : ""}
          <button class="primary-button" type="submit">Sign In</button>
        </form>
        <div class="divider">or</div>
        <button id="guest-button" class="secondary-button" type="button">Continue as Guest</button>
        <p class="hint">Demo only: user-scoped alerts are stored in localStorage.</p>
      </section>
    </main>
  `;
}

function renderShell(content) {
  return `
    <main class="app-shell">
      <aside class="sidebar">
        <div class="brand-row">
          <div class="logo-mark small">T</div>
          <strong>TICKFRAME</strong>
        </div>
        <nav>
          <button data-route="dashboard" class="${state.route === "dashboard" ? "active" : ""}">Dashboard</button>
          <button data-route="alerts" class="${state.route === "alerts" ? "active" : ""}">Alerts <span>${readAlerts().filter((alert) => alert.status === "Active").length}</span></button>
          <button data-route="create-alert" class="${state.route === "create-alert" ? "active" : ""}">Create Alert</button>
        </nav>
        <button id="logout-button" class="logout-button">Log out</button>
      </aside>
      <section class="main-panel">
        <header class="topbar">
          <div class="asset-lock" aria-label="Selected asset">BTC/USDT</div>
          <div class="user-pill">${state.user.name}</div>
        </header>
        ${content}
      </section>
    </main>
  `;
}

function renderDashboard() {
  const alerts = readAlerts();
  const activeAlerts = alerts.filter((alert) => alert.status === "Active").slice(0, 3);
  const market = getSelectedMarket();
  const asset = market.asset;
  const candles = getCurrentCandles();
  const latest = candles[candles.length - 1];
  const first = candles[0];
  const change = ((latest.close - first.open) / first.open) * 100;
  const high = Math.max(...candles.map((candle) => candle.high));
  const low = Math.min(...candles.map((candle) => candle.low));
  return `
    <section class="dashboard-grid">
      <div class="market-card asset-card">
        <div class="asset-heading">
          <div class="coin">${asset.icon}</div>
          <div>
            <h2>${asset.symbol}</h2>
            <p>${asset.name}</p>
          </div>
          <div class="price-block">
            <strong>${formatPrice(latest.close)}</strong>
            <span class="${change >= 0 ? "positive" : "negative"}">${change >= 0 ? "+" : ""}${change.toFixed(2)}% (${state.selectedTimeframe})</span>
          </div>
        </div>
        <div class="stats-row">
          <span>Range High <strong>${formatPrice(high)}</strong></span>
          <span>Range Low <strong>${formatPrice(low)}</strong></span>
          <span>Market Cap <strong>${asset.marketCap}</strong></span>
          <span>Supply <strong>${asset.supply}</strong></span>
        </div>
      </div>

      <div class="chart-card">
        <div class="toolbar">
          ${TIMEFRAMES.map((timeframe) => `<button data-timeframe="${timeframe.id}" class="${timeframe.id === state.selectedTimeframe ? "active" : ""}">${timeframe.label}</button>`).join("")}
          <button>Indicators</button>
        </div>
        ${renderMainChart(candles, asset)}
      </div>

      <div class="pattern-card">
        <p>Current Pattern</p>
        <h3>${asset.pattern}</h3>
        ${renderPatternIcon(asset.pattern)}
        <div class="confidence">
          <span>Confidence Score</span>
          <strong>${asset.confidence}%</strong>
          <div><i style="width:${asset.confidence}%"></i></div>
        </div>
        <div class="confidence">
          <span>Hit Rate</span>
          <strong>${asset.hitRate}%</strong>
          <div><i style="width:${asset.hitRate}%"></i></div>
        </div>
      </div>

      <div class="metric-row">
        ${renderMetric("RSI (14)", "61.2", "Neutral")}
        ${renderMetric("MACD", "Bullish", "Signal")}
        ${renderMetric("EMA Trend", "Uptrend", "Trend")}
        ${renderMetric("Volume", asset.volume, "Current")}
        ${renderMetric("Volatility", asset.volatility, "Realized")}
      </div>

      <div class="signal-feed">
        <div class="section-heading">
          <h3>Recent Alerts</h3>
          <button data-route="alerts">View all</button>
        </div>
        ${activeAlerts.map(renderFeedItem).join("") || renderEmptyFeed()}
      </div>

      <div class="opportunities">
        <div class="section-heading">
          <h3>BTC Timeframe Snapshots</h3>
          <button data-route="alerts">Alerts</button>
        </div>
        ${["1m", "15m", "1h"].map((timeframeId, index) => renderOpportunity("BTC/USDT", timeframeId, 91 - index * 7, 75 - index * 3)).join("")}
      </div>
    </section>
  `;
}

function renderAlerts() {
  const alerts = readAlerts();
  return `
    <section class="alerts-page">
      <div class="section-heading page-heading">
        <h2>Alerts</h2>
        <button class="primary-button small-button" data-route="create-alert">+ Create Alert</button>
      </div>
      <div class="alert-list">
        ${alerts.map(renderAlertRow).join("") || renderNoAlerts()}
      </div>
    </section>
  `;
}

function renderCreateAlert() {
  return `
    <section class="form-page">
      <div class="form-card">
        <h2>Create New Alert</h2>
        <p class="form-intro">Configure the alert inputs used by the smoke check. This is mock behavior, but the selected values are saved to this user.</p>
        ${state.lastError ? `<div class="error-message">${state.lastError}</div>` : ""}
        <form id="create-alert-form">
          <input type="hidden" name="asset" value="BTC/USDT" />
          <div class="fixed-field">
            <span>Coin / Pair</span>
            <strong>BTC/USDT</strong>
          </div>
          <label>Alert Type
            <select name="type">
              <option>Pattern Detected</option>
              <option>Confidence > 80%</option>
              <option>Volume Spike</option>
              <option>Volatility Shift</option>
              <option>RSI Oversold</option>
              <option>MACD Bullish Crossover</option>
            </select>
          </label>
          <div class="range-field">
            <div class="range-heading">
              <label for="confidence-range">Confidence Rate</label>
              <strong id="confidence-value">80%</strong>
            </div>
            <input id="confidence-range" name="threshold" type="range" min="1" max="100" value="80" />
          </div>
          <fieldset class="method-fieldset">
            <legend>Notification Method</legend>
            <label class="choice-row">
              <input name="methods" type="checkbox" value="In-App Notification" checked />
              <span>In-App Notification</span>
            </label>
            <label class="choice-row">
              <input name="methods" type="checkbox" value="Email" />
              <span>Email</span>
            </label>
            <label class="choice-row">
              <input name="methods" type="checkbox" value="SMS" />
              <span>SMS</span>
            </label>
          </fieldset>
          <button class="primary-button" type="submit">Create Alert</button>
        </form>
      </div>
    </section>
  `;
}

function renderSuccess() {
  return `
    <section class="state-page">
      <div class="success-orb">OK</div>
      <h2>Success!</h2>
      <p>${state.successMessage || "The alert was created."}</p>
      <button id="continue-button" class="success-button">Continue</button>
    </section>
  `;
}

function renderMetric(label, value, caption) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong><small>${caption}</small></div>`;
}

function renderFeedItem(alert) {
  return `
    <div class="feed-item">
      <i></i>
      <strong>${alert.asset}</strong>
      <span>${alert.type}</span>
      <time>${relativeTime(alert.createdAt)}</time>
    </div>
  `;
}

function renderAlertRow(alert) {
  const isActive = alert.status === "Active";
  return `
    <article class="alert-row">
      <div class="alert-icon ${isActive ? "" : "muted"}">${isActive ? "^" : "x"}</div>
      <div>
        <h3>${alert.asset}</h3>
        <p>${alert.type} - Threshold ${alert.threshold}%</p>
        <small>${relativeTime(alert.createdAt)} - ${alert.method}</small>
      </div>
      <div class="alert-actions">
        <span class="${isActive ? "status-active" : "status-inactive"}">${alert.status}</span>
        <button type="button" class="delete-alert-button" data-delete-alert="${alert.id}">Delete</button>
      </div>
    </article>
  `;
}

function renderOpportunity(asset, timeframeId, confidence, hitRate) {
  const market = state.markets[asset];
  const timeframe = TIMEFRAMES.find((item) => item.id === timeframeId) || getSelectedTimeframe();
  const candles = buildCandlesFromTicks(market, timeframe);
  return `
    <article class="opportunity-card">
      <div>
        <strong>${asset}</strong>
        <small>${timeframe.label} snapshot</small>
        <small>Confidence</small>
        <b>${confidence}%</b>
      </div>
      ${renderMiniChart(candles.map((candle) => candle.close).slice(-18), "small")}
      <div>
        <small>Hit Rate</small>
        <b>${hitRate}%</b>
      </div>
    </article>
  `;
}

function renderEmptyFeed() {
  return `<p class="empty-text">No alerts yet. Create one to populate the signal feed.</p>`;
}

function renderNoAlerts() {
  return `
    <div class="empty-state">
      <div class="empty-icon">?</div>
      <h3>No alerts yet</h3>
      <p>Create a pattern alert to start monitoring market signals.</p>
      <button data-route="create-alert" class="primary-button small-button">Create Alert</button>
    </div>
  `;
}

function renderMainChart(candles, asset) {
  const width = 860;
  const height = 310;
  const chartLeft = 34;
  const chartRight = 730;
  const chartTop = 18;
  const chartBottom = 218;
  const volumeTop = 232;
  const volumeBottom = 272;
  const timeLabelY = 296;
  const priceAxisX = 750;
  const rawMin = Math.min(...candles.map((candle) => candle.low));
  const rawMax = Math.max(...candles.map((candle) => candle.high));
  const timeframe = getSelectedTimeframe();
  const latest = candles[candles.length - 1];
  const scale = getPriceScale(rawMin, rawMax, latest.close, asset, timeframe);
  const min = scale.min;
  const max = scale.max;
  const maxVolume = Math.max(...candles.map((candle) => candle.volume));
  const spread = Math.max(1, max - min);
  const step = (chartRight - chartLeft) / candles.length;
  const candleWidth = clamp(step * 0.68, 8, 22);
  const yFor = (value) => chartTop + (1 - (value - min) / spread) * (chartBottom - chartTop);
  const priceTicks = scale.ticks.map((value) => {
    const y = yFor(value);
    return `
      <line x1="${chartLeft}" y1="${y.toFixed(2)}" x2="${chartRight}" y2="${y.toFixed(2)}" stroke="#142536" stroke-width="1" />
      <text x="${priceAxisX}" y="${(y + 4).toFixed(2)}" fill="#7f91a5" font-size="12">${formatAxisPrice(value)}</text>
    `;
  }).join("");
  const timeTicks = [0, 0.25, 0.5, 0.75, 1].map((position) => {
    const candleIndex = Math.min(candles.length - 1, Math.round(position * (candles.length - 1)));
    const x = chartLeft + candleIndex * step + step / 2;
    return `
      <line x1="${x.toFixed(2)}" y1="${chartBottom}" x2="${x.toFixed(2)}" y2="${volumeBottom}" stroke="#142536" stroke-width="1" opacity="0.45" />
      <text x="${(x - 22).toFixed(2)}" y="${timeLabelY}" fill="#7f91a5" font-size="12">${formatAxisTime(candles[candleIndex].time, timeframe)}</text>
    `;
  }).join("");
  const bodies = candles
    .map((candle, index) => {
      const x = chartLeft + index * step + step / 2;
      const openY = yFor(candle.open);
      const closeY = yFor(candle.close);
      const highY = yFor(candle.high);
      const lowY = yFor(candle.low);
      const up = candle.close >= candle.open;
      const color = up ? "#16c784" : "#ef4444";
      const isLive = index === candles.length - 1 && !candle.final;
      const bodyY = Math.min(openY, closeY);
      const bodyHeight = Math.max(8, Math.abs(closeY - openY));
      const volumeHeight = Math.max(5, (candle.volume / maxVolume) * (volumeBottom - volumeTop));
      return `
        <line x1="${x.toFixed(2)}" y1="${highY.toFixed(2)}" x2="${x.toFixed(2)}" y2="${lowY.toFixed(2)}" stroke="${color}" stroke-width="2.6" opacity="0.98" />
        <rect x="${(x - candleWidth / 2).toFixed(2)}" y="${bodyY.toFixed(2)}" width="${candleWidth.toFixed(2)}" height="${bodyHeight.toFixed(2)}" rx="2" fill="${color}" stroke="${isLive ? "#edf5ff" : color}" stroke-width="${isLive ? 1.5 : 0}" />
        <rect x="${(x - candleWidth / 2).toFixed(2)}" y="${(volumeBottom - volumeHeight).toFixed(2)}" width="${candleWidth.toFixed(2)}" height="${volumeHeight.toFixed(2)}" rx="2" fill="${color}" opacity="0.45" />
      `;
    })
    .join("");
  const currentPriceY = yFor(latest.close);
  const closesIn = formatDuration(getCandleCloseRemaining(latest.time, timeframe));

  return `
    <svg class="main-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${asset.symbol} moving candlestick chart">
      <rect x="${chartLeft}" y="${chartTop}" width="${chartRight - chartLeft}" height="${volumeBottom - chartTop}" rx="6" fill="#07111b" opacity="0.35" />
      ${priceTicks}
      ${timeTicks}
      ${bodies}
      <line x1="${chartLeft}" y1="${volumeTop}" x2="${chartRight}" y2="${volumeTop}" stroke="#142536" stroke-width="1" />
      <line x1="${chartLeft}" y1="${currentPriceY.toFixed(2)}" x2="${chartRight}" y2="${currentPriceY.toFixed(2)}" stroke="#16c784" stroke-dasharray="4 5" opacity="0.75" />
      <rect x="${priceAxisX - 4}" y="${(currentPriceY - 12).toFixed(2)}" width="86" height="24" rx="5" fill="#10251f" stroke="#16c784" />
      <text x="${priceAxisX + 3}" y="${(currentPriceY + 4).toFixed(2)}" fill="#16c784" font-size="12">${formatAxisPrice(latest.close)}</text>
      <text x="${chartLeft}" y="16" fill="#7f91a5" font-size="12">30d synthetic tick history - ${state.selectedTimeframe} candles - price step ${formatAxisPrice(scale.step)}</text>
      <text x="${chartRight - 132}" y="16" fill="#edf5ff" font-size="12">current closes in ${closesIn}</text>
    </svg>
  `;
}

function getCandleCloseRemaining(time, timeframe) {
  const bucket = Math.floor(time / timeframe.ms) * timeframe.ms;
  const elapsed = time - bucket;
  return Math.max(BASE_TICK_MS, timeframe.ms - elapsed);
}

function formatDuration(ms) {
  const seconds = Math.ceil(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const restSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${restSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const restMinutes = minutes % 60;
  return `${hours}h ${restMinutes}m`;
}

function getPriceScale(rawMin, rawMax, currentPrice, asset, timeframe) {
  let step = getPriceStep(asset, timeframe);
  const distanceFromCurrent = Math.max(Math.abs(currentPrice - rawMin), Math.abs(rawMax - currentPrice));
  let halfRange = Math.ceil(Math.max(distanceFromCurrent * 1.08, step * 6) / step) * step;
  const maxTicks = timeframe.id === "15m" || timeframe.id === "1h" ? 24 : 18;

  while ((halfRange * 2) / step > maxTicks) {
    step *= 2;
    halfRange = Math.ceil(Math.max(distanceFromCurrent * 1.08, step * 6) / step) * step;
  }

  const min = currentPrice - halfRange;
  const max = currentPrice + halfRange;

  const ticks = [];
  for (let value = max; value >= min - step * 0.25; value -= step) {
    ticks.push(value);
  }

  return { min, max, step, ticks };
}

function getPriceStep(asset, timeframe) {
  if (asset.symbol === "BTC/USDT") {
    return timeframe.btcPriceStep;
  }

  const baseStep = asset.basePrice * (timeframe.ms / 60000) * 0.0014;
  return nicePriceStep(Math.max(asset.basePrice * 0.0005, baseStep));
}

function nicePriceStep(value) {
  const exponent = Math.floor(Math.log10(value));
  const power = 10 ** exponent;
  const scaled = value / power;

  if (scaled <= 1) return power;
  if (scaled <= 2) return 2 * power;
  if (scaled <= 5) return 5 * power;
  return 10 * power;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function renderPatternOverlay(pattern, chartLeft, chartRight, chartTop, chartBottom, yFor, min, max) {
  const range = max - min;
  const x1 = chartLeft + 42;
  const x2 = chartRight - 58;
  const mid = (x1 + x2) / 2;
  const topLine = yFor(max - range * 0.22);
  const midLine = yFor(max - range * 0.47);
  const lowLine = yFor(min + range * 0.24);

  if (pattern === "Ascending Triangle") {
    return `
      <path d="M ${x1} ${topLine} L ${x2} ${topLine}" stroke="#7c4dff" stroke-width="2" stroke-dasharray="6 5" fill="none" />
      <path d="M ${x1} ${chartBottom - 30} L ${x2} ${topLine}" stroke="#16c784" stroke-width="2" fill="none" />
      <text x="${x1 + 8}" y="${topLine - 8}" fill="#16c784" font-size="12">ascending triangle</text>
    `;
  }

  if (pattern === "Bull Flag") {
    return `
      <path d="M ${x1} ${chartBottom - 24} L ${x1 + 120} ${chartTop + 36}" stroke="#16c784" stroke-width="2" fill="none" />
      <path d="M ${x1 + 140} ${chartTop + 48} L ${x2} ${chartTop + 78}" stroke="#7c4dff" stroke-width="2" fill="none" />
      <path d="M ${x1 + 140} ${chartTop + 84} L ${x2} ${chartTop + 114}" stroke="#7c4dff" stroke-width="2" fill="none" />
      <text x="${x1 + 150}" y="${chartTop + 42}" fill="#16c784" font-size="12">bull flag</text>
    `;
  }

  if (pattern === "Double Bottom") {
    return `
      <path d="M ${x1} ${midLine} Q ${x1 + 70} ${lowLine} ${mid - 24} ${midLine} Q ${mid + 76} ${lowLine} ${x2} ${midLine}" stroke="#16c784" stroke-width="2" fill="none" />
      <circle cx="${x1 + 70}" cy="${lowLine}" r="14" stroke="#7c4dff" stroke-width="2" fill="none" />
      <circle cx="${mid + 76}" cy="${lowLine}" r="14" stroke="#7c4dff" stroke-width="2" fill="none" />
      <text x="${x1 + 54}" y="${lowLine + 34}" fill="#16c784" font-size="12">double bottom</text>
    `;
  }

  if (pattern === "Head and Shoulders") {
    return `
      <path d="M ${x1} ${midLine} L ${x1 + 88} ${topLine + 26} L ${mid} ${chartTop + 32} L ${x2 - 88} ${topLine + 26} L ${x2} ${midLine}" stroke="#16c784" stroke-width="2" fill="none" />
      <path d="M ${x1} ${midLine + 26} L ${x2} ${midLine + 26}" stroke="#7c4dff" stroke-width="2" stroke-dasharray="6 5" />
      <text x="${mid - 70}" y="${chartTop + 24}" fill="#16c784" font-size="12">head and shoulders</text>
    `;
  }

  if (pattern === "Volume Spike") {
    return `
      <rect x="${x2 - 80}" y="${chartTop + 24}" width="56" height="${chartBottom - chartTop - 32}" fill="#16c784" opacity="0.09" />
      <path d="M ${x1} ${midLine + 22} L ${x2 - 90} ${midLine + 10} L ${x2 - 20} ${topLine}" stroke="#16c784" stroke-width="2" fill="none" />
      <text x="${x2 - 112}" y="${chartTop + 18}" fill="#16c784" font-size="12">volume spike</text>
    `;
  }

  return `
    <rect x="${mid - 70}" y="${chartTop + 18}" width="140" height="${chartBottom - chartTop - 36}" fill="#7c4dff" opacity="0.08" />
    <path d="M ${x1} ${midLine} C ${mid - 80} ${topLine} ${mid + 80} ${lowLine} ${x2} ${midLine - 18}" stroke="#16c784" stroke-width="2" fill="none" />
    <text x="${mid - 44}" y="${chartTop + 34}" fill="#16c784" font-size="12">volatility shift</text>
  `;
}

function formatAxisPrice(value) {
  if (value >= 1000) return `$${Math.round(value).toLocaleString("en-US")}`;
  if (value >= 10) return `$${Math.round(value).toLocaleString("en-US")}`;
  if (value >= 1) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
}

function formatAxisTime(timestamp, timeframe) {
  const date = new Date(timestamp);
  if (timeframe.ms >= 86400000) {
    return `${date.getMonth() + 1}/${date.getDate()}`;
  }
  return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function renderMiniChart(points, size) {
  const width = size === "large" ? 300 : 130;
  const height = size === "large" ? 170 : 46;
  return `<svg class="mini-chart ${size}" viewBox="0 0 ${width} ${height}" aria-hidden="true"><path d="${buildPath(points, width, height, 8)}" fill="none" stroke="#16c784" stroke-width="${size === "large" ? 4 : 2}" /></svg>`;
}

function renderPatternIcon() {
  return `
    <svg class="pattern-icon" viewBox="0 0 220 110" aria-hidden="true">
      <path d="M16 84 L64 20 L108 70 L202 18" fill="none" stroke="#16c784" stroke-width="4" />
      <path d="M28 88 L202 26" stroke="#5b35d5" stroke-width="3" />
      <path d="M54 25 L205 18 L105 72 Z" fill="none" stroke="#16c784" stroke-width="2" opacity="0.65" />
    </svg>
  `;
}

function buildPath(points, width, height, padding) {
  const min = Math.min(...points);
  const max = Math.max(...points);
  const spread = Math.max(1, max - min);
  return points
    .map((value, index) => {
      const x = padding + (index / (points.length - 1)) * (width - padding * 2);
      const y = padding + (1 - (value - min) / spread) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

render();
