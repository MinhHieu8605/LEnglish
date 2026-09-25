import asyncio
from unittest.mock import AsyncMock

import pytest

from app.features.preferences.schemas import UserPreferencesUpdate
from app.features.preferences.service import UserPreferencesService


def test_preferences_return_defaults_without_creating_a_row(monkeypatch):
    monkeypatch.setattr(
        "app.features.preferences.service.async_get_one_record_by",
        AsyncMock(return_value=None),
    )

    result = asyncio.run(UserPreferencesService.get_preferences(7, object()))

    assert result.user_id == 7
    assert result.daily_goal_minutes == 15
    assert result.timezone == "Asia/Ho_Chi_Minh"


def test_preferences_reject_unknown_timezone():
    with pytest.raises(ValueError):
        UserPreferencesUpdate(timezone="Mars/Olympus")
