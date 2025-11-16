# Sticker Pack Manager Module

This module provides a complete domain layer for managing sticker packs in the Meme Stickers AstrBot plugin.

## Overview

The `sticker_pack` module handles all pack-related operations including:
- Loading and validating packs from disk
- Downloading and installing packs from a hub
- Updating existing packs
- Deleting packs
- Manifest and configuration management

## Architecture

### Models (`models.py`)

Core data structures using dataclasses:

- **FileSource**: Enum for sticker source (LOCAL, REMOTE, BUILTIN)
- **StickerInfo**: Information about a single sticker
- **GridSettings**: Grid rendering configuration for a pack
- **PackManifest**: Pack metadata from `metadata.json`
- **PackConfig**: Pack configuration settings
- **HubPackInfo**: Information about a pack in the hub

All models support JSON serialization via `to_dict()` and `from_dict()` methods.

### Pack Operations (`pack.py`)

The `Pack` class represents a single sticker pack on disk:

```python
from meme_stickers.sticker_pack import Pack

pack = Pack(Path("/path/to/pack"))
manifest = await pack.load_manifest()
stickers = await pack.discover_stickers()
is_valid = await pack.validate()
```

Key methods:
- `load_manifest()`: Load and validate pack metadata
- `discover_stickers()`: Find sticker files in the pack
- `validate()`: Check pack structure and contents
- `save_manifest()`: Write manifest to disk
- `list_stickers()`: Get list of sticker names

### Hub Access (`hub.py`)

The `HubClient` class handles communication with the pack hub:

```python
from meme_stickers.sticker_pack import HubClient

hub = HubClient("http://example.com/hub")
packs = await hub.fetch_packs()
pack_info = await hub.fetch_pack_info("pack_name")
await hub.download_pack(url, output_path)
```

Features:
- Fetch available packs from hub
- Download pack files
- Checksum validation
- Built-in caching with TTL
- Manifest URL fetching

### Pack Updates (`update.py`)

The `PackUpdater` class handles downloading and installing packs:

```python
from meme_stickers.sticker_pack import PackUpdater, HubClient

hub = HubClient(hub_url)
updater = PackUpdater(hub)

pack_zip = await updater.download_pack(hub_pack_info, output_dir)
extracted = await updater.extract_pack(zip_path, extract_dir)
installed = await updater.install_pack(pack_zip, install_dir)
```

### Pack Manager (`manager.py`)

The `StickerPackManager` class orchestrates all operations:

```python
from meme_stickers.sticker_pack import create_pack_manager, PackState

# Create manager using factory function
manager = create_pack_manager(base_path, hub_url)

# Load packs from disk
await manager.reload()

# List packs
packs = manager.list_packs()
manifest = manager.get_manifest("pack_name")

# Install a pack
await manager.install_pack(hub_pack_info)

# Update a pack
await manager.update_pack("pack_name")

# Delete a pack
await manager.delete_pack("pack_name")

# Fetch available packs from hub
hub_packs = await manager.fetch_hub_packs()
```

#### Pack State Events

The manager supports callbacks for pack state changes:

```python
def on_pack_event(event):
    print(f"Pack {event.pack_name}: {event.state}")
    if event.error:
        print(f"Error: {event.error}")

manager.on_pack_state_change(on_pack_event)
```

Pack states:
- `LOADING`: Pack is being loaded
- `LOADED`: Pack loaded successfully
- `INSTALLING`: Pack installation in progress
- `INSTALLED`: Pack installed successfully
- `UPDATING`: Pack update in progress
- `UPDATED`: Pack updated successfully
- `DELETING`: Pack deletion in progress
- `DELETED`: Pack deleted successfully
- `ERROR`: Operation failed

## Directory Structure

Expected pack structure:

```
packs/
├── pack_name_1/
│   ├── metadata.json
│   └── stickers/
│       ├── sticker1.png
│       ├── sticker2.png
│       └── ...
├── pack_name_2/
│   ├── metadata.json
│   └── stickers/
│       └── ...
└── ...
```

## Configuration

Configuration is stored in `config.json` in the base directory:

```json
{
  "packs": {
    "pack_name": {
      "name": "pack_name",
      "display_name": "Display Name",
      "description": "Pack description",
      "enabled": true,
      "shortcuts": [],
      "grid_settings": {
        "columns": 3,
        "rows": 3,
        "cell_width": 200,
        "cell_height": 200,
        "background_color": "#FFFFFF",
        "border_color": "#000000",
        "border_width": 1
      }
    }
  }
}
```

## Pack Manifest Format

Each pack's `metadata.json`:

```json
{
  "name": "pack_name",
  "display_name": "Display Name",
  "description": "Description",
  "version": "1.0.0",
  "author": "Author Name",
  "enabled": true,
  "url": "https://example.com/pack.zip",
  "checksum": "abc123def456",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-02T00:00:00",
  "stickers": [
    {
      "name": "sticker1",
      "path": "stickers/sticker1.png",
      "file_source": "local",
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

## Hub API Format

The hub returns pack information in this format:

```json
{
  "status": "success",
  "total": 5,
  "packs": [
    {
      "name": "pack_name",
      "display_name": "Display Name",
      "description": "Description",
      "url": "https://example.com/pack.zip",
      "version": "1.0.0",
      "author": "Author Name",
      "size": 1024000,
      "preview_url": "https://example.com/preview.jpg",
      "downloads": 1250,
      "checksum": "abc123def456"
    }
  ]
}
```

## Error Handling

All operations raise specific exceptions:

- **PackError**: Pack operation failed (load, validate, save)
- **HubError**: Hub communication failed
- **UpdateError**: Update/install operation failed
- **ManagerError**: Manager operation failed

```python
from meme_stickers.sticker_pack import PackError, HubError, UpdateError, ManagerError

try:
    manifest = await pack.load_manifest()
except PackError as e:
    print(f"Pack error: {e}")
except HubError as e:
    print(f"Hub error: {e}")
except UpdateError as e:
    print(f"Update error: {e}")
except ManagerError as e:
    print(f"Manager error: {e}")
```

## Integration with AstrBot Plugin

The module is designed to work without NoneBot dependencies. Integration with the main plugin:

```python
from meme_stickers.sticker_pack import create_pack_manager
from pathlib import Path

# In plugin initialization
manager = create_pack_manager(
    base_path=plugin_data_dir,
    hub_url=config.get("hub_url", "http://localhost:8888")
)

await manager.reload()

# Register state change callbacks for dynamic shortcut registration
def on_pack_state_change(event):
    if event.state == PackState.LOADED:
        register_pack_shortcuts(event.pack_name)

manager.on_pack_state_change(on_pack_state_change)
```

## Testing

The module includes comprehensive integration tests using temporary directories:

```bash
python test_pack_manager.py
```

Test coverage includes:
- Manifest serialization/deserialization
- Config serialization/deserialization
- Pack validation
- Pack loading from disk
- Pack event callbacks
- Hub pack listing
- Pack installation
- Pack deletion

## Performance Considerations

1. **Caching**: Hub pack list is cached with configurable TTL
2. **Async Operations**: All I/O operations are async to avoid blocking
3. **Streaming Downloads**: Pack downloads use streaming for large files
4. **Lazy Loading**: Packs are loaded on-demand during reload
5. **Checksum Verification**: Optional checksum validation for downloaded files

## Security

1. **Path Validation**: All paths are validated and normalized
2. **Checksum Verification**: Downloaded files are validated against checksums
3. **Sandbox Extraction**: Pack extraction uses safe zip handling
4. **Configuration Isolation**: Each pack has isolated configuration

## Future Enhancements

1. Incremental updates (delta sync)
2. Parallel pack downloads
3. Pack dependency resolution
4. Backup/restore functionality
5. Pack search and filtering
6. Performance metrics and monitoring
