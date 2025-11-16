#!/usr/bin/env python3
"""
Tests for utility layer (meme_stickers/utils/).
Tests retry behavior, checksums, number parsing, GitHub URL formatting, and async utilities.
"""

import sys
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent))

from meme_stickers.utils import (
    op_retry,
    calculate_checksum,
    calculate_file_checksum,
    parse_relative_number,
    json_dumps,
    exception_notify,
)
from meme_stickers.utils.file_source import (
    format_github_raw_url,
    format_github_release_url,
    create_semaphore,
    create_async_client,
    semaphore_context,
    client_context,
    fetch_url,
    fetch_url_json,
)


# ============================================================================
# Tests for op_retry decorator
# ============================================================================


def test_op_retry_async_success():
    """Test op_retry with successful async operation"""

    call_count = 0

    @op_retry(max_retries=3)
    async def successful_operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = asyncio.run(successful_operation())
    assert result == "success"
    assert call_count == 1


def test_op_retry_async_with_retries():
    """Test op_retry with failing then succeeding async operation"""

    call_count = 0

    @op_retry(max_retries=3, delay=0.01)
    async def failing_then_succeeding():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Not yet!")
        return "success"

    result = asyncio.run(failing_then_succeeding())
    assert result == "success"
    assert call_count == 3


def test_op_retry_async_exhausted():
    """Test op_retry with exhausted retries"""

    call_count = 0

    @op_retry(max_retries=2, delay=0.01)
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError("Always fails")

    try:
        asyncio.run(always_fails())
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Always fails"
        assert call_count == 3  # Initial attempt + 2 retries


def test_op_retry_async_with_specific_exception():
    """Test op_retry with specific exception types"""

    call_count = 0

    @op_retry(max_retries=2, delay=0.01, exceptions=(ValueError,))
    async def fails_with_value_error():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Retryable")
        else:
            raise RuntimeError("Not retryable")

    try:
        asyncio.run(fails_with_value_error())
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert str(e) == "Not retryable"
        assert call_count == 2  # Initial + 1 retry


# ============================================================================
# Tests for checksum helpers
# ============================================================================


def test_calculate_checksum_md5():
    """Test MD5 checksum calculation"""
    data = "hello world"
    checksum = calculate_checksum(data, algorithm="md5")
    assert checksum == "5eb63bbbe01eeed093cb22bb8f5acdc3"


def test_calculate_checksum_sha1():
    """Test SHA1 checksum calculation"""
    data = "hello world"
    checksum = calculate_checksum(data, algorithm="sha1")
    assert checksum == "2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"


def test_calculate_checksum_sha256():
    """Test SHA256 checksum calculation"""
    data = "hello world"
    checksum = calculate_checksum(data, algorithm="sha256")
    assert (
        checksum
        == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    )


def test_calculate_checksum_bytes():
    """Test checksum with bytes input"""
    data = b"hello world"
    checksum = calculate_checksum(data, algorithm="md5")
    assert checksum == "5eb63bbbe01eeed093cb22bb8f5acdc3"


def test_calculate_checksum_invalid_algorithm():
    """Test checksum with invalid algorithm"""
    try:
        calculate_checksum("data", algorithm="invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unsupported algorithm" in str(e)


def test_calculate_file_checksum():
    """Test file checksum calculation"""
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello world")
        temp_path = f.name

    try:
        checksum = calculate_file_checksum(temp_path, algorithm="md5")
        assert checksum == "5eb63bbbe01eeed093cb22bb8f5acdc3"
    finally:
        Path(temp_path).unlink()


def test_calculate_file_checksum_not_found():
    """Test file checksum with non-existent file"""
    try:
        calculate_file_checksum("/nonexistent/file.txt")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


# ============================================================================
# Tests for number parsing
# ============================================================================


def test_parse_relative_number_plain():
    """Test parsing plain numbers"""
    assert parse_relative_number("100") == 100
    assert parse_relative_number("0") == 0
    assert parse_relative_number("999999") == 999999


def test_parse_relative_number_kilobytes():
    """Test parsing kilobyte numbers"""
    assert parse_relative_number("1K") == 1024
    assert parse_relative_number("2K") == 2048
    assert parse_relative_number("1 K") == 1024
    assert parse_relative_number("1KB") == 1024


def test_parse_relative_number_megabytes():
    """Test parsing megabyte numbers"""
    assert parse_relative_number("1M") == 1024 * 1024
    assert parse_relative_number("2M") == 2 * 1024 * 1024
    assert parse_relative_number("1 MB") == 1024 * 1024


def test_parse_relative_number_gigabytes():
    """Test parsing gigabyte numbers"""
    assert parse_relative_number("1G") == 1024 * 1024 * 1024
    assert parse_relative_number("2G") == 2 * 1024 * 1024 * 1024


def test_parse_relative_number_terabytes():
    """Test parsing terabyte numbers"""
    assert parse_relative_number("1T") == 1024 * 1024 * 1024 * 1024


def test_parse_relative_number_decimal():
    """Test parsing decimal numbers"""
    assert parse_relative_number("1.5K") == int(1.5 * 1024)
    assert parse_relative_number("2.5M") == int(2.5 * 1024 * 1024)


def test_parse_relative_number_invalid():
    """Test parsing invalid numbers"""
    try:
        parse_relative_number("invalid")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    try:
        parse_relative_number("1Z")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ============================================================================
# Tests for JSON dumping
# ============================================================================


def test_json_dumps_basic():
    """Test basic JSON dumping"""
    data = {"name": "test", "value": 123}
    result = json_dumps(data)
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert parsed == data


def test_json_dumps_ensure_ascii_false():
    """Test JSON dumping with ensure_ascii=False"""
    data = {"name": "测试", "emoji": "😀"}
    result = json_dumps(data, ensure_ascii=False)
    assert "测试" in result
    assert "😀" in result


def test_json_dumps_with_indent():
    """Test JSON dumping with indentation"""
    data = {"a": 1, "b": 2}
    result = json_dumps(data, indent=4)
    assert "\n" in result


def test_json_dumps_sort_keys():
    """Test JSON dumping with sorted keys"""
    data = {"z": 1, "a": 2, "m": 3}
    result = json_dumps(data, sort_keys=True)
    # Parse and verify order
    lines = result.strip().split("\n")
    # Check that 'a' appears before 'z'
    a_line = next(i for i, line in enumerate(lines) if '"a"' in line)
    z_line = next(i for i, line in enumerate(lines) if '"z"' in line)
    assert a_line < z_line


# ============================================================================
# Tests for exception_notify context manager
# ============================================================================


def test_exception_notify_no_error():
    """Test exception_notify with no error"""

    async def test_case():
        async with exception_notify("test_operation"):
            return "success"

    result = asyncio.run(test_case())
    assert result == "success"


def test_exception_notify_with_reraise():
    """Test exception_notify that re-raises exceptions"""

    async def test_case():
        async with exception_notify("test_operation", re_raise=True):
            raise ValueError("Test error")

    try:
        asyncio.run(test_case())
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Test error"


def test_exception_notify_without_reraise():
    """Test exception_notify that doesn't re-raise"""

    async def test_case():
        async with exception_notify("test_operation", re_raise=False):
            raise ValueError("Test error")
        return "after_error"

    result = asyncio.run(test_case())
    assert result == "after_error"


# ============================================================================
# Tests for GitHub URL formatting
# ============================================================================


def test_format_github_raw_url():
    """Test GitHub raw URL formatting"""
    url = format_github_raw_url("user", "repo", "main", "README.md")
    assert url == "https://raw.githubusercontent.com/user/repo/main/README.md"


def test_format_github_raw_url_with_subdirs():
    """Test GitHub raw URL with subdirectories"""
    url = format_github_raw_url("user", "repo", "v1.0", "/path/to/file.txt")
    assert url == "https://raw.githubusercontent.com/user/repo/v1.0/path/to/file.txt"


def test_format_github_release_url():
    """Test GitHub release URL formatting"""
    url = format_github_release_url("user", "repo", "v1.0.0", "pack.zip")
    assert url == "https://github.com/user/repo/releases/download/v1.0.0/pack.zip"


def test_format_github_release_url_with_tag():
    """Test GitHub release URL with different tag formats"""
    url = format_github_release_url("user", "repo", "release-1.0", "data.zip")
    assert url == "https://github.com/user/repo/releases/download/release-1.0/data.zip"


# ============================================================================
# Tests for semaphore
# ============================================================================


def test_create_semaphore():
    """Test semaphore creation"""
    sem = create_semaphore(max_concurrent=5)
    assert isinstance(sem, asyncio.Semaphore)


def test_semaphore_context():
    """Test semaphore context manager"""

    async def test_case():
        async with semaphore_context(max_concurrent=3) as sem:
            assert isinstance(sem, asyncio.Semaphore)
            async with sem:
                return "success"

    result = asyncio.run(test_case())
    assert result == "success"


def test_semaphore_concurrency():
    """Test semaphore concurrency limiting"""

    active_count = 0
    max_active = 0

    async def mock_operation():
        nonlocal active_count, max_active
        active_count += 1
        max_active = max(max_active, active_count)
        await asyncio.sleep(0.01)
        active_count -= 1

    async def test_case():
        nonlocal max_active
        async with semaphore_context(max_concurrent=2) as sem:
            tasks = []
            for _ in range(5):
                tasks.append(
                    asyncio.create_task(
                        async_with_sem(sem, mock_operation)
                    )
                )
            await asyncio.gather(*tasks)

    async def async_with_sem(sem, coro):
        async with sem:
            await coro()

    asyncio.run(test_case())
    assert max_active <= 2


# ============================================================================
# Tests for async client
# ============================================================================


def test_create_async_client():
    """Test async client creation"""
    try:
        client = create_async_client(timeout=60)
        assert client is not None
        asyncio.run(client.aclose())
    except ImportError:
        pass  # httpx not installed


def test_client_context():
    """Test client context manager"""

    async def test_case():
        async with client_context(timeout=60) as client:
            assert client is not None
        return "success"

    try:
        result = asyncio.run(test_case())
        assert result == "success"
    except ImportError:
        pass  # httpx not installed


@patch("meme_stickers.utils.file_source.httpx")
def test_fetch_url_with_mocked_client(mock_httpx):
    """Test fetching URL with mocked client"""
    async def test_case():
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "test content"
        mock_client.get.return_value = mock_response

        result = await fetch_url("https://example.com", client=mock_client)
        assert result == "test content"

    asyncio.run(test_case())


@patch("meme_stickers.utils.file_source.httpx")
def test_fetch_url_json_with_mocked_client(mock_httpx):
    """Test fetching JSON with mocked client"""
    async def test_case():
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_client.get.return_value = mock_response

        result = await fetch_url_json("https://api.example.com", client=mock_client)
        assert result == {"key": "value"}

    asyncio.run(test_case())


# ============================================================================
# Run tests
# ============================================================================


if __name__ == "__main__":
    import sys

    test_functions = [
        # op_retry tests
        test_op_retry_async_success,
        test_op_retry_async_with_retries,
        test_op_retry_async_exhausted,
        test_op_retry_async_with_specific_exception,
        # Checksum tests
        test_calculate_checksum_md5,
        test_calculate_checksum_sha1,
        test_calculate_checksum_sha256,
        test_calculate_checksum_bytes,
        test_calculate_checksum_invalid_algorithm,
        test_calculate_file_checksum,
        test_calculate_file_checksum_not_found,
        # Number parsing tests
        test_parse_relative_number_plain,
        test_parse_relative_number_kilobytes,
        test_parse_relative_number_megabytes,
        test_parse_relative_number_gigabytes,
        test_parse_relative_number_terabytes,
        test_parse_relative_number_decimal,
        test_parse_relative_number_invalid,
        # JSON tests
        test_json_dumps_basic,
        test_json_dumps_ensure_ascii_false,
        test_json_dumps_with_indent,
        test_json_dumps_sort_keys,
        # exception_notify tests
        test_exception_notify_no_error,
        test_exception_notify_with_reraise,
        test_exception_notify_without_reraise,
        # GitHub URL tests
        test_format_github_raw_url,
        test_format_github_raw_url_with_subdirs,
        test_format_github_release_url,
        test_format_github_release_url_with_tag,
        # Semaphore tests
        test_create_semaphore,
        test_semaphore_context,
        test_semaphore_concurrency,
        # Client tests
        test_create_async_client,
        test_client_context,
        test_fetch_url_with_mocked_client,
        test_fetch_url_json_with_mocked_client,
    ]

    failed = 0
    passed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
