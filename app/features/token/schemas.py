from pydantic import BaseModel


class AccessTokenPayload(BaseModel):
    """Payload encoded into the access token."""
    model_config = {
        "json_schemas_extra": {
            "example": [
                    {
                    "user_id": 1,
                    "user_email": "test@example.com",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.......",
                    "role": "user",
                }
            ]
        }
    }

    user_id: int
    user_email: str
    refresh_token: str
    role: str


class AccessTokenResponse(BaseModel):
    """Response model for access token."""

    id: int
    email: str
    access_token: str
    refresh_token: str
    role: str
