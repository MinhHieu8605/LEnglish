"""Rename word-list tables and move lesson models into the lesson feature."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_09_29_word_lists_lesson"
down_revision: Union[str, Sequence[str], None] = "2026_09_28_review_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_RENAMES = (
    ("WordList", "pk_Notebook", "pk_WordList"),
    ("WordList", "fk_Notebook_user_id_User", "fk_WordList_user_id_User"),
    ("WordList", "uq_notebooks_user_id_name", "uq_word_lists_user_id_name"),
    ("WordListItem", "pk_NotebookItem", "pk_WordListItem"),
    (
        "WordListItem",
        "fk_NotebookItem_notebook_id_Notebook",
        "fk_WordListItem_word_list_id_WordList",
    ),
    (
        "WordListItem",
        "fk_NotebookItem_vocabulary_id_Vocabulary",
        "fk_WordListItem_vocabulary_id_Vocabulary",
    ),
    (
        "WordListItem",
        "fk_NotebookItem_source_subtitle_id_Subtitle",
        "fk_WordListItem_source_subtitle_id_Subtitle",
    ),
    (
        "WordListItem",
        "uq_notebook_items_notebook_id_vocabulary_id",
        "uq_word_list_items_word_list_id_vocabulary_id",
    ),
)


def upgrade() -> None:
    op.execute(
        sa.text(
            'UPDATE "NotebookItem" AS item '
            'SET source_subtitle_id = vocabulary.source_subtitle_id, '
            'context_sentence = COALESCE(item.context_sentence, subtitle.content_en) '
            'FROM "Vocabulary" AS vocabulary '
            'LEFT JOIN "Subtitle" AS subtitle '
            'ON subtitle.id = vocabulary.source_subtitle_id '
            'WHERE item.vocabulary_id = vocabulary.id '
            'AND item.source_subtitle_id IS NULL '
            'AND item.context_sentence IS NULL '
            'AND vocabulary.source_subtitle_id IS NOT NULL'
        )
    )
    op.rename_table("Notebook", "WordList")
    op.rename_table("NotebookItem", "WordListItem")
    op.alter_column("WordListItem", "notebook_id", new_column_name="word_list_id")

    for table, old_name, new_name in CONSTRAINT_RENAMES:
        op.execute(
            sa.text(
                f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
            )
        )

    op.drop_constraint(
        "fk_Vocabulary_source_subtitle_id_Subtitle",
        "Vocabulary",
        type_="foreignkey",
    )
    op.drop_column("Vocabulary", "source_subtitle_id")


def downgrade() -> None:
    op.add_column(
        "Vocabulary",
        sa.Column("source_subtitle_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            'UPDATE "Vocabulary" AS vocabulary '
            'SET source_subtitle_id = ('
            'SELECT item.source_subtitle_id FROM "WordListItem" AS item '
            'WHERE item.vocabulary_id = vocabulary.id '
            'AND item.source_subtitle_id IS NOT NULL ORDER BY item.id LIMIT 1'
            ')'
        )
    )
    op.create_foreign_key(
        "fk_Vocabulary_source_subtitle_id_Subtitle",
        "Vocabulary",
        "Subtitle",
        ["source_subtitle_id"],
        ["id"],
        ondelete="SET NULL",
    )

    for table, old_name, new_name in reversed(CONSTRAINT_RENAMES):
        op.execute(
            sa.text(
                f'ALTER TABLE "{table}" RENAME CONSTRAINT "{new_name}" TO "{old_name}"'
            )
        )

    op.alter_column("WordListItem", "word_list_id", new_column_name="notebook_id")
    op.rename_table("WordListItem", "NotebookItem")
    op.rename_table("WordList", "Notebook")
