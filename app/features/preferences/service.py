from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_record,
    async_get_one_record_by,
    async_update_one_record,
    transactional,
)
from app.features.preferences.model import UserPreferences
from app.features.preferences.schemas import (
    UserPreferencesResponse,
    UserPreferencesUpdate,
)


def _default_preferences(user_id: int) -> UserPreferencesResponse:
    return UserPreferencesResponse(user_id=user_id)


class UserPreferencesService:
    """Read and update per-user learning preferences."""

    @staticmethod
    async def get_preferences(
        user_id: int, session: AsyncSession
    ) -> UserPreferencesResponse:
        preferences = await async_get_one_record_by(
            UserPreferences,
            [UserPreferences.user_id == user_id],
            session,
            raise_if_not_found=False,
        )
        if preferences is None:
            return _default_preferences(user_id)
        return UserPreferencesResponse.model_validate(preferences)

    @staticmethod
    @transactional()
    async def update_preferences(
        user_id: int,
        data: UserPreferencesUpdate,
        session: AsyncSession,
    ) -> UserPreferencesResponse:
        preferences = await async_get_one_record_by(
            UserPreferences,
            [UserPreferences.user_id == user_id],
            session,
            raise_if_not_found=False,
        )
        update_data = data.model_dump(exclude_unset=True, mode="python")
        if preferences is None:
            preferences = await async_create_record(
                UserPreferences,
                update_data,
                session,
                extra_data={"user_id": user_id},
            )
        elif update_data:
            preferences = await async_update_one_record(
                UserPreferences,
                preferences.id,
                update_data,
                session,
            )
        return UserPreferencesResponse.model_validate(preferences)
