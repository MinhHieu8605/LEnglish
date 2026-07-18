"""shorten index names

Revision ID: c7e21d6b984a
Revises: b61d7c20a4e1
Create Date: 2026-07-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c7e21d6b984a"
down_revision: Union[str, Sequence[str], None] = "b61d7c20a4e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_RENAMES = (
    ("ix_dictionary_lookups_user_id_created_time", "dictionary_lookups_idx"),
    ("ix_lessons_status_published_at", "lessons_idx"),
    ("ix_lessons_category_id_status", "lessons_category_idx"),
    ("ix_lessons_difficulty_status", "lessons_difficulty_idx"),
    ("ix_notifications_user_id_is_read_created_time", "notifications_idx"),
    ("ix_learning_progress_user_id_last_watched_at", "learning_progress_idx"),
    ("ix_subtitles_lesson_id_start_ms", "subtitles_idx"),
    ("ix_messages_conversation_id_created_time", "messages_idx"),
    ("uq_vocabularies_word_word_type", "vocabularies_idx"),
    ("ix_vocabularies_word", "vocabularies_word_idx"),
    ("ix_activity_events_user_id_created_time", "activity_events_idx"),
    ("ix_activity_events_user_id_type_created_time", "activity_events_type_idx"),
    ("ix_vocabulary_progress_user_id_status_next_review_at", "vocabulary_progress_idx"),
)


def upgrade() -> None:
    op.drop_index("ix_user_roles_email", table_name="user_roles")
    for old_name, new_name in INDEX_RENAMES:
        op.execute(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"')


def downgrade() -> None:
    for old_name, new_name in reversed(INDEX_RENAMES):
        op.execute(f'ALTER INDEX "{new_name}" RENAME TO "{old_name}"')
    op.create_index("ix_user_roles_email", "user_roles", ["email"], unique=False)
