from unittest.mock import AsyncMock

from fastapi import Request
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.database.async_db import get_session
from app.features.lesson.schemas import LessonAnswerRequest
from app.features.lesson.service import LessonService
from app.features.review.service import ReviewService
from app.features.wordlist.model import WordList, WordListItem
from app.features.wordlist.service import WordListService
from app.features.dictionary.service import DictionaryService
from app.main import app
from app.middleware.auth import get_current_user
from app.utils.constants import ReviewMode, ReviewRating, ReviewScope


NOW = "2026-10-06T10:00:00Z"
LESSON_SESSION = {
    "id": 11, "lesson_id": 2, "mode": "dictation", "status": "completed",
    "score": 100, "correct_count": 1, "total_count": 1, "duration_seconds": 10,
    "started_at": NOW, "completed_at": NOW,
}
REVIEW_SESSION = {
    "id": 12, "topic_slug": "fruit", "scope": "due", "initial_mode": "flashcard",
    "status": "started", "current_position": 0, "total_items": 0,
    "started_at": NOW, "completed_at": None, "items": [],
}
SAVED_WORD = {
    "id": 3, "word": "apple", "word_type": "noun", "ipa": None,
    "audio_url": None, "image_url": None, "definition_vi": "tao",
    "example_sentence": None, "example_translation_vi": None, "created_time": NOW,
    "word_list_item_id": 4, "word_list_id": 5, "source_subtitle_id": None,
    "context_sentence": None, "note": None, "status": "learning", "ease_factor": 2.5,
    "repetition_count": 1, "interval_days": 1, "next_review_at": NOW,
    "last_reviewed_at": NOW, "personal_note": None,
}


@pytest.fixture
def client():
    async def session_override():
        yield object()

    async def user_override(request: Request):
        request.state.user_id = 7
        request.state.role = "user"

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = user_override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_sentence_submission_uses_body_context_and_authenticated_user(client, monkeypatch):
    submit = AsyncMock(return_value={
        "subtitle_id": 9, "user_input": "Hello", "accuracy_score": 100,
        "is_correct": True, "attempt_count": 1, "answered_at": NOW,
    })
    monkeypatch.setattr(LessonService, "submit_answer", submit)
    response = client.post("/api/v1/sentences/submit", json={
        "lesson_slug": "hello", "session_id": 11, "subtitle_id": 9,
        "user_input": "Hello", "user_id": 999,
    })
    assert response.status_code == 200
    assert response.json()["is_correct"] is True
    args = submit.await_args.args
    assert args[:3] == (7, "hello", 11)
    assert args[3] == LessonAnswerRequest(subtitle_id=9, user_input="Hello")


def test_lesson_completion_accepts_body_ids(client, monkeypatch):
    complete = AsyncMock(return_value=LESSON_SESSION)
    monkeypatch.setattr(LessonService, "complete_session", complete)
    response = client.post("/api/v1/lessons/complete", json={
        "lesson_slug": "hello", "session_id": 11,
    })
    assert response.status_code == 200
    assert response.json()["id"] == 11
    assert complete.await_args.args[:3] == (7, "hello", 11)


def test_youtube_import_still_requires_admin(client, monkeypatch):
    import_lesson = AsyncMock()
    monkeypatch.setattr(LessonService, "import_youtube", import_lesson)
    response = client.post("/api/v1/lessons/from-youtube", json={
        "video_url": "https://youtu.be/example",
    })
    assert response.status_code == 403
    import_lesson.assert_not_awaited()


def test_topic_queue_uses_query_selectors(client, monkeypatch):
    queue = AsyncMock(return_value={
        "topic_slug": "fruit", "mode": "typing", "scope": "all",
        "total_word_count": 0, "due_count": 0, "new_count": 0, "items": [],
    })
    monkeypatch.setattr(ReviewService, "get_review_queue", queue)
    response = client.get("/api/v1/review/queue", params={
        "book_slug": "oxford", "topic_slug": "fruit", "mode": "typing", "scope": "all",
    })
    assert response.status_code == 200
    assert response.json()["topic_slug"] == "fruit"
    assert queue.await_args.args[:5] == (
        7, "oxford", "fruit", ReviewMode.TYPING, ReviewScope.ALL,
    )


def test_saved_word_queue_preserves_pagination_and_response(client, monkeypatch):
    due = AsyncMock(return_value=([SAVED_WORD], 21, 3))
    monkeypatch.setattr(WordListService, "list_due_words", due)
    response = client.get("/api/v1/review/queue", params={
        "word_list_id": 5, "status": "due", "page": 2, "page_size": 10,
    })
    assert response.status_code == 200
    assert response.json()["data"][0]["word_list_id"] == 5
    assert response.json()["metadata"] == {"total": 21, "pages": 3, "page": 2, "page_size": 10}
    args = due.await_args.args
    assert args[:2] == (7, 5)
    assert (args[2].page, args[2].page_size) == (2, 10)


@pytest.mark.parametrize("params", [
    {}, {"book_slug": "oxford"}, {"topic_slug": "fruit"},
    {"word_list_id": 5, "book_slug": "oxford", "topic_slug": "fruit"},
    {"word_list_id": 0}, {"word_list_id": 5, "scope": "all"},
    {"word_list_id": 5, "status": "new"},
    {"book_slug": "oxford", "topic_slug": "fruit", "status": "due", "scope": "all"},
    {"word_list_id": 5, "page_size": 101},
])
def test_queue_rejects_missing_conflicting_or_invalid_selectors(client, monkeypatch, params):
    queue, due = AsyncMock(), AsyncMock()
    monkeypatch.setattr(ReviewService, "get_review_queue", queue)
    monkeypatch.setattr(WordListService, "list_due_words", due)
    assert client.get("/api/v1/review/queue", params=params).status_code == 422
    queue.assert_not_awaited()
    due.assert_not_awaited()


def test_review_session_moves_topic_to_body(client, monkeypatch):
    start = AsyncMock(return_value=REVIEW_SESSION)
    monkeypatch.setattr(ReviewService, "start_review_session", start)
    response = client.post("/api/v1/review/sessions", json={
        "book_slug": "oxford", "topic_slug": "fruit",
        "scope": "due", "initial_mode": "flashcard",
    })
    assert response.status_code == 201
    assert start.await_args.args[:3] == (7, "oxford", "fruit")
    assert start.await_args.args[3].scope == ReviewScope.DUE


@pytest.mark.parametrize("action", ["check", "cloze"])
def test_short_word_actions_still_validate_topic_membership(client, monkeypatch, action):
    ensure = AsyncMock()
    monkeypatch.setattr(ReviewService, "ensure_topic_vocabulary", ensure)
    if action == "check":
        operation = AsyncMock(return_value={
            "attempt_id": "a1", "correct": True, "correct_answer": "apple", "review_options": {},
        })
        monkeypatch.setattr(ReviewService, "check_answer", operation)
    else:
        operation = AsyncMock(return_value={
            "attempt_id": "a1", "vocabulary_id": 3, "sentence": "An _____ a day.",
            "translation_vi": "", "hint_vi": "fruit",
        })
        monkeypatch.setattr(ReviewService, "generate_cloze", operation)
    response = client.post(f"/api/v1/review/words/3/{action}", json={
        "book_slug": "oxford", "topic_slug": "fruit", "attempt_id": "a1", "answer": "apple",
    })
    assert response.status_code == 200
    assert ensure.await_args.args[:3] == ("oxford", "fruit", 3)
    assert operation.await_args.args[:2] == (7, 3)


def test_saved_review_moves_list_id_to_body(client, monkeypatch):
    saved, general = AsyncMock(return_value=SAVED_WORD), AsyncMock()
    monkeypatch.setattr(WordListService, "record_review", saved)
    monkeypatch.setattr(ReviewService, "record_review", general)
    response = client.post("/api/v1/review/words/3", json={
        "word_list_id": 5, "attempt_id": "a1", "rating": "good",
    })
    assert response.status_code == 200
    assert response.json()["word_list_item_id"] == 4
    assert saved.await_args.args[:4] == (7, 5, 3, ReviewRating.GOOD)
    assert saved.await_args.args[5] == "a1"
    general.assert_not_awaited()


def test_general_review_keeps_its_existing_contract(client, monkeypatch):
    general = AsyncMock(return_value={
        "vocabulary_id": 3, "attempt_id": "a1", "rating": "good", "status": "learning",
        "repetition_count": 1, "interval_days": 1, "interval_seconds": 86400,
        "next_review_at": NOW,
    })
    monkeypatch.setattr(ReviewService, "record_review", general)
    response = client.post("/api/v1/review/words/3", json={"attempt_id": "a1", "rating": "good"})
    assert response.status_code == 200
    assert response.json()["vocabulary_id"] == 3
    assert "word_list_id" not in general.await_args.args[2].model_dump()


def test_dictionary_moves_word_to_path_and_decodes_spaces(client, monkeypatch):
    lookup = AsyncMock(return_value={"word": "take off", "meanings": [], "sources": []})
    monkeypatch.setattr(DictionaryService, "lookup", lookup)
    response = client.get("/api/v1/dictionary/word/take%20off")
    assert response.status_code == 200
    assert response.json()["word"] == "take off"
    assert lookup.await_args.args[0] == "take off"


@pytest.mark.parametrize(("path", "body"), [
    ("/sentences/submit", {"subtitle_id": 9, "user_input": "Hello"}),
    ("/sentences/submit", {"lesson_slug": "hello", "session_id": 0, "subtitle_id": 9, "user_input": "Hello"}),
    ("/lessons/complete", {"lesson_slug": "hello"}),
    ("/review/sessions", {"scope": "due"}),
    ("/review/words/3/check", {"attempt_id": "a1", "answer": "apple"}),
    ("/review/words/3/cloze", {"attempt_id": "a1"}),
    ("/review/words/3", {"word_list_id": 0, "attempt_id": "a1", "rating": "good"}),
])
def test_moved_body_selectors_are_validated(client, path, body):
    assert client.post("/api/v1" + path, json=body).status_code == 422


@pytest.mark.parametrize(("method", "path"), [
    ("post", "/lessons/import/youtube"),
    ("post", "/lessons/hello/sessions/11/answers"),
    ("post", "/lessons/hello/sessions/11/complete"),
    ("get", "/review/books/oxford/topics/fruit/queue"),
    ("post", "/review/books/oxford/topics/fruit/sessions"),
    ("post", "/review/books/oxford/topics/fruit/words/3/check"),
    ("post", "/review/books/oxford/topics/fruit/words/3/cloze"),
    ("post", "/word-lists/5/words/3/review"),
    ("get", "/word-lists/5/review/due"),
    ("get", "/dictionary/lookup?word=apple"),
])
def test_replaced_paths_are_no_longer_registered(client, method, path):
    assert getattr(client, method)("/api/v1" + path).status_code == 404


def test_new_routes_remain_authenticated(client, monkeypatch):
    app.dependency_overrides.pop(get_current_user)
    submit = AsyncMock()
    monkeypatch.setattr(LessonService, "submit_answer", submit)
    assert client.post("/api/v1/sentences/submit", json={
        "lesson_slug": "hello", "session_id": 11, "subtitle_id": 9, "user_input": "Hello",
    }).status_code == 401
    assert client.get("/api/v1/review/queue?word_list_id=5&status=due").status_code == 401
    submit.assert_not_awaited()


def test_merged_saved_routes_keep_real_ownership_and_membership_checks(client, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    try:
        WordList.__table__.create(engine)
        WordListItem.__table__.create(engine)
        # Vocabulary is queried for membership after validating list ownership.
        from app.features.vocabulary.model import Vocabulary
        Vocabulary.__table__.create(engine)
        with Session(engine) as sync_session:
            sync_session.add_all([
                WordList(id=5, user_id=8, name="Other user's list"),
                WordList(id=6, user_id=7, name="My empty list"),
            ])
            sync_session.commit()

            class ReadSession:
                async def exec(self, statement):
                    return sync_session.exec(statement)

            async def session_override():
                yield ReadSession()

            monkeypatch.setitem(app.dependency_overrides, get_session, session_override)
            write_review = AsyncMock()
            monkeypatch.setattr(ReviewService, "record_review", write_review)
            assert client.get("/api/v1/review/queue?word_list_id=5&status=due").status_code == 404
            for list_id in (5, 6):
                assert client.post("/api/v1/review/words/3", json={
                    "word_list_id": list_id, "attempt_id": "a1", "rating": "good",
                }).status_code == 404
            write_review.assert_not_awaited()
    finally:
        engine.dispose()


def test_openapi_describes_new_paths_and_body_context(client):
    schema = client.get("/api/v1/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/sentences/submit" in paths
    assert "/api/v1/lessons/complete" in paths
    assert "/api/v1/dictionary/lookup" not in paths
    assert "word" in {p["name"] for p in paths["/api/v1/dictionary/word/{word}"]["get"]["parameters"] if p["in"] == "path"}
    for name in ("ReviewTopicCheckRequest", "ReviewTopicClozeRequest", "ReviewTopicSessionStartRequest"):
        assert {"book_slug", "topic_slug"} <= set(schema["components"]["schemas"][name]["required"])
    assert {"lesson_slug", "session_id"} <= set(schema["components"]["schemas"]["LessonAnswerSubmitRequest"]["required"])
