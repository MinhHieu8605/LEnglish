"""
Asynchronous Database Operations Module for IvyChat Backend API

This module provides comprehensive utilities for managing asynchronous database
operations using SQLModel, SQLAlchemy, and PostgreSQL. It includes connection
pooling, transaction management, CRUD operations, retry mechanisms, and monitoring
capabilities for high-performance FastAPI applications.

Key Features:
============

Connection Management:
- Asynchronous connection pooling with PostgreSQL-specific optimizations
- Connection monitoring and cleanup to prevent memory leaks
- Configurable connection limits and timeout settings
- Automatic connection state management

Transaction Management:
- Decorator-based transaction handling with automatic rollback
- Retry mechanisms for transient database failures
- Transaction timeout support to prevent hanging operations
- Support for nested transactions and savepoints

CRUD Operations:
- Type-safe async CRUD operations for SQLModel entities
- Bulk operations for high-performance data manipulation
- Flexible query building with criteria-based filtering
- Proper error handling and logging

Monitoring & Observability:
- Connection pool utilization tracking
- Transaction lifecycle logging
- Performance monitoring with session ID tracking
- Memory usage optimization with garbage collection

Usage Examples:
===============

Basic Database Session:
```python
async def get_user(user_id: int):
    async with get_session() as session:
        user = await async_get_one_record_by_id(User, user_id, session)
        return user
```

Transaction Management:
```python
@db_transaction()
async def create_user_with_profile(user_data: dict, profile_data: dict,
                                   session: AsyncSession):
    user = await async_create_record(User, user_data, session)
    profile_data["user_id"] = user.id
    profile = await async_create_record(UserProfile, profile_data, session)
    return user, profile

# With retry and timeout
@db_transaction(max_retries=3, timeout=30.0)
async def complex_operation(data: dict, session: AsyncSession):
    # Complex database operations that might fail transiently
    pass
```

FastAPI Integration:
```python
@router.post("/users/")
@db_transaction()
async def create_user_endpoint(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    return await async_create_record(User, user_data.dict(), session)
```

Configuration:
==============

The module uses settings from `app.settings.Database` for:
- Connection pool sizing (pool_size, max_overflow)
- Connection timeouts and keepalive settings
- PostgreSQL-specific parameters
- Connection string configuration

Dependencies:
=============

- SQLModel: For ORM models and type safety
- SQLAlchemy: For core database operations and connection management
- AsyncPG: PostgreSQL async driver (implicit)
- Pydantic: For data validation and serialization
- Loguru: For structured logging

Error Handling:
===============

The module provides comprehensive error handling for:
- Connection failures and timeouts
- Transaction conflicts and deadlocks
- Integrity constraint violations
- Resource exhaustion scenarios

All database errors are logged and converted to appropriate HTTP exceptions
for API responses.

Performance Considerations:
===========================

- Connection pooling reduces connection overhead
- Bulk operations minimize round trips to the database
- Transaction decorators optimize commit/rollback patterns
- Memory cleanup prevents connection leaks
- Monitoring helps identify performance bottlenecks
"""

import asyncio
import gc
from dataclasses import dataclass
from functools import wraps
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Coroutine,
    Dict,
    List,
    Literal,
    Optional,
    Type,
)

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func as _func
from sqlalchemy.engine.events import event
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
    MultipleResultsFound,
    NoResultFound,
    OperationalError,
    TimeoutError,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import asc, create_engine, desc, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from loguru import logger
from app.config.settings import Database
from app.utils.common import raise_bad_request, raise_not_found
from app.utils.constants import Message, SortOrder

# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class RetryConfig(object):
    """Configuration for retry behavior with exponential backoff."""

    max_retries: int = 0
    delay: float = 0.5
    backoff: float = 2.0
    exception_types: tuple = ()


@dataclass
class ExecutionContext(object):
    """Context for function execution with transaction management."""

    session: AsyncSession
    func: Callable[..., Coroutine[Any, Any, Any]]
    args: tuple
    kwargs: Dict[str, Any]
    commit: bool = True
    timeout: Optional[float] = None


# ============================================================================
# CONFIGURATION & ENGINE SETUP
# ============================================================================


database = Database()

# Create at module level
_ENGINE = None
_ASYNC_ENGINE = None
_ASYNC_SESSION_FACTORY = None


def get_engine():
    """Get or create the synchronous SQLAlchemy engine."""
    global _ENGINE

    if _ENGINE is None:
        # Synchronous engine use for Alembic migrations in app/cli.py
        _ENGINE = create_engine(
            str(database.sqlalchemy_database_uri),
            pool_size=database.pool_size,
            max_overflow=database.max_overflow,
            pool_pre_ping=True,
            pool_recycle=database.pool_recycle,
            pool_timeout=database.pool_timeout,
            echo=False,
        )

    return _ENGINE


def get_async_engine():
    """Get or create the asynchronous SQLAlchemy engine."""
    global _ASYNC_ENGINE

    if _ASYNC_ENGINE is None:
        _ASYNC_ENGINE = create_async_engine(
            str(database.sqlalchemy_async_database_uri),
            pool_size=database.pool_size,
            max_overflow=database.max_overflow,
            pool_pre_ping=True,
            pool_recycle=database.pool_recycle,
            pool_timeout=database.pool_timeout,
            echo=False,
            connect_args={
                "server_settings": {
                    # "statement_timeout": str(database.statement_timeout),
                    # "idle_in_transaction_session_timeout": str(
                    #     database.idle_in_transaction_session_timeout
                    # ),
                    "tcp_keepalives_idle": "600",
                    "tcp_keepalives_interval": "30",
                    "tcp_keepalives_count": "3",
                }
            },
        )

        # Register event listeners after engine creation
        _register_event_listeners()

    return _ASYNC_ENGINE


def _register_event_listeners():
    """Register database event listeners for connection monitoring"""

    @event.listens_for(_ASYNC_ENGINE.sync_engine, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        """Monitor connection checkout and enforce limits"""
        pool = get_async_engine().pool
        checked_out = pool.checkedout()
        total_capacity = database.pool_size + database.max_overflow

        logger.debug(f"Connection checked out: {checked_out}/{total_capacity}")

        # Log warning if we're using too many connections
        if checked_out > (total_capacity * 0.8):
            logger.warning(
                f"High connection usage: {checked_out}/{total_capacity} "
                f"Pool info: {_get_pool_status()}"
            )

    @event.listens_for(_ASYNC_ENGINE.sync_engine, "checkin")
    def receive_checkin(dbapi_connection, connection_record):
        """Enhanced connection cleanup on checkin"""
        logger.debug(f"Connection returned to pool. Pool info: {_get_pool_status()}")


def get_async_session_factory():
    """Get or create the async session factory."""
    global _ASYNC_SESSION_FACTORY

    if _ASYNC_SESSION_FACTORY is None:
        _ASYNC_SESSION_FACTORY = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _ASYNC_SESSION_FACTORY


def _get_pool_status() -> str:
    """Get current connection pool status for monitoring"""
    try:
        pool = get_async_engine().pool
        return (
            f"size={pool.size()}, checked_in={pool.checkedin()}, "
            f"checked_out={pool.checkedout()}"
        )
    except Exception:
        return "unavailable"


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Creates and yields an async database session with enhanced cleanup.
    """

    session = None
    session_id = None
    try:
        async_session_factory = get_async_session_factory()
        session_id = id(session)
        logger.debug(f"Session {session_id} created. Pool info: {_get_pool_status()}")

        async with async_session_factory() as session:
            yield session

        # Ensure any pending changes are handled
        if session.in_transaction():
            await session.commit()

    except Exception as e:
        logger.error(f"Session {session_id} error: {str(e)}")
        if session:
            try:
                await session.rollback()
            except Exception as rollback_error:
                logger.error(
                    f"Rollback error for session {session_id}: " f"{rollback_error}"
                )
        raise
    finally:
        if session:
            try:
                # Force close the session
                await session.close()
                logger.debug(
                    f"Session {session_id} closed. Pool info: " f"{_get_pool_status()}"
                )
            except Exception as close_error:
                logger.error(f"Error closing session {session_id}: {close_error}")
            finally:
                # Explicit cleanup
                session = None
                gc.collect()


async def cleanup_connection_pool():
    """
    Cleanup connection pool to prevent memory leaks.
    Call this during application shutdown or periodically.
    """
    try:
        logger.info("Cleaning up connection pool...")

        # Dispose of all connections in the pool
        await get_async_engine().dispose()

        # Force garbage collection
        gc.collect()

        logger.info("Connection pool cleanup completed")
    except Exception as e:
        logger.error(f"Error during connection pool cleanup: {str(e)}")


async def monitor_connection_pool():
    """Enhanced monitoring with memory usage tracking"""
    try:
        pool = get_async_engine().pool
        pool_size = pool.size()
        checked_out = pool.checkedout()
        checked_in = pool.checkedin()

        # Calculate utilization
        total_capacity = database.pool_size + database.max_overflow
        utilization = checked_out / total_capacity if total_capacity > 0 else 0

        # Log detailed status
        logger.info(
            f"Pool status: size={pool_size}, out={checked_out}/"
            f"{total_capacity} ({utilization:.1%}), in={checked_in}"
        )

        # Alert on high utilization
        if utilization > 0.8:
            logger.warning(
                f"HIGH POOL UTILIZATION: {utilization:.1%} - "
                f"Consider investigating connection leaks"
            )

        # Force cleanup if utilization is very high
        if utilization > 0.9:
            logger.error("CRITICAL: Pool nearly exhausted, forcing cleanup")
            gc.collect()

    except Exception as e:
        logger.error(f"Error monitoring connection pool: {str(e)}")


async def periodic_monitoring():
    """Periodically monitor the connection pool every 5 minutes."""
    while True:
        try:
            await monitor_connection_pool()
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            logger.info("Pool monitoring task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in pool monitoring: {str(e)}")

            # Wait 1 minute before retrying
            await asyncio.sleep(60)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _is_managed_by_transactional(session: AsyncSession) -> bool:
    """
    Private helper function to check if a session is being managed by the
    transactional decorator.

    Args:
        session (AsyncSession): The SQLAlchemy async session to check

    Returns:
        bool: True if the session is managed by the transactional decorator,
            False otherwise
    """
    return hasattr(session, "_managed_by_transactional") and getattr(
        session, "_managed_by_transactional"
    )


def _get_or_create_session(
    args: tuple, kwargs: Dict[str, Any]
) -> tuple[AsyncSession, bool]:
    """
    Helper function to get an existing session or create a new one.

    Args:
        args: Positional arguments that might contain a session
        kwargs: Keyword arguments that might contain a session

    Returns:
        tuple: (session, session_created_internally)
    """
    # First check in kwargs
    session = kwargs.get("session", None) or kwargs.get("db_session", None)
    session_created_internally = False
    source = None

    if session is not None:
        source = "kwargs"
    # If not found in kwargs, search in args
    elif arg_session := next(
        (arg for arg in args if isinstance(arg, AsyncSession)), None
    ):
        session = arg_session
        source = "args"
    # If still no session, create one
    else:
        async_session_factory = get_async_session_factory()
        session = async_session_factory()
        session_created_internally = True
        kwargs["session"] = session
        source = "new"

    logger.debug(
        f"Session {id(session)}: {source} "
        f"{'(created)' if session_created_internally else ''}"
    )

    # Ensure the session is of the correct type
    if not isinstance(session, AsyncSession):
        raise TypeError("The provided session must be an instance of AsyncSession.")

    # Add a flag to indicate this session is managed by the transactional
    # decorator
    setattr(session, "_managed_by_transactional", True)

    return session, session_created_internally


def _get_session_id(session: AsyncSession) -> int:
    """
    Get a unique identifier for a session object.

    Args:
        session (AsyncSession): The SQLAlchemy async session to identify

    Returns:
        int: A unique identifier for the session
    """
    if not hasattr(session, "_session_id"):
        setattr(session, "_session_id", id(session))
    return getattr(session, "_session_id")


def _validate_retry_exceptions(
    retry_exceptions: Optional[List[Type[Exception]]], max_retries: int
) -> tuple:
    """
    Validate and prepare retry exception types.

    Args:
        retry_exceptions: List of exception types to retry on
        max_retries: Maximum number of retries

    Returns:
        tuple: Tuple of validated exception types
    """
    if retry_exceptions is None and max_retries > 0:
        retry_exceptions = [OperationalError, DBAPIError, TimeoutError]

    if max_retries > 0 and retry_exceptions:
        # Validate that all items in retry_exceptions are Exception subclasses
        for exc_type in retry_exceptions:
            if not isinstance(exc_type, type) or not issubclass(exc_type, Exception):
                raise TypeError(f"Expected Exception subclass, got {exc_type}")
        return tuple(retry_exceptions)

    return ()


async def _execute_transaction(
    session: AsyncSession,
    func: Callable[..., Coroutine[Any, Any, Any]],
    args: tuple,
    kwargs: Dict[str, Any],
    commit: bool = True,
) -> Any:
    """Helper function to execute a transaction with proper error handling."""
    func_name = getattr(func, "__name__", "unknown_function")
    session_id = _get_session_id(session)
    logger.debug(
        f"TX start: {func_name}@{session_id} " f"(in_tx: {session.in_transaction()})"
    )

    try:
        # Use a context manager to handle transaction boundaries
        async with (
            session.begin_nested() if session.in_transaction() else session.begin()
        ):
            result = await func(*args, **kwargs)

        # Commit the transaction if required
        if commit and session.in_transaction():
            await session.commit()
            logger.info(f"TX commit: {func_name}@{session_id}")
            # Reset the flag after commit
            setattr(session, "_managed_by_transactional", False)

        return result
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"TX failed: {func_name}@{session_id} - {error_type}: {str(e)}")
        # Rollback the transaction in case of an error
        if session.in_transaction():
            await session.rollback()
            logger.info(f"TX rollback: {func_name}@{session_id}")
        raise


async def _execute_with_timeout(
    session: AsyncSession,
    func: Callable[..., Coroutine[Any, Any, Any]],
    args: tuple,
    kwargs: Dict[str, Any],
    commit: bool,
    timeout: Optional[float],
) -> Any:
    """
    Execute transaction with optional timeout.

    Args:
        session: Database session
        func: Function to execute
        args: Function arguments
        kwargs: Function keyword arguments
        commit: Whether to commit transaction
        timeout: Timeout in seconds

    Returns:
        Function result
    """
    if timeout is not None:
        transaction_task = asyncio.create_task(
            _execute_transaction(session, func, args, kwargs, commit)
        )

        try:
            return await asyncio.wait_for(transaction_task, timeout=timeout)
        except asyncio.TimeoutError as exc:
            transaction_task.cancel()
            logger.error(f"Transaction timed out after {timeout} seconds")
            raise TimeoutError(
                f"Transaction timed out after {timeout} seconds"
            ) from exc
    else:
        return await _execute_transaction(session, func, args, kwargs, commit)


async def _execute_with_retry_backoff(
    context: ExecutionContext, retry_config: RetryConfig
) -> Any:
    """
    Execute function with retry mechanism and exponential backoff.

    Attempts to execute the given function with configurable retry behavior,
    applying exponential backoff between retry attempts for transient errors.

    Args:
        context: Execution context containing session, function, and parameters
        retry_config: Retry configuration with backoff settings

    Returns:
        Function result

    Raises:
        Exception: Re-raises the last retry exception or non-retryable
            exceptions
    """
    if retry_config.max_retries == 0:
        # No retries, execute once
        return await _execute_with_timeout(
            context.session,
            context.func,
            context.args,
            context.kwargs,
            context.commit,
            context.timeout,
        )

    last_exception = None
    current_delay = retry_config.delay

    # +1 to include initial attempt
    for attempt in range(retry_config.max_retries + 1):
        try:
            return await _execute_with_timeout(
                context.session,
                context.func,
                context.args,
                context.kwargs,
                context.commit,
                context.timeout,
            )
        except retry_config.exception_types as e:
            last_exception = e

            # Check if we have more attempts left
            if attempt < retry_config.max_retries:
                logger.warning(
                    f"Transient error on attempt {attempt + 1}/"
                    f"{retry_config.max_retries + 1}: {str(e)}. "
                    f"Retrying in {current_delay:.2f}s"
                )
                await asyncio.sleep(current_delay)
                current_delay *= retry_config.backoff
            else:
                logger.error(
                    f"Transaction failed after {retry_config.max_retries + 1} "
                    f"attempts: {str(e)}"
                )
                break
        except Exception as e:
            # Non-retryable exception - fail immediately
            logger.exception(f"Non-retryable error in transaction: {str(e)}")
            raise

    # If we get here, all retry attempts failed
    if last_exception:
        raise last_exception


# ============================================================================
# TRANSACTION DECORATORS
# ============================================================================


def db_transaction(
    commit: bool = True,
    max_retries: int = 0,
    retry_delay: float = 0.5,
    retry_backoff: float = 2.0,
    retry_exceptions: List[Type[Exception]] = None,
    timeout: Optional[float] = None,
):
    """
    Unified database transaction decorator with optional retry and timeout
    capabilities.

    This decorator wraps a function in a database transaction, handling session
    management, transaction boundaries, retries for transient failures, and
    optional timeout.

    Args:
        commit (bool): Whether to commit the transaction after execution.
            Defaults to True.
        max_retries (int): Maximum number of retry attempts for transient
            failures. 0 means no retries. Defaults to 0.
        retry_delay (float): Initial delay between retries in seconds.
            Defaults to 0.5.
        retry_backoff (float): Multiplier for the delay between retries.
            Defaults to 2.0.
        retry_exceptions (List[Type[Exception]]): List of exception types to
            retry on. Defaults to common transient database errors.
        timeout (Optional[float]): Transaction timeout in seconds.
            None means no timeout.

    Returns:
        Callable: A wrapped function that automatically manages database
            transactions.

    Raises:
        Exception: Any exception raised by the wrapped function will be
                  re-raised after the transaction is rolled back.

    Example:
        # Basic transaction with no retries or timeout
        @db_transaction()
        async def create_user(session, user_data):
            new_user = User(**user_data)
            session.add(new_user)

        # Transaction with retries for transient errors
        @db_transaction(max_retries=3, retry_delay=1.0)
        async def update_user(session, user_id, data):
            user = await session.get(User, user_id)
            for key, value in data.items():
                setattr(user, key, value)
            session.add(user)
    """
    retry_exception_types = _validate_retry_exceptions(retry_exceptions, max_retries)

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            session, session_created_internally = _get_or_create_session(args, kwargs)

            try:
                context = ExecutionContext(
                    session=session,
                    func=func,
                    args=args,
                    kwargs=kwargs,
                    commit=commit,
                    timeout=timeout,
                )
                retry_config = RetryConfig(
                    max_retries=max_retries,
                    delay=retry_delay,
                    backoff=retry_backoff,
                    exception_types=retry_exception_types,
                )
                return await _execute_with_retry_backoff(context, retry_config)
            finally:
                if session_created_internally:
                    await session.close()
                    logger.debug("db_transaction: Closed internally created session")

        return wrapper

    return decorator


def transactional(commit: bool = True):
    """
    Backward-compatible alias for db_transaction with no retries or timeout.

    Args:
        commit (bool): Whether to commit the transaction after execution.
            Defaults to True.

    Returns:
        Callable: A wrapped function that automatically manages database
            transactions.
    """
    return db_transaction(commit=commit)


def transactional_retry_timeout(
    commit: bool = True,
    max_retries: int = 3,
    retry_delay: float = 0.5,
    retry_backoff: float = 2.0,
    retry_exceptions: List[Type[Exception]] = None,
    timeout: Optional[float] = None,
):
    """
    Backward-compatible alias for db_transaction with retries and timeout.

    Args:
        commit (bool): Whether to commit the transaction after execution.
            Defaults to True.
        max_retries (int): Maximum number of retry attempts for transient
            failures. Defaults to 3.
        retry_delay (float): Initial delay between retries in seconds.
            Defaults to 0.5.
        retry_backoff (float): Multiplier for the delay between retries.
            Defaults to 2.0.
        retry_exceptions (List[Type[Exception]]): List of exception types to
            retry on. Defaults to common transient database errors.
        timeout (Optional[float]): Transaction timeout in seconds.
            None means no timeout.

    Returns:
        Callable: A wrapped function that automatically manages database
            transactions.
    """
    return db_transaction(
        commit=commit,
        max_retries=max_retries,
        retry_delay=retry_delay,
        retry_backoff=retry_backoff,
        retry_exceptions=retry_exceptions,
        timeout=timeout,
    )


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================


async def transactional_commit(session: AsyncSession, force: bool = False) -> bool:
    """
    Commit a transaction with proper checks and error handling.

    This function provides a safe way to commit transactions with proper
    validation of transaction state and management status.

    Args:
        session (AsyncSession): The database session to commit
        force (bool): If True, commits even when session is managed by
                     transactional decorator. If False, respects transactional
                     decorator management and only commits when the session is
                     not managed by decorators.

    Returns:
        bool: True if commit was successful or skipped appropriately, False if
              failed

    Raises:
        Exception: Re-raises commit-related exceptions after logging

    Example:
        # Standard usage - respects transactional decorator management
        success = await transactional_commit(session)

        # Force commit regardless of decorator management
        success = await transactional_commit(session, force=True)
    """
    session_id = _get_session_id(session)

    try:
        # Check if session is in a transaction
        if not session.in_transaction():
            logger.debug(
                f"transactional_commit@{session_id}: "
                f"No active transaction to commit"
            )
            # Return True as there's nothing to commit
            return True

        # Check management status
        is_managed = _is_managed_by_transactional(session)

        # Logic:
        # - If not managed by transactional decorator, always commit
        # - If managed by transactional decorator, only commit if force=True
        if is_managed and not force:
            logger.debug(
                f"transactional_commit@{session_id}: Session managed by "
                f"transactional decorator, skipping commit "
                f"(use force=True to override)"
            )
            # Return True as the commit is appropriately skipped
            return True

        # Perform the actual commit
        await session.commit()
        logger.info(
            f"transactional_commit@{session_id}: " f"Transaction committed successfully"
        )

        # Reset management flag after successful commit
        if is_managed:
            setattr(session, "_managed_by_transactional", False)
            logger.debug(
                f"transactional_commit@{session_id}: Reset transactional "
                f"management flag"
            )

        return True

    except Exception as e:
        logger.error(
            f"transactional_commit@{session_id}: Commit failed - "
            f"{type(e).__name__}: {str(e)}"
        )
        raise


async def async_get_one_record_by_id(
    model,
    id,
    session: AsyncSession,
    options: list = [],
    raise_if_not_found: bool = True,
):
    """
    Retrieve a single record by its primary key asynchronously.

    Args:
        model: The SQLAlchemy model class to query.
        id: The primary key value of the record to retrieve.
        session (AsyncSession): The SQLAlchemy async session for database
            operations.
        options (list, optional): Additional SQLAlchemy loader options
            (e.g. joinedload).
        raise_if_not_found (bool, optional): If False, returns None instead of
            raising NotFound exception.

    Returns:
        Instance of model with the specified primary key, or None if not found
        and raise_if_not_found is False.

    Raises:
        NotFound: If no record with the given id exists and raise_if_not_found
            is True.
        BadRequest: If multiple records are found for the given id (should not
            happen for PK).
    """
    try:
        if not (record := await session.get(model, id, options=options)):
            if raise_if_not_found:
                raise_not_found(
                    f"Model: {model.__name__} does not have the record: {id}"
                )
            return None
        return record
    except MultipleResultsFound as e:
        logger.exception(str(e))
        raise_bad_request(str(e))


async def async_get_one_record_by(
    model,
    criteria: list,
    session: AsyncSession,
    not_found_msg: str = None,
    multiple_row_msg: str = None,
    duplicate_msg: str = None,
    duplication_check: bool = False,
    raise_if_not_found: bool = True,
    options: list = [],
):
    """
    Retrieve a single record matching specific criteria from the database
    asynchronously.

    Args:
        model: The SQLAlchemy model class to query.
        criteria (list): List of SQLAlchemy filter expressions (WHERE
            conditions).
        session (AsyncSession): The SQLAlchemy async session for database
            operations.
        not_found_msg (str, optional): Custom error message if no match is
            found.
        multiple_row_msg (str, optional): Custom error message for multiple
            matches.
        duplicate_msg (str, optional): Custom error message if duplication is
            detected.
        duplication_check (bool, optional): If True, raises BadRequest if
            a duplicate record is found.
        raise_if_not_found (bool, optional): If False, returns None instead of
            raising NotFound exception.
        options (list, optional): Additional SQLAlchemy loader options
            (e.g. joinedload).

    Returns:
        Instance of model matching the criteria, or None if not found and
        raise_if_not_found is False.

    Raises:
        NotFound: If no record is found and raise_if_not_found is True.
        BadRequest: If multiple records are found or duplication is detected.
    """

    if not not_found_msg:
        not_found_msg = (
            f"Model: {model.__name__} does not have the record with searching "
            f"criteria"
        )
    if not multiple_row_msg:
        multiple_row_msg = (
            f"Model: {model.__name__} has multiple rows while expecting exact "
            f"only one record"
        )
    if not duplicate_msg:
        duplicate_msg = (
            f"Model: {model.__name__} already has a record with the given " f"criteria"
        )
    try:
        statement = select(model).where(*criteria).options(*options)
        record = (await session.exec(statement)).one()
        if record and not duplication_check:
            return record
        else:
            raise_bad_request(duplicate_msg)
    except NoResultFound as e:
        if duplication_check:
            return None
        if not raise_if_not_found:
            return None
        logger.exception(str(e))
        raise_not_found(not_found_msg)
    except MultipleResultsFound as e:
        logger.exception(str(e))
        raise_bad_request(multiple_row_msg)


async def async_bulk_update_records(
    model,
    search_criteria: list,
    data: BaseModel | dict,
    session: AsyncSession,
    dump_mode: Literal["python", "json"] = "python",
    returns: list = [],
):
    """
    Perform a bulk update on records matching the given criteria asynchronously.

    Args:
        model: The SQLAlchemy model class to update.
        search_criteria (list): List of SQLAlchemy filter expressions to select
            records.
        data (BaseModel | dict): The data to update, provided as a Pydantic
            model or dict.
        session (AsyncSession): The SQLAlchemy async session for database
            operations.
        dump_mode (Literal["python", "json"], optional): Serialization mode for
            Pydantic model (default: "python").
        returns (list, optional): List of columns to return after update.

    Returns:
        List of updated values if 'returns' is provided; otherwise, None.

    Raises:
        NotFound: If no matching records are found.
        BadRequest: If update fails or no records are updated.
    """

    try:
        update_items = (
            data.model_dump(exclude_defaults=True, exclude_unset=True, mode=dump_mode)
            if isinstance(data, BaseModel)
            else data
        )
        statement = update(model).values(update_items).where(*search_criteria)
        if returns:
            statement = statement.returning(*returns)

        number_of_modified = await session.exec(statement)

        if _is_managed_by_transactional(session) and session.in_transaction():
            session_id = _get_session_id(session)
            logger.info(
                f"async_bulk_update_records@{session_id}: in transaction, "
                f"skipping commit"
            )
            await session.flush()
        else:
            await session.commit()

        if not number_of_modified:
            raise_bad_request(
                "No records were saved successfully. Please contact " "administrator!"
            )
        if returns:
            if len(returns) == 1:
                return number_of_modified.scalars().all()
            else:
                return number_of_modified.all()

    except NoResultFound:
        raise_not_found(
            f"Cannot bulk update the model {model.__name__}. No results found"
        )
    except Exception as ex:
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        return raise_bad_request(
            f"Cannot bulk update {model.__name__} failed! Please contact "
            f"administrator for support"
        )


async def async_update_one_record(
    model,
    id: Optional[Any],
    data: BaseModel,
    session: AsyncSession,
    extra_data: Dict[str, Any] = {},
    search_criteria: list = [],
    extra_refresh_field: List[str] = [],
    dump_mode: Literal["json", "python"] = "python",
):
    """
    Update a single record (located by primary key or search criteria)
    asynchronously.

    Args:
        model: The SQLAlchemy model class to update.
        id: The primary key value of the record to update (used if
            search_criteria is not provided).
        data (BaseModel): The Pydantic model containing update fields.
        session (AsyncSession): The SQLAlchemy async session for database
            operations.
        extra_data (Dict[str, Any], optional): Additional fields to update.
        search_criteria (list, optional): List of SQLAlchemy filter expressions
            to select the record.
        extra_refresh_field (List[str], optional): Fields to refresh after
            update.
        dump_mode (Literal["json", "python"], optional): Serialization mode for
            Pydantic model (default: "python").

    Returns:
        The updated instance of model M.

    Raises:
        BadRequest: If the update fails.
    """

    try:
        if search_criteria:
            record = await async_get_one_record_by(model, search_criteria, session)
        else:
            record = await async_get_one_record_by_id(model, id, session)

        if isinstance(data, dict):
            update_data = {**data, **extra_data}
        else:
            update_data = {
                **data.model_dump(
                    exclude_unset=True, exclude_none=True, mode=dump_mode
                ),
                **extra_data,
            }

        for key, value in update_data.items():
            setattr(record, key, value)

        session.add(record)
        if _is_managed_by_transactional(session) and session.in_transaction():
            session_id = _get_session_id(session)
            logger.info(
                f"async_update_one_record@{session_id}: in transaction, "
                f"skipping commit"
            )
            await session.flush()
        else:
            await session.commit()
        await session.refresh(record, extra_refresh_field)
        return record
    except Exception as ex:
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        return raise_bad_request(
            f"Update {model.__name__} failed! Please contact administrator "
            f"for support"
        )


async def async_get_many_records_by(
    model,
    criteria: list,
    session: AsyncSession,
    not_found_msg: str = None,
    options: list = None,
    raise_if_not_found: bool = True,
):
    """
    Asynchronously fetch multiple records from the database based on criteria.

    Args:
        model: The model class to query.
        criteria (list): A list of SQLAlchemy filter conditions.
        session (AsyncSession): Async database session.
        not_found_msg (str, optional): Custom error message if no records
            found.
        options (list, optional): List of SQLAlchemy loader options for eager
            loading (e.g., selectinload, joinedload).
        raise_if_not_found (bool, optional): Whether to raise an exception if no
            records found. Defaults to True.

    Returns:
        List of records matching the criteria.
    """
    if not not_found_msg:
        not_found_msg = (
            f"Model: {model.__name__} does not have any records with the "
            f"given criteria"
        )

    try:
        statement = select(model).where(*criteria)

        # Apply eager loading options if provided
        if options:
            statement = statement.options(*options)

        result = await session.exec(statement)
        records = result.all()
        if not records and raise_if_not_found:
            raise_not_found(not_found_msg)
        return records
    except HTTPException as e:
        logger.exception(str(e))
        raise
    except Exception as e:
        logger.exception(str(e))
        raise_bad_request(
            f"Fetching records from {model.__name__} failed. "
            f"Please contact administrator."
        )


async def async_get_paginated_records(
    model,
    session: AsyncSession,
    criteria: Optional[list] = None,
    skip: int = 0,
    limit: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = SortOrder.ASCEND,
) -> tuple[int, list]:
    """
    Return (total_count, records) for *model* with optional filtering,
    sorting, and pagination.
    """
    where_clause = criteria or []
    try:
        count_stmt = select(_func.count()).select_from(model)
        if where_clause:
            count_stmt = count_stmt.where(*where_clause)
        total = (await session.exec(count_stmt)).one()

        stmt = select(model)
        if where_clause:
            stmt = stmt.where(*where_clause)
        if sort_by:
            sort_column = getattr(model, sort_by, None)
            if sort_column is not None:
                order_fn = desc if sort_order == SortOrder.DESCEND else asc
                stmt = stmt.order_by(order_fn(sort_column))
        rows = await session.exec(stmt.offset(skip).limit(limit))
        records = rows.all()
        return total, records
    except Exception as e:
        logger.exception(str(e))
        return raise_bad_request(
            f"Fetching paginated records from {model.__name__} failed. "
            f"Please contact administrator."
        )


async def async_create_record(
    model,
    data,
    session: AsyncSession,
    extra_data: Dict[str, Any] = {},
):
    """
    Asynchronously creates a new record in the database.

    This function creates a new instance of the model class with the provided
    data, adds it to the database session, commits the transaction, and
    refreshes the record to ensure all database-generated values (like
    auto-incremented IDs) are populated.

    Parameters
    ----------
    model : Type
        The SQLAlchemy model class to instantiate.
    data : dict
        Dictionary containing the primary data for creating the record.
    session : AsyncSession
        The SQLAlchemy async session to use for database operations.
    extra_data : Dict[str, Any], optional
        Additional data to be merged with the primary data when creating the
        record, by default an empty dict.

    Returns
    -------
    Any
        The newly created and committed record instance.

    Example
    -------
    >>> async with async_session_maker() as session:
    >>>     user = await async_create_record(
    >>>         User,
    >>>         {"username": "johndoe", "email": "john@example.com"},
    >>>         session,
    >>>         {"created_at": datetime.now()}
    >>>     )
    """
    record = model(**data, **extra_data)

    session.add(record)
    if _is_managed_by_transactional(session) and session.in_transaction():
        session_id = _get_session_id(session)
        logger.info(
            f"async_create_record@{session_id}: in transaction, " f"skipping commit"
        )
        await session.flush()
    else:
        await session.commit()
    await session.refresh(record)

    return record


async def async_create_bulk_records(
    model,
    data_list: List[Dict[str, Any]],
    session: AsyncSession,
    extra_data: Dict[str, Any] = {},
):
    """
    Asynchronously create multiple records in the database in a single
    transaction.

    Args:
        model: The ORM model class.
        data_list (List[Dict[str, Any]]): A list of data dictionaries for the
            new records.
        session (AsyncSession): The SQLAlchemy async session for database
            operations.
        extra_data (Dict[str, Any], optional): Additional data to merge into
            all records (default: empty dict).

    Returns:
        List: The list of created record instances.

    Raises:
        BadRequest: If the bulk creation fails.

    Examples:
        >>> # Example 1: Create multiple User records
        >>> async with get_session() as session:
        >>>     users_data = [
        >>>         {"name": "John", "email": "john@example.com", "age": 30},
        >>>         {"name": "Jane", "email": "jane@example.com", "age": 25},
        >>>         {"name": "Bob", "email": "bob@example.com", "age": 40}
        >>>     ]
        >>>     created_users = await async_create_bulk_records(
        >>>         User, users_data, session
        >>>     )
    """
    try:
        # Create model instances for all records
        records = [model(**data, **extra_data) for data in data_list]

        # Add all records to the session
        session.add_all(records)

        # Commit the transaction
        if _is_managed_by_transactional(session) and session.in_transaction():
            session_id = _get_session_id(session)
            logger.info(
                f"async_create_bulk_records@{session_id}: in transaction, "
                f"skipping commit"
            )
            # Flush to ensure all records are persistent in the session
            await session.flush()
        else:
            await session.commit()
        # Refresh all records to get their database-generated values
        for record in records:
            await session.refresh(record)

        return records
    except Exception as ex:
        # Rollback the transaction in case of error
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        return raise_bad_request(
            f"Bulk creation of {model.__name__} records failed! Please "
            f"contact administrator for support"
        )


@transactional_retry_timeout(max_retries=5, retry_delay=2, retry_backoff=2)
async def async_create_bulk_records_with_retry(
    model,
    data_list: List[Dict[str, Any]],
    session: AsyncSession,
    extra_data: Dict[str, Any] = {},
):
    """
    Asynchronously create multiple records with automatic retry on transient failures.

    This function wraps async_create_bulk_records with the transactional_retry_timeout
    decorator, providing automatic retry logic with exponential backoff for handling
    transient database errors.

    Args:
        model: The ORM model class.
        data_list (List[Dict[str, Any]]): A list of data dictionaries for the
            new records.
        session (AsyncSession): The SQLAlchemy async session for database
            operations. Automatically provided by
            @transactional_retry_timeout decorator.
        extra_data (Dict[str, Any], optional): Additional data to merge into
            all records (default: empty dict).

    Returns:
        List: The list of created record instances.

    Raises:
        BadRequest: If the bulk creation fails after all retry attempts.

    Examples:
        >>> # Example: Create multiple notification records with retry
        >>> async with get_session() as session:
        >>>     notifications_data = [
        >>>         {"user_id": 1, "title": "Alert", "message": "Test"},
        >>>         {"user_id": 2, "title": "Alert", "message": "Test"}
        >>>     ]
        >>>     created_notifications = await async_create_bulk_records_with_retry(
        >>>         Notification, notifications_data, session
        >>>     )
    """
    return await async_create_bulk_records(model, data_list, session, extra_data)


async def async_delete_one_record_by(
    model,
    session: AsyncSession,
    id=None,
    search_criteria: list = [],
    integrity_error_msg: str = (
        "Delete {model} with id: {id} failed. "
        "Please contact administrator for support"
    ),
):
    """
    Asynchronously delete a single record from the database using the specified
    model and criteria.

    Args:
        model: SQLAlchemy model class representing the target table.
        session (AsyncSession): SQLAlchemy asynchronous session for database
            operations.
        id (Any): The primary key value of the record to delete.
        search_criteria (list): List of SQLAlchemy filter conditions.
        integrity_error_msg (str): Custom error message template for integrity
            errors.

    Returns:
        The deleted record object if deletion succeeds.

    Raises:
        Returns a bad request response with an appropriate error message
        if deletion fails due to integrity or other exceptions.
    """
    if search_criteria:
        record = await async_get_one_record_by(model, search_criteria, session)
    else:
        record = await async_get_one_record_by_id(model, id, session)
    try:
        await session.delete(record)
        if _is_managed_by_transactional(session) and session.in_transaction():
            session_id = _get_session_id(session)
            logger.info(
                f"async_delete_one_record_by@{session_id}: in transaction, "
                f"skipping commit"
            )
            await session.flush()
        else:
            await session.commit()
        return record
    except IntegrityError as ex:
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        return raise_bad_request(
            integrity_error_msg.format(model=model.__name__, id=id)
        )

    except Exception as ex:
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        return raise_bad_request(
            f"Delete {model.__name__} failed! Please contact administrator "
            f"for support"
        )


async def async_delete_multiple_records(
    model,
    session: AsyncSession,
    ids: List[Any] = None,
    search_criteria: list = None,
    integrity_error_msg: str = (
        "Delete {model} with criteria failed. "
        "Please contact administrator for support"
    ),
    raise_if_not_found: bool = True,
):
    """
    Asynchronously delete multiple records from the database using the
    specified model and criteria.

    Args:
        model: SQLAlchemy model class representing the target table.
        session (AsyncSession): SQLAlchemy asynchronous session for database
            operations.
        ids (List[Any], optional): A list of primary key values of the records
            to delete.
        search_criteria (list, optional): List of SQLAlchemy filter conditions
            for deletion.
        integrity_error_msg (str): Custom error message template for integrity
            errors.
        raise_if_not_found (bool, optional): Whether to raise an exception if
            no records are found. Defaults to True.

    Returns:
        List of deleted record objects if deletion succeeds, or an empty list
        if no records are found and raise_if_not_found is False.

    Raises:
        HTTPException: 404 Not Found if no records match the criteria and
            raise_if_not_found is True.
        HTTPException: 400 Bad Request if deletion fails due to integrity or
            other exceptions.

    Examples:
        >>> # Example 1: Delete records by a list of IDs
        >>> async with get_session() as session:
        >>>     deleted_records = await async_delete_multiple_records(
        >>>         model=User,
        >>>         session=session,
        >>>         ids=[1, 2, 3]
        >>>     )
        >>>     print(f"Deleted records: {deleted_records}")

        >>> # Example 2: Delete records by search criteria
        >>> async with get_session() as session:
        >>>     deleted_records = await async_delete_multiple_records(
        >>>         model=User,
        >>>         session=session,
        >>>         search_criteria=[User.age > 30]
        >>>     )
        >>>     print(f"Deleted records: {deleted_records}")

        >>> # Example 3: Delete records without raising exception if none found
        >>> async with get_session() as session:
        >>>     deleted_records = await async_delete_multiple_records(
        >>>         model=User,
        >>>         session=session,
        >>>         search_criteria=[User.age > 100],
        >>>         raise_if_not_found=False
        >>>     )
        >>>     # Will be an empty list if none found
        >>>     print(f"Deleted records: {deleted_records}")
    """
    try:
        # Determine the criteria for deletion
        if ids:
            statement = select(model).where(model.id.in_(ids))
        elif search_criteria:
            statement = select(model).where(*search_criteria)
        else:
            raise ValueError("Either 'ids' or 'search_criteria' must be provided.")

        # Fetch records to be deleted
        result = await session.exec(statement)
        records = result.all()

        if not records:
            if raise_if_not_found:
                raise_not_found(
                    f"Model: {model.__name__} does not have records matching "
                    f"the given criteria."
                )
            else:
                logger.debug(
                    f"No records found for {model.__name__} with the given "
                    f"criteria. Skipping deletion."
                )
                return []

        # Delete records
        for record in records:
            await session.delete(record)

        if _is_managed_by_transactional(session) and session.in_transaction():
            session_id = _get_session_id(session)
            logger.info(
                f"async_delete_multiple_records@{session_id}: in transaction, "
                f"skipping commit"
            )
            await session.flush()
        else:
            await session.commit()
        return records

    except IntegrityError as ex:
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        return raise_bad_request(integrity_error_msg.format(model=model.__name__))

    except Exception as ex:
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        return raise_bad_request(
            f"Delete {model.__name__} failed! Please contact administrator "
            f"for support"
        )


async def async_find_record_or_404(
    model,
    session: AsyncSession,
    criteria: Optional[List] = None,
    field_name: Optional[str] = None,
    field_value: Optional[Any] = None,
    options: List = [],
):
    """
    General helper to fetch a model instance by criteria or field and raise 404
    if not found.

    Args:
        model: SQLAlchemy model class
        session (AsyncSession): Async database session
        criteria (list, optional): List of SQLAlchemy filter expressions
        field_name (str, optional): Field name for single-field lookup
        field_value (any, optional): Value for single-field lookup
        options (list, optional): List of SQLAlchemy loader options for eager
            loading (e.g., selectinload, joinedload).

    Returns:
        Instance of model if found

    Raises:
        HTTPException (or custom): 404 if not found
    """
    # Use provided or default exception/status

    # Build criteria
    filters = []
    if criteria:
        filters.extend(criteria)
    elif field_name and field_value is not None:
        filters.append(getattr(model, field_name) == field_value)

    instance = await async_get_one_record_by(
        model, filters, session, raise_if_not_found=False, options=options
    )

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=Message.MSG_NOT_FOUND
        )

    return instance
