import asyncio

from dataclasses import dataclass
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import DBAPIError
from functools import wraps
from typing import Coroutine
from typing import Callable
from typing import Type
from app.config.settings import Database
import gc

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.engine.events import event
from sqlmodel import create_engine
from typing import Any, Dict, List, Literal, Optional, Union

from loguru import logger
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError, MultipleResultsFound, NoResultFound
from sqlmodel import select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.utils.common import raise_bad_request, raise_not_found

# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class RetryConfig(object):
    """Configuration for retry behavior with exponential backoff"""

    max_retries: int = 0
    delay: float = 0.5
    backoff: float = 2.0
    exception_types: tuple = ()


@dataclass
class ExecutionContext(object):
    """Configuration for function execution"""
    
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
                "timeout": 10,
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


# ==================================================
# HELPER FUNC
# ==================================================


def _is_managed_by_transactional(session: AsyncSession) -> bool:
    """
    Private helper function to check if the session is managed by a transactional context.

    Args:
        session (AsyncSession): The SQLAlchemy async session to check.

    Returns:
        bool: True if the session is managed by a transactional context, False otherwise.
    """
    return hasattr(session, "_is_managed_by_transactional") and getattr(
        session, "_is_managed_by_transactional"
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
    setattr(session, "_is_managed_by_transactional", True)

    return session, session_created_internally


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
            setattr(session, "_is_managed_by_transactional", False)

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


def _get_session_id(session: AsyncSession) -> int:
    """
    Get a unique identifier for the session, useful for logging.

    Args:
        session (AsyncSession): The SQLAlchemy async session.

    Returns:
        int: A unique identifier for the session
    """
    if not hasattr(session, "_session_id"):
        setattr(session, "_session_id", id(session))
    return getattr(session, "_session_id")


async def async_get_one_record_by_id(
    model,
    id,
    session: AsyncSession,
    options: list = [],
    raise_if_not_found: bool = True,
):
    """
    Retrieve a single record from the database by its primary key asynchronously.
    Args:
        model: The SQLAlchemy model class to query.
        id: The primary key value of the record to retrieve.
        session (AsyncSession): The SQLAlchemy async session for database operations.
        options (list, optional): Additional SQLAlchemy loader options
            (e.g. joinedload).
        raise_if_not_found (bool, optional): Whether to raise an exception
            if no record is found. Defaults to True.
    Returns:
        Instance of model with the specified primary key, or None if not found
        and raise_if_not_found is False.
    Raises:
        NotFound: If no record with the given id exists and
            raise_if_not_found is True.
        BadRequest: If multiple records are found for the given id
            (should not happen for PK).
    """
    try:
        record = await session.get(model, id, options=options)
        if not record:
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
    options: list = [],
    not_found_msg: Optional[str] = None,
    multiple_row_msg: Optional[str] = None,
    duplicate_msg: Optional[str] = None,
    duplication_check: bool = False,
    raise_if_not_found: bool = False,
):
    """
    Retrieve a single record matching specific criteria from the database
    asynchronously.
    Args:
        model: The SQLAlchemy model class to query.
        criteria (list): List of SQLAlchemy filter expressions
            (WHERE conditions).
        session (AsyncSession): The SQLAlchemy async session for database
            operations.
        options (list, optional): Additional SQLAlchemy loader options
        not_found_msg (str, optional): Custom error message if no match is found.
        multiple_row_msg (str, optional): Custom error message for multiple
            matches.
        duplicate_msg (str, optional): Custom error message if duplication is
            detected.
        duplication_check (bool, optional): If True, returns None if no record
            found (useful for existence checks).
        raise_if_not_found (bool, optional): If True, raises NotFound error
            if no record is found.
    Returns:
        Instance of model matching the criteria, or None if duplication_check
        is True and not found.
    Raises:
        NotFound: If no record is found and duplication_check is False.
        BadRequest: If multiple records are found or duplication is detected.
    """
    if not not_found_msg:
        not_found_msg = (
            f"Model: {model.__name__} does not have the record with "
            f"searching criteria"
        )
    if not multiple_row_msg:
        multiple_row_msg = (
            f"Model: {model.__name__} has multiple rows while expecting "
            f"exact only one record"
        )
        
    try:
        statement = select(model).where(*criteria).options(*options)
        record = (await session.exec(statement)).one()
        if record and not duplication_check:
            return record
        else:
            raise_bad_request(duplicate_msg or "Duplicate record found")
    except NoResultFound as e:
        if duplication_check:
            return None
        if raise_if_not_found:
            logger.exception(str(e))
            raise_not_found(not_found_msg)
        else:
            return None
    except MultipleResultsFound as e:
        logger.exception(str(e))
        raise_bad_request(multiple_row_msg)


async def async_update_one_record(
    model,
    id,
    data,
    session: AsyncSession,
    extra_data: Dict[str, Any] = {},
    search_criteria: list = [],
    extra_refresh_field: List[str] = [],
    dump_mode: Literal["json", "python"] = "python",
):
    """
    Update a single record (located by primary key or search criteria) asynchronously.
    Args:
        model: The SQLAlchemy model class to update.
        id: The primary key value of the record to update
            (used if search_criteria is not provided).
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
        The updated instance of model.
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
        raise_bad_request(
            f"Update {model.__name__} failed! "
            f"Please contact administrator for support"
        )


async def async_get_many_records_by(
    model,
    criteria: list,
    session: AsyncSession,
    not_found_msg: Optional[str] = None,
    options: Optional[list] = None,
    order_by: Optional[list] = None,
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
        order_by (list, optional): List of columns to order the results by.
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
        if order_by:
            statement = statement.order_by(*order_by)
        result = await session.exec(statement)
        records = result.all()
        if not records and raise_if_not_found:
            raise_not_found(not_found_msg)
        return records
    except Exception as e:
        logger.exception(str(e))
        return raise_bad_request(
            f"Fetching records from {model.__name__} failed. "
            f"Please contact administrator."
        )


async def async_create_record(
    model, data, session: AsyncSession, extra_data: Dict[str, Any] = {}
):
    """
    Asynchronously create a new record in the database.
    Args:
        model: The ORM model class.
        data: The data dictionary for the new record.
        session: The AsyncSession instance.
        extra_data: Additional data to merge into the record (default: empty dict).
    Returns:
        The created record instance.
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
    Asynchronously create multiple records in the database in a single transaction.
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
        raise_bad_request(
            f"Bulk creation of {model.__name__} records failed! "
            f"Please contact administrator for support"
        )


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
        session (AsyncSession): SQLAlchemy asynchronous session for database operations.
        id (Any): The primary key value of the record to delete.
        search_criteria (list): List of SQLAlchemy filter conditions.
        integrity_error_msg (str): Custom error message template for integrity errors.
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
        raise_bad_request(integrity_error_msg.format(model=model.__name__, id=id))
    except Exception as ex:
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        raise_bad_request(
            f"Delete {model.__name__} failed! Please contact administrator for support"
        )


async def async_delete_multiple_records(
    model,
    session: AsyncSession,
    ids: Optional[List[Any]] = None,
    search_criteria: Optional[list] = None,
    integrity_error_msg: str = (
        "Delete {model} with criteria failed. "
        "Please contact administrator for support"
    ),
    raise_if_not_found: bool = True,
):
    """
    Asynchronously delete multiple records from the database using the specified
    model and criteria.
    Args:
        model: SQLAlchemy model class representing the target table.
        session (AsyncSession): SQLAlchemy asynchronous session for database operations.
        ids (List[Any], optional): A list of primary key values of the records
            to delete.
        search_criteria (list, optional): List of SQLAlchemy filter conditions
            for deletion.
        integrity_error_msg (str): Custom error message template for
            integrity errors.
        raise_if_not_found (bool, optional): Whether to raise an exception if no
            records are found. Defaults to True.
    Returns:
        List of deleted record objects if deletion succeeds, or an empty list
        if no records are found and raise_if_not_found is False.
    Raises:
        HTTPException: 404 Not Found if no records match the criteria and
            raise_if_not_found is True.
        HTTPException: 400 Bad Request if deletion fails due to integrity or
            other exceptions.
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
        raise_bad_request(integrity_error_msg.format(model=model.__name__))
    except Exception as ex:
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        raise_bad_request(
            f"Delete {model.__name__} failed! Please contact administrator for support"
        )


async def async_bulk_update_records(
    model,
    search_criteria: list,
    data: BaseModel | dict,
    session: AsyncSession,
    dump_mode: Literal["python", "json"] = "python",
    returns: list = [],
) -> Union[List[Any], None]:
    """
    Perform a bulk update on records matching the given criteria asynchronously.
    Args:
        model: The SQLAlchemy model class to update.
        search_criteria (list): List of SQLAlchemy filter expressions to
            select records.
        data (BaseModel | dict): The data to update, provided as a Pydantic
            model or dict.
        session (AsyncSession): The SQLAlchemy async session for database
            operations.
        dump_mode (Literal["python", "json"], optional): Serialization mode
            for Pydantic model (default: "python").
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
                "No records were saved successfully. " "Please contact administrator!"
            )
        if returns:
            if len(returns) == 1:
                return number_of_modified.scalars().all()
            else:
                return number_of_modified.all()
        return None
    except NoResultFound:
        raise_not_found(
            f"Cannot bulk update the model {model.__name__}. No results found"
        )
    except Exception as ex:
        if not _is_managed_by_transactional(session) and session.in_transaction():
            await session.rollback()
        logger.exception(str(ex))
        raise_bad_request(
            f"Cannot bulk update {model.__name__} failed! "
            f"Please contact administrator for support"
        )
