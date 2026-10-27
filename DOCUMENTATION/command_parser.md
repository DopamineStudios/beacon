## Dynamic Command Link Parser Documentation

The Dynamic Command Link Parser solves the problem of broken Discord application command mentions (`</command:id>`) caused by changing command IDs after synchronization (`sync()`). 

Instead of hardcoding snowflake IDs, developers can reference commands by their natural name or hierarchical path (e.g. `</ping>` or `</beacon diagnostics>`), and the framework automatically resolves the active Discord command ID from cache or remote API fetch, outputting the correct Discord mention format `</name:id>`.

---

## Functions

### `resolve_command_mention`

Resolves a command path (e.g. `'ping'` or `'beacon diagnostics'`) to a clickable Discord mention string.

#### **Usage**

```python
from beacon import resolve_command_mention
from beacon.core import beacon_commands
import discord

@beacon_commands.command()
async def test_mention(interaction: discord.Interaction):
    mention = await resolve_command_mention(interaction.client, "ping")
    await interaction.response.send_message(f"Please use {mention} for details.")
```

#### **Parameters**

|   Parameter    |         Type          | Default |                               Description                                |
|:--------------:|:---------------------:|:-------:|:------------------------------------------------------------------------:|
|     `bot`      | `commands.Bot`        |   N/A   |                Bot instance owning the command tree.                     |
| `command_path` | `str`                 |   N/A   |            Name or space-separated hierarchical path of the command.       |
|    `guild`     | `discord.Guild \| None` | `None`  |                Optional guild for guild-scoped command resolution.       |

---

### `parse_command_links`

Scans text for dynamic command tags (e.g. `'</ping>'` or `'</beacon diagnostics>'`) and replaces them with valid mentions.

#### **Usage**

```python
from beacon import parse_command_links
from beacon.core import beacon_commands
import discord

@beacon_commands.command()
async def info(interaction: discord.Interaction):
    text = "Check out our commands: </ping> and </beacon diagnostics>."
    resolved = await parse_command_links(interaction.client, text)
    await interaction.response.send_message(resolved)
```

#### **Parameters**

| Parameter |         Type          | Default |                         Description                          |
|:---------:|:---------------------:|:-------:|:------------------------------------------------------------:|
|   `bot`   | `commands.Bot`        |   N/A   |             Bot instance owning the command tree.            |
|  `text`   | `str`                 |   N/A   |     Input string containing dynamic command tags.            |
|  `guild`  | `discord.Guild \| None` | `None`  |         Optional guild for guild-scoped resolution.          |

---

## Caching & Synchronization

The command parser maintains an in-memory cache of resolved application command IDs (`bot._beacon_command_cache`). When commands are synchronized via Beacon's `CommandRegistry` (`smart_sync()` or `force_sync()`), the cache is automatically invalidated and refreshed, ensuring that command links remain unbroken even after tree updates.
