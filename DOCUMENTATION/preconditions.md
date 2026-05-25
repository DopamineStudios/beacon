## Preconditions Feature Documentation

<sub>(This documentation is about the decorators meant to be used with slash commands when you use the discord.py `@app_commands.command` decorator instead of Beacon's equivalent. To use preconditions through the `@beacon.command()` decorator, read `beacon.md`.)

The **Preconditions** feature provides set of decorators for `discord.py` slash commands to enforce specific rules. They cover common use cases such as permission checks and rate limiting (cooldowns).

---

## **Permission Checks**

### Presets
#### `permissions_preset(preset_name: str)`
Instead of listing every required permission manually, you can use pre-defined presets tailored for specific roles.

* **Usage:** `@preconditions.permissions_preset("moderator")`

| Preset | Required Permissions |
| :--- | :--- |
| `"bot_owner"` | Restricts usage to the bot owner/team owners. |
| `moderator` | Manage Messages, Kick Members, Ban Members |
| `admin` | Administrator |
| `giveaways` | Manage Guild, Manage Messages |
| `automation` | Manage Guild, Manage Messages, Manage Channels |
| `manager` | Manage Guild, Manage Roles, Manage Channels |
| `support` | Manage Messages, Read Message History |
| `security` | View Audit Log, Moderate Members |
| `community` | Manage Expressions, Manage Threads, Create Public Threads |
| `technical` | Manage Webhooks, Manage Guild |

### Non-Preset Decorators
#### 1. `has_permissions(**perms)`
Ensures the user has **all** of the specified permissions.
* **Usage:** `@preconditions.has_permissions(manage_messages=True, manage_nicknames=True)`

#### 2. `has_permissions_any(**perms)`
Passes if the user has **at least one** of the specified permissions.
* **Usage:** `@preconditions.has_permissions_any(manage_guild=True, administrator=True)`

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
Applies the bot-wide cooldown where all commands with this cooldown share a single "bucket" for the cooldown. If a user is rate limited from one of the commands that use global cooldown, they won't be able to use any other one of the same. This is useful for preventing spam across all commands simultaneously.
* **Configuration:** Set `global_cooldown_rate` and `global_cooldown_per` when initializing your `Bot` class to edit the default parameters.
* **Usage:** `@preconditions.global_cooldown()`

---

### **Error Handling**

The framework automatically handles failed preconditions within `bot.py`. Users will receive an ephemeral message explaining why the command failed.

* **`MissingBeaconPermissions`**: Returns a formatted list of the specific permissions the user is missing (e.g., "Manage Messages").
* **`RateLimited`**: Tells the user exactly how many seconds they must wait before trying again.
* **`PreconditionFailed`**: Returns a custom string, such as "This command can only be used in a server."

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