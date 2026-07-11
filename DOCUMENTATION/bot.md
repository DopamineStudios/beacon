## `bot.py` Documentation


This is the entry point for the framework. Follow the initialization example below to load your Discord bot with Beacon (Note: For simplicity and security's sake, the framework does NOT run/start the bot automatically. You have to do it yourself, as shown in the code snippet below).

---

### Initialization (in your main.py)

```python
from beacon import Bot
import discord

bot = Bot(
    command_prefix="!",
    cogs_path="cogs",
    version_file="VERSION.txt",
    default_diagnostics=True,
    status=discord.Status.online,
    activity=discord.Game(name="Example"),
    intents=discord.Intents.default()
)

bot.run("YOUR_TOKEN_HERE")

```

#### Parameters

|       Parameter        |        Type        |            Default             |                                                                                                                                                                      Description                                                                                                                                                                      |
|:----------------------:|:------------------:|:------------------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|    `command_prefix`    |       `str`        |              `!`               |                                                                                                                                                            Prefix for text-based commands.                                                                                                                                                            |
|      `cogs_path`       |       `str`        |            `"cogs"`            |                                                                                                                                             Directory containing `.py` files to be loaded as extensions.                                                                                                                                              |
|       `log_path`       |       `str`        |             `None`             |                                                                                                                              File path for the `aiosqlite` logging database. If `None`, the Logging Manager is disabled.                                                                                                                              |
| `default_diagnostics`  |       `bool`       |             `True`             |                                                                                                                                                  Whether to load the built-in diagnostics extension.                                                                                                                                                  |
|        `status`        |  `discord.Status`  |             `None`             |                                                                                                                                                         Initial presence status for the bot.                                                                                                                                                          |
|       `activity`       | `discord.Activity` |             `None`             |                                                                                                                                                             Initial activity for the bot.                                                                                                                                                             |
| `global_cooldown_rate` |       `int`        |              `10`              |                                                                                                                             The number of commands that use global cooldown that are allowed within the cooldown window.                                                                                                                              |
| `global_cooldown_per`  |      `float`       |             `60.0`             |                                                                                                                                                     The length of the cooldown window in seconds.                                                                                                                                                     |
|   `minimal_caching`    |       `bool`       |            `False`             |                                                                                                                                           Reduces memory usage by disabling useless caching of all members.                                                                                                                                           |
|    `accent_colour`     |  `discord.Colour`  |   `discord.Color(0x944ae8)`    |                                                                                                                                         Accent colour used for the `/ping` embed and `/latency graph` graph.                                                                                                                                          |
|      `bot_logger`      |  `logging.Logger`  | `logging.GetLogger("discord")` |                                                                                                                                                            The logger for the bot process.                                                                                                                                                            |
|     `version_file`     |       `str`        |             `None`             |                                                                                                                                           Optional path to a file containing the bot's deployment version.                                                                                                                                            |
|     `secure_mode`      |       `bool`       |            `False`             | Optional parameter to enable Beacon's secure mode. Strips down the /ping command to not show host location and not load in geocoder, and Owner Dashboard to only cog reloading and slash command syncing to prevent damage if owner account is hacked. Cog unloading & uploading, bot shutdown and restart, and the ability to view logs is disabled. |
|   `*args / **kwargs`   |       `Any`        |               -                |                                                                                                                                     Supports all standard `discord.ext.commands.Bot` arguments (e.g., `intents`).                                                                                                                                     |

---

### Usage Notes

* **IMPORTANT:** Do NOT define a `setup_hook` or `on_ready` function in your main.py. The framework already defines those. If you try to define your own, the bot may crash due to conflicts.