"""
Shared utility helpers for meme stickers plugin.
Provides retry logic, checksum helpers, and other common utilities for AstrBot.
"""

import asyncio
import hashlib
import json
import re
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Optional,
    TypeVar,
    Union,
)

from astrbot.api import logger

__all__ = [
    "op_retry",
    "calculate_checksum",
    "calculate_file_checksum",
    "parse_relative_number",
    "json_dumps",
    "exception_notify",
]

F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


def op_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[[F], F]:
    """
    Decorator for retrying operations with exponential backoff.

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for each retry
        exceptions: Tuple of exceptions to catch and retry on

    Returns:
        Decorated function that retries on failure

    Example:
        @op_retry(max_retries=3, delay=1.0)
        async def fetch_data():
            # operation that might fail
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Operation {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_delay:.2f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Operation {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Operation {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_delay:.2f}s..."
                        )
                        asyncio.run(asyncio.sleep(current_delay))
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Operation {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )

            raise last_exception

        # Return async wrapper if original is async, else sync wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def calculate_file_checksum(
    file_path: Union[str, Path], algorithm: str = "md5"
) -> str:
    """
    Calculate checksum for a file.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        Hex digest of file

    Raises:
        ValueError: If algorithm is not supported
        FileNotFoundError: If file does not exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if algorithm == "md5":
        hash_obj = hashlib.md5()
    elif algorithm == "sha1":
        hash_obj = hashlib.sha1()
    elif algorithm == "sha256":
        hash_obj = hashlib.sha256()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def calculate_checksum(
    data: Union[str, bytes], algorithm: str = "md5"
) -> str:
    """
    Calculate checksum for data.

    Args:
        data: String or bytes data
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        Hex digest of data

    Raises:
        ValueError: If algorithm is not supported
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    if algorithm == "md5":
        hash_obj = hashlib.md5()
    elif algorithm == "sha1":
        hash_obj = hashlib.sha1()
    elif algorithm == "sha256":
        hash_obj = hashlib.sha256()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    hash_obj.update(data)
    return hash_obj.hexdigest()


def parse_relative_number(value: str) -> int:
    """
    Parse a relative number string like "1K", "2M", "1G".

    Args:
        value: String value to parse (e.g., "100", "1K", "2M", "3G")

    Returns:
        Parsed number as integer

    Raises:
        ValueError: If value format is invalid

    Examples:
        >>> parse_relative_number("100")
        100
        >>> parse_relative_number("1K")
        1024
        >>> parse_relative_number("2M")
        2097152
    """
    value = value.strip().upper()

    # Try direct integer parsing first
    try:
        return int(value)
    except ValueError:
        pass

    # Parse with suffix
    match = re.match(r"^([\d.]+)\s*([KMGT])B?$", value)
    if not match:
        raise ValueError(f"Invalid relative number format: {value}")

    number_str, suffix = match.groups()

    try:
        number = float(number_str)
    except ValueError:
        raise ValueError(f"Invalid number in relative format: {number_str}")

    multipliers = {
        "K": 1024,
        "M": 1024 * 1024,
        "G": 1024 * 1024 * 1024,
        "T": 1024 * 1024 * 1024 * 1024,
    }

    return int(number * multipliers[suffix])


def json_dumps(
    obj: Any,
    ensure_ascii: bool = False,
    indent: Optional[int] = 2,
    sort_keys: bool = False,
    **kwargs: Any,
) -> str:
    """
    Dump object to JSON string with common settings for AstrBot plugins.

    Args:
        obj: Object to serialize
        ensure_ascii: Whether to escape non-ASCII characters (default: False)
        indent: Number of spaces for indentation (default: 2)
        sort_keys: Whether to sort dictionary keys (default: False)
        **kwargs: Additional arguments to json.dumps

    Returns:
        JSON string

    Examples:
        >>> json_dumps({"name": "test", "value": 123})
        '{\\n  "name": "test",\\n  "value": 123\\n}'
    """
    return json.dumps(
        obj,
        ensure_ascii=ensure_ascii,
        indent=indent,
        sort_keys=sort_keys,
        **kwargs,
    )


@asynccontextmanager
async def exception_notify(
    context_name: str = "Operation",
    log_level: str = "error",
    re_raise: bool = True,
) -> AsyncIterator[None]:
    """
    Async context manager for exception handling with logging.

    A lightweight replacement for cookit.nonebot.exception_notify that:
    - Logs exceptions using AstrBot's logger
    - Optionally re-raises exceptions for caller handling
    - Allows callers to emit user-facing messages based on exception

    Args:
        context_name: Name of the context for logging
        log_level: Log level ("debug", "info", "warning", "error")
        re_raise: Whether to re-raise caught exceptions

    Yields:
        None

    Raises:
        Exception: If re_raise=True and an exception occurs

    Examples:
        >>> async with exception_notify("fetch_packs"):
        ...     # code that might raise exceptions
        ...     result = await fetch_packs()
        ...
        >>> async with exception_notify("download", re_raise=False):
        ...     # exceptions logged but not re-raised
        ...     await risky_operation()
    """
    try:
        yield
    except Exception as e:
        log_func = getattr(logger, log_level, logger.error)
        log_func(f"Exception in {context_name}: {type(e).__name__}: {e}")

        if re_raise:
            raise
