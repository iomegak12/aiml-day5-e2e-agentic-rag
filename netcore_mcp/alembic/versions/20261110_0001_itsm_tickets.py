"""itsm schema: IT support tickets mirrored to Jira

Revision ID: itsm_0001
Revises:
Create Date: 2026-11-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "itsm_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "itsm"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    op.create_table(
        "tickets",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ticket_id", sa.String(16), sa.Computed("'TKT-' || lpad(id::text, 6, '0')", persisted=True),
                  nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("registered_by", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("product_family", sa.String(32), nullable=False),
        sa.Column("region", sa.String(8), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), server_default="open", nullable=False),
        sa.Column("resolved_by", sa.String(64)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("remarks", sa.Text()),
        sa.Column("jira_id", sa.String(32)),
        sa.Column("jira_key", sa.String(32)),
        sa.Column("jira_url", sa.String(300)),
        sa.Column("jira_status", sa.String(32)),
        sa.Column("jira_comment_id", sa.String(32)),
        sa.Column("jira_sync", sa.String(16), server_default="pending", nullable=False),
        sa.Column("jira_error", sa.Text()),
        sa.Column("jira_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("ticket_id", name="uq_tickets_ticket_id"),
        sa.CheckConstraint("product_family IN ('networking', 'meetings')", name="ck_tickets_product_family"),
        sa.CheckConstraint("region IN ('AMER', 'EMEA', 'APAC')", name="ck_tickets_region"),
        sa.CheckConstraint("severity IN ('critical', 'high', 'medium', 'low')", name="ck_tickets_severity"),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_tickets_status"),
        sa.CheckConstraint("jira_sync IN ('pending', 'synced')", name="ck_tickets_jira_sync"),
        schema=SCHEMA,
    )
    op.create_index("ix_tickets_registered_by_status", "tickets", ["registered_by", "status"], schema=SCHEMA)
    op.create_index("ix_tickets_status", "tickets", ["status"], schema=SCHEMA)
    op.create_index("ix_tickets_jira_sync", "tickets", ["jira_sync"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("tickets", schema=SCHEMA)  # the schema (and its alembic_version table) is kept
