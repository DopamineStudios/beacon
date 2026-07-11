<div align="center">

# Beacon

</div>

<p align="center">
  <a href="https://pypi.org/project/discord-beacon/">
    <img src="https://img.shields.io/pypi/v/discord-beacon?style=for-the-badge&logo=pypi&color=blue" />
  </a>
  <a href="https://www.python.org/">
  <img src="https://img.shields.io/badge/python-3.12+-yellow?style=for-the-badge&logo=python&logoColor=white" />
</a>
  <a href="https://github.com/dopaminestudios/beacon/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/dopaminestudios/beacon?style=for-the-badge&color=orange" />
  </a>
</p>

<p align="center">
  <a href="#installing"><b>Install</b></a> •
  <a href="#features"><b>Features</b></a> •
  <a href="#comparison-with-sapphire-framework-and-bare-bones-discordpy"><b>Comparison</b></a> •
  <a href="#implementation-example"><b>Quick Start</b></a> •
  <a href="https://github.com/smite-codes/beacon/issues"><b>Report Bug</b></a>
</p>

Beacon is an **Unopinionated Framework** for discord.py which allows you to initialise a production-ready Discord bot in just 4 lines of code. It is designed to streamline the development of scalable Discord applications by automating the process of registering commands and simplify the process of creating them, diagnosing the bot, and various other utilities such as a paginator helper and "Private View" helpers which let only the user who initiated the interaction to interact with the components like buttons.

A **Dopamine Studios** project.

---
## Installing

**Use Python 3.12 or higher:**

```Linux/MacOS
# Linux/MacOS
python3 -m pip install -U discord-beacon
```
```Windows
# Windows
py -3 -m pip install -U discord-beacon
```
## Features

### 1. Smart Command Syncing

The framework includes a Command Registry that compares local command states with remote Discord API states. This ensures that global and guild-specific slash commands are only synced when changes are detected, preventing unnecessary API overhead and rate-limit triggers.

### 2. Beacon Commands decorator with Preconditions
The `@beacon_commands.command` decorator replaces the standard discord.py version, allowing you to define permissions and cooldowns in a single line.

* **Simplified Syntax:** Define name, description, permissions, and cooldowns within one decorator.
* **Implicit Global Cooldown:** Every command is protected by the bot's global rate limit by default.
* **Group Support:** Use `beacon_commands.Group` to apply permissions or cooldowns to an entire category of subcommands at once.

```python
from beacon import beacon_commands

@beacon_commands.command(
    name="ban",
    permissions_preset="moderator"
)
async def ban_member(interaction: discord.Interaction, member: discord.Member):
    await member.ban()
    await interaction.response.send_message(f"{member.display_name} has been banned.")
```

### 3. Precondition Decorators
If you prefer using standard `app_commands`, you can use the standalone `@preconditions` decorators to enforce rules dynamically.

* **Permission Presets:** Use pre-defined roles like `"admin"`, `"moderator"`, or `"support"` instead of manual permission bitfields.
* **Advanced Logic:** Includes `has_permissions_any` (pass if user has one of many) and `has_permissions` (must have all).
* **Smart Rate Limiting:** Easily implement command-specific or bot-wide global cooldowns to prevent spam.

|    Preset     |                   Required Permissions                    |
|:-------------:|:---------------------------------------------------------:|
| `"bot_owner"` |       Restricts usage to the bot owner/team owners.       |
|  `moderator`  |        Manage Messages, Kick Members, Ban Members         |
|    `admin`    |                       Administrator                       |
|  `giveaways`  |               Manage Guild, Manage Messages               |
| `automation`  |      Manage Guild, Manage Messages, Manage Channels       |
|   `manager`   |        Manage Guild, Manage Roles, Manage Channels        |
|   `support`   |           Manage Messages, Read Message History           |
|  `security`   |             View Audit Log, Moderate Members              |
|  `community`  | Manage Expressions, Manage Threads, Create Public Threads |
|  `technical`  |               Manage Webhooks, Manage Guild               |

### 4. In-Discord Owner Dashboard

No need for terminal access/SSH. This simple to use and feature-rich dashboard for bot owners allows you to unload/reload cogs on the fly, restart the bot, or check logs, accessed using `/od`. This allows bot owner(s) to manage, diagnose the bot right within Discord itself. This dashboard allows the bot to run idefinitely without restarts:

* **Cog Management:** Dynamic loading, unloading, and uploading/replacing of cogs.
* **Power State:** Remote shutdown and process-level restarts.
* **Logs:** Real-time retrieval of log files via the Discord UI.
* **Manual Command Syncs:** Sync commands manually globally or within only the current guild.
### 5. Diagnostics

The built-in `Diagnostics` "cog" (module) provides real-time monitoring of the bot's health, including:

* **Latency:** High precision API, Heartbeat, and Round-trip latency monitoring.
* **Resource Utilization:** CPU and RAM usage tracking via `psutil`.
* **Graphs:** Generate graphs for the bot's latency for visual performance auditing.
* **Host Device Metrics:** Integration with system sensors to report host location and battery status, if available.

### 6. Helper Views

* Beacon Framework includes a suite of helper views which provides subclasses or wrappers of `discord.ui.View` and `discord.ui.LayoutView` that restrict interaction to a specific user and doesn't let anyone use the interaction (buttons, dropdowns, etc.) other than the person who triggered the command or interaction, and provides Confirmation Views that trigger a given callback upon confirmation.


---

### Comparison (with Sapphire Framework and standard discord.py)

| Feature                                                |              Beacon              |         Sapphire (js/ts)         |             discord.py             |
|:-------------------------------------------------------|:--------------------------------:|:--------------------------------:|:----------------------------------:|
| **Easy Setup**                                         | **✅ <br/>(minimal boilerplate)** | **❌** <br/>(Lots of boilerplate) |               **❌**                |
| **Preconditions Support**                              |              **✅**               |              **✅**               |               **❌**                |
| **Presets for Permission Checks<br/>in Preconditions** |              **✅**               |              **❌**               |               **❌**                |
| **No tantrums over different structure**               |              **✅**               |              **❌**               |               **✅**                |
| **Python's ease of use**                               |              **✅**               |              **❌**               |               **✅**                |
| **Smart Commands Sync**                                |       **✅<br/>(Built-in)**       |   **✅** <br/>(Through plugins)   | **❌** <br/>(not included/standard) |
| **In-Discord Dashboard**                               |      **✅ <br/>(Built-in)**       |              **❌**               |               **❌**                |
| **Latency Graphs**                                     |      **✅ <br/>(Built-in)**       |              **❌**               |               **❌**                |
| **Scalability***                                       |              **✅**               |              **✅**               |               **✅**                |
| **Fast Iteration**                                     |              **✅**               |              **❌**               |               **❌**                |
| **Strict TypeScript Rules**                            |              **❌**               |              **✅**               |               **❌**                |
| **Built-in Resource Monitoring**                       |              **✅**               |              **❌**               |               **❌**                |
| **Built-in helper Views**                              |              **✅**               |              **❌**               |               **❌**                |
| **Is it JS, tho?**                                     |              **❌**               |              **✅**               |               **❌**                |
| **Wins Imaginary Benchmarks**                          |              **❌**               |              **✅**               |               **❌**                |

<sup>*Scalability refers to ability to run without problems when the bot is in tens of thousands of servers or more. While it's a common myth that "Python is bloated", that's not true in the context of Discord bots. The real bottleneck in popular Discord bots always comes down to network, not code execution time or memory usage.</sup>


---

## Implementation Example

To initialize a bot using the Beacon, follow the following example:

```python
import discord
from beacon import BeaconBot # or import and use BeaconAutoShardedBot so that your bot will automatically handle sharding as it grows

bot = BeaconBot(command_prefix="?", cogs_path="your cogs/modules folder path here*", logging_path="path to .sqlite, .db, or .db3 file; only define if you want to use this logging backend.", default_diagnostics=True, intents=discord.Intents.default()) # If no cogs folder is defined, it will default to "cogs". If no logging path, logging will be disabled.

bot.run("YOUR_BOT_TOKEN_HERE")
```
<sub>*Note: It's recommended to put all your cogs or modules into the path you define for it. All .py files will be attempted to be loaded in the folder. However, if it can't be loaded for whatever reason, the bot will not crash and simply give a warning and continue, which is helpful if you don't want to create a second folder for non-cog files or load a cog manually. This is what makes Beacon an unopinionated framework.</sub>

---

## Requirements

* `discord.py`
* `aiosqlite`
* `psutil`
* `pyvips`
* `geocoder`

---

## Licence & Attribution

Beacon is licensed under the **Apache Licence 2.0**.

### How to Credit
While you are free to use this framework for private or commercial bots, we require explicit credit. Please include a link to this repository or a mention of "Beacon Framework by Dopamine Studios" in:
1. Your project's **README** or documentation.
2. Your bot's **info/credits command** (for example `/about` or `/help`).

*Example: "Built with [__Beacon Framework by Dopamine Studios__](https://github.com/dopaminestudios/beacon)"*
