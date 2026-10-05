"""Store the source channel name for lesson catalog cards and search."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6c0d715350a3"
down_revision: Union[str, Sequence[str], None] = "1de46002d80e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("Lesson", sa.Column("channel_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("Lesson", "channel_name")
