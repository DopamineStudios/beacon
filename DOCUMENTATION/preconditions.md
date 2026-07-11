## Preconditions Feature Documentation

<sub>(This documentation is about the decorators meant to be used with slash commands when you use the discord.py `@app_commands.command` decorator instead of Beacon's equivalent. To use preconditions through the `@beacon_commands.command()` decorator, read `beacon_commands.md`.)

The **Preconditions** feature provides set of decorators for `discord.py` slash commands to enforce specific rules. They cover common use cases such as permission checks and rate limiting (cooldowns).

---

## **Permission Checks**

*Note: Except for the `"bot_owner"` preset, applying any of the permission decorators below automatically restricts the command to guilds only, because the command will fail and be unusable outside guilds anyway if there is a preset or any permission check because they require a guild context, and if you use a permission check like that then there really isn't any case where the command needs to be permission-restricted in guilds but still usable in DMs.*

### Preset Decorators

#### `permissions_preset(preset_name: str)`

Instead of listing every required permission manually, you can use pre-defined presets tailored for specific roles.

* **Usage:** `@preconditions.permissions_preset("moderator")`


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

### Non-Preset Decorators

#### 1. `has_permissions(min_required: int = None, perms)`

Ensures the user has the specified permissions. By default, they must match **ALL** provided permissions, but this can be customised using `min_required`.

* **Parameters:**
  * `min_required`: The number of permissions out of the total provided that the user must possess. Defaults to `None` (all must match).
* **Usage (All):** `@preconditions.has_permissions(manage_messages=True, manage_nicknames=True)`
* **Usage (Any/Minimum):** `@preconditions.has_permissions(min_required=1, manage_guild=True, administrator=True)`

#### 2. `is_bot_owner()`

A dedicated check to restrict command usage strictly to the bot owner or team owners.
* **Usage:** `@preconditions.is_bot_owner()`

---

### **Rate Limiting/Cooldowns**

The framework supports both command-specific cooldowns and a global cooldown. Both are meant to be mutually exclusive, and you should only use one of them at once.

#### 1. `cooldown(rate: int = 10, per: float = 60)`

Applies a cooldown to a specific command for the user.

* **Parameters:**
  * `rate`: Number of times the command can be used.
  * `per`: The window of time (in seconds).
* **Usage:** `@preconditions.cooldown(rate=1, per=5.0)` (Allows 1 use every 5 seconds).



#### 2. `global_cooldown()`

Applies a bot-wide cooldown where all commands with this cooldown share a single bucket. If a user is rate-limited from one command using the global cooldown, they will be blocked from all others sharing it. This is useful for preventing spam across all commands simultaneously.

* **Configuration:** Set `global_cooldown_rate` and `global_cooldown_per` when initialising your `Bot` class to edit the default parameters.
* **Usage:** `@preconditions.global_cooldown()`


---

### **Error Handling**

The framework automatically handles failed preconditions within `bot.py`. Users will receive an ephemeral message explaining why the command failed.

* **`MissingBeaconPermissions`**: Returns a formatted list of the specific permissions the user is missing.
* **`RateLimited`**: Tells the user exactly how many seconds they must wait before trying again.
* **`PreconditionFailed`**: Returns a custom string, such as "This command can only be used in a server."
* **`NotBotOwner`**: Custom error triggered when a non-owner attempts to execute an owner-only command.



---

### **Usage**

```python
from discord import app_commands
from beacon import preconditions

@app_commands.command(name="ban", description="Ban a member")
@preconditions.permissions_preset("moderator")
@preconditions.cooldown(rate=1, per=10)
async def ban(interaction: discord.Interaction, member: discord.Member):
    await member.ban()
    await interaction.response.send_message(f"Banned {member.display_name}")

```