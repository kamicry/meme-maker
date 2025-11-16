# Meme Stickers Plugin Usage

## Overview

The Meme Stickers plugin provides sticker pack management and generation capabilities for AstrBot.

## Architecture

### Core Components

1. **ConfigWrapper** - Wraps plugin configuration
   - Auto-loads from `config.json` in plugin data directory
   - Provides properties: `auto_update`, `force_update`, `hub_url`, `packs`
   - Handles save/load operations

2. **StickerPackManager** - Manages sticker packs
   - Discovers and loads packs from `packs/` directory
   - Supports pack filtering by enabled status
   - Handles automatic updates via background tasks
   - Provides pack metadata and sticker list access

3. **MemeStickersPlugin** - Main plugin class
   - Registered with `@register` decorator
   - Implements lifecycle hooks: `initialize()` and `terminate()`
   - Wires together ConfigWrapper and StickerPackManager
   - Creates data directories automatically

## Plugin Registration

```python
@register("meme_stickers", "kamicry", "Meme Stickers plugin for AstrBot", "2.0.0")
class MemeStickersPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        # Initialize configuration and manager
        ...
```

## Directory Structure

```
data/plugins/meme_stickers/
├── config.json              # Plugin configuration
└── packs/                   # Sticker packs directory
    ├── pack1/
    │   ├── metadata.json    # Pack metadata
    │   └── stickers/        # Sticker images
    │       ├── sticker1.png
    │       └── sticker2.png
    └── pack2/
        ├── metadata.json
        └── stickers/
            └── ...
```

## Configuration Format

The `config.json` file structure:

```json
{
  "auto_update": false,
  "force_update": false,
  "hub_url": "http://localhost:8888",
  "cache_timeout": 3600,
  "packs": {}
}
```

## Pack Metadata Format

Each pack's `metadata.json`:

```json
{
  "name": "pack_name",
  "display_name": "Friendly Pack Name",
  "description": "Pack description",
  "version": "1.0.0",
  "author": "Author Name",
  "enabled": true,
  "url": "https://example.com/pack.zip",
  "checksum": "abc123..."
}
```

## Lifecycle

### Initialization

1. Plugin constructor:
   - Creates ConfigWrapper instance
   - Resolves data directory (from context or fallback)
   - Creates data/packs directories if missing

2. `initialize()` hook:
   - Loads configuration from `config.json`
   - Creates StickerPackManager
   - Reloads all packs from disk
   - Optionally starts auto-update background task

### Termination

The `terminate()` hook:
- Stops auto-update task if running
- Cancels all background tasks
- Performs cleanup

## Commands

The plugin provides the following commands:

### `/meme` (no subcommand)
Shows help message with available commands.

### `/meme list`
Lists all available sticker packs with their status and sticker count.

### `/meme status`
Shows plugin status including:
- Data directory paths
- Number of loaded packs
- Auto-update status

### `/meme help`
Shows detailed help information.

## Usage Example

```python
# In AstrBot context
from astrbot.api.star import Context
from astrbot.api.config import AstrBotConfig

# Plugin is automatically instantiated by AstrBot
# context and config are provided by the framework
plugin = MemeStickersPlugin(context, config)

# Initialize plugin
await plugin.initialize()

# Access pack manager
packs = plugin.pack_manager.list_packs()
enabled_packs = plugin.pack_manager.list_enabled_packs()

# Get specific pack
pack = plugin.pack_manager.get_pack("pack_name")
if pack:
    print(f"Pack: {pack.display_name}")
    print(f"Stickers: {len(pack.stickers)}")

# Clean shutdown
await plugin.terminate()
```

## Auto-Update Feature

When `auto_update` is enabled in config:

1. Plugin creates a background asyncio task during initialization
2. Task runs every hour (3600 seconds)
3. Each cycle calls `pack_manager.reload()` to refresh packs
4. Task is cancelled during plugin termination

Force update (`force_update: true`) ensures packs are reloaded even if unchanged.

## Testing

Run smoke tests to verify plugin functionality:

```bash
python test_smoke.py
```

Tests cover:
- ConfigWrapper initialization and operations
- StickerPackManager pack loading and filtering
- Auto-update task management
- Integration between components
- Error handling with empty directories

## Implementation Notes

1. **Data Directory Resolution**:
   - First tries `context.get_data_path()`
   - Falls back to `data/plugins/meme_stickers`
   - Creates directories automatically

2. **Pack Discovery**:
   - Scans `packs/` directory for subdirectories
   - Each subdirectory must contain `metadata.json`
   - Stickers loaded from `stickers/` subdirectory
   - Supports: .png, .jpg, .jpeg, .gif

3. **Configuration Loading**:
   - Loads from `config.json` if exists
   - Uses defaults if file not found
   - Automatically saves when modified

4. **Error Handling**:
   - Graceful handling of missing files
   - Logs errors without crashing
   - Continues operation with partial data

## Extension Points

The plugin is designed to be extended:

1. Add new pack sources (network downloads)
2. Implement pack installation/removal
3. Add sticker generation capabilities
4. Implement caching mechanisms
5. Add pack validation and checksums

## Dependencies

Required AstrBot API imports:
- `astrbot.api.event` - Filter decorators and event types
- `astrbot.api.star` - Context, Star base class, register decorator
- `astrbot.api.config` - AstrBotConfig
- `astrbot.api` - Logger

Standard library dependencies:
- `asyncio` - Async operations and background tasks
- `json` - Configuration and metadata parsing
- `pathlib` - Path operations
- `dataclasses` - Structured data (StickerPackMetadata)
