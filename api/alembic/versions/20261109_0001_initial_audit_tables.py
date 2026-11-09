"""initial audit tables: api_requests, agent_runs

Revision ID: 0001
Revises:
Create Date: 2026-11-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "api_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("route", sa.String(256)),
        sa.Column("query_string", sa.Text()),
        sa.Column("client_ip", sa.String(64)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("user_id", sa.String(64)),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("request_headers", JSON),
        sa.Column("request_body", JSON),
        sa.Column("response_headers", JSON),
        sa.Column("response_body", JSON),
        sa.Column("body_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("correlation_id", sa.String(128)),
    )
    op.create_index("ix_api_requests_created_at", "api_requests", ["created_at"])
    op.create_index("ix_api_requests_path", "api_requests", ["path"])
    op.create_index("ix_api_requests_client_ip", "api_requests", ["client_ip"])
    op.create_index("ix_api_requests_user_id", "api_requests", ["user_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("client_ip", sa.String(64)),
        sa.Column("endpoint", sa.String(16), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", JSON, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("agent_status", sa.String(32)),
        sa.Column("client_disconnected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("elapsed_s", sa.Float()),
        sa.Column("result", JSON),
        sa.Column("error", JSON),
    )
    op.create_index("ix_agent_runs_user_created", "agent_runs", ["user_id", "created_at"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("api_requests")
