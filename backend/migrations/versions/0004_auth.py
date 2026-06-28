"""Add user authentication storage.

Revision ID: 0004_auth
Revises: 0003_historical_candles
Create Date: 2026-06-20
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0004_auth"
down_revision: Union[str, None] = "0003_historical_candles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_users (
            id UUID PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS auth_sessions_user_idx
        ON auth_sessions (user_id, expires_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth_sessions")
    op.execute("DROP TABLE IF EXISTS auth_users")
