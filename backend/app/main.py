import json
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .auth import AuthConflict, AuthInvalidCredentials, AuthService
from .config import load_config
from .history import TIMEFRAME_SECONDS
from .pattern_ml import pattern_ml_detector
from .service import MarketDataService


def unix_ms() -> int:
    return int(time.time() * 1000)


config = load_config()
service = MarketDataService(config)
auth_service = AuthService()


class RegisterRequest(BaseModel):
    email: str
    password: str
    displayName: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class DisplayLatencySample(BaseModel):
    channel: str
    exchange: str
    instrument_id: str = Field(alias="instrumentId")
    timeframe: Optional[str] = None
    price: Optional[str] = None
    exchange_timestamp: Optional[int] = Field(
        default=None,
        alias="exchangeTimestamp",
    )
    backend_received_at: Optional[int] = Field(
        default=None,
        alias="backendReceivedAt",
    )
    backend_generated_at: Optional[int] = Field(
        default=None,
        alias="backendGeneratedAt",
    )
    data_timestamp: Optional[int] = Field(default=None, alias="dataTimestamp")
    frontend_received_at: int = Field(alias="frontendReceivedAt")
    displayed_at: int = Field(alias="displayedAt")


class DisplayLatencyRequest(BaseModel):
    samples: list[DisplayLatencySample]


def model_dump_aliases(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(by_alias=True)
    return model.dict(by_alias=True)


def ensure_supported_market(exchange: str, instrument_id: str) -> None:
    if exchange not in config.exchanges:
        raise HTTPException(status_code=400, detail="Unsupported exchange")
    instrument = config.instrument_by_id(instrument_id)
    if instrument is None:
        raise HTTPException(status_code=400, detail="Unsupported instrument")
    if exchange not in instrument.symbols:
        raise HTTPException(
            status_code=400,
            detail="Instrument unavailable on exchange",
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await auth_service.start()
    if os.getenv("TICKFRAME_DISABLE_COLLECTORS") != "1":
        await service.start()
    yield
    if os.getenv("TICKFRAME_DISABLE_COLLECTORS") != "1":
        await service.stop()
    await auth_service.stop()


app = FastAPI(
    title="Tickframe Market Data API",
    version="0.3.0",
    description=("Canonical Spot trades and historical OHLCV from Binance and Bybit."),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://tickframe.h1n.ru",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.get("/health")
async def health() -> dict:
    return service.health()


@app.get("/metrics")
async def prometheus_metrics() -> Response:
    return Response(
        content=service.prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/api/v1/observability/latency")
async def latency_observability() -> dict:
    return service.observability_snapshot()


@app.post("/api/v1/telemetry/display-latency")
async def display_latency(payload: DisplayLatencyRequest) -> dict:
    accepted = service.record_frontend_display_latency(
        [model_dump_aliases(sample) for sample in payload.samples]
    )
    return {"accepted": accepted}


def bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization")
    return token


@app.post("/api/v1/auth/register")
async def register(payload: RegisterRequest) -> dict:
    try:
        return await auth_service.register(
            email=payload.email,
            password=payload.password,
            display_name=payload.displayName,
        )
    except AuthConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/v1/auth/login")
async def login(payload: LoginRequest) -> dict:
    try:
        return await auth_service.login(
            email=payload.email,
            password=payload.password,
        )
    except (AuthInvalidCredentials, ValueError) as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.get("/api/v1/auth/me")
async def current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    user = await auth_service.current_user(bearer_token(authorization))
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired")
    return {"user": user.to_api()}


@app.post("/api/v1/auth/logout")
async def logout(authorization: Optional[str] = Header(default=None)) -> dict:
    await auth_service.logout(bearer_token(authorization))
    return {"status": "ok"}


@app.get("/api/v1/instruments")
async def instruments() -> dict:
    return {
        "configVersion": config.config_version,
        "marketType": config.market_type,
        "instruments": [
            {
                "instrumentId": instrument.instrument_id,
                "name": instrument.name,
                "base": instrument.base,
                "quote": instrument.quote,
                "symbols": instrument.symbols,
            }
            for instrument in config.instruments
        ],
    }


@app.get("/api/v1/markets")
async def markets(exchange: Optional[str] = None) -> dict:
    if exchange is not None and exchange not in config.exchanges:
        raise HTTPException(status_code=400, detail="Unsupported exchange")
    return await service.store.market_snapshot(unix_ms(), exchange=exchange)


@app.get("/api/v1/candles")
async def candles(
    exchange: str,
    instrument_id: str = Query(alias="instrumentId"),
    timeframe: str = Query(default="1s"),
    from_ms: Optional[int] = Query(default=None, alias="from", ge=0),
    to_ms: Optional[int] = Query(default=None, alias="to", ge=1),
    limit: int = Query(default=1000, ge=1, le=5000),
) -> dict:
    ensure_supported_market(exchange, instrument_id)
    if timeframe not in TIMEFRAME_SECONDS:
        raise HTTPException(status_code=400, detail="Unsupported timeframe")
    if from_ms is not None and to_ms is not None and from_ms >= to_ms:
        raise HTTPException(
            status_code=400,
            detail="'from' must be less than 'to'",
        )
    try:
        return await service.candle_history(
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            limit=limit,
            from_ms=from_ms,
            to_ms=to_ms,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/v1/metrics")
async def metrics(
    exchange: str,
    instrument_id: str = Query(alias="instrumentId"),
    timeframe: str = Query(default="1m"),
    from_ms: Optional[int] = Query(default=None, alias="from", ge=0),
    to_ms: Optional[int] = Query(default=None, alias="to", ge=1),
    limit: int = Query(default=300, ge=30, le=5000),
) -> dict:
    ensure_supported_market(exchange, instrument_id)
    if timeframe not in TIMEFRAME_SECONDS:
        raise HTTPException(status_code=400, detail="Unsupported timeframe")
    if from_ms is not None and to_ms is not None and from_ms >= to_ms:
        raise HTTPException(
            status_code=400,
            detail="'from' must be less than 'to'",
        )
    try:
        return await service.metrics_snapshot(
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            limit=limit,
            from_ms=from_ms,
            to_ms=to_ms,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/v1/patterns/ml")
async def ml_patterns(
    exchange: str,
    instrument_id: str = Query(alias="instrumentId"),
    timeframe: str = Query(default="1m"),
) -> dict:
    ensure_supported_market(exchange, instrument_id)
    if timeframe not in TIMEFRAME_SECONDS:
        raise HTTPException(status_code=400, detail="Unsupported timeframe")
    if timeframe != "1m":
        return pattern_ml_detector.predict(
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            source="unsupported",
            candles=[],
        )
    try:
        history = await service.candle_history(
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            limit=240,
            from_ms=None,
            to_ms=None,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return pattern_ml_detector.predict(
        exchange=exchange,
        instrument_id=instrument_id,
        timeframe=timeframe,
        source=str(history["source"]),
        candles=history["candles"],
    )


@app.websocket("/ws/v1/markets")
async def market_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    last_revision = -1
    try:
        while True:
            revision = service.market_stream_revision
            if revision != last_revision:
                snapshot = await service.store.market_snapshot(unix_ms())
                await websocket.send_json(snapshot)
                last_revision = revision
            await service.wait_for_market_update(last_revision)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/v1/metrics")
async def metrics_stream(
    websocket: WebSocket,
    exchange: str,
    instrument_id: str = Query(alias="instrumentId"),
    timeframe: str = Query(default="1m"),
    window: str = Query(default="default"),
) -> None:
    await websocket.accept()
    if (
        exchange not in config.exchanges
        or timeframe not in TIMEFRAME_SECONDS
        or window not in {"default", "24h"}
    ):
        await websocket.close(code=1008)
        return
    try:
        ensure_supported_market(exchange, instrument_id)
    except HTTPException:
        await websocket.close(code=1008)
        return

    last_revision = -1
    try:
        while True:
            revision, snapshot = service.cached_metrics(
                exchange=exchange,
                instrument_id=instrument_id,
                timeframe=timeframe,
                window_name=window,
            )
            if snapshot is not None and revision != last_revision:
                await websocket.send_json(snapshot)
                last_revision = revision
            await service.wait_for_metric_update(
                exchange=exchange,
                instrument_id=instrument_id,
                timeframe=timeframe,
                window_name=window,
                last_revision=last_revision,
            )
    except WebSocketDisconnect:
        return


@app.websocket("/ws/v1/candles/stable")
async def stable_candle_stream(
    websocket: WebSocket,
    exchange: str,
    instrument_id: str = Query(alias="instrumentId"),
    timeframe: str = Query(default="1s"),
    limit: int = Query(default=20, ge=1, le=500),
) -> None:
    await websocket.accept()
    if exchange not in config.exchanges or timeframe not in TIMEFRAME_SECONDS:
        await websocket.close(code=1008)
        return
    try:
        ensure_supported_market(exchange, instrument_id)
    except HTTPException:
        await websocket.close(code=1008)
        return

    last_revision = -1
    last_payload = ""
    try:
        while True:
            revision = service.stable_candle_revision
            if revision != last_revision:
                snapshot = await service.stable_candle_snapshot(
                    exchange=exchange,
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    limit=limit,
                )
                payload = json.dumps(snapshot, sort_keys=True)
                if payload != last_payload:
                    await websocket.send_json(snapshot)
                    last_payload = payload
                last_revision = revision
            await service.wait_for_stable_candle_update(last_revision)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/v1/candles")
async def candle_stream(
    websocket: WebSocket,
    exchange: str,
    instrument_id: str = Query(alias="instrumentId"),
    timeframe: str = Query(default="1s"),
) -> None:
    await websocket.accept()
    if exchange not in config.exchanges or timeframe not in TIMEFRAME_SECONDS:
        await websocket.close(code=1008)
        return
    try:
        ensure_supported_market(exchange, instrument_id)
    except HTTPException:
        await websocket.close(code=1008)
        return

    last_payload = ""
    last_revision = -1
    try:
        while True:
            revision = service.provisional_candle_revision
            if revision != last_revision:
                snapshot = await service.provisional_candle_snapshot(
                    exchange=exchange,
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                )
                payload = json.dumps(snapshot, sort_keys=True)
                if payload != last_payload:
                    await websocket.send_json(snapshot)
                    last_payload = payload
                last_revision = revision
            await service.wait_for_provisional_candle_update(last_revision)
    except WebSocketDisconnect:
        return
