## Beacon Commands Documentation
<sub>(This documentation is about the framework's `@beacon_commands` wrapper for standard discord.py's decorator `@app_commands`, and about how to use the preconditions feature through it. To read about the decorators meant to be used with slash commands when you use the discord.py `@app_commands.command` decorator instead of Beacon's equivalent, read `preconditions.md`.)

The `beacon_commands` module provides a wrapper around standard `discord.py` app commands. It simplifies the process of creating slash commands by integrating **permission presets**, **cooldowns**, and **global rate limiting** directly into a single decorator or group class.

All standard features, decorators, and classes from `discord.app_commands` are also exposed directly through this module.

---

## `beacon_commands.command`

This decorator replaces the standard `@app_commands.command()`. It allows you to define functional constraints (like permissions and rate limits) as keyword arguments.

### **Usage**

```python
from discord import interaction, member
import beacon_commands

@beacon_commands.command(
    name="ban",
    description="Ban a user from the server",
    permissions_preset="moderator",
    global_cooldown=True
)
async def ban_member(interaction: interaction, member: member):
    await member.ban()
    await interaction.response.send_message(f"Banned {member}")

```

### **Parameters**
|       Parameter       |         Type         |    Default     |                                       Description                                        |
|:---------------------:|:--------------------:|:--------------:|:----------------------------------------------------------------------------------------:|
|        `name`         |        `str`         | Function Name  |                              The name of the slash command.                              |
|     `description`     |        `str`         |   Docstring    |                       The command description visible in Discord.                        |
| `permissions_preset`  |        `str`         |     `None`     |         Apply a pre-defined set of permissions (e.g., `"admin"`, `"moderator"`).         |
|      `cooldown`       | `tuple[int, float]`  |     `None`     |           A custom cooldown for this specific command: `(rate, per_seconds)`.            |
|   `global_cooldown`   |        `bool`        |     `True`     | If `True`, the command respects the bot's global rate limit defined in the `Bot` class.  |
 |
|      `**kwargs`       |        `Any`         |      N/A       |           Standard `app_commands.command` kwargs (e.g., `guild_only`, `nsfw`).           |

|

Note: Except for the `"bot_owner"` preset, applying any of the permission decorators below automatically restricts the command to guilds only, because the command will fail and be unusable outside guilds anyway if there is a preset or any permission check because they require a guild context, and if you use a permission check like that then there really isn't any case where the command needs to be permission-restricted in guilds but still usable in DMs.

---

## `beacon_commands.Group`

A subclass of `app_commands.Group` that automatically cascades settings down to any subcommand added to the group.

### **Usage**

```python
from beacon import beacon_commands

# Create the group with preset configuration
admin_group = beacon_commands.Group(name="admin", description="Admin commands", permissions_preset="admin")

# Define a standard command
@beacon_commands.command(name="check", description="Checks admin status")
async def admin_check(interaction):
    await interaction.response.send_message("You're an admin!")

# Add the command to the group to inherit features
admin_group.add_command(admin_check)

```

### **Cascade Behaviour**

When a command is added to a `Group` using `.add_command()`, the group applies its own constraints onto that command:

1. **Guild Only:** Except for the `"bot_owner"` preset, applying any of the permission decorators below automatically restricts the command to guilds only, because the command will fail and be unusable outside guilds anyway if there is a preset or any permission check because they require a guild context, and if you use a permission check like that then there really isn't any case where the command needs to be permission-restricted in guilds but still usable in DMs.
2. **Permissions:** The group’s permissions preset is applied to the command.
3. **Cooldowns:** If a specific group `cooldown` is defined, it is applied to the command. Otherwise, if `global_cooldown` is active on the group, a global cooldown is enforced.



---

## Permission Presets

|    Preset    |                    Required Permissions                     |
|:------------:|:-----------------------------------------------------------:|
| `bot_owner`  |        Restricts usage to the bot owner/team owners.        |
| `moderator`  | Manage Messages, Kick Members, Timeout Members, Ban Members |
|   `admin`    |                        Administrator                        |
| `giveaways`  |                Manage Guild, Manage Messages                |
| `automation` |       Manage Guild, Manage Messages, Manage Channels        |
|  `manager`   |         Manage Guild, Manage Roles, Manage Channels         |
|  `support`   |            Manage Messages, Read Message History            |
|  `security`  |              View Audit Log, Moderate Members               |
| `community`  |  Manage Expressions, Manage Threads, Create Public Threads  |
| `technical`  |                Manage Webhooks, Manage Guild                |

---

## Error Handling

The framework includes a built-in error handler in `bot.py` that catches issues raised by these decorators.

* **Missing Permissions:** If a user lacks the required preset permissions, they receive a message listing the specific missing requirements.
* **Rate Limiting:** If a user triggers a local or global cooldown, they are notified of the exact time remaining.

In addition to these, the error handler also serves a dual purpose of acting as an error handler for any unexpected command related exception in your code and gracefully displaying an error message to the users instead of letting the interaction fail.

---

## Key Differences from Standard Discord.py

1. **Implicit Global Cooldown:** Every beacon command is protected by the global rate limit by default.
2. **Dynamic Inheritance:** Commands added to a `beacon_commands.Group` automatically inherit cooldowns and permission structures from their parent group layout.
3. **Module Passthrough:** You do not need to import both `discord.app_commands` and `beacon_commands`; the framework dynamically exposes all vanilla attributes directly from `beacon_commands`.
