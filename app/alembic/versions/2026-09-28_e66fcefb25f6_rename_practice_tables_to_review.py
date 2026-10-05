"""Rename vocabulary practice tables to review."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e66fcefb25f6"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_RENAMES = (
    ("ReviewProgress", "pk_practice_progress", "pk_ReviewProgress"),
    ("ReviewProgress", "fk_practice_progress_user_id_users", "fk_ReviewProgress_user_id_User"),
    ("ReviewProgress", "fk_practice_progress_vocabulary_id_vocabularies", "fk_ReviewProgress_vocabulary_id_Vocabulary"),
    ("ReviewProgress", "uq_practice_progress_user_id_vocabulary_id", "uq_review_progress_user_id_vocabulary_id"),
    ("ReviewAttempt", "pk_practice_attempt", "pk_ReviewAttempt"),
    ("ReviewAttempt", "fk_practice_attempt_practice_progress_id_practice_progress", "fk_ReviewAttempt_review_progress_id_ReviewProgress"),
    ("ReviewSession", "pk_PracticeSession", "pk_ReviewSession"),
    ("ReviewSession", "fk_PracticeSession_user_id_User", "fk_ReviewSession_user_id_User"),
    ("ReviewSession", "fk_PracticeSession_topic_id_VocabularyTopic", "fk_ReviewSession_topic_id_VocabularyTopic"),
    ("ReviewSessionItem", "pk_PracticeSessionItem", "pk_ReviewSessionItem"),
    ("ReviewSessionItem", "fk_PracticeSessionItem_session_id_PracticeSession", "fk_ReviewSessionItem_session_id_ReviewSession"),
    ("ReviewSessionItem", "fk_PracticeSessionItem_vocabulary_id_Vocabulary", "fk_ReviewSessionItem_vocabulary_id_Vocabulary"),
    ("ReviewSessionItem", "uq_practice_session_items_session_order", "uq_review_session_items_session_order"),
    ("ReviewSessionItem", "uq_practice_session_items_session_vocab", "uq_review_session_items_session_vocab"),
)
INDEX_RENAMES = (
    ("practice_progress_idx", "review_progress_idx"),
    ("practice_attempts_attempt_id_uq", "review_attempts_attempt_id_uq"),
    ("practice_sessions_user_status_idx", "review_sessions_user_status_idx"),
)


def upgrade() -> None:
    op.rename_table("PracticeProgress", "ReviewProgress")
    op.rename_table("PracticeAttempt", "ReviewAttempt")
    op.rename_table("PracticeSession", "ReviewSession")
    op.rename_table("PracticeSessionItem", "ReviewSessionItem")
    op.alter_column(
        "ReviewAttempt",
        "practice_progress_id",
        new_column_name="review_progress_id",
    )

    for table, old_name, new_name in CONSTRAINT_RENAMES:
        op.execute(
            sa.text(
                f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
            )
        )

    for old_name, new_name in INDEX_RENAMES:
        op.execute(sa.text(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"'))


def downgrade() -> None:
    for table, old_name, new_name in reversed(CONSTRAINT_RENAMES):
        op.execute(
            sa.text(
                f'ALTER TABLE "{table}" RENAME CONSTRAINT "{new_name}" TO "{old_name}"'
            )
        )

    for old_name, new_name in reversed(INDEX_RENAMES):
        op.execute(sa.text(f'ALTER INDEX "{new_name}" RENAME TO "{old_name}"'))

    op.alter_column(
        "ReviewAttempt",
        "review_progress_id",
        new_column_name="practice_progress_id",
    )
    op.rename_table("ReviewSessionItem", "PracticeSessionItem")
    op.rename_table("ReviewSession", "PracticeSession")
    op.rename_table("ReviewAttempt", "PracticeAttempt")
    op.rename_table("ReviewProgress", "PracticeProgress")
