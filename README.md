# Meme Stickers Plugin for AstrBot

A modular and extensible AstrBot plugin for sticker pack management with comprehensive lifecycle management, configuration handling, and auto-update capabilities.

## Features

### 🎨 Sticker Pack Management
- **Pack Discovery** - Automatically discovers and loads sticker packs from directory
- **Metadata Support** - Each pack has rich metadata (name, version, author, description)
- **Pack Filtering** - Enable/disable packs individually
- **Dynamic Reload** - Reload packs without restarting

### ⚙️ Configuration
- **ConfigWrapper** - Type-safe configuration management
- **JSON Configuration** - Easy-to-edit configuration file
- **Default Values** - Sensible defaults when config is missing
- **Property Accessors** - Convenient access to common settings

### 🔄 Auto-Update
- **Background Tasks** - Async background task for automatic updates
- **Configurable** - Enable/disable via configuration
- **Force Update** - Optional force update mode
- **Graceful Shutdown** - Proper task cancellation on plugin termination

### 🏗️ Architecture
- **Modular Design** - Clean separation of concerns
- **Lifecycle Hooks** - Proper initialize/terminate handling
- **Error Handling** - Graceful error handling with logging
- **Type Safety** - Full type hints throughout

## Installation

### Requirements

- Python 3.8+
- AstrBot framework

### Setup

1. Copy the plugin to your AstrBot plugins directory:
```bash
cp -r meme_stickers /path/to/astrbot/plugins/
```

2. AstrBot will automatically load and initialize the plugin on startup.

## Directory Structure

```
data/plugins/meme_stickers/     # Auto-created on first run
├── config.json                 # Plugin configuration
└── packs/                      # Sticker packs directory
    ├── pack1/
    │   ├── metadata.json      # Pack metadata
    │   └── stickers/          # Sticker images
    │       ├── sticker1.png
    │       └── sticker2.png
    └── pack2/
        └── ...
```

## Configuration

The plugin uses a `config.json` file with the following structure:

```json
{
  "auto_update": false,
  "force_update": false,
  "hub_url": "http://localhost:8888",
  "cache_timeout": 3600,
  "packs": {}
}
```

### Configuration Options

- **auto_update** - Enable automatic pack updates (default: false)
- **force_update** - Force update even if unchanged (default: false)
- **hub_url** - URL for pack downloads (default: http://localhost:8888)
- **cache_timeout** - Cache timeout in seconds (default: 3600)
- **packs** - Pack-specific configuration (default: {})

## Sticker Pack Format

Each sticker pack is a directory containing:

### metadata.json
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

### Sticker Files
- Located in `stickers/` subdirectory
- Supported formats: `.png`, `.jpg`, `.jpeg`, `.gif`
- Files are named `<sticker_name>.<ext>`

## Commands

### `/meme`
Shows help message with available commands.

### `/meme list`
Lists all available sticker packs with their status and sticker count.

Example output:
```
Available Sticker Packs:
  [✓] Animals (animals) - 5 sticker(s) - v1.0.0
  [✗] Memes (memes) - 10 sticker(s) - v1.2.0
```

### `/meme status`
Shows plugin status including:
- Data directory path
- Packs directory path
- Number of loaded packs
- Number of enabled packs
- Auto-update status

### `/meme help`
Shows detailed help information.

## Development

### Running Tests

Comprehensive smoke tests are included:

```bash
python test_smoke.py
```

Tests cover:
- ConfigWrapper functionality
- StickerPackManager operations
- Pack loading and filtering
- Auto-update task management
- Integration between components

### Component Demo

Run the component demonstration:

```bash
python demo_components.py
```

This demonstrates:
- ConfigWrapper usage
- StickerPackManager usage
- Component integration
- Simulated plugin lifecycle

### Project Structure

```
meme_stickers/
├── main.py                    # Main plugin code
├── metadata.yaml              # Plugin metadata
├── test_smoke.py              # Smoke tests
├── demo_components.py         # Component demo
├── PLUGIN_USAGE.md           # Detailed usage guide
├── TICKET_IMPLEMENTATION.md  # Implementation details
├── README.md                 # This file
└── .gitignore               # Git ignore rules
```

## Core Components

### ConfigWrapper
Wraps AstrBot configuration and provides convenient access to plugin settings.

**Key Methods:**
- `load(config_path)` - Load configuration from file
- `save(config_path)` - Save configuration to file
- `get(key, default)` - Get configuration value
- `set(key, value)` - Set configuration value

**Properties:**
- `auto_update` - Whether auto-update is enabled
- `force_update` - Whether force update is enabled
- `hub_url` - Hub URL for pack downloads
- `packs` - Sticker packs configuration

### StickerPackManager
Manages sticker pack lifecycle: loading, updating, and metadata.

**Key Methods:**
- `reload()` - Reload all packs from disk
- `get_pack(name)` - Get specific pack by name
- `list_packs()` - List all loaded packs
- `list_enabled_packs()` - List only enabled packs
- `start_auto_update(force)` - Start auto-update task
- `stop_auto_update()` - Stop auto-update task

### MemeStickersPlugin
Main plugin class that integrates all components.

**Lifecycle:**
- `__init__(context, config)` - Initialize plugin
- `initialize()` - Setup and start services
- `terminate()` - Cleanup and stop services

**Helper Methods:**
- `_plain(text)` - Create plain text message
- `_image(path)` - Create image message
- `_resolve_data_dir()` - Resolve data directory

## API Usage

### Basic Example

```python
from astrbot.api.star import Context
from astrbot.api.config import AstrBotConfig

# Plugin is automatically instantiated by AstrBot
plugin = MemeStickersPlugin(context, config)

# Initialize
await plugin.initialize()

# Access packs
packs = plugin.pack_manager.list_packs()
for pack in packs:
    print(f"{pack.display_name}: {len(pack.stickers)} stickers")

# Get specific pack
pack = plugin.pack_manager.get_pack("animals")
if pack:
    print(f"Stickers: {', '.join(pack.stickers)}")

# Cleanup
await plugin.terminate()
```

## Implementation Details

### Data Directory Resolution
1. First tries `context.get_data_path()`
2. Falls back to `data/plugins/meme_stickers`
3. Creates directory automatically if missing

### Pack Discovery
- Scans `packs/` directory for subdirectories
- Each subdirectory must have `metadata.json`
- Stickers loaded from `stickers/` subdirectory
- Invalid packs are logged and skipped

### Auto-Update
When enabled:
1. Background asyncio task created during initialization
2. Runs reload every hour (3600 seconds)
3. Honors `force_update` flag in configuration
4. Logs operations through AstrBot logger
5. Gracefully cancelled during termination

## Troubleshooting

### Plugin doesn't initialize
- Check AstrBot logs for errors
- Verify directory permissions
- Ensure data directory is writable

### Packs not loading
- Check pack directory structure
- Verify `metadata.json` format
- Check file permissions
- Review plugin logs

### Auto-update not working
- Verify `auto_update: true` in config
- Check network connectivity (if downloading)
- Review background task logs

## Contributing

Contributions are welcome! Areas for improvement:
- Network-based pack downloads
- Pack installation commands
- Sticker generation features
- Pack validation and checksums
- Cache mechanisms

## License

[MIT License](LICENSE)

## Author

**kamicry**

For more details, see:
- [PLUGIN_USAGE.md](PLUGIN_USAGE.md) - Detailed usage guide
- [TICKET_IMPLEMENTATION.md](TICKET_IMPLEMENTATION.md) - Implementation details

## Version History

### v2.0.0 (Current)
- Complete rewrite with modular architecture
- ConfigWrapper for configuration management
- StickerPackManager for pack lifecycle
- Comprehensive lifecycle hooks
- Auto-update with background tasks
- Full smoke test coverage

### v1.3.0 (Previous)
- Initial implementation with basic features
