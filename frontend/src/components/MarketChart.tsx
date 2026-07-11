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
  AreaSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
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

type ChartMode = "candles" | "line" | "area";
type DrawingTool = "cursor" | "trend" | "rect" | "level" | "vertical" | "fib" | "measure";
type DrawingType = Exclude<DrawingTool, "cursor">;
type PriceLineSeries =
  | ISeriesApi<"Candlestick">
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
const DRAWINGS_STORAGE_PREFIX = "tickframe.chartDrawings.v2:";
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
  { id: "line", label: "Line" },
  { id: "area", label: "Area" },
];

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
    const raw = window.localStorage.getItem(drawingStorageKey(scopeKey));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChartDrawing[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (drawing) =>
        typeof drawing.id === "string" &&
        isDrawingType(drawing.type) &&
        Array.isArray(drawing.points) &&
        drawing.points.every(
          (point) =>
            Number.isFinite(point.time) && Number.isFinite(point.price),
        ),
    );
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
      if (first?.x === null || first?.y === null) return;
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
  lineSeries: ISeriesApi<"Line"> | null,
  areaSeries: ISeriesApi<"Area"> | null,
): PriceLineSeries | null {
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
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const areaSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
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
  const [chartMode, setChartMode] = useState<ChartMode>("candles");
  const [activeTool, setActiveTool] = useState<DrawingTool>("cursor");
  const [drawings, setDrawings] = useState<ChartDrawing[]>([]);
  const [selectedDrawingId, setSelectedDrawingId] = useState<string | null>(null);
  const [editingDrawing, setEditingDrawing] = useState(false);
  const [hasCopiedDrawing, setHasCopiedDrawing] = useState(false);
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
      setSelectedDrawingId(null);
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
  }, [activeTool, detachPreview]);

  useEffect(() => {
    candlesRef.current = candles;
    candlesByTimeRef.current = new Map(candles.map((candle) => [candle.time, candle]));
  }, [candles]);

  useEffect(() => {
    suppressDrawingSaveRef.current = true;
    draftPointRef.current = null;
    detachPreview();
    setSelectedDrawingId(null);
    drawingEditSessionRef.current = null;
    setEditingDrawing(false);
    setDrawings(loadStoredDrawings(scopeKey));
    setInspectCandle(null);
  }, [detachPreview, scopeKey]);

  useEffect(() => {
    if (suppressDrawingSaveRef.current) {
      suppressDrawingSaveRef.current = false;
      return;
    }
    window.localStorage.setItem(drawingStorageKey(scopeKey), JSON.stringify(drawings));
  }, [drawings, scopeKey]);

  useEffect(() => {
    if (
      selectedDrawingId !== null &&
      !drawings.some((drawing) => drawing.id === selectedDrawingId)
    ) {
      setSelectedDrawingId(null);
    }
  }, [drawings, selectedDrawingId]);

  const drawingSeries = useCallback(
    () =>
      activePriceSeries(
        chartModeRef.current,
        candleSeriesRef.current,
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

  const addDrawing = useCallback((drawing: ChartDrawing) => {
    setDrawings((current) => [...current, drawing]);
  }, []);

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
    setDrawings((current) => {
      const removed = current.at(-1);
      if (removed?.id === selectedDrawingIdRef.current) {
        setSelectedDrawingId(null);
      }
      return current.slice(0, -1);
    });
  }, []);

  const clearDrawings = useCallback(() => {
    draftPointRef.current = null;
    detachPreview();
    setSelectedDrawingId(null);
    setDrawings([]);
  }, [detachPreview]);

  const deleteSelectedDrawing = useCallback(() => {
    const drawingId = selectedDrawingIdRef.current;
    if (!drawingId) return;
    setDrawings((current) =>
      current.filter((drawing) => drawing.id !== drawingId),
    );
    setSelectedDrawingId(null);
    drawingEditSessionRef.current = null;
    setEditingDrawing(false);
  }, []);

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

  const pasteCopiedDrawing = useCallback(() => {
    const drawing = copiedDrawingRef.current;
    if (!drawing) return;
    const timeDelta = candleTimeStep(candlesRef.current) * 8;
    const priceDelta = visiblePriceRange(candlesRef.current, drawing) * 0.035;
    const pasted = moveDrawing(
      {
        ...drawing,
        id: createDrawingId(),
        points: drawing.points.map((point) => ({ ...point })),
      },
      timeDelta,
      priceDelta,
    );
    setDrawings((current) => [...current, pasted]);
    setSelectedDrawingId(pasted.id);
  }, []);

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

  const finishDrawingEdit = useCallback(
    (event?: ReactPointerEvent<HTMLDivElement>) => {
      if (
        event &&
        event.currentTarget.hasPointerCapture(event.pointerId)
      ) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
      drawingEditSessionRef.current = null;
      setEditingDrawing(false);
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
      if (activeToolRef.current !== "cursor") return;
      const pointer = pointerChartPoint(event);
      if (!pointer) return;
      const hit = hitTestDrawing(pointer);
      if (!hit) {
        setSelectedDrawingId(null);
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      event.currentTarget.setPointerCapture(event.pointerId);
      setSelectedDrawingId(hit.drawing.id);
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
    [hitTestDrawing, pointerChartPoint],
  );

  const moveDrawingEdit = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const session = drawingEditSessionRef.current;
      if (!session) return;
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
    [pointerChartPoint],
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
      if (event.key === "Escape") {
        if (activeToolRef.current !== "cursor") {
          draftPointRef.current = null;
          detachPreview();
          setActiveTool("cursor");
          return;
        }
        if (selectedDrawingIdRef.current) {
          setSelectedDrawingId(null);
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
  }, [copySelectedDrawing, deleteSelectedDrawing, detachPreview, pasteCopiedDrawing]);

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

    const lineSeries = chart.addSeries(LineSeries, {
      color: "#9b7cff",
      lineWidth: 2,
      lastValueVisible: true,
      priceLineColor: "#7c4dff",
      visible: false,
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: "#7c4dff",
      topColor: "rgba(124, 77, 255, 0.28)",
      bottomColor: "rgba(124, 77, 255, 0.02)",
      lineWidth: 2,
      lastValueVisible: true,
      priceLineColor: "#7c4dff",
      visible: false,
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
    lineSeriesRef.current = lineSeries;
    areaSeriesRef.current = areaSeries;
    volumeSeriesRef.current = volumeSeries;

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
      lineSeriesRef.current = null;
      areaSeriesRef.current = null;
      volumeSeriesRef.current = null;
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
    const lineSeries = lineSeriesRef.current;
    const areaSeries = areaSeriesRef.current;
    if (!candleSeries || !lineSeries || !areaSeries) return;

    for (const item of alertLineRefs.current) item.series.removePriceLine(item.line);
    const seriesList: PriceLineSeries[] = [candleSeries, lineSeries, areaSeries];
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
    const lineSeries = lineSeriesRef.current;
    const areaSeries = areaSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    const chart = chartRef.current;
    if (!candleSeries || !lineSeries || !areaSeries || !volumeSeries || !chart) return;

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
    lineSeries.applyOptions({ priceFormat });
    areaSeries.applyOptions({ priceFormat });

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
        lineSeries.update(closePoints[index]);
        areaSeries.update(closePoints[index]);
        volumeSeries.update(volumePoints[index]);
      }
    } else {
      candleSeries.setData(candlePoints);
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

  return (
    <div className="chart-stage">
      <div ref={containerRef} className="chart-canvas" />
      {patternOverlay && (
        <div className="chart-pattern-overlay" aria-hidden="true">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none">
            <line
              className="pattern-start-line"
              x1={patternOverlay.startX}
              x2={patternOverlay.startX}
              y1="0"
              y2="100"
            />
          </svg>
        </div>
      )}
      <button
        className="chart-reset"
        type="button"
        disabled={candles.length === 0}
        onClick={resetViewport}
      >
        AUTO FIT
      </button>
      {hasMore && (
        <div className="tv-drawing-rail" aria-label={drawCountLabel}>
          <button
            type="button"
            title="Paste copied drawing"
            disabled={!hasCopiedDrawing}
            onClick={pasteCopiedDrawing}
          >
            Paste
          </button>
          <button
            type="button"
            title="Delete selected drawing"
            disabled={selectedDrawing === null}
            onClick={deleteSelectedDrawing}
          >
            Delete
          </button>
          <button type="button" title="Clear drawings" onClick={clearDrawings}>
            Clear
          </button>
        </div>
      )}
      {hasMore && (
        <button
          className="chart-load-earlier"
          type="button"
          disabled={historyLoading}
          onClick={onLoadEarlier}
        >
          {historyLoading ? "Loading..." : "Load earlier"}
        </button>
      )}

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
