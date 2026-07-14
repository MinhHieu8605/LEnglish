"""add source subtitle to notebook items

Revision ID: b61d7c20a4e1
Revises: 213d4bfb5049
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b61d7c20a4e1"
down_revision: Union[str, Sequence[str], None] = "213d4bfb5049"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notebook_items",
        sa.Column("source_subtitle_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_notebook_items_source_subtitle_id_subtitles",
        "notebook_items",
        "subtitles",
        ["source_subtitle_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_notebook_items_source_subtitle_id_subtitles",
        "notebook_items",
        type_="foreignkey",
    )
    op.drop_column("notebook_items", "source_subtitle_id")
