"""Add experience points to characters."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_character_experience"
down_revision: str | None = "0003_security_audit_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column(
            "experience",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    with op.batch_alter_table("characters") as batch_op:
        batch_op.create_check_constraint(
            "ck_characters_experience_nonnegative",
            "experience >= 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("characters") as batch_op:
        batch_op.drop_constraint(
            "ck_characters_experience_nonnegative",
            type_="check",
        )
        batch_op.drop_column("experience")
