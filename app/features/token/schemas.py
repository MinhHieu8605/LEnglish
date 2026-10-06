from pydantic import BaseModel


class AccessTokenPayload(BaseModel):
    """
    Payload encoded into the access token.

    Attributes:
        user_id (int): The identifier of the user who owns the record.
        user_email (str): The user's email address.
        refresh_token (str): The refresh token used to obtain a replacement access
            token.
        role (str): The user's assigned role.
    """

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
    """
    Response model for access token.

    Attributes:
        id (int): The unique identifier of the record.
        email (str): The user's email address.
        access_token (str): The access token used to authenticate API requests.
        refresh_token (str): The refresh token used to obtain a replacement access
            token.
        role (str): The user's assigned role.
    """

    id: int
    email: str
    access_token: str
    refresh_token: str
    role: str
