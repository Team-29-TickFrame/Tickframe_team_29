"""Add daily candle rollup.

Revision ID: 0006_daily_candle_rollup
Revises: 0005_persisted_metrics
Create Date: 2026-07-10
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0006_daily_candle_rollup"
down_revision: Union[str, None] = "0005_persisted_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW candles_1d
        WITH (timescaledb.continuous) AS
        SELECT
            exchange,
            market_type,
            instrument_id,
            time_bucket(INTERVAL '1 day', open_time) AS open_time,
            first(open, open_time) FILTER (WHERE open IS NOT NULL) AS open,
            max(high) AS high,
            min(low) AS low,
            last(close, open_time) FILTER (WHERE close IS NOT NULL) AS close,
            sum(base_volume) AS base_volume,
            sum(quote_volume) AS quote_volume,
            sum(trade_count)::BIGINT AS trade_count,
            count(*)::BIGINT AS source_candle_count,
            count(*) FILTER (
                WHERE status = 'incomplete'
            )::BIGINT AS incomplete_count,
            count(*) FILTER (
                WHERE status = 'recovered'
            )::BIGINT AS recovered_count,
            max(revision) AS revision,
            max(finalized_at) AS finalized_at
        FROM candles
        WHERE timeframe = '1s' AND current = TRUE
        GROUP BY
            exchange,
            market_type,
            instrument_id,
            time_bucket(INTERVAL '1 day', open_time)
        WITH NO DATA
        """
    )
    op.execute(
        """
        ALTER MATERIALIZED VIEW candles_1d
        SET (timescaledb.materialized_only = FALSE)
        """
    )
    op.execute(
        """
        CREATE INDEX candles_1d_stream_time_idx
        ON candles_1d (
            exchange,
            instrument_id,
            open_time DESC
        )
        """
    )
    op.execute(
        """
        SELECT add_continuous_aggregate_policy(
            'candles_1d',
            start_offset => INTERVAL '30 days',
            end_offset => INTERVAL '1 day',
            schedule_interval => INTERVAL '1 hour',
            if_not_exists => TRUE
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS candles_1d")
