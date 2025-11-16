# Async Generator Handlers Fix

## Problem
The `meme_command` handler was incorrectly trying to `await` async generator functions, causing:
```
TypeError: object async_generator can't be used in 'await' expression
```

## Root Cause
In `main.py` lines 447-449, the code attempted:
```python
await self._handle_list(event)  # ❌ Wrong - async generators cannot be awaited
await self._handle_status(event)  # ❌ Wrong - async generators cannot be awaited
```

Both `_handle_list` and `_handle_status` are async generator functions (they use `yield`), which cannot be awaited directly. They must be iterated using `async for`.

## Solution Applied
Changed all async generator handler calls to use `async for` iteration:

### Before
```python
if sub_command == "list":
    await self._handle_list(event)
elif sub_command == "status":
    await self._handle_status(event)
```

### After
```python
if sub_command == "list":
    async for msg in self._handle_list(event):
        yield msg
elif sub_command == "status":
    async for msg in self._handle_status(event):
        yield msg
```

## Changes Made
1. **Line 447-448**: `await self._handle_list(event)` → `async for msg in self._handle_list(event): yield msg`
2. **Line 450-451**: `await self._handle_status(event)` → `async for msg in self._handle_status(event): yield msg`

## Verification
- ✅ Python syntax validation passes
- ✅ Git diff shows correct changes
- ✅ All handler methods remain as async generators (using `yield`)
- ✅ Command routing logic preserved
- ✅ No other async generator calls found in the codebase

## Expected Behavior After Fix
- `/meme list` - Lists all sticker packs without TypeError
- `/meme status` - Shows plugin status without TypeError
- `/meme help` - Shows help message (already working, uses direct yield)
- `/meme` - Shows default help (already working, uses direct yield)
- All messages correctly propagate through the event pipeline

## Technical Details
- **Async generators** are functions that use both `async def` and `yield`
- They return async generator objects, not awaitables
- Must be consumed with `async for`, not `await`
- The `meme_command` handler itself is also an async generator
- Messages must be yielded from the main handler to propagate to AstrBot
