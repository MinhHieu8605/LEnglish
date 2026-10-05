"""Deduplicate learning time reports per user without changing old events."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f21d6e930b"
down_revision: Union[str, Sequence[str], None] = "6c0d715350a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ActivityEvent", sa.Column("event_id", sa.String(36), nullable=True))
    op.create_unique_constraint(
        "uq_activity_events_user_event", "ActivityEvent", ["user_id", "event_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_activity_events_user_event", "ActivityEvent", type_="unique")
    op.drop_column("ActivityEvent", "event_id")
