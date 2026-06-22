"""Add exchange historical candle backfill storage.

Revision ID: 0003_historical_candles
Revises: 0002_history_rollups
Create Date: 2026-06-16
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0003_historical_candles"
down_revision: Union[str, None] = "0002_history_rollups"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE historical_candles (
            exchange TEXT NOT NULL,
            market_type TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            source TEXT NOT NULL,
            source_symbol TEXT NOT NULL,
            open_time TIMESTAMPTZ NOT NULL,
            close_time TIMESTAMPTZ NOT NULL,
            open NUMERIC(38, 18) NOT NULL CHECK (open > 0),
            high NUMERIC(38, 18) NOT NULL CHECK (high > 0),
            low NUMERIC(38, 18) NOT NULL CHECK (low > 0),
            close NUMERIC(38, 18) NOT NULL CHECK (close > 0),
            base_volume NUMERIC(38, 18) NOT NULL CHECK (base_volume >= 0),
            quote_volume NUMERIC(38, 18) NOT NULL CHECK (quote_volume >= 0),
            trade_count INTEGER NOT NULL CHECK (trade_count >= 0),
            status TEXT NOT NULL CHECK (
                status IN (
                    'complete',
                    'complete_empty',
                    'recovered',
                    'incomplete'
                )
            ),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            finalized_at TIMESTAMPTZ NOT NULL,
            imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (
                exchange, market_type, instrument_id, timeframe,
                open_time, source
            ),
            CHECK (high >= open),
            CHECK (high >= close),
            CHECK (low <= open),
            CHECK (low <= close),
            CHECK (high >= low),
            CHECK (close_time > open_time)
        )
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'historical_candles',
            'open_time',
            if_not_exists => TRUE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX historical_candles_stream_time_idx
        ON historical_candles (
            exchange,
            market_type,
            instrument_id,
            timeframe,
            open_time DESC
        )
        """
    )
    op.execute(
        """
        ALTER TABLE historical_candles SET (
            timescaledb.compress,
            timescaledb.compress_segmentby =
                'exchange,market_type,instrument_id,timeframe,source',
            timescaledb.compress_orderby = 'open_time DESC'
        )
        """
    )
    op.execute(
        """
        SELECT add_compression_policy(
            'historical_candles',
            INTERVAL '7 days',
            if_not_exists => TRUE
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        SELECT remove_compression_policy(
            'historical_candles',
            if_exists => TRUE
        )
        """
    )
    op.execute("DROP TABLE IF EXISTS historical_candles")
