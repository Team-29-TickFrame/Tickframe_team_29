"""Create raw trades and revisioned 1s candles.

Revision ID: 0001_market_data
Revises:
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0001_market_data"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute(
        """
        CREATE TABLE raw_trades (
            exchange TEXT NOT NULL,
            market_type TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            exchange_symbol TEXT NOT NULL,
            trade_id TEXT NOT NULL,
            exchange_time TIMESTAMPTZ NOT NULL,
            received_time TIMESTAMPTZ NOT NULL,
            price NUMERIC(38, 18) NOT NULL CHECK (price > 0),
            base_quantity NUMERIC(38, 18) NOT NULL CHECK (base_quantity >= 0),
            quote_quantity NUMERIC(38, 18) NOT NULL CHECK (quote_quantity >= 0),
            side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
            sequence BIGINT NULL,
            inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (
                exchange, market_type, instrument_id, trade_id, exchange_time
            )
        )
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'raw_trades',
            'exchange_time',
            if_not_exists => TRUE
        )
        """
    )
    op.execute(
        """
        SELECT add_retention_policy(
            'raw_trades',
            INTERVAL '72 hours',
            if_not_exists => TRUE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX raw_trades_stream_time_idx
        ON raw_trades (
            exchange, market_type, instrument_id, exchange_time DESC
        )
        """
    )

    op.execute(
        """
        CREATE TABLE candles (
            exchange TEXT NOT NULL,
            market_type TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            open_time TIMESTAMPTZ NOT NULL,
            close_time TIMESTAMPTZ NOT NULL,
            open NUMERIC(38, 18) NULL,
            high NUMERIC(38, 18) NULL,
            low NUMERIC(38, 18) NULL,
            close NUMERIC(38, 18) NULL,
            base_volume NUMERIC(38, 18) NOT NULL,
            quote_volume NUMERIC(38, 18) NOT NULL,
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
            first_trade_id TEXT NULL,
            last_trade_id TEXT NULL,
            finalized_at TIMESTAMPTZ NOT NULL,
            current BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (
                exchange, market_type, instrument_id, timeframe,
                open_time, revision
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
            'candles',
            'open_time',
            if_not_exists => TRUE
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX candles_one_current_revision_idx
        ON candles (
            exchange, market_type, instrument_id, timeframe, open_time
        )
        WHERE current = TRUE
        """
    )
    op.execute(
        """
        CREATE INDEX candles_stream_time_idx
        ON candles (
            exchange, market_type, instrument_id, timeframe, open_time DESC
        )
        WHERE current = TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS candles")
    op.execute("DROP TABLE IF EXISTS raw_trades")
