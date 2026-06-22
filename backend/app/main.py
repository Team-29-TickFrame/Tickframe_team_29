import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .auth import AuthConflict, AuthInvalidCredentials, AuthService
from .config import load_config
from .history import TIMEFRAME_SECONDS
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
    description=(
        "Canonical Spot trades and historical OHLCV from Binance and Bybit."
    ),
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


@app.websocket("/ws/v1/markets")
async def market_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    last_revision = -1
    try:
        while True:
            if service.store.revision != last_revision:
                snapshot = await service.store.market_snapshot(unix_ms())
                await websocket.send_json(snapshot)
                last_revision = snapshot["revision"]
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return
