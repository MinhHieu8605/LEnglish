"""rename tables to model names

Revision ID: d4f8a12c6e30
Revises: c7e21d6b984a
Create Date: 2026-07-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d4f8a12c6e30"
down_revision: Union[str, Sequence[str], None] = "c7e21d6b984a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_RENAMES = (
    ("users", "User"),
    ("user_roles", "UserRole"),
    ("tokens", "Token"),
    ("user_preferences", "UserPreferences"),
    ("categories", "Category"),
    ("tags", "Tag"),
    ("lessons", "Lesson"),
    ("lesson_tags", "LessonTag"),
    ("subtitles", "Subtitle"),
    ("learning_progress", "LearningProgress"),
    ("practice_sessions", "PracticeSession"),
    ("practice_answers", "PracticeAnswer"),
    ("scenarios", "Scenario"),
    ("conversations", "Conversation"),
    ("messages", "Message"),
    ("activity_events", "ActivityEvent"),
    ("achievements", "Achievement"),
    ("achievement_unlocks", "AchievementUnlock"),
    ("streaks", "Streak"),
    ("dictionary_lookups", "DictionaryLookup"),
    ("notifications", "Notification"),
    ("notebooks", "Notebook"),
    ("notebook_items", "NotebookItem"),
    ("vocabularies", "Vocabulary"),
    ("vocabulary_progress", "VocabularyProgress"),
    ("vocabulary_review_logs", "VocabularyReviewLog"),
    ("vocabulary_books", "VocabularyBook"),
    ("vocabulary_topics", "VocabularyTopic"),
    ("vocabulary_topic_words", "VocabularyTopicWord"),
)


def upgrade() -> None:
    for old_name, new_name in TABLE_RENAMES:
        op.rename_table(old_name, new_name)
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('feedback') IS NOT NULL
                AND to_regclass('"Feedback"') IS NULL THEN
                ALTER TABLE feedback RENAME TO "Feedback";
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('"Feedback"') IS NOT NULL
                AND to_regclass('feedback') IS NULL THEN
                ALTER TABLE "Feedback" RENAME TO feedback;
            END IF;
        END $$
        """
    )
    for old_name, new_name in reversed(TABLE_RENAMES):
        op.rename_table(new_name, old_name)
