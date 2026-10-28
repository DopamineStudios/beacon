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
    try:
        mention = await resolve_command_mention(interaction.client, "ping")
        await interaction.response.send_message(f"Please use {mention} for details.")
    except (discord.HTTPException, discord.Forbidden) as e:
        await interaction.response.send_message(
            "⚠️ Unable to fetch command information. Please try again later.",
            ephemeral=True
        )
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
    try:
        resolved = await parse_command_links(interaction.client, text)
        await interaction.response.send_message(resolved)
    except (discord.HTTPException, discord.Forbidden) as e:
        await interaction.response.send_message(
            "⚠️ Unable to process command links at this time.",
            ephemeral=True
        )
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

---

## Fallback Behavior

When a command cannot be found (not registered or not yet synced), the parser returns the command path as monospace code (e.g. `` `/unknown_command` ``) instead of a clickable mention. This provides clear visual feedback to users that the command reference is incomplete while maintaining message readability.

**Example:**
```python
# Command exists in tree
"</ping>" → "</ping:123456789012345678>" (clickable)

# Command not found or not synced
"</unknown>" → "`/unknown`" (plain text, monospace)
```

---

## Error Handling

Both `resolve_command_mention()` and `parse_command_links()` may raise exceptions during command fetching:

- **`discord.HTTPException`**: Discord API errors (rate limits, server issues)
- **`discord.Forbidden`**: Bot lacks `applications.commands` scope or permissions
- **`discord.NotFound`**: Command tree or guild no longer exists

**Best Practice:** Wrap calls in try-except blocks and provide user-friendly fallback messages for production code.
