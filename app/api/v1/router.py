from fastapi import APIRouter, Depends, Security
from fastapi.security import HTTPBearer

from app.api.v1.endpoint import (
    dictionary,
    engagement,
    feedback,
    lesson,
    preferences,
    review,
    sentence,
    token,
    user,
    vocabulary,
    wordlist,
)
from app.middleware.auth import get_current_user


_bearer_auth = HTTPBearer(
    bearerFormat="JWT",
    scheme_name="BearerAuth",
    auto_error=False,
)

api_router = APIRouter(prefix="/api/v1")
authentication_api_router = APIRouter()

# UNAUTHENTICATED ROUTES
api_router.include_router(token.token_router, prefix="/token", tags=["Token"])
api_router.include_router(user.public_router, prefix="/users", tags=["Users"])

# AUTHENTICATED ROUTES
authentication_api_router.include_router(user.router, prefix="/users", tags=["Users"])
authentication_api_router.include_router(dictionary.router, prefix="/dictionary", tags=["Dictionary"])
authentication_api_router.include_router(wordlist.router, prefix="/word-lists", tags=["Word Lists"])
authentication_api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["Vocabulary"])
authentication_api_router.include_router(review.router, prefix="/review", tags=["Review"])
authentication_api_router.include_router(lesson.router, prefix="/lessons", tags=["Lessons"])
authentication_api_router.include_router(sentence.router, prefix="/sentences", tags=["Sentences"])
authentication_api_router.include_router(
    engagement.router,
    prefix="/engagement",
    tags=["Engagement"],
)
authentication_api_router.include_router(
    preferences.router,
    prefix="/preferences",
    tags=["Preferences"],
)
authentication_api_router.include_router(
    feedback.router,
    prefix="/feedbacks",
    tags=["Feedbacks"],
)

api_router.include_router(
    authentication_api_router,
    dependencies=[Security(_bearer_auth), Depends(get_current_user)],
)
