"""Track login sessions across refresh-token rotations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_sessions"
down_revision: str | None = "0001_current_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("compromised_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"])
    with op.batch_alter_table("auth_tokens") as batch_op:
        batch_op.add_column(sa.Column("session_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_auth_tokens_session_id_user_sessions",
            "user_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(op.f("ix_auth_tokens_session_id"), ["session_id"])


def downgrade() -> None:
    with op.batch_alter_table("auth_tokens") as batch_op:
        batch_op.drop_index(op.f("ix_auth_tokens_session_id"))
        batch_op.drop_constraint(
            "fk_auth_tokens_session_id_user_sessions", type_="foreignkey"
        )
        batch_op.drop_column("session_id")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")
