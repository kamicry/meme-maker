"""
File source utilities for fetching resources from GitHub and other URLs.
Provides GitHub URL formatting, semaphore management, and async HTTP clients.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Tuple

from astrbot.api import logger

try:
    import httpx
except ImportError:
    httpx = None

__all__ = [
    "format_github_raw_url",
    "format_github_release_url",
    "create_semaphore",
    "create_async_client",
    "semaphore_context",
    "client_context",
]


def format_github_raw_url(
    owner: str,
    repo: str,
    branch: str,
    path: str,
) -> str:
    """
    Format a GitHub raw content URL.

    Args:
        owner: GitHub repository owner
        repo: Repository name
        branch: Branch or tag name
        path: Path to file in repository

    Returns:
        Formatted GitHub raw content URL

    Examples:
        >>> format_github_raw_url("user", "repo", "main", "README.md")
        'https://raw.githubusercontent.com/user/repo/main/README.md'
    """
    # Remove leading slashes from path
    path = path.lstrip("/")

    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"


def format_github_release_url(
    owner: str,
    repo: str,
    tag: str,
    filename: str,
) -> str:
    """
    Format a GitHub release download URL.

    Args:
        owner: GitHub repository owner
        repo: Repository name
        tag: Release tag (e.g., "v1.0.0")
        filename: Filename in the release

    Returns:
        Formatted GitHub release URL

    Examples:
        >>> format_github_release_url("user", "repo", "v1.0.0", "pack.zip")
        'https://github.com/user/repo/releases/download/v1.0.0/pack.zip'
    """
    return f"https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}"


def create_semaphore(max_concurrent: int = 5) -> asyncio.Semaphore:
    """
    Create a semaphore for limiting concurrent operations.

    Args:
        max_concurrent: Maximum number of concurrent operations

    Returns:
        Semaphore instance

    Examples:
        >>> semaphore = create_semaphore(max_concurrent=3)
        >>> async with semaphore:
        ...     await some_operation()
    """
    return asyncio.Semaphore(max_concurrent)


def create_async_client(
    timeout: Optional[float] = None,
    proxy: Optional[str] = None,
    verify_ssl: bool = True,
) -> "httpx.AsyncClient":
    """
    Create an httpx AsyncClient with common settings.

    Args:
        timeout: Request timeout in seconds (default: 30)
        proxy: HTTP(S) proxy URL
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Configured httpx.AsyncClient instance

    Raises:
        ImportError: If httpx is not installed

    Examples:
        >>> client = create_async_client(timeout=60)
        >>> async with client:
        ...     response = await client.get("https://example.com")
    """
    if httpx is None:
        raise ImportError(
            "httpx is required for HTTP operations. "
            "Install with: pip install httpx>=0.27.0"
        )

    if timeout is None:
        timeout = 30.0

    return httpx.AsyncClient(
        timeout=timeout,
        proxy=proxy,
        verify=verify_ssl,
    )


@asynccontextmanager
async def semaphore_context(
    max_concurrent: int = 5,
) -> AsyncIterator[asyncio.Semaphore]:
    """
    Async context manager for a semaphore.

    Args:
        max_concurrent: Maximum number of concurrent operations

    Yields:
        Semaphore instance

    Examples:
        >>> async with semaphore_context(max_concurrent=3) as sem:
        ...     async with sem:
        ...         await operation_1()
        ...     async with sem:
        ...         await operation_2()
    """
    semaphore = create_semaphore(max_concurrent)
    try:
        yield semaphore
    finally:
        # Semaphore doesn't need cleanup
        pass


@asynccontextmanager
async def client_context(
    timeout: Optional[float] = None,
    proxy: Optional[str] = None,
    verify_ssl: bool = True,
) -> AsyncIterator["httpx.AsyncClient"]:
    """
    Async context manager for an httpx AsyncClient.

    Automatically handles client lifecycle and ensures proper cleanup.

    Args:
        timeout: Request timeout in seconds (default: 30)
        proxy: HTTP(S) proxy URL
        verify_ssl: Whether to verify SSL certificates

    Yields:
        Configured httpx.AsyncClient instance

    Raises:
        ImportError: If httpx is not installed

    Examples:
        >>> async with client_context(timeout=60) as client:
        ...     response = await client.get("https://example.com")
        ...     return response.text
    """
    if httpx is None:
        raise ImportError(
            "httpx is required for HTTP operations. "
            "Install with: pip install httpx>=0.27.0"
        )

    if timeout is None:
        timeout = 30.0

    async with httpx.AsyncClient(
        timeout=timeout,
        proxy=proxy,
        verify=verify_ssl,
    ) as client:
        yield client


async def fetch_url(
    url: str,
    client: Optional["httpx.AsyncClient"] = None,
    timeout: Optional[float] = None,
    proxy: Optional[str] = None,
) -> str:
    """
    Fetch content from a URL.

    Args:
        url: URL to fetch
        client: Optional httpx.AsyncClient to use (will create one if not provided)
        timeout: Request timeout in seconds
        proxy: HTTP(S) proxy URL

    Returns:
        Response text

    Raises:
        httpx.HTTPError: If request fails
        ImportError: If httpx is not installed

    Examples:
        >>> content = await fetch_url("https://example.com")
    """
    if client is None:
        async with client_context(timeout=timeout, proxy=proxy) as _client:
            response = await _client.get(url)
            response.raise_for_status()
            return response.text
    else:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def fetch_url_json(
    url: str,
    client: Optional["httpx.AsyncClient"] = None,
    timeout: Optional[float] = None,
    proxy: Optional[str] = None,
) -> dict:
    """
    Fetch JSON content from a URL.

    Args:
        url: URL to fetch
        client: Optional httpx.AsyncClient to use (will create one if not provided)
        timeout: Request timeout in seconds
        proxy: HTTP(S) proxy URL

    Returns:
        Parsed JSON as dictionary

    Raises:
        httpx.HTTPError: If request fails
        ValueError: If response is not valid JSON
        ImportError: If httpx is not installed

    Examples:
        >>> data = await fetch_url_json("https://api.example.com/data")
    """
    if client is None:
        async with client_context(timeout=timeout, proxy=proxy) as _client:
            response = await _client.get(url)
            response.raise_for_status()
            return response.json()
    else:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def download_file(
    url: str,
    file_path: str,
    client: Optional["httpx.AsyncClient"] = None,
    timeout: Optional[float] = None,
    proxy: Optional[str] = None,
    chunk_size: int = 8192,
) -> str:
    """
    Download a file from a URL.

    Args:
        url: URL to download from
        file_path: Path where to save the file
        client: Optional httpx.AsyncClient to use (will create one if not provided)
        timeout: Request timeout in seconds
        proxy: HTTP(S) proxy URL
        chunk_size: Size of chunks to download at once

    Returns:
        Path to downloaded file

    Raises:
        httpx.HTTPError: If request fails
        IOError: If file write fails
        ImportError: If httpx is not installed

    Examples:
        >>> path = await download_file(
        ...     "https://example.com/file.zip",
        ...     "/tmp/file.zip"
        ... )
    """
    should_close_client = False

    if client is None:
        client = create_async_client(timeout=timeout, proxy=proxy)
        should_close_client = True

    try:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            with open(file_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)

        return file_path

    finally:
        if should_close_client:
            await client.aclose()
