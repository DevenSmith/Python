"""Add append-only security audit events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_security_audit_events"
down_revision: str | None = "0002_user_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "security_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_security_audit_events_created_at"),
        "security_audit_events",
        ["created_at"],
    )
    op.create_index(
        op.f("ix_security_audit_events_event_type"),
        "security_audit_events",
        ["event_type"],
    )
    op.create_index(
        op.f("ix_security_audit_events_user_id"),
        "security_audit_events",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_security_audit_events_user_id"),
        table_name="security_audit_events",
    )
    op.drop_index(
        op.f("ix_security_audit_events_event_type"),
        table_name="security_audit_events",
    )
    op.drop_index(
        op.f("ix_security_audit_events_created_at"),
        table_name="security_audit_events",
    )
    op.drop_table("security_audit_events")
