# Utilities Layer Implementation

## Overview

This document describes the port of shared utility helpers from the NoneBot plugin to the AstrBot-compatible utility layer. The utilities are located in `meme_stickers/utils/` and provide core functionality for the plugin without any NoneBot-specific dependencies.

## Modules

### `meme_stickers/utils/__init__.py`

Contains core utility functions and decorators for the plugin:

#### Functions

1. **`op_retry(max_retries=3, delay=1.0, backoff=2.0, exceptions=(Exception,))`**
   - Decorator for retrying operations with exponential backoff
   - Works with both async and sync functions
   - Logs retry attempts and final failures using AstrBot's logger
   - Example:
     ```python
     @op_retry(max_retries=3, delay=1.0)
     async def fetch_data():
         # operation that might fail
         pass
     ```

2. **`calculate_checksum(data, algorithm='md5')`**
   - Calculate checksum for string or bytes data
   - Supports: md5, sha1, sha256
   - Returns hex digest string

3. **`calculate_file_checksum(file_path, algorithm='md5')`**
   - Calculate checksum for a file
   - Supports: md5, sha1, sha256
   - Raises FileNotFoundError if file doesn't exist

4. **`parse_relative_number(value)`**
   - Parse relative number strings like "1K", "2M", "3G"
   - Supports: K (kilobytes), M (megabytes), G (gigabytes), T (terabytes)
   - Examples:
     - `parse_relative_number("100")` → 100
     - `parse_relative_number("1K")` → 1024
     - `parse_relative_number("2.5M")` → 2621440

5. **`json_dumps(obj, ensure_ascii=False, indent=2, sort_keys=False, **kwargs)`**
   - Dump object to JSON string with AstrBot-friendly defaults
   - Default: UTF-8 support, 2-space indentation
   - Wrapper around json.dumps with sensible defaults

#### Context Managers

1. **`async with exception_notify(context_name="Operation", log_level="error", re_raise=True)`**
   - Async context manager for exception handling with logging
   - Logs exceptions using AstrBot's logger
   - Optionally re-raises exceptions for caller handling
   - Allows callers to emit user-facing messages based on exception
   - Example:
     ```python
     async with exception_notify("fetch_packs"):
         result = await fetch_packs()
     ```

### `meme_stickers/utils/file_source.py`

Contains utilities for HTTP operations, GitHub URL formatting, and async primitives:

#### Functions

1. **`format_github_raw_url(owner, repo, branch, path)`**
   - Format GitHub raw content URL
   - Example: `format_github_raw_url("user", "repo", "main", "README.md")`
   - Returns: `https://raw.githubusercontent.com/user/repo/main/README.md`

2. **`format_github_release_url(owner, repo, tag, filename)`**
   - Format GitHub release download URL
   - Example: `format_github_release_url("user", "repo", "v1.0.0", "pack.zip")`
   - Returns: `https://github.com/user/repo/releases/download/v1.0.0/pack.zip`

3. **`create_semaphore(max_concurrent=5)`**
   - Create asyncio.Semaphore for limiting concurrent operations
   - Returns: asyncio.Semaphore instance

4. **`create_async_client(timeout=None, proxy=None, verify_ssl=True)`**
   - Create httpx.AsyncClient with common settings
   - Default timeout: 30 seconds
   - Returns: Configured httpx.AsyncClient instance

5. **`async fetch_url(url, client=None, timeout=None, proxy=None)`**
   - Fetch text content from a URL
   - Accepts optional injected client for testing
   - Returns: Response text

6. **`async fetch_url_json(url, client=None, timeout=None, proxy=None)`**
   - Fetch JSON content from a URL
   - Accepts optional injected client for testing
   - Returns: Parsed JSON as dictionary

7. **`async download_file(url, file_path, client=None, timeout=None, proxy=None, chunk_size=8192)`**
   - Download file from URL with streaming
   - Accepts optional injected client for testing
   - Returns: Path to downloaded file

#### Context Managers

1. **`async with semaphore_context(max_concurrent=5)`**
   - Context manager for semaphore lifecycle
   - Yields: Configured semaphore instance

2. **`async with client_context(timeout=None, proxy=None, verify_ssl=True)`**
   - Context manager for httpx.AsyncClient lifecycle
   - Automatically handles client cleanup
   - Yields: Configured httpx.AsyncClient instance
   - Example:
     ```python
     async with client_context(timeout=60) as client:
         response = await client.get("https://example.com")
     ```

## AstrBot Integration

### Logger Usage

All logging uses `astrbot.api.logger` instead of NoneBot's logger:

```python
from astrbot.api import logger

logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
```

### No NoneBot Dependencies

The utilities module contains:
- ✅ No imports from `nonebot`
- ✅ No imports from `cookit.nonebot`
- ✅ No NoneBot-specific decorators or context managers

### Configuration Integration

The utilities can be used with the ConfigWrapper from main.py:

```python
async with client_context(
    timeout=config.get("request_timeout", 30),
    proxy=config.get("proxy")
) as client:
    data = await fetch_url_json("https://api.example.com", client=client)
```

## Testing

A comprehensive test suite is provided in `test_utils.py` with 36 tests covering:

- **Retry Logic**: Async/sync operations, exponential backoff, specific exception handling
- **Checksum Calculations**: MD5, SHA1, SHA256 for strings, bytes, and files
- **Number Parsing**: Plain numbers, K/M/G/T suffixes, decimal values
- **JSON Utilities**: Basic dumping, UTF-8 support, indentation, key sorting
- **Exception Handling**: Context manager with and without re-raising
- **GitHub URLs**: Raw content and release URL formatting
- **Async Primitives**: Semaphore creation and context management
- **HTTP Utilities**: Client creation, URL fetching with mocked responses

Run tests with:
```bash
source .venv/bin/activate
python test_utils.py
```

## Type Hints and Documentation

All modules include:
- ✅ Full type hints for all functions and parameters
- ✅ Comprehensive docstrings with Args/Returns/Raises sections
- ✅ Usage examples for complex functions
- ✅ Clear exception documentation

## Dependency Management

### Required Dependencies

Already specified in requirements.txt:
- `httpx>=0.27.0` - For HTTP operations (optional in code, raises ImportError if missing)

### Optional Dependencies

All HTTP functionality gracefully handles missing httpx:
```python
try:
    import httpx
except ImportError:
    httpx = None
```

If httpx is not installed, ImportError will be raised when attempting HTTP operations with clear guidance on installation.

## Integration with Existing Code

The utilities module is designed to be used by:
1. **sticker_pack/hub.py**: For HTTP operations with retries
2. **sticker_pack/update.py**: For checksum validation and progress tracking
3. **main.py**: For configuration-driven client creation
4. **Future command handlers**: For GitHub-sourced pack management

Example integration with hub.py:

```python
from meme_stickers.utils import op_retry, calculate_checksum
from meme_stickers.utils.file_source import fetch_url_json

@op_retry(max_retries=3, delay=1.0)
async def fetch_packs_with_retry():
    return await fetch_url_json(f"{hub_url}/packs")
```

## Migration Path

To use utilities in existing code:

1. **Replace httpx creation**:
   ```python
   # Before: httpx.AsyncClient(timeout=30)
   # After:
   from meme_stickers.utils.file_source import create_async_client, client_context
   client = create_async_client(timeout=30)
   # Or with context manager:
   async with client_context(timeout=30) as client:
       ...
   ```

2. **Replace retry logic**:
   ```python
   # Before: Manual try/except with sleep
   # After:
   from meme_stickers.utils import op_retry
   @op_retry(max_retries=3)
   async def operation():
       ...
   ```

3. **Replace checksum calculations**:
   ```python
   # Before: hashlib directly
   # After:
   from meme_stickers.utils import calculate_file_checksum
   checksum = calculate_file_checksum(file_path)
   ```

## Acceptance Criteria Checklist

- ✅ Tests covering retry logging and GitHub URL formatting pass (36/36 passed)
- ✅ Static analysis shows no NoneBot imports in `meme_stickers/utils`
- ✅ Async fetch utilities can be imported without side effects
- ✅ AsyncClient/Semaphore instances can be injected (needed for later commands)
- ✅ Logger outputs use AstrBot's logger when retries occur
- ✅ Full type hints and docstrings throughout
- ✅ No NoneBot-specific dependencies or patterns
- ✅ All functions work within AstrBot environment
