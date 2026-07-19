import {
  type PointerEvent as ReactPointerEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { CanvasRenderingTarget2D } from "fancy-canvas";
import {
  CandlestickChart,
  Camera,
  ChartArea,
  ChartLine,
  ChartNoAxesCombined,
  ChartSpline,
  ClipboardPaste,
  Copy,
  CopyPlus,
  Ellipsis,
  Eraser,
  Expand,
  Grid3X3,
  History,
  Maximize2,
  Minus,
  MousePointer2,
  PencilRuler,
  Ruler,
  ScanLine,
  Square,
  Trash2,
  TrendingUp,
  Undo2,
  Volume2,
  type LucideIcon,
} from "lucide-react";
import {
  AreaSeries,
  BarSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  PriceScaleMode,
  createChart,
  type AutoscaleInfo,
  type Coordinate,
  type IChartApi,
  type IPriceLine,
  type IPrimitivePaneRenderer,
  type IPrimitivePaneView,
  type ISeriesApi,
  type ISeriesPrimitive,
  type Logical,
  type MouseEventParams,
  type SeriesAttachedParameter,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import type { DisplayCandle } from "../types";
import { safeStorageGet, safeStorageSet } from "../storage";
import {
  bollingerBands,
  exponentialMovingAverage,
  rollingVwap,
  simpleMovingAverage,
} from "../chart-indicators";

export interface ChartAlertLine {
  id: string;
  label: string;
  price: number;
  tone: "above" | "below";
}

export interface ChartPatternLine {
  id: string;
  points: [
    {
      time: number;
      price: number;
    },
    {
      time: number;
      price: number;
    },
  ];
}

interface MarketChartProps {
  candles: DisplayCandle[];
  scopeKey: string;
  loading: boolean;
  historyLoading: boolean;
  hasMore: boolean;
  onLoadEarlier: () => void;
  alertLines?: ChartAlertLine[];
  patternLines?: ChartPatternLine[];
}

type ChartMode = "candles" | "bars" | "line" | "area";
type IndicatorId = "ema20" | "sma50" | "bollinger20" | "vwap100";
type DrawingTool = "cursor" | "trend" | "rect" | "level" | "vertical" | "fib" | "measure";
type DrawingType = Exclude<DrawingTool, "cursor">;
type PriceLineSeries =
  | ISeriesApi<"Candlestick">
  | ISeriesApi<"Bar">
  | ISeriesApi<"Line">
  | ISeriesApi<"Area">;

interface DrawingPoint {
  time: UTCTimestamp;
  price: number;
}

interface ChartDrawing {
  id: string;
  type: DrawingType;
  points: DrawingPoint[];
}

interface ViewPoint {
  x: Coordinate | null;
  y: Coordinate | null;
}

interface PrimitiveStyle {
  color: string;
  fillColor: string;
  preview: boolean;
  precision: number;
  selected: boolean;
  showPoints?: boolean;
  lineWidth?: number;
}

interface ScreenPoint {
  x: number;
  y: number;
}

interface PointerChartPoint extends ScreenPoint {
  point: DrawingPoint;
}

interface DrawingHit {
  drawing: ChartDrawing;
  action: "move" | "point";
  pointIndex?: number;
}

interface DrawingEditSession {
  drawingId: string;
  action: "move" | "point";
  pointIndex?: number;
  startPoint: DrawingPoint;
  originalDrawing: ChartDrawing;
}

const DEFAULT_VISIBLE_BARS = 120;
const INDICATOR_MAX_BARS = 5_000;
const DRAWINGS_STORAGE_PREFIX = "tickframe.chartDrawings.v2:";
const CHART_PREFERENCES_STORAGE_KEY = "tickframe.chartPreferences.v2";
const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];

const DRAWING_TOOLS: Array<{
  id: DrawingTool;
  label: string;
  title: string;
}> = [
  { id: "cursor", label: "Cursor", title: "Pan, zoom, and inspect candles" },
  { id: "trend", label: "Trend", title: "Draw a trend line" },
  { id: "rect", label: "Rect", title: "Draw a range rectangle" },
  { id: "level", label: "Level", title: "Place a price level" },
  { id: "vertical", label: "VLine", title: "Place a vertical time marker" },
  { id: "fib", label: "Fib", title: "Draw Fibonacci retracement levels" },
  { id: "measure", label: "Ruler", title: "Measure price and time distance" },
];

const CHART_MODES: Array<{ id: ChartMode; label: string }> = [
  { id: "candles", label: "Candles" },
  { id: "bars", label: "Bars" },
  { id: "line", label: "Line" },
  { id: "area", label: "Area" },
];

const DRAWING_TOOL_ICONS: Record<DrawingTool, LucideIcon> = {
  cursor: MousePointer2,
  trend: TrendingUp,
  rect: Square,
  level: Minus,
  vertical: ScanLine,
  fib: ChartSpline,
  measure: Ruler,
};

const CHART_MODE_ICONS: Record<ChartMode, LucideIcon> = {
  candles: CandlestickChart,
  bars: ChartNoAxesCombined,
  line: ChartLine,
  area: ChartArea,
};

interface ChartPreferences {
  chartMode: ChartMode;
  indicators: Record<IndicatorId, boolean>;
  logarithmicScale: boolean;
  magnetCrosshair: boolean;
  showGrid: boolean;
  showVolume: boolean;
}

const DEFAULT_CHART_PREFERENCES: ChartPreferences = {
  chartMode: "candles",
  indicators: {
    ema20: false,
    sma50: false,
    bollinger20: false,
    vwap100: false,
  },
  logarithmicScale: false,
  magnetCrosshair: true,
  showGrid: true,
  showVolume: true,
};

const INDICATORS: Array<{
  id: IndicatorId;
  label: string;
  detail: string;
  color: string;
}> = [
  { id: "ema20", label: "EMA 20", detail: "Fast trend", color: "#f6c86b" },
  { id: "sma50", label: "SMA 50", detail: "Structure", color: "#63d8ff" },
  {
    id: "bollinger20",
    label: "Bollinger 20",
    detail: "2 standard deviations",
    color: "#b9aaff",
  },
  { id: "vwap100", label: "VWAP 100", detail: "Volume weighted", color: "#5df2b5" },
];

function loadChartPreferences(): ChartPreferences {
  try {
    const raw = safeStorageGet(CHART_PREFERENCES_STORAGE_KEY);
    if (!raw) return DEFAULT_CHART_PREFERENCES;
    const parsed = JSON.parse(raw) as Partial<ChartPreferences>;
    const chartMode = CHART_MODES.some((mode) => mode.id === parsed.chartMode)
      ? parsed.chartMode as ChartMode
      : DEFAULT_CHART_PREFERENCES.chartMode;
    return {
      chartMode,
      indicators: {
        ...DEFAULT_CHART_PREFERENCES.indicators,
        ...(parsed.indicators ?? {}),
      },
      logarithmicScale: parsed.logarithmicScale === true,
      magnetCrosshair: parsed.magnetCrosshair !== false,
      showGrid: parsed.showGrid !== false,
      showVolume: parsed.showVolume !== false,
    };
  } catch {
    return DEFAULT_CHART_PREFERENCES;
  }
}

function volumeColor(candle: DisplayCandle): string {
  return candle.close >= candle.open
    ? "rgba(53, 229, 138, 0.26)"
    : "rgba(255, 78, 103, 0.24)";
}

function candleSignature(candle: DisplayCandle): string {
  return [
    candle.time,
    candle.open,
    candle.high,
    candle.low,
    candle.close,
    candle.volume,
  ].join(":");
}

function pricePrecision(value: number): number {
  if (value >= 1000) return 2;
  if (value >= 1) return 4;
  if (value >= 0.01) return 5;
  return 8;
}

function formatChartPrice(value: number, precision: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: Math.min(precision, 2),
    maximumFractionDigits: Math.min(precision, 6),
  });
}

function formatCompact(value: number): string {
  return Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function createDrawingId(): string {
  return `drawing-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function drawingStorageKey(scopeKey: string): string {
  return `${DRAWINGS_STORAGE_PREFIX}${scopeKey}`;
}

function isDrawingType(value: unknown): value is DrawingType {
  return (
    typeof value === "string" &&
    DRAWING_TOOLS.some((tool) => tool.id === value && tool.id !== "cursor")
  );
}

function loadStoredDrawings(scopeKey: string): ChartDrawing[] {
  try {
    const raw = safeStorageGet(drawingStorageKey(scopeKey));
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((value): value is ChartDrawing => {
      if (!value || typeof value !== "object") return false;
      const drawing = value as Partial<ChartDrawing>;
      if (
        typeof drawing.id !== "string" ||
        !isDrawingType(drawing.type) ||
        !Array.isArray(drawing.points)
      ) {
        return false;
      }
      const requiredPoints =
        drawing.type === "level" || drawing.type === "vertical" ? 1 : 2;
      return (
        drawing.points.length >= requiredPoints &&
        drawing.points.every(
          (point) =>
            Boolean(point) &&
            Number.isFinite(point.time) &&
            Number.isFinite(point.price),
        )
      );
    });
  } catch {
    return [];
  }
}

function closestCandle(candles: DisplayCandle[], time: number): DisplayCandle | null {
  if (candles.length === 0) return null;
  return candles.reduce((best, candle) =>
    Math.abs(candle.time - time) < Math.abs(best.time - time) ? candle : best,
  );
}

function scaledCoordinate(value: Coordinate | number, pixelRatio: number): number {
  return Math.round(Number(value) * pixelRatio);
}

function distanceBetween(first: ScreenPoint, second: ScreenPoint): number {
  return Math.hypot(first.x - second.x, first.y - second.y);
}

function distanceToSegment(point: ScreenPoint, start: ScreenPoint, end: ScreenPoint): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return distanceBetween(point, start);
  const t = Math.max(
    0,
    Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSquared),
  );
  return distanceBetween(point, {
    x: start.x + t * dx,
    y: start.y + t * dy,
  });
}

function isInsideRect(point: ScreenPoint, first: ScreenPoint, second: ScreenPoint): boolean {
  const left = Math.min(first.x, second.x);
  const right = Math.max(first.x, second.x);
  const top = Math.min(first.y, second.y);
  const bottom = Math.max(first.y, second.y);
  return point.x >= left && point.x <= right && point.y >= top && point.y <= bottom;
}

function drawingLabel(drawing: ChartDrawing | null): string {
  if (!drawing) return "No selection";
  if (drawing.type === "rect") return "Rectangle selected";
  if (drawing.type === "level") return "Level selected";
  if (drawing.type === "vertical") return "Vertical line selected";
  if (drawing.type === "fib") return "Fib selected";
  if (drawing.type === "measure") return "Ruler selected";
  return "Trend selected";
}

function isEditableKeyboardTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
  );
}

function moveDrawing(
  drawing: ChartDrawing,
  timeDelta: number,
  priceDelta: number,
): ChartDrawing {
  return {
    ...drawing,
    points: drawing.points.map((point) => ({
      time: Math.max(0, Math.round(Number(point.time) + timeDelta)) as UTCTimestamp,
      price: point.price + priceDelta,
    })),
  };
}

function candleTimeStep(candles: DisplayCandle[]): number {
  if (candles.length < 2) return 60;
  const last = candles[candles.length - 1];
  const previous = candles[candles.length - 2];
  return Math.max(1, last.time - previous.time);
}

function visiblePriceRange(candles: DisplayCandle[], drawing: ChartDrawing): number {
  const candlePrices = candles.flatMap((candle) => [candle.high, candle.low]);
  const drawingPrices = drawing.points.map((point) => point.price);
  const prices = [...candlePrices, ...drawingPrices].filter(Number.isFinite);
  if (prices.length === 0) return 1;
  return Math.max(1, Math.max(...prices) - Math.min(...prices));
}

function replaceDrawingPoint(
  drawing: ChartDrawing,
  pointIndex: number,
  point: DrawingPoint,
): ChartDrawing {
  return {
    ...drawing,
    points: drawing.points.map((existing, index) =>
      index === pointIndex ? point : existing,
    ),
  };
}

function drawLabel(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  fill: string,
  ratio: number,
) {
  const paddingX = 6 * ratio;
  const paddingY = 4 * ratio;
  const fontSize = 10 * ratio;
  ctx.font = `800 ${fontSize}px "IBM Plex Mono", monospace`;
  const metrics = ctx.measureText(text);
  const width = metrics.width + paddingX * 2;
  const height = fontSize + paddingY * 2;
  ctx.fillStyle = "rgba(8, 13, 21, 0.86)";
  ctx.beginPath();
  ctx.roundRect(x, y - height, width, height, 6 * ratio);
  ctx.fill();
  ctx.fillStyle = fill;
  ctx.fillText(text, x + paddingX, y - paddingY);
}

function drawHandle(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  color: string,
  ratio: number,
) {
  ctx.save();
  ctx.fillStyle = "#020916";
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5 * ratio;
  ctx.beginPath();
  ctx.arc(x, y, 4.5 * ratio, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

class DrawingPaneRenderer implements IPrimitivePaneRenderer {
  constructor(
    private readonly drawing: ChartDrawing,
    private readonly points: ViewPoint[],
    private readonly style: PrimitiveStyle,
  ) {}

  draw(target: CanvasRenderingTarget2D) {
    target.useBitmapCoordinateSpace((scope) => {
      const [first, second] = this.points;
      if (!first || first.x === null || first.y === null) return;
      const ctx = scope.context;
      const ratio = Math.max(scope.horizontalPixelRatio, scope.verticalPixelRatio);
      const color = this.style.preview
        ? "rgba(185, 170, 255, 0.72)"
        : this.style.selected
          ? "#63d8ff"
          : this.style.color;
      ctx.save();
      ctx.lineWidth =
        (this.style.lineWidth ?? (this.style.selected ? 1.9 : 1.35)) * ratio;
      ctx.strokeStyle = color;
      ctx.fillStyle = this.style.fillColor;
      if (this.style.preview) ctx.setLineDash([5 * ratio, 4 * ratio]);

      const x1 = scaledCoordinate(first.x, scope.horizontalPixelRatio);
      const y1 = scaledCoordinate(first.y, scope.verticalPixelRatio);

      if (this.drawing.type === "vertical") {
        ctx.beginPath();
        ctx.moveTo(x1, 0);
        ctx.lineTo(x1, scope.bitmapSize.height);
        ctx.stroke();
        if (this.style.selected) drawHandle(ctx, x1, y1, color, ratio);
        ctx.restore();
        return;
      }

      if (!second || second.x === null || second.y === null) {
        if (this.style.selected) drawHandle(ctx, x1, y1, color, ratio);
        ctx.restore();
        return;
      }

      const x2 = scaledCoordinate(second.x, scope.horizontalPixelRatio);
      const y2 = scaledCoordinate(second.y, scope.verticalPixelRatio);

      if (this.drawing.type === "rect") {
        const x = Math.min(x1, x2);
        const y = Math.min(y1, y2);
        const width = Math.abs(x2 - x1);
        const height = Math.abs(y2 - y1);
        ctx.fillRect(x, y, width, height);
        ctx.strokeRect(x, y, width, height);
        if (this.style.selected) {
          drawHandle(ctx, x1, y1, color, ratio);
          drawHandle(ctx, x2, y2, color, ratio);
        }
        ctx.restore();
        return;
      }

      if (this.drawing.type === "fib") {
        const left = Math.min(x1, x2);
        const right = Math.max(x1, x2);
        ctx.setLineDash([4 * ratio, 3 * ratio]);
        for (const level of FIB_LEVELS) {
          const y = y1 + (y2 - y1) * level;
          ctx.beginPath();
          ctx.moveTo(left, y);
          ctx.lineTo(right, y);
          ctx.stroke();
          drawLabel(ctx, `${(level * 100).toFixed(1)}%`, left + 7 * ratio, y - 4 * ratio, color, ratio);
        }
        if (this.style.selected) {
          drawHandle(ctx, x1, y1, color, ratio);
          drawHandle(ctx, x2, y2, color, ratio);
        }
        ctx.restore();
        return;
      }

      if (this.drawing.type === "measure") {
        const [start, end] = this.drawing.points;
        const priceDelta = end.price - start.price;
        const pct = start.price === 0 ? 0 : (priceDelta / start.price) * 100;
        const seconds = Math.abs(Number(end.time) - Number(start.time));
        const label = `${priceDelta >= 0 ? "+" : ""}${formatChartPrice(
          priceDelta,
          this.style.precision,
        )} / ${pct >= 0 ? "+" : ""}${pct.toFixed(2)}% / ${formatCompact(seconds)}s`;
        ctx.strokeStyle = "#f6c86b";
        ctx.fillStyle = "#f6c86b";
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(x1, y1, 3.5 * ratio, 0, Math.PI * 2);
        ctx.arc(x2, y2, 3.5 * ratio, 0, Math.PI * 2);
        ctx.fill();
        drawLabel(ctx, label, (x1 + x2) / 2 + 8 * ratio, (y1 + y2) / 2 - 8 * ratio, "#ffe2a3", ratio);
        if (this.style.selected) {
          drawHandle(ctx, x1, y1, "#ffe2a3", ratio);
          drawHandle(ctx, x2, y2, "#ffe2a3", ratio);
        }
        ctx.restore();
        return;
      }

      if (this.drawing.type === "trend") {
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        if (this.style.showPoints !== false) {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(x1, y1, 3 * ratio, 0, Math.PI * 2);
          ctx.arc(x2, y2, 3 * ratio, 0, Math.PI * 2);
          ctx.fill();
        }
        if (this.style.selected) {
          drawHandle(ctx, x1, y1, color, ratio);
          drawHandle(ctx, x2, y2, color, ratio);
        }
      }
      ctx.restore();
    });
  }
}

class DrawingPaneView implements IPrimitivePaneView {
  private points: ViewPoint[] = [];

  constructor(private readonly source: DrawingPrimitive) {}

  update() {
    const chart = this.source.chart();
    const series = this.source.series();
    if (!chart || !series) {
      this.points = [];
      return;
    }
    this.points = this.source.drawing.points.map((point) => ({
      x: chart.timeScale().timeToCoordinate(point.time),
      y: series.priceToCoordinate(point.price),
    }));
  }

  renderer() {
    return new DrawingPaneRenderer(
      this.source.drawing,
      this.points,
      this.source.style,
    );
  }

  zOrder() {
    return "top" as const;
  }
}

class DrawingPrimitive implements ISeriesPrimitive<Time> {
  private attachedParams: SeriesAttachedParameter<Time> | null = null;
  private readonly paneView = new DrawingPaneView(this);

  constructor(
    public drawing: ChartDrawing,
    public style: PrimitiveStyle,
  ) {}

  attached(param: SeriesAttachedParameter<Time>) {
    this.attachedParams = param;
  }

  detached() {
    this.attachedParams = null;
  }

  chart() {
    return this.attachedParams?.chart ?? null;
  }

  series() {
    return this.attachedParams?.series ?? null;
  }

  updateDrawing(drawing: ChartDrawing) {
    this.drawing = drawing;
    this.updateAllViews();
    this.attachedParams?.requestUpdate();
  }

  updateAllViews() {
    this.paneView.update();
  }

  paneViews() {
    return [this.paneView];
  }

  autoscaleInfo(start: Logical, end: Logical): AutoscaleInfo | null {
    if (this.drawing.type === "vertical") return null;
    const chart = this.chart();
    if (!chart) return null;
    const indexes = this.drawing.points
      .map((point) => chart.timeScale().timeToCoordinate(point.time))
      .map((coordinate) =>
        coordinate === null ? null : chart.timeScale().coordinateToLogical(coordinate),
      )
      .filter((value): value is Logical => value !== null);
    if (indexes.length === 0) return null;
    if (Math.max(...indexes) < start || Math.min(...indexes) > end) return null;
    const prices = this.drawing.points.map((point) => point.price);
    return {
      priceRange: {
        minValue: Math.min(...prices),
        maxValue: Math.max(...prices),
      },
    };
  }
}

function activePriceSeries(
  mode: ChartMode,
  candleSeries: ISeriesApi<"Candlestick"> | null,
  barSeries: ISeriesApi<"Bar"> | null,
  lineSeries: ISeriesApi<"Line"> | null,
  areaSeries: ISeriesApi<"Area"> | null,
): PriceLineSeries | null {
  if (mode === "bars") return barSeries;
  if (mode === "line") return lineSeries;
  if (mode === "area") return areaSeries;
  return candleSeries;
}

export default function MarketChart({
  candles,
  scopeKey,
  loading,
  historyLoading,
  hasMore,
  onLoadEarlier,
  alertLines = [],
  patternLines = [],
}: MarketChartProps) {
  const stageRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const barSeriesRef = useRef<ISeriesApi<"Bar"> | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const areaSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const emaSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const smaSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const vwapSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bollingerUpperRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bollingerMiddleRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bollingerLowerRef = useRef<ISeriesApi<"Line"> | null>(null);
  const [visibleLogicalRange, setVisibleLogicalRange] = useState<{
    from: number;
    to: number;
  } | null>(null);
  const lastScopeRef = useRef<string | null>(null);
  const resetPendingRef = useRef(true);
  const suppressDrawingSaveRef = useRef(true);
  const previousRangeRef = useRef<{ first: number; last: number } | null>(null);
  const renderedTimesRef = useRef<number[]>([]);
  const renderedSignaturesRef = useRef<string[]>([]);
  const candlesRef = useRef<DisplayCandle[]>([]);
  const candlesByTimeRef = useRef<Map<number, DisplayCandle>>(new Map());
  const historyStateRef = useRef({ hasMore, historyLoading, onLoadEarlier });
  const chartModeRef = useRef<ChartMode>("candles");
  const activeToolRef = useRef<DrawingTool>("cursor");
  const selectedDrawingIdRef = useRef<string | null>(null);
  const draftPointRef = useRef<DrawingPoint | null>(null);
  const drawingEditSessionRef = useRef<DrawingEditSession | null>(null);
  const copiedDrawingRef = useRef<ChartDrawing | null>(null);
  const previewPrimitiveRef = useRef<{
    series: PriceLineSeries;
    primitive: DrawingPrimitive;
  } | null>(null);
  const drawingPrimitiveRefs = useRef<
    Array<{ series: PriceLineSeries; primitive: DrawingPrimitive }>
  >([]);
  const patternPrimitiveRefs = useRef<
    Array<{ series: PriceLineSeries; primitive: DrawingPrimitive }>
  >([]);
  const drawingLevelRefs = useRef<
    Array<{ series: PriceLineSeries; line: IPriceLine }>
  >([]);
  const alertLineRefs = useRef<
    Array<{ series: PriceLineSeries; line: IPriceLine }>
  >([]);
  const [chartPreferences, setChartPreferences] = useState<ChartPreferences>(
    loadChartPreferences,
  );
  const chartMode = chartPreferences.chartMode;
  const setChartMode = useCallback((mode: ChartMode) => {
    setChartPreferences((current) => ({ ...current, chartMode: mode }));
  }, []);
  const [activeTool, setActiveTool] = useState<DrawingTool>("cursor");
  const [drawings, setDrawings] = useState<ChartDrawing[]>([]);
  const [selectedDrawingId, setSelectedDrawingId] = useState<string | null>(null);
  const [editingDrawing, setEditingDrawing] = useState(false);
  const [drawingHoverAction, setDrawingHoverAction] =
    useState<DrawingHit["action"] | null>(null);
  const [hasCopiedDrawing, setHasCopiedDrawing] = useState(false);
  const [drawingMenuOpen, setDrawingMenuOpen] = useState(false);
  const [indicatorMenuOpen, setIndicatorMenuOpen] = useState(false);
  const [displayMenuOpen, setDisplayMenuOpen] = useState(false);
  const [drawingToolsOpen, setDrawingToolsOpen] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [inspectCandle, setInspectCandle] = useState<DisplayCandle | null>(null);
  const latestCandle = candles.at(-1) ?? null;
  const readoutCandle = inspectCandle ?? latestCandle;
  const latestPrice = latestCandle?.close ?? 0;
  const precision = useMemo(() => pricePrecision(latestPrice), [latestPrice]);
  const precisionRef = useRef(precision);
  const selectedDrawing = useMemo(
    () => drawings.find((drawing) => drawing.id === selectedDrawingId) ?? null,
    [drawings, selectedDrawingId],
  );
  const patternOverlay = useMemo(
    () => patternOverlayGeometry(candles, visibleLogicalRange),
    [candles, visibleLogicalRange],
  );

  const selectDrawing = useCallback((drawingId: string | null) => {
    selectedDrawingIdRef.current = drawingId;
    setSelectedDrawingId(drawingId);
  }, []);

  const detachPreview = useCallback(() => {
    const preview = previewPrimitiveRef.current;
    if (!preview) return;
    preview.series.detachPrimitive(preview.primitive);
    previewPrimitiveRef.current = null;
  }, []);

  useEffect(() => {
    historyStateRef.current = { hasMore, historyLoading, onLoadEarlier };
  }, [hasMore, historyLoading, onLoadEarlier]);

  useEffect(() => {
    setChartPreferences((current) => {
      if (!current.indicators.ema20) return current;
      return {
        ...current,
        indicators: {
          ...current.indicators,
          ema20: false,
        },
      };
    });
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      safeStorageSet(
        CHART_PREFERENCES_STORAGE_KEY,
        JSON.stringify(chartPreferences),
      );
    }, 120);
    return () => window.clearTimeout(timer);
  }, [chartPreferences]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === stageRef.current);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  useEffect(() => {
    precisionRef.current = precision;
  }, [precision]);

  useEffect(() => {
    selectedDrawingIdRef.current = selectedDrawingId;
  }, [selectedDrawingId]);

  useEffect(() => {
    activeToolRef.current = activeTool;
    if (activeTool === "cursor") {
      draftPointRef.current = null;
      detachPreview();
    } else {
      selectDrawing(null);
      setDrawingHoverAction(null);
    }
    chartRef.current?.applyOptions({
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: activeTool === "cursor",
        horzTouchDrag: activeTool === "cursor",
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    });
  }, [activeTool, detachPreview, selectDrawing]);

  useEffect(() => {
    candlesRef.current = candles;
    candlesByTimeRef.current = new Map(candles.map((candle) => [candle.time, candle]));
  }, [candles]);

  useEffect(() => {
    suppressDrawingSaveRef.current = true;
    draftPointRef.current = null;
    detachPreview();
    selectDrawing(null);
    setDrawingHoverAction(null);
    drawingEditSessionRef.current = null;
    setEditingDrawing(false);
    setDrawings(loadStoredDrawings(scopeKey));
    setInspectCandle(null);
  }, [detachPreview, scopeKey, selectDrawing]);

  useEffect(() => {
    if (suppressDrawingSaveRef.current) {
      suppressDrawingSaveRef.current = false;
      return;
    }
    const timer = window.setTimeout(() => {
      safeStorageSet(drawingStorageKey(scopeKey), JSON.stringify(drawings));
    }, 150);
    return () => window.clearTimeout(timer);
  }, [drawings, scopeKey]);

  useEffect(() => {
    if (
      selectedDrawingId !== null &&
      !drawings.some((drawing) => drawing.id === selectedDrawingId)
    ) {
      selectDrawing(null);
    }
  }, [drawings, selectDrawing, selectedDrawingId]);

  const drawingSeries = useCallback(
    () =>
      activePriceSeries(
        chartModeRef.current,
        candleSeriesRef.current,
        barSeriesRef.current,
        lineSeriesRef.current,
        areaSeriesRef.current,
      ),
    [],
  );

  const resetViewport = useCallback(() => {
    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    if (!chart || !candleSeries || !volumeSeries || candles.length === 0) return;

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

  const scrollToLatest = useCallback(() => {
    chartRef.current?.timeScale().scrollToRealTime();
  }, []);

  const toggleIndicator = useCallback((indicator: IndicatorId) => {
    setChartPreferences((current) => ({
      ...current,
      indicators: {
        ...current.indicators,
        [indicator]: !current.indicators[indicator],
      },
    }));
  }, []);

  const toggleChartPreference = useCallback(
    (
      preference:
        | "logarithmicScale"
        | "magnetCrosshair"
        | "showGrid"
        | "showVolume",
    ) => {
      setChartPreferences((current) => ({
        ...current,
        [preference]: !current[preference],
      }));
    },
    [],
  );

  const toggleFullscreen = useCallback(async () => {
    const stage = stageRef.current;
    if (!stage || !document.fullscreenEnabled) return;
    try {
      if (document.fullscreenElement === stage) {
        await document.exitFullscreen();
        return;
      }
      await stage.requestFullscreen();
    } catch {
      setIsFullscreen(false);
    }
  }, []);

  const saveSnapshot = useCallback(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const canvas = chart.takeScreenshot(true, true);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);
      link.href = url;
      link.download = `tickframe-${scopeKey.replace(/[^a-z0-9-]+/gi, "-")}.png`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    }, "image/png");
  }, [scopeKey]);

  const pointFromMouse = useCallback((param: MouseEventParams<Time>): DrawingPoint | null => {
    const series = drawingSeries();
    if (!series || !param.point || typeof param.time !== "number") return null;
    const price = series.coordinateToPrice(param.point.y);
    if (price === null || !Number.isFinite(Number(price))) return null;
    return {
      time: param.time as UTCTimestamp,
      price: Number(price),
    };
  }, [drawingSeries]);

  const addDrawing = useCallback(
    (drawing: ChartDrawing) => {
      setDrawings((current) => [...current, drawing]);
      selectDrawing(drawing.id);
    },
    [selectDrawing],
  );

  const updatePreview = useCallback(
    (drawing: ChartDrawing | null) => {
      const series = drawingSeries();
      if (!drawing || !series) {
        detachPreview();
        return;
      }
      const existing = previewPrimitiveRef.current;
      if (existing) {
        existing.primitive.updateDrawing(drawing);
        return;
      }
      const primitive = new DrawingPrimitive(drawing, {
        color: "#b9aaff",
        fillColor: "rgba(124, 77, 255, 0.12)",
        preview: true,
        precision: precisionRef.current,
        selected: false,
      });
      series.attachPrimitive(primitive);
      previewPrimitiveRef.current = { series, primitive };
    },
    [detachPreview, drawingSeries],
  );

  const undoDrawing = useCallback(() => {
    const removed = drawings.at(-1);
    if (!removed) return;
    setDrawings(drawings.slice(0, -1));
    if (removed.id === selectedDrawingIdRef.current) selectDrawing(null);
  }, [drawings, selectDrawing]);

  const clearDrawings = useCallback(() => {
    draftPointRef.current = null;
    detachPreview();
    selectDrawing(null);
    setDrawingHoverAction(null);
    setDrawings([]);
  }, [detachPreview, selectDrawing]);

  const deleteSelectedDrawing = useCallback(() => {
    const drawingId = selectedDrawingIdRef.current;
    if (!drawingId) return;
    setDrawings((current) =>
      current.filter((drawing) => drawing.id !== drawingId),
    );
    selectDrawing(null);
    setDrawingHoverAction(null);
    drawingEditSessionRef.current = null;
    setEditingDrawing(false);
  }, [selectDrawing]);

  const copySelectedDrawing = useCallback(() => {
    const drawingId = selectedDrawingIdRef.current;
    if (!drawingId) return;
    const drawing = drawings.find((item) => item.id === drawingId);
    if (!drawing) return;
    copiedDrawingRef.current = {
      ...drawing,
      points: drawing.points.map((point) => ({ ...point })),
    };
    setHasCopiedDrawing(true);
  }, [drawings]);

  const offsetDrawingCopy = useCallback((drawing: ChartDrawing) => {
    const timeDelta = candleTimeStep(candlesRef.current) * 8;
    const priceDelta = visiblePriceRange(candlesRef.current, drawing) * 0.035;
    return moveDrawing(
      {
        ...drawing,
        id: createDrawingId(),
        points: drawing.points.map((point) => ({ ...point })),
      },
      timeDelta,
      priceDelta,
    );
  }, []);

  const appendDrawingCopy = useCallback(
    (drawing: ChartDrawing) => {
      const copy = offsetDrawingCopy(drawing);
      setDrawings((current) => [...current, copy]);
      selectDrawing(copy.id);
    },
    [offsetDrawingCopy, selectDrawing],
  );

  const pasteCopiedDrawing = useCallback(() => {
    const drawing = copiedDrawingRef.current;
    if (!drawing) return;
    appendDrawingCopy(drawing);
  }, [appendDrawingCopy]);

  const duplicateSelectedDrawing = useCallback(() => {
    const drawingId = selectedDrawingIdRef.current;
    if (!drawingId) return;
    const drawing = drawings.find((item) => item.id === drawingId);
    if (!drawing) return;
    appendDrawingCopy(drawing);
  }, [appendDrawingCopy, drawings]);

  const nudgeSelectedDrawing = useCallback(
    (timeDirection: -1 | 0 | 1, priceDirection: -1 | 0 | 1, amount: number) => {
      const drawingId = selectedDrawingIdRef.current;
      if (!drawingId) return;
      setDrawings((current) =>
        current.map((drawing) => {
          if (drawing.id !== drawingId) return drawing;
          const timeDelta =
            drawing.type === "level"
              ? 0
              : candleTimeStep(candlesRef.current) * timeDirection * amount;
          const priceDelta =
            drawing.type === "vertical"
              ? 0
              : visiblePriceRange(candlesRef.current, drawing) *
                0.0025 *
                priceDirection *
                amount;
          return moveDrawing(drawing, timeDelta, priceDelta);
        }),
      );
    },
    [],
  );

  const drawingScreenPoints = useCallback(
    (drawing: ChartDrawing): ScreenPoint[] | null => {
      const chart = chartRef.current;
      const series = drawingSeries();
      if (!chart || !series) return null;
      const points = drawing.points.map((point): ScreenPoint | null => {
        const x = chart.timeScale().timeToCoordinate(point.time);
        const y = series.priceToCoordinate(point.price);
        if (drawing.type === "level") {
          if (y === null) return null;
          return { x: x === null ? 0 : Number(x), y: Number(y) };
        }
        if (drawing.type === "vertical") {
          if (x === null) return null;
          return { x: Number(x), y: y === null ? 0 : Number(y) };
        }
        if (x === null || y === null) return null;
        return { x: Number(x), y: Number(y) };
      });
      if (points.some((point) => point === null)) return null;
      return points as ScreenPoint[];
    },
    [drawingSeries],
  );

  const hitTestDrawing = useCallback(
    (pointer: ScreenPoint): DrawingHit | null => {
      const tolerance = 9;
      for (const drawing of [...drawings].reverse()) {
        const points = drawingScreenPoints(drawing);
        if (!points || points.length === 0) continue;

        const handleIndex = points.findIndex(
          (point) => distanceBetween(pointer, point) <= tolerance + 2,
        );
        if (handleIndex >= 0) {
          return {
            drawing,
            action: "point",
            pointIndex: handleIndex,
          };
        }

        const [first, second] = points;
        if (drawing.type === "level") {
          if (Math.abs(pointer.y - first.y) <= tolerance) {
            return { drawing, action: "move" };
          }
          continue;
        }
        if (drawing.type === "vertical") {
          if (Math.abs(pointer.x - first.x) <= tolerance) {
            return { drawing, action: "move" };
          }
          continue;
        }
        if (!second) continue;

        if (drawing.type === "rect") {
          if (isInsideRect(pointer, first, second)) {
            return { drawing, action: "move" };
          }
          continue;
        }
        if (drawing.type === "fib") {
          const left = Math.min(first.x, second.x);
          const right = Math.max(first.x, second.x);
          const withinX = pointer.x >= left - tolerance && pointer.x <= right + tolerance;
          const nearFibLine =
            withinX &&
            FIB_LEVELS.some((level) => {
              const y = first.y + (second.y - first.y) * level;
              return Math.abs(pointer.y - y) <= tolerance;
            });
          if (nearFibLine) return { drawing, action: "move" };
          continue;
        }
        if (distanceToSegment(pointer, first, second) <= tolerance) {
          return { drawing, action: "move" };
        }
      }
      return null;
    },
    [drawingScreenPoints, drawings],
  );

  const pointerChartPoint = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>): PointerChartPoint | null => {
      const chart = chartRef.current;
      const series = drawingSeries();
      if (!chart || !series) return null;
      const bounds = event.currentTarget.getBoundingClientRect();
      const x = event.clientX - bounds.left;
      const y = event.clientY - bounds.top;
      const time = chart.timeScale().coordinateToTime(x);
      const price = series.coordinateToPrice(y);
      if (typeof time !== "number" || price === null) return null;
      return {
        x,
        y,
        point: {
          time: time as UTCTimestamp,
          price: Number(price),
        },
      };
    },
    [drawingSeries],
  );

  const isChartCanvasTarget = useCallback((target: EventTarget | null) => {
    return target instanceof Node && Boolean(containerRef.current?.contains(target));
  }, []);

  const finishDrawingEdit = useCallback(
    (event?: ReactPointerEvent<HTMLDivElement>) => {
      if (!drawingEditSessionRef.current) return;
      if (
        event &&
        event.currentTarget.hasPointerCapture(event.pointerId)
      ) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
      drawingEditSessionRef.current = null;
      setEditingDrawing(false);
      setDrawingHoverAction(null);
      chartRef.current?.applyOptions({
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: activeToolRef.current === "cursor",
          horzTouchDrag: activeToolRef.current === "cursor",
          vertTouchDrag: false,
        },
      });
    },
    [],
  );

  const startDrawingEdit = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (
        activeToolRef.current !== "cursor" ||
        event.button !== 0 ||
        !event.isPrimary ||
        !isChartCanvasTarget(event.target)
      ) {
        return;
      }
      const pointer = pointerChartPoint(event);
      if (!pointer) return;
      const hit = hitTestDrawing(pointer);
      if (!hit) {
        selectDrawing(null);
        setDrawingHoverAction(null);
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      event.currentTarget.setPointerCapture(event.pointerId);
      selectDrawing(hit.drawing.id);
      setDrawingHoverAction(hit.action);
      drawingEditSessionRef.current = {
        drawingId: hit.drawing.id,
        action: hit.action,
        pointIndex: hit.pointIndex,
        startPoint: pointer.point,
        originalDrawing: hit.drawing,
      };
      setEditingDrawing(true);
      chartRef.current?.applyOptions({
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: false,
          horzTouchDrag: false,
          vertTouchDrag: false,
        },
      });
    },
    [hitTestDrawing, isChartCanvasTarget, pointerChartPoint, selectDrawing],
  );

  const moveDrawingEdit = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const session = drawingEditSessionRef.current;
      if (!session) {
        if (
          activeToolRef.current !== "cursor" ||
          !isChartCanvasTarget(event.target)
        ) {
          setDrawingHoverAction(null);
          return;
        }
        const pointer = pointerChartPoint(event);
        setDrawingHoverAction(
          pointer ? hitTestDrawing(pointer)?.action ?? null : null,
        );
        return;
      }
      const pointer = pointerChartPoint(event);
      if (!pointer) return;
      event.preventDefault();
      event.stopPropagation();

      const nextDrawing =
        session.action === "point" && session.pointIndex !== undefined
          ? replaceDrawingPoint(
              session.originalDrawing,
              session.pointIndex,
              pointer.point,
            )
          : moveDrawing(
              session.originalDrawing,
              Number(pointer.point.time) - Number(session.startPoint.time),
              pointer.point.price - session.startPoint.price,
            );

      setDrawings((current) =>
        current.map((drawing) =>
          drawing.id === session.drawingId ? nextDrawing : drawing,
        ),
      );
    },
    [hitTestDrawing, isChartCanvasTarget, pointerChartPoint],
  );

  useEffect(() => {
    const handleDrawingKeys = (event: KeyboardEvent) => {
      if (isEditableKeyboardTarget(event.target)) return;
      const shortcutKey = event.key.toLowerCase();
      if ((event.ctrlKey || event.metaKey) && shortcutKey === "c") {
        if (selectedDrawingIdRef.current) {
          event.preventDefault();
          copySelectedDrawing();
        }
        return;
      }
      if ((event.ctrlKey || event.metaKey) && shortcutKey === "v") {
        if (copiedDrawingRef.current) {
          event.preventDefault();
          pasteCopiedDrawing();
        }
        return;
      }
      if ((event.ctrlKey || event.metaKey) && shortcutKey === "d") {
        if (selectedDrawingIdRef.current) {
          event.preventDefault();
          duplicateSelectedDrawing();
        }
        return;
      }
      if (
        (event.ctrlKey || event.metaKey) &&
        !event.shiftKey &&
        shortcutKey === "z"
      ) {
        if (drawings.length > 0) {
          event.preventDefault();
          undoDrawing();
        }
        return;
      }
      if (!event.ctrlKey && !event.metaKey && !event.altKey) {
        if (
          selectedDrawingIdRef.current &&
          ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(
            event.key,
          )
        ) {
          event.preventDefault();
          const amount = event.shiftKey ? 5 : 1;
          nudgeSelectedDrawing(
            event.key === "ArrowLeft"
              ? -1
              : event.key === "ArrowRight"
                ? 1
                : 0,
            event.key === "ArrowDown"
              ? -1
              : event.key === "ArrowUp"
                ? 1
                : 0,
            amount,
          );
          return;
        }
        const modeByKey: Partial<Record<string, ChartMode>> = {
          "1": "candles",
          "2": "bars",
          "3": "line",
          "4": "area",
        };
        const mode = modeByKey[event.key];
        if (mode) {
          event.preventDefault();
          setChartMode(mode);
          return;
        }
        if (shortcutKey === "i") {
          event.preventDefault();
          setIndicatorMenuOpen((open) => !open);
          setDisplayMenuOpen(false);
          return;
        }
        if (shortcutKey === "g") {
          event.preventDefault();
          toggleChartPreference("showGrid");
          return;
        }
        if (shortcutKey === "v") {
          event.preventDefault();
          toggleChartPreference("showVolume");
          return;
        }
        if (shortcutKey === "l") {
          event.preventDefault();
          toggleChartPreference("logarithmicScale");
          return;
        }
        if (shortcutKey === "m") {
          event.preventDefault();
          toggleChartPreference("magnetCrosshair");
          return;
        }
        if (shortcutKey === "f") {
          event.preventDefault();
          void toggleFullscreen();
          return;
        }
        if (shortcutKey === "r") {
          event.preventDefault();
          resetViewport();
          return;
        }
        if (event.key === "End") {
          event.preventDefault();
          scrollToLatest();
          return;
        }
      }
      if (event.key === "Escape") {
        setDrawingMenuOpen(false);
        setIndicatorMenuOpen(false);
        setDisplayMenuOpen(false);
        if (activeToolRef.current !== "cursor") {
          draftPointRef.current = null;
          detachPreview();
          setActiveTool("cursor");
          return;
        }
        if (selectedDrawingIdRef.current) {
          selectDrawing(null);
        }
        return;
      }
      if (
        (event.key === "Delete" || event.key === "Backspace") &&
        selectedDrawingIdRef.current
      ) {
        event.preventDefault();
        deleteSelectedDrawing();
      }
    };
    window.addEventListener("keydown", handleDrawingKeys);
    return () => window.removeEventListener("keydown", handleDrawingKeys);
  }, [
    copySelectedDrawing,
    deleteSelectedDrawing,
    detachPreview,
    drawings.length,
    duplicateSelectedDrawing,
    nudgeSelectedDrawing,
    pasteCopiedDrawing,
    resetViewport,
    scrollToLatest,
    setChartMode,
    selectDrawing,
    toggleChartPreference,
    toggleFullscreen,
    undoDrawing,
  ]);

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
        vertLines: {
          color: chartPreferences.showGrid
            ? "rgba(255, 255, 255, 0.045)"
            : "rgba(255, 255, 255, 0)",
        },
        horzLines: {
          color: chartPreferences.showGrid
            ? "rgba(255, 255, 255, 0.045)"
            : "rgba(255, 255, 255, 0)",
        },
      },
      crosshair: {
        mode: chartPreferences.magnetCrosshair
          ? CrosshairMode.Magnet
          : CrosshairMode.Normal,
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
        mode: chartPreferences.logarithmicScale
          ? PriceScaleMode.Logarithmic
          : PriceScaleMode.Normal,
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
      lastValueVisible: chartMode === "candles",
      visible: chartMode === "candles",
    });

    const barSeries = chart.addSeries(BarSeries, {
      upColor: "#35e58a",
      downColor: "#ff4e67",
      thinBars: true,
      priceLineColor: "#7c4dff",
      lastValueVisible: chartMode === "bars",
      visible: chartMode === "bars",
    });

    const lineSeries = chart.addSeries(LineSeries, {
      color: "#9b7cff",
      lineWidth: 2,
      lastValueVisible: chartMode === "line",
      priceLineColor: "#7c4dff",
      visible: chartMode === "line",
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: "#7c4dff",
      topColor: "rgba(124, 77, 255, 0.28)",
      bottomColor: "rgba(124, 77, 255, 0.02)",
      lineWidth: 2,
      lastValueVisible: chartMode === "area",
      priceLineColor: "#7c4dff",
      visible: chartMode === "area",
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "",
      lastValueVisible: false,
      priceLineVisible: false,
      visible: chartPreferences.showVolume,
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    const addIndicatorSeries = (
      color: string,
      lineStyle = LineStyle.Solid,
      lineWidth: 1 | 2 | 3 | 4 = 1,
    ) =>
      chart.addSeries(LineSeries, {
        color,
        lineStyle,
        lineWidth,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
        visible: false,
      });
    const emaSeries = addIndicatorSeries("#f6c86b", LineStyle.Solid, 2);
    const smaSeries = addIndicatorSeries("#63d8ff", LineStyle.Solid, 2);
    const vwapSeries = addIndicatorSeries("#5df2b5", LineStyle.Dashed, 2);
    const bollingerUpper = addIndicatorSeries("rgba(185, 170, 255, 0.8)");
    const bollingerMiddle = addIndicatorSeries(
      "rgba(185, 170, 255, 0.52)",
      LineStyle.Dashed,
    );
    const bollingerLower = addIndicatorSeries("rgba(185, 170, 255, 0.8)");

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    barSeriesRef.current = barSeries;
    lineSeriesRef.current = lineSeries;
    areaSeriesRef.current = areaSeries;
    volumeSeriesRef.current = volumeSeries;
    emaSeriesRef.current = emaSeries;
    smaSeriesRef.current = smaSeries;
    vwapSeriesRef.current = vwapSeries;
    bollingerUpperRef.current = bollingerUpper;
    bollingerMiddleRef.current = bollingerMiddle;
    bollingerLowerRef.current = bollingerLower;

    const indicatorSource = candles.slice(-INDICATOR_MAX_BARS);
    if (chartPreferences.indicators.ema20) {
      emaSeries.applyOptions({ visible: true });
      emaSeries.setData(exponentialMovingAverage(indicatorSource, 20));
    }
    if (chartPreferences.indicators.sma50) {
      smaSeries.applyOptions({ visible: true });
      smaSeries.setData(simpleMovingAverage(indicatorSource, 50));
    }
    if (chartPreferences.indicators.vwap100) {
      vwapSeries.applyOptions({ visible: true });
      vwapSeries.setData(rollingVwap(indicatorSource, 100));
    }
    if (chartPreferences.indicators.bollinger20) {
      const bands = bollingerBands(indicatorSource, 20);
      for (const series of [bollingerUpper, bollingerMiddle, bollingerLower]) {
        series.applyOptions({ visible: true });
      }
      bollingerUpper.setData(bands.upper);
      bollingerMiddle.setData(bands.middle);
      bollingerLower.setData(bands.lower);
    }

    const handleVisibleRange = (range: { from: number; to: number } | null) => {
      setVisibleLogicalRange(range);
      if (!range || range.from > 15) return;
      const state = historyStateRef.current;
      if (state.hasMore && !state.historyLoading) state.onLoadEarlier();
    };

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      if (typeof param.time === "number") {
        const exact = candlesByTimeRef.current.get(param.time);
        setInspectCandle(exact ?? closestCandle(candlesRef.current, param.time));
      } else {
        setInspectCandle(null);
      }

      const start = draftPointRef.current;
      if (!start) return;
      const point = pointFromMouse(param);
      const tool = activeToolRef.current;
      if (!point || tool === "cursor" || tool === "level" || tool === "vertical") return;
      updatePreview({
        id: "preview",
        type: tool,
        points: [start, point],
      });
    };

    const handleClick = (param: MouseEventParams<Time>) => {
      const point = pointFromMouse(param);
      const tool = activeToolRef.current;
      if (!point || tool === "cursor") return;

      if (tool === "level" || tool === "vertical") {
        addDrawing({
          id: createDrawingId(),
          type: tool,
          points: [point],
        });
        setActiveTool("cursor");
        return;
      }

      const start = draftPointRef.current;
      if (!start) {
        draftPointRef.current = point;
        updatePreview({
          id: "preview",
          type: tool,
          points: [point, point],
        });
        return;
      }

      addDrawing({
        id: createDrawingId(),
        type: tool,
        points: [start, point],
      });
      draftPointRef.current = null;
      detachPreview();
      setActiveTool("cursor");
    };

    chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleRange);
    chart.subscribeCrosshairMove(handleCrosshairMove);
    chart.subscribeClick(handleClick);

    const resizeObserver = new ResizeObserver(([entry]) => {
      chart.applyOptions({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleRange);
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      chart.unsubscribeClick(handleClick);
      resizeObserver.disconnect();
      detachPreview();
      for (const item of alertLineRefs.current) item.series.removePriceLine(item.line);
      for (const item of drawingPrimitiveRefs.current) {
        item.series.detachPrimitive(item.primitive);
      }
      for (const item of patternPrimitiveRefs.current) {
        item.series.detachPrimitive(item.primitive);
      }
      for (const item of drawingLevelRefs.current) {
        item.series.removePriceLine(item.line);
      }
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      barSeriesRef.current = null;
      lineSeriesRef.current = null;
      areaSeriesRef.current = null;
      volumeSeriesRef.current = null;
      emaSeriesRef.current = null;
      smaSeriesRef.current = null;
      vwapSeriesRef.current = null;
      bollingerUpperRef.current = null;
      bollingerMiddleRef.current = null;
      bollingerLowerRef.current = null;
      alertLineRefs.current = [];
      drawingPrimitiveRefs.current = [];
      patternPrimitiveRefs.current = [];
      drawingLevelRefs.current = [];
      renderedTimesRef.current = [];
      renderedSignaturesRef.current = [];
    };
  }, [addDrawing, detachPreview, pointFromMouse, updatePreview]);

  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const barSeries = barSeriesRef.current;
    const lineSeries = lineSeriesRef.current;
    const areaSeries = areaSeriesRef.current;
    if (!candleSeries || !barSeries || !lineSeries || !areaSeries) return;

    for (const item of alertLineRefs.current) item.series.removePriceLine(item.line);
    const seriesList: PriceLineSeries[] = [
      candleSeries,
      barSeries,
      lineSeries,
      areaSeries,
    ];
    alertLineRefs.current = seriesList.flatMap((series) =>
      alertLines.map((line) => ({
        series,
        line: series.createPriceLine({
          id: line.id,
          price: line.price,
          color:
            line.tone === "above"
              ? "rgba(124, 77, 255, 0.88)"
              : "rgba(255, 78, 103, 0.88)",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          lineVisible: true,
          axisLabelVisible: true,
          axisLabelColor: line.tone === "above" ? "#7c4dff" : "#ff4e67",
          axisLabelTextColor: "#f4f6ff",
          title: line.label,
        }),
      })),
    );
  }, [alertLines]);

  useEffect(() => {
    chartModeRef.current = chartMode;
    draftPointRef.current = null;
    detachPreview();
    candleSeriesRef.current?.applyOptions({
      visible: chartMode === "candles",
      lastValueVisible: chartMode === "candles",
    });
    barSeriesRef.current?.applyOptions({
      visible: chartMode === "bars",
      lastValueVisible: chartMode === "bars",
    });
    lineSeriesRef.current?.applyOptions({
      visible: chartMode === "line",
      lastValueVisible: chartMode === "line",
    });
    areaSeriesRef.current?.applyOptions({
      visible: chartMode === "area",
      lastValueVisible: chartMode === "area",
    });
  }, [chartMode, detachPreview]);

  useEffect(() => {
    const chart = chartRef.current;
    const volumeSeries = volumeSeriesRef.current;
    if (!chart || !volumeSeries) return;
    const gridColor = chartPreferences.showGrid
      ? "rgba(255, 255, 255, 0.045)"
      : "rgba(255, 255, 255, 0)";
    chart.applyOptions({
      crosshair: {
        mode: chartPreferences.magnetCrosshair
          ? CrosshairMode.Magnet
          : CrosshairMode.Normal,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      rightPriceScale: {
        mode: chartPreferences.logarithmicScale
          ? PriceScaleMode.Logarithmic
          : PriceScaleMode.Normal,
      },
    });
    volumeSeries.applyOptions({ visible: chartPreferences.showVolume });
  }, [
    chartPreferences.logarithmicScale,
    chartPreferences.magnetCrosshair,
    chartPreferences.showGrid,
    chartPreferences.showVolume,
  ]);

  useEffect(() => {
    const emaSeries = emaSeriesRef.current;
    const smaSeries = smaSeriesRef.current;
    const vwapSeries = vwapSeriesRef.current;
    const upperSeries = bollingerUpperRef.current;
    const middleSeries = bollingerMiddleRef.current;
    const lowerSeries = bollingerLowerRef.current;
    if (
      !emaSeries ||
      !smaSeries ||
      !vwapSeries ||
      !upperSeries ||
      !middleSeries ||
      !lowerSeries
    ) return;

    const source = candles.slice(-INDICATOR_MAX_BARS);
    const { indicators } = chartPreferences;
    emaSeries.applyOptions({ visible: indicators.ema20 });
    smaSeries.applyOptions({ visible: indicators.sma50 });
    vwapSeries.applyOptions({ visible: indicators.vwap100 });
    upperSeries.applyOptions({ visible: indicators.bollinger20 });
    middleSeries.applyOptions({ visible: indicators.bollinger20 });
    lowerSeries.applyOptions({ visible: indicators.bollinger20 });

    if (indicators.ema20) emaSeries.setData(exponentialMovingAverage(source, 20));
    if (indicators.sma50) smaSeries.setData(simpleMovingAverage(source, 50));
    if (indicators.vwap100) vwapSeries.setData(rollingVwap(source, 100));
    if (indicators.bollinger20) {
      const bands = bollingerBands(source, 20);
      upperSeries.setData(bands.upper);
      middleSeries.setData(bands.middle);
      lowerSeries.setData(bands.lower);
    }
  }, [candles, chartPreferences.indicators]);

  useEffect(() => {
    const series = drawingSeries();
    if (!series) return;

    for (const item of drawingPrimitiveRefs.current) {
      item.series.detachPrimitive(item.primitive);
    }
    for (const item of drawingLevelRefs.current) {
      item.series.removePriceLine(item.line);
    }
    drawingPrimitiveRefs.current = [];
    drawingLevelRefs.current = [];

    for (const drawing of drawings) {
      const selected = drawing.id === selectedDrawingId;
      if (drawing.type === "level") {
        const point = drawing.points[0];
        if (!point) continue;
        const seriesList = [
          candleSeriesRef.current,
          barSeriesRef.current,
          lineSeriesRef.current,
          areaSeriesRef.current,
        ].filter((item): item is PriceLineSeries => item !== null);
        for (const levelSeries of seriesList) {
          drawingLevelRefs.current.push({
            series: levelSeries,
            line: levelSeries.createPriceLine({
              id: drawing.id,
              price: point.price,
              color: selected ? "#63d8ff" : "rgba(93, 242, 181, 0.88)",
              lineWidth: selected ? 2 : 1,
              lineStyle: LineStyle.Dashed,
              axisLabelVisible: true,
              axisLabelColor: selected ? "#63d8ff" : "#35e58a",
              axisLabelTextColor: selected ? "#020916" : "#06110d",
              title: selected ? "Selected level" : "Level",
            }),
          });
        }
        continue;
      }
      const primitive = new DrawingPrimitive(drawing, {
        color: drawing.type === "measure" ? "#f6c86b" : "#9b7cff",
        fillColor: "rgba(124, 77, 255, 0.12)",
        preview: false,
        precision,
        selected,
      });
      series.attachPrimitive(primitive);
      drawingPrimitiveRefs.current.push({ series, primitive });
    }

    return () => {
      for (const item of drawingPrimitiveRefs.current) {
        item.series.detachPrimitive(item.primitive);
      }
      for (const item of drawingLevelRefs.current) {
        item.series.removePriceLine(item.line);
      }
      drawingPrimitiveRefs.current = [];
      drawingLevelRefs.current = [];
    };
  }, [chartMode, drawingSeries, drawings, precision, selectedDrawingId]);

  useEffect(() => {
    const series = drawingSeries();
    if (!series) return;

    for (const item of patternPrimitiveRefs.current) {
      item.series.detachPrimitive(item.primitive);
    }
    patternPrimitiveRefs.current = [];

    for (const line of patternLines) {
      const drawing: ChartDrawing = {
        id: line.id,
        type: "trend",
        points: line.points.map((point) => ({
          time: point.time as UTCTimestamp,
          price: point.price,
        })),
      };
      const primitive = new DrawingPrimitive(drawing, {
        color: "#2f7cff",
        fillColor: "rgba(47, 124, 255, 0.10)",
        preview: false,
        precision,
        selected: false,
        showPoints: false,
        lineWidth: 2,
      });
      series.attachPrimitive(primitive);
      patternPrimitiveRefs.current.push({ series, primitive });
    }

    return () => {
      for (const item of patternPrimitiveRefs.current) {
        item.series.detachPrimitive(item.primitive);
      }
      patternPrimitiveRefs.current = [];
    };
  }, [chartMode, drawingSeries, patternLines, precision]);

  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const barSeries = barSeriesRef.current;
    const lineSeries = lineSeriesRef.current;
    const areaSeries = areaSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    const chart = chartRef.current;
    if (
      !candleSeries ||
      !barSeries ||
      !lineSeries ||
      !areaSeries ||
      !volumeSeries ||
      !chart
    ) return;

    const previousRange = previousRangeRef.current;
    const visibleRange = chart.timeScale().getVisibleRange();
    const nextRange =
      candles.length > 0
        ? { first: candles[0].time, last: candles[candles.length - 1].time }
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
      renderedTimesRef.current = [];
      renderedSignaturesRef.current = [];
    }

    const multiplier = 10 ** precision;
    const priceFormat = {
      type: "price" as const,
      precision,
      minMove: 1 / multiplier,
    };
    candleSeries.applyOptions({ priceFormat });
    barSeries.applyOptions({ priceFormat });
    lineSeries.applyOptions({ priceFormat });
    areaSeries.applyOptions({ priceFormat });
    for (const indicatorSeries of [
      emaSeriesRef.current,
      smaSeriesRef.current,
      vwapSeriesRef.current,
      bollingerUpperRef.current,
      bollingerMiddleRef.current,
      bollingerLowerRef.current,
    ]) {
      indicatorSeries?.applyOptions({ priceFormat });
    }

    const candlePoints = candles.map((candle) => ({
      time: candle.time as UTCTimestamp,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));
    const closePoints = candles.map((candle) => ({
      time: candle.time as UTCTimestamp,
      value: candle.close,
    }));
    const volumePoints = candles.map((candle) => ({
      time: candle.time as UTCTimestamp,
      value: candle.volume,
      color: volumeColor(candle),
    }));
    const nextTimes = candles.map((candle) => candle.time);
    const nextSignatures = candles.map(candleSignature);
    const previousTimes = renderedTimesRef.current;
    const previousSignatures = renderedSignaturesRef.current;
    const prefixTimesMatch = previousTimes.every(
      (time, index) => nextTimes[index] === time,
    );
    const firstChangedIndex = nextSignatures.findIndex(
      (signature, index) => previousSignatures[index] !== signature,
    );
    const dataUnchanged =
      !resetPendingRef.current &&
      !historyWasPrepended &&
      candles.length === previousTimes.length &&
      firstChangedIndex === -1;
    const canUpdateTail =
      !resetPendingRef.current &&
      !historyWasPrepended &&
      candles.length >= previousTimes.length &&
      previousTimes.length > 0 &&
      prefixTimesMatch &&
      firstChangedIndex >= previousTimes.length - 1;

    if (dataUnchanged) {
      previousRangeRef.current = nextRange;
      return;
    }

    if (canUpdateTail) {
      for (let index = firstChangedIndex; index < candles.length; index += 1) {
        candleSeries.update(candlePoints[index]);
        barSeries.update(candlePoints[index]);
        lineSeries.update(closePoints[index]);
        areaSeries.update(closePoints[index]);
        volumeSeries.update(volumePoints[index]);
      }
    } else {
      candleSeries.setData(candlePoints);
      barSeries.setData(candlePoints);
      lineSeries.setData(closePoints);
      areaSeries.setData(closePoints);
      volumeSeries.setData(volumePoints);
    }
    renderedTimesRef.current = nextTimes;
    renderedSignaturesRef.current = nextSignatures;
    setVisibleLogicalRange(chart.timeScale().getVisibleLogicalRange());

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

  const drawCountLabel =
    selectedDrawing !== null
      ? drawingLabel(selectedDrawing)
      : drawings.length === 0
      ? "No drawings"
      : `${drawings.length} drawing${drawings.length === 1 ? "" : "s"}`;
  const chartStageClassName = [
    "chart-stage",
    activeTool !== "cursor" ? "is-drawing-mode" : "",
    drawingHoverAction === "move" ? "is-drawing-hover-move" : "",
    drawingHoverAction === "point" ? "is-drawing-hover-point" : "",
    editingDrawing ? "is-editing-drawing" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      ref={stageRef}
      className={chartStageClassName}
      onLostPointerCapture={finishDrawingEdit}
      onPointerCancelCapture={finishDrawingEdit}
      onPointerDownCapture={startDrawingEdit}
      onPointerLeave={() => {
        if (!drawingEditSessionRef.current) setDrawingHoverAction(null);
      }}
      onPointerMoveCapture={moveDrawingEdit}
      onPointerUpCapture={finishDrawingEdit}
      onWheelCapture={(event) => {
        if (!event.ctrlKey && !event.metaKey) {
          event.stopPropagation();
        }
      }}
    >
      <div ref={containerRef} className="chart-canvas" />
      {patternOverlay && (
        <div className="chart-pattern-overlay" aria-hidden="true">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none">
            <line
              className="pattern-start-line"
              vectorEffect="non-scaling-stroke"
              x1={patternOverlay.startX}
              x2={patternOverlay.startX}
              y1="0"
              y2="100"
            />
          </svg>
        </div>
      )}
      <div className="tv-chart-toolbar" aria-label="Chart controls">
        <div className="tv-toolbar-group" aria-label="Chart style">
          {CHART_MODES.map((mode) => {
            const Icon = CHART_MODE_ICONS[mode.id];
            return (
              <button
                aria-label={`${mode.label} chart`}
                aria-pressed={chartMode === mode.id}
                className={chartMode === mode.id ? "active" : ""}
                data-tooltip={mode.label}
                key={mode.id}
                title={`${mode.label} chart`}
                type="button"
                onClick={() => setChartMode(mode.id)}
              >
                <Icon aria-hidden="true" size={16} strokeWidth={1.8} />
              </button>
            );
          })}
        </div>
        {readoutCandle && (
          <div className="tv-chart-readout" aria-label="OHLC values">
            <span>O {formatChartPrice(readoutCandle.open, precision)}</span>
            <span>H {formatChartPrice(readoutCandle.high, precision)}</span>
            <span>L {formatChartPrice(readoutCandle.low, precision)}</span>
            <span>C {formatChartPrice(readoutCandle.close, precision)}</span>
            <span>V {formatCompact(readoutCandle.volume)}</span>
            <span>T {new Date(readoutCandle.time * 1000).toLocaleTimeString()}</span>
          </div>
        )}
        <div className="tv-toolbar-group tv-toolbar-actions" aria-label="Chart actions">
          <button
            aria-label="Indicators"
            aria-expanded={indicatorMenuOpen}
            aria-pressed={Object.values(chartPreferences.indicators).some(Boolean)}
            className={Object.values(chartPreferences.indicators).some(Boolean) ? "active" : ""}
            data-tooltip="Indicators"
            title="Choose chart indicators (I)"
            type="button"
            onClick={() => {
              setIndicatorMenuOpen((open) => !open);
              setDisplayMenuOpen(false);
              setDrawingMenuOpen(false);
            }}
          >
            <ChartSpline aria-hidden="true" size={16} strokeWidth={1.8} />
          </button>
          <button
            aria-label="Chart display settings"
            aria-expanded={displayMenuOpen}
            data-tooltip="Display"
            title="Volume, grid, and price scale"
            type="button"
            onClick={() => {
              setDisplayMenuOpen((open) => !open);
              setIndicatorMenuOpen(false);
              setDrawingMenuOpen(false);
            }}
          >
            <Grid3X3 aria-hidden="true" size={16} strokeWidth={1.8} />
          </button>
          <button
            aria-label="Toggle drawing tools"
            aria-pressed={drawingToolsOpen}
            className={drawingToolsOpen ? "active" : ""}
            data-tooltip="Drawing tools"
            title="Show or hide drawing tools"
            type="button"
            onClick={() => {
              if (drawingToolsOpen) setActiveTool("cursor");
              setDrawingToolsOpen((open) => !open);
            }}
          >
            <PencilRuler aria-hidden="true" size={16} strokeWidth={1.8} />
          </button>
          <button
            aria-label="Auto fit chart"
            data-tooltip="Auto fit"
            title="Fit the latest candles in view"
            disabled={candles.length === 0}
            type="button"
            onClick={resetViewport}
          >
            <Maximize2 aria-hidden="true" size={16} strokeWidth={1.8} />
          </button>
          <button
            aria-label="Scroll to latest candle"
            data-tooltip="Latest"
            title="Return to the latest candle (End)"
            disabled={candles.length === 0}
            type="button"
            onClick={scrollToLatest}
          >
            <TrendingUp aria-hidden="true" size={16} strokeWidth={1.8} />
          </button>
          <button
            aria-label="Load earlier history"
            data-tooltip={historyLoading ? "Loading history" : "History"}
            disabled={!hasMore || historyLoading}
            title={hasMore ? "Load older candles" : "All available history is loaded"}
            type="button"
            onClick={onLoadEarlier}
          >
            <History aria-hidden="true" size={16} strokeWidth={1.8} />
          </button>
          <button
            aria-label="Drawing actions"
            aria-expanded={drawingMenuOpen}
            data-tooltip="Drawing actions"
            title="Duplicate, copy, paste, undo, or delete drawings"
            type="button"
            onClick={() => {
              setDrawingMenuOpen((open) => !open);
              setIndicatorMenuOpen(false);
              setDisplayMenuOpen(false);
            }}
          >
            <Ellipsis aria-hidden="true" size={17} strokeWidth={1.8} />
          </button>
          <button
            aria-label="Save chart snapshot"
            data-tooltip="Snapshot"
            title="Save chart as PNG"
            disabled={candles.length === 0}
            type="button"
            onClick={saveSnapshot}
          >
            <Camera aria-hidden="true" size={16} strokeWidth={1.8} />
          </button>
          <button
            aria-label={isFullscreen ? "Exit fullscreen chart" : "Open fullscreen chart"}
            aria-pressed={isFullscreen}
            className={isFullscreen ? "active" : ""}
            data-tooltip="Fullscreen"
            title="Toggle fullscreen chart (F)"
            type="button"
            onClick={() => void toggleFullscreen()}
          >
            <Expand aria-hidden="true" size={16} strokeWidth={1.8} />
          </button>
        </div>
      </div>
      {indicatorMenuOpen && (
        <div className="chart-control-menu chart-indicator-menu" role="menu" aria-label="Indicators">
          <header>
            <span>Indicators</span>
            <small>Calculated locally</small>
          </header>
          {INDICATORS.map((indicator) => (
            <button
              aria-checked={chartPreferences.indicators[indicator.id]}
              key={indicator.id}
              role="menuitemcheckbox"
              type="button"
              onClick={() => toggleIndicator(indicator.id)}
            >
              <i style={{ backgroundColor: indicator.color }} />
              <span>
                <strong>{indicator.label}</strong>
                <small>{indicator.detail}</small>
              </span>
              <b>{chartPreferences.indicators[indicator.id] ? "ON" : "OFF"}</b>
            </button>
          ))}
        </div>
      )}
      {displayMenuOpen && (
        <div className="chart-control-menu chart-display-menu" role="menu" aria-label="Chart display">
          <header>
            <span>Display</span>
            <small>Chart workspace</small>
          </header>
          <button
            aria-checked={chartPreferences.showVolume}
            role="menuitemcheckbox"
            type="button"
            onClick={() => toggleChartPreference("showVolume")}
          >
            <Volume2 aria-hidden="true" size={15} />
            <span><strong>Volume</strong><small>Bottom histogram</small></span>
            <b>{chartPreferences.showVolume ? "ON" : "OFF"}</b>
          </button>
          <button
            aria-checked={chartPreferences.showGrid}
            role="menuitemcheckbox"
            type="button"
            onClick={() => toggleChartPreference("showGrid")}
          >
            <Grid3X3 aria-hidden="true" size={15} />
            <span><strong>Grid</strong><small>Price and time guides</small></span>
            <b>{chartPreferences.showGrid ? "ON" : "OFF"}</b>
          </button>
          <button
            aria-checked={chartPreferences.logarithmicScale}
            role="menuitemcheckbox"
            type="button"
            onClick={() => toggleChartPreference("logarithmicScale")}
          >
            <ChartNoAxesCombined aria-hidden="true" size={15} />
            <span><strong>Log scale</strong><small>Percentage-like spacing</small></span>
            <b>{chartPreferences.logarithmicScale ? "ON" : "OFF"}</b>
          </button>
          <button
            aria-checked={chartPreferences.magnetCrosshair}
            role="menuitemcheckbox"
            type="button"
            onClick={() => toggleChartPreference("magnetCrosshair")}
          >
            <ScanLine aria-hidden="true" size={15} />
            <span><strong>Magnet crosshair</strong><small>Snap to OHLC values</small></span>
            <b>{chartPreferences.magnetCrosshair ? "ON" : "OFF"}</b>
          </button>
          <button
            role="menuitem"
            type="button"
            onClick={() =>
              setChartPreferences({
                ...DEFAULT_CHART_PREFERENCES,
                indicators: { ...DEFAULT_CHART_PREFERENCES.indicators },
              })
            }
          >
            <Eraser aria-hidden="true" size={15} />
            <span><strong>Reset display</strong><small>Restore Tickframe defaults</small></span>
            <b>RESET</b>
          </button>
        </div>
      )}
      {Object.values(chartPreferences.indicators).some(Boolean) && (
        <div className="chart-indicator-legend" aria-label="Active indicators">
          {INDICATORS.filter((item) => chartPreferences.indicators[item.id]).map((item) => (
            <button
              key={item.id}
              title={`Hide ${item.label}`}
              type="button"
              onClick={() => toggleIndicator(item.id)}
            >
              <i style={{ backgroundColor: item.color }} />
              {item.label}
            </button>
          ))}
        </div>
      )}
      {drawingToolsOpen && (
        <div className="tv-drawing-tools" aria-label="Drawing tools">
          {DRAWING_TOOLS.map((tool) => {
            const Icon = DRAWING_TOOL_ICONS[tool.id];
            return (
              <button
                aria-label={tool.title}
                aria-pressed={activeTool === tool.id}
                className={activeTool === tool.id ? "active" : ""}
                data-tooltip={tool.label}
                key={tool.id}
                title={tool.title}
                type="button"
                onClick={() => setActiveTool(tool.id)}
              >
                <Icon aria-hidden="true" size={17} strokeWidth={1.75} />
              </button>
            );
          })}
          <span className="drawing-count" title={drawCountLabel}>
            {drawings.length}
          </span>
        </div>
      )}
      {drawingMenuOpen && (
        <div className="chart-edit-menu" role="menu" aria-label="Drawing actions">
          <button
            disabled={selectedDrawing === null}
            role="menuitem"
            type="button"
            onClick={() => {
              duplicateSelectedDrawing();
              setDrawingMenuOpen(false);
            }}
          >
            <CopyPlus aria-hidden="true" size={14} />
            Duplicate selected
          </button>
          <button
            disabled={selectedDrawing === null}
            role="menuitem"
            type="button"
            onClick={() => {
              copySelectedDrawing();
              setDrawingMenuOpen(false);
            }}
          >
            <Copy aria-hidden="true" size={14} />
            Copy selected
          </button>
          <button
            disabled={!hasCopiedDrawing}
            role="menuitem"
            type="button"
            onClick={() => {
              pasteCopiedDrawing();
              setDrawingMenuOpen(false);
            }}
          >
            <ClipboardPaste aria-hidden="true" size={14} />
            Paste drawing
          </button>
          <button
            disabled={drawings.length === 0}
            role="menuitem"
            type="button"
            onClick={() => {
              undoDrawing();
              setDrawingMenuOpen(false);
            }}
          >
            <Undo2 aria-hidden="true" size={14} />
            Undo last drawing
          </button>
          <button
            disabled={selectedDrawing === null}
            role="menuitem"
            type="button"
            onClick={() => {
              deleteSelectedDrawing();
              setDrawingMenuOpen(false);
            }}
          >
            <Trash2 aria-hidden="true" size={14} />
            Delete selected
          </button>
          <button
            disabled={drawings.length === 0}
            role="menuitem"
            type="button"
            onClick={() => {
              clearDrawings();
              setDrawingMenuOpen(false);
            }}
          >
            <Eraser aria-hidden="true" size={14} />
            Clear all drawings
          </button>
        </div>
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

function patternOverlayGeometry(
  candles: DisplayCandle[],
  visibleRange: { from: number; to: number } | null,
): { startX: number } | null {
  if (candles.length < 96 || !visibleRange) {
    return null;
  }

  const visibleSpan = Math.max(0.000001, visibleRange.to - visibleRange.from);
  const startIndex = candles.length - 96;
  const patternBoundaryIndex = startIndex - 0.5;
  return {
    startX: clamp(
      ((patternBoundaryIndex - visibleRange.from) / visibleSpan) * 100,
      -4,
      104,
    ),
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
