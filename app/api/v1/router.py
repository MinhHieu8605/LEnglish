from fastapi import APIRouter

from app.api.v1.endpoint import auth, token, user

api_router = APIRouter()

api_router.include_router(auth.auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(user.user_router, prefix="/users", tags=["Users"])
api_router.include_router(token.token_router, prefix="/token", tags=["Token"])
