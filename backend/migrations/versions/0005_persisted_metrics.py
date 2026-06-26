"""Persist metric points, events, and summaries.

Revision ID: 0005_persisted_metrics
Revises: 0004_auth
Create Date: 2026-06-26
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0005_persisted_metrics"
down_revision: Union[str, None] = "0004_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE metric_points (
            exchange TEXT NOT NULL,
            market_type TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            metrics_version TEXT NOT NULL,
            open_time TIMESTAMPTZ NOT NULL,
            close_time TIMESTAMPTZ NOT NULL,
            close DOUBLE PRECISION NULL,
            vwap DOUBLE PRECISION NULL,
            vwap_deviation_pct DOUBLE PRECISION NULL,
            realized_volatility_pct DOUBLE PRECISION NULL,
            parkinson_volatility_pct DOUBLE PRECISION NULL,
            garman_klass_volatility_pct DOUBLE PRECISION NULL,
            rsi DOUBLE PRECISION NULL,
            short_momentum_pct DOUBLE PRECISION NULL,
            momentum_pct DOUBLE PRECISION NULL,
            mean_reversion_z_score DOUBLE PRECISION NULL,
            distance_to_mean_pct DOUBLE PRECISION NULL,
            price_volume_divergence_pct DOUBLE PRECISION NULL,
            volume_spike_ratio DOUBLE PRECISION NULL,
            base_volume DOUBLE PRECISION NULL,
            trade_count INTEGER NOT NULL CHECK (trade_count >= 0),
            status TEXT NULL,
            source TEXT NULL,
            source_candle_revision INTEGER NULL,
            source_candle_status TEXT NULL,
            source_candle_finalized_at TIMESTAMPTZ NULL,
            calculated_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (
                exchange,
                market_type,
                instrument_id,
                timeframe,
                metrics_version,
                open_time
            ),
            CHECK (close_time > open_time)
        )
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'metric_points',
            'open_time',
            if_not_exists => TRUE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX metric_points_stream_time_idx
        ON metric_points (
            exchange,
            market_type,
            instrument_id,
            timeframe,
            metrics_version,
            open_time DESC
        )
        """
    )

    op.execute(
        """
        CREATE TABLE metric_events (
            exchange TEXT NOT NULL,
            market_type TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            metrics_version TEXT NOT NULL,
            open_time TIMESTAMPTZ NOT NULL,
            event_key TEXT NOT NULL,
            close_time TIMESTAMPTZ NOT NULL,
            type TEXT NOT NULL,
            metric TEXT NOT NULL,
            severity TEXT NOT NULL CHECK (severity IN ('medium', 'high')),
            confidence DOUBLE PRECISION NULL,
            value DOUBLE PRECISION NULL,
            threshold DOUBLE PRECISION NULL,
            description TEXT NOT NULL,
            calculated_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (
                exchange,
                market_type,
                instrument_id,
                timeframe,
                metrics_version,
                open_time,
                event_key
            ),
            CHECK (close_time > open_time)
        )
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'metric_events',
            'open_time',
            if_not_exists => TRUE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX metric_events_stream_time_idx
        ON metric_events (
            exchange,
            market_type,
            instrument_id,
            timeframe,
            metrics_version,
            open_time DESC
        )
        """
    )

    op.execute(
        """
        CREATE TABLE metric_summaries (
            exchange TEXT NOT NULL,
            market_type TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            metrics_version TEXT NOT NULL,
            window_name TEXT NOT NULL,
            window_start TIMESTAMPTZ NOT NULL,
            window_end TIMESTAMPTZ NOT NULL,
            point_count INTEGER NOT NULL CHECK (point_count >= 0),
            source TEXT NOT NULL,
            summary JSONB NOT NULL,
            latest JSONB NULL,
            windows JSONB NOT NULL,
            events JSONB NOT NULL,
            cross_pair_correlations JSONB NOT NULL,
            calculated_at TIMESTAMPTZ NOT NULL,
            compute_duration_ms INTEGER NOT NULL CHECK (compute_duration_ms >= 0),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (
                exchange,
                market_type,
                instrument_id,
                timeframe,
                metrics_version,
                window_name
            ),
            CHECK (window_end >= window_start)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX metric_summaries_updated_idx
        ON metric_summaries (updated_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS metric_summaries")
    op.execute("DROP TABLE IF EXISTS metric_events")
    op.execute("DROP TABLE IF EXISTS metric_points")
