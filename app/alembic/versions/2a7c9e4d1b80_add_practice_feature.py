"""add practice feature

Revision ID: 2a7c9e4d1b80
Revises: fcd02fc77104
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2a7c9e4d1b80"
down_revision: Union[str, Sequence[str], None] = "fcd02fc77104"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_constraint(table: str, old_name: str, new_name: str) -> None:
    op.execute(
        f'ALTER TABLE "{table}" RENAME CONSTRAINT '
        f'"{old_name}" TO "{new_name}"'
    )


def upgrade() -> None:
    op.rename_table("LearningProgress", "LessonProgress")
    op.rename_table("PracticeSession", "LessonSession")
    op.rename_table("PracticeAnswer", "LessonAnswer")
    op.rename_table("VocabularyProgress", "PracticeProgress")
    op.rename_table("VocabularyReviewLog", "PracticeAttempt")

    op.alter_column(
        "PracticeAttempt",
        "vocabulary_progress_id",
        new_column_name="practice_progress_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "ActivityEvent",
        "practice_session_id",
        new_column_name="lesson_session_id",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )

    constraint_renames = (
        ("LessonProgress", "pk_learning_progress", "pk_lesson_progress"),
        (
            "LessonProgress",
            "fk_learning_progress_lesson_id_lessons",
            "fk_lesson_progress_lesson_id_lessons",
        ),
        (
            "LessonProgress",
            "fk_learning_progress_user_id_users",
            "fk_lesson_progress_user_id_users",
        ),
        (
            "LessonProgress",
            "uq_learning_progress_user_id_lesson_id",
            "uq_lesson_progress_user_id_lesson_id",
        ),
        ("LessonSession", "pk_practice_sessions", "pk_lesson_session"),
        (
            "LessonSession",
            "fk_practice_sessions_lesson_id_lessons",
            "fk_lesson_session_lesson_id_lessons",
        ),
        (
            "LessonSession",
            "fk_practice_sessions_user_id_users",
            "fk_lesson_session_user_id_users",
        ),
        ("LessonAnswer", "pk_practice_answers", "pk_lesson_answer"),
        (
            "LessonAnswer",
            "fk_practice_answers_session_id_practice_sessions",
            "fk_lesson_answer_session_id_lesson_session",
        ),
        (
            "LessonAnswer",
            "fk_practice_answers_subtitle_id_subtitles",
            "fk_lesson_answer_subtitle_id_subtitles",
        ),
        (
            "LessonAnswer",
            "uq_practice_answers_session_id_subtitle_id",
            "uq_lesson_answers_session_id_subtitle_id",
        ),
        ("PracticeProgress", "pk_vocabulary_progress", "pk_practice_progress"),
        (
            "PracticeProgress",
            "fk_vocabulary_progress_user_id_users",
            "fk_practice_progress_user_id_users",
        ),
        (
            "PracticeProgress",
            "fk_vocabulary_progress_vocabulary_id_vocabularies",
            "fk_practice_progress_vocabulary_id_vocabularies",
        ),
        (
            "PracticeProgress",
            "uq_vocabulary_progress_user_id_vocabulary_id",
            "uq_practice_progress_user_id_vocabulary_id",
        ),
        (
            "PracticeAttempt",
            "pk_vocabulary_review_logs",
            "pk_practice_attempt",
        ),
        (
            "PracticeAttempt",
            "fk_vocabulary_review_logs_vocabulary_progress_id_vocabu_5463",
            "fk_practice_attempt_practice_progress_id_practice_progress",
        ),
        (
            "ActivityEvent",
            "fk_activity_events_practice_session_id_practice_sessions",
            "fk_activity_event_lesson_session",
        ),
    )
    for table, old_name, new_name in constraint_renames:
        _rename_constraint(table, old_name, new_name)

    op.execute(
        'ALTER INDEX "learning_progress_idx" RENAME TO "lesson_progress_idx"'
    )
    op.execute(
        'ALTER INDEX "vocabulary_progress_idx" RENAME TO "practice_progress_idx"'
    )

    op.add_column(
        "PracticeAttempt", sa.Column("attempt_id", sa.String(), nullable=True)
    )
    op.add_column(
        "PracticeAttempt", sa.Column("mode", sa.String(), nullable=True)
    )
    op.add_column(
        "PracticeAttempt", sa.Column("correct", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "PracticeAttempt",
        sa.Column(
            "used_hint", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "PracticeAttempt",
        sa.Column(
            "revealed_answer", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "PracticeAttempt", sa.Column("submitted_answer", sa.Text(), nullable=True)
    )
    op.create_index(
        "practice_attempts_attempt_id_uq",
        "PracticeAttempt",
        ["attempt_id"],
        unique=True,
    )

    op.create_table(
        "PracticeSession",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("initial_mode", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_position", sa.Integer(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["VocabularyTopic.id"],
            name="fk_PracticeSession_topic_id_VocabularyTopic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["User.id"],
            name="fk_PracticeSession_user_id_User",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_PracticeSession"),
    )
    op.create_index(
        "practice_sessions_user_status_idx",
        "PracticeSession",
        ["user_id", "status"],
    )
    op.create_table(
        "PracticeSessionItem",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("vocabulary_id", sa.Integer(), nullable=False),
        sa.Column("order_num", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_id", sa.String(), nullable=True),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["PracticeSession.id"],
            name="fk_PracticeSessionItem_session_id_PracticeSession",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vocabulary_id"],
            ["Vocabulary.id"],
            name="fk_PracticeSessionItem_vocabulary_id_Vocabulary",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_PracticeSessionItem"),
        sa.UniqueConstraint(
            "session_id",
            "vocabulary_id",
            name="uq_practice_session_items_session_vocab",
        ),
        sa.UniqueConstraint(
            "session_id",
            "order_num",
            name="uq_practice_session_items_session_order",
        ),
    )


def downgrade() -> None:
    op.drop_table("PracticeSessionItem")
    op.drop_index(
        "practice_sessions_user_status_idx", table_name="PracticeSession"
    )
    op.drop_table("PracticeSession")

    op.drop_index(
        "practice_attempts_attempt_id_uq", table_name="PracticeAttempt"
    )
    op.drop_column("PracticeAttempt", "submitted_answer")
    op.drop_column("PracticeAttempt", "revealed_answer")
    op.drop_column("PracticeAttempt", "used_hint")
    op.drop_column("PracticeAttempt", "correct")
    op.drop_column("PracticeAttempt", "mode")
    op.drop_column("PracticeAttempt", "attempt_id")

    op.execute(
        'ALTER INDEX "practice_progress_idx" RENAME TO "vocabulary_progress_idx"'
    )
    op.execute(
        'ALTER INDEX "lesson_progress_idx" RENAME TO "learning_progress_idx"'
    )

    constraint_renames = (
        (
            "ActivityEvent",
            "fk_activity_event_lesson_session",
            "fk_activity_events_practice_session_id_practice_sessions",
        ),
        (
            "PracticeAttempt",
            "fk_practice_attempt_practice_progress_id_practice_progress",
            "fk_vocabulary_review_logs_vocabulary_progress_id_vocabu_5463",
        ),
        (
            "PracticeAttempt",
            "pk_practice_attempt",
            "pk_vocabulary_review_logs",
        ),
        (
            "PracticeProgress",
            "uq_practice_progress_user_id_vocabulary_id",
            "uq_vocabulary_progress_user_id_vocabulary_id",
        ),
        (
            "PracticeProgress",
            "fk_practice_progress_vocabulary_id_vocabularies",
            "fk_vocabulary_progress_vocabulary_id_vocabularies",
        ),
        (
            "PracticeProgress",
            "fk_practice_progress_user_id_users",
            "fk_vocabulary_progress_user_id_users",
        ),
        ("PracticeProgress", "pk_practice_progress", "pk_vocabulary_progress"),
        (
            "LessonAnswer",
            "uq_lesson_answers_session_id_subtitle_id",
            "uq_practice_answers_session_id_subtitle_id",
        ),
        (
            "LessonAnswer",
            "fk_lesson_answer_subtitle_id_subtitles",
            "fk_practice_answers_subtitle_id_subtitles",
        ),
        (
            "LessonAnswer",
            "fk_lesson_answer_session_id_lesson_session",
            "fk_practice_answers_session_id_practice_sessions",
        ),
        ("LessonAnswer", "pk_lesson_answer", "pk_practice_answers"),
        (
            "LessonSession",
            "fk_lesson_session_user_id_users",
            "fk_practice_sessions_user_id_users",
        ),
        (
            "LessonSession",
            "fk_lesson_session_lesson_id_lessons",
            "fk_practice_sessions_lesson_id_lessons",
        ),
        ("LessonSession", "pk_lesson_session", "pk_practice_sessions"),
        (
            "LessonProgress",
            "uq_lesson_progress_user_id_lesson_id",
            "uq_learning_progress_user_id_lesson_id",
        ),
        (
            "LessonProgress",
            "fk_lesson_progress_user_id_users",
            "fk_learning_progress_user_id_users",
        ),
        (
            "LessonProgress",
            "fk_lesson_progress_lesson_id_lessons",
            "fk_learning_progress_lesson_id_lessons",
        ),
        ("LessonProgress", "pk_lesson_progress", "pk_learning_progress"),
    )
    for table, old_name, new_name in constraint_renames:
        _rename_constraint(table, old_name, new_name)

    op.alter_column(
        "ActivityEvent",
        "lesson_session_id",
        new_column_name="practice_session_id",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "PracticeAttempt",
        "practice_progress_id",
        new_column_name="vocabulary_progress_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    op.rename_table("PracticeAttempt", "VocabularyReviewLog")
    op.rename_table("PracticeProgress", "VocabularyProgress")
    op.rename_table("LessonAnswer", "PracticeAnswer")
    op.rename_table("LessonSession", "PracticeSession")
    op.rename_table("LessonProgress", "LearningProgress")
