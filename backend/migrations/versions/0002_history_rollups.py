"""Add historical rollups, compression, and candle retention.

Revision ID: 0002_history_rollups
Revises: 0001_market_data
Create Date: 2026-06-15
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0002_history_rollups"
down_revision: Union[str, None] = "0001_market_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLLUPS = (
    ("candles_1m", "1 minute", "1 minute", "30 seconds"),
    ("candles_5m", "5 minutes", "5 minutes", "1 minute"),
    ("candles_15m", "15 minutes", "15 minutes", "5 minutes"),
    ("candles_1h", "1 hour", "1 hour", "15 minutes"),
)


def upgrade() -> None:
    op.execute(
        """
        SELECT set_chunk_time_interval('raw_trades', INTERVAL '6 hours')
        """
    )
    op.execute(
        """
        SELECT set_chunk_time_interval('candles', INTERVAL '1 day')
        """
    )
    op.execute(
        """
        ALTER TABLE candles SET (
            timescaledb.compress,
            timescaledb.compress_segmentby =
                'exchange,market_type,instrument_id,timeframe',
            timescaledb.compress_orderby = 'open_time DESC,revision DESC'
        )
        """
    )
    op.execute(
        """
        SELECT add_compression_policy(
            'candles',
            INTERVAL '6 hours',
            if_not_exists => TRUE
        )
        """
    )
    op.execute(
        """
        SELECT add_retention_policy(
            'candles',
            INTERVAL '14 days',
            if_not_exists => TRUE
        )
        """
    )

    for view_name, bucket, end_offset, schedule in ROLLUPS:
        op.execute(
            f"""
            CREATE MATERIALIZED VIEW {view_name}
            WITH (timescaledb.continuous) AS
            SELECT
                exchange,
                market_type,
                instrument_id,
                time_bucket(INTERVAL '{bucket}', open_time) AS open_time,
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
                time_bucket(INTERVAL '{bucket}', open_time)
            WITH NO DATA
            """
        )
        op.execute(
            f"""
            ALTER MATERIALIZED VIEW {view_name}
            SET (timescaledb.materialized_only = FALSE)
            """
        )
        op.execute(
            f"""
            CREATE INDEX {view_name}_stream_time_idx
            ON {view_name} (
                exchange,
                instrument_id,
                open_time DESC
            )
            """
        )
        op.execute(
            f"""
            SELECT add_continuous_aggregate_policy(
                '{view_name}',
                start_offset => INTERVAL '13 days',
                end_offset => INTERVAL '{end_offset}',
                schedule_interval => INTERVAL '{schedule}',
                if_not_exists => TRUE
            )
            """
        )


def downgrade() -> None:
    for view_name, _, _, _ in reversed(ROLLUPS):
        op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {view_name} CASCADE")

    op.execute(
        """
        SELECT remove_retention_policy('candles', if_exists => TRUE)
        """
    )
    op.execute(
        """
        SELECT remove_compression_policy('candles', if_exists => TRUE)
        """
    )
