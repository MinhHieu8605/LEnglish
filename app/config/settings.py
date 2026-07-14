from dotenv import load_dotenv, dotenv_values
from typing import Union

from app.utils.singleton import BaseSingleton

load_dotenv()
config = dotenv_values(".env")


class Database(object):
    """
    Database Configuration Class.

    This class manages the configuration settings for connecting to a
    PostgreSQL database, including host, credentials, and connection parameters.

    Attributes:
        db_host: The database host address.
        db_user: The database username.
        db_password: The database password.
        db_name: The name of the database.
        db_port: The port number for the database connection.
        pool_size: The number of DB connections to keep in the connection pool.
        max_overflow: The number of temporary connections allowed when the pool is full.
        pool_recycle: The number of seconds after which a connection is recycled (to avoid stale connections).
        pool_timeout: The maximum number of seconds to wait when the pool is full.
        sqlalchemy_database_uri: The SQLAlchemy database URI for
            synchronous connections (postgresql+psycopg2).
        sqlalchemy_async_database_uri: The SQLAlchemy database URI for
            asynchronous connections (postgresql+asyncpg).
    """

    db_host: Union[str, None]
    db_user: Union[str, None]
    db_password: Union[str, None]
    db_name: Union[str, None]
    db_port: Union[str, None]

    pool_size: int
    max_overflow: int
    pool_recycle: int
    pool_timeout: int

    sqlalchemy_database_uri: Union[str, None]
    sqlalchemy_async_database_uri: Union[str, None]

    def __init__(self) -> None:
        self.db_host = config.get("DB_HOST")
        self.db_user = config.get("DB_USER")
        self.db_password = config.get("DB_PASSWORD")
        self.db_name = config.get("DB_NAME")
        self.db_port = config.get("DB_PORT")

        self.pool_size = int(config.get("DB_POOL_SIZE", 5))
        self.max_overflow = int(config.get("DB_MAX_OVERFLOW", 10))
        self.pool_recycle = int(config.get("DB_POOL_RECYCLE", 1800))
        self.pool_timeout = int(config.get("DB_POOL_TIMEOUT", 30))

        # postgresql+psycopg2  → dùng cho synchronous engine (Alembic migrations)
        # postgresql+asyncpg   → dùng cho async engine (FastAPI requests)
        self.sqlalchemy_database_uri = (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )
        self.sqlalchemy_async_database_uri = (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )


class JWT(BaseSingleton):
    """
    JWT Configuration Class.

    This class is responsible for managing the configuration settings
    related to JSON Web Tokens (JWT) used in the application. It
    initializes the expiration times for access and refresh tokens, the
    JWT algorithm, and the secret key from the application's configuration.

    Attributes:
        access_token_expire_minutes: The expiration time for access tokens
            in minutes. Default is 60 minutes.
        jwt_alg: The algorithm used for signing the JWT.
        jwt_secret_key: The secret key used for encoding and decoding the
            JWT.
        refresh_token_expire_minutes: The expiration time for refresh
            tokens in minutes. Default is 1440 minutes (24 hours).
    """

    access_token_expire_minutes: Union[int, None]
    jwt_alg: Union[str, None]
    jwt_secret_key: Union[str, None]
    refresh_token_expire_minutes: Union[int, None]

    def __init__(self) -> None:
        self.access_token_expire_minutes = config.get("ACCESS-TOKEN-EXPIRE", 60)
        self.jwt_alg = config.get("JWT-ALG", "HS256")
        self.jwt_secret_key = config.get("JWT-SECRET-KEY", "secret key for project")
        self.refresh_token_expire_minutes = config.get("REFRESH-TOKEN-EXPIRE", 1440)


class AI(BaseSingleton):
    """
    AI API Configuration Class.

    Attributes:
        api_key: The AI API key.
        model: The model name to use for completions.
        api_url: The AI API endpoint URL.
    """

    api_key: Union[str, None]
    model: Union[str, None]
    api_url: Union[str, None]

    def __init__(self) -> None:
        self.api_key = config.get("AI_API_KEY")
        self.model = config.get("AI_MODEL")
        self.api_url = config.get("AI_API_URL")
