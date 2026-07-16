from fastapi import APIRouter, Depends

from app.api.v1.endpoint import dictionary, lesson, token, user, vocabulary, wordlist
from app.middleware.auth import get_current_user

api_router = APIRouter(prefix="/api/v1")
authentication_api_router = APIRouter()

# UNAUTHENTICATED ROUTES
api_router.include_router(token.token_router, prefix="/token", tags=["Token"])
api_router.include_router(user.public_router, prefix="/users", tags=["Users"])

# AUTHENTICATED ROUTES
authentication_api_router.include_router(user.user_router, prefix="/users", tags=["Users"])
authentication_api_router.include_router(dictionary.router, prefix="/dictionary", tags=["Dictionary"])
authentication_api_router.include_router(wordlist.router, prefix="/word-lists", tags=["Word Lists"])
authentication_api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["Vocabulary"])
authentication_api_router.include_router(lesson.router, prefix="/lessons", tags=["Lessons"])

api_router.include_router(
    authentication_api_router, dependencies=[Depends(get_current_user)]
)
