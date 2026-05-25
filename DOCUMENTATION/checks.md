## `checks.py` Documentation

The `checks.py` module provides check for whehter the user running the command has mod permissions for both legacy prefix commands and modern slash commands.

---

### `prefix_mod_check()`

Designed for use with `discord.ext.commands` (prefix commands).


* **Requirements**: The user must have either `moderate_members` or `ban_members` permissions.
* **Raises**: `commands.MissingPermissions` if the user lacks both required permissions.
* **Usage**:

```python
from beacon import prefix_mod_check

@bot.command()
@prefix_mod_check()
async def kick(ctx, member: discord.Member):
    await member.kick()

```

---

### `mod_check(interaction)`

Designed for use with `discord.app_commands` (slash commands).

* **Requirements**:
* The interaction must occur within a guild (fails in DMs).
* The user must have either `moderate_members` or `ban_members` permissions.


* **Raises**: `app_commands.MissingPermissions` if the interaction is in DMs or if the user lacks permissions.
* **Usage**:

```python
from beacon import mod_check

@app_commands.command(name="ban", description="Ban a member")
@app_commands.check(mod_check)
async def ban(interaction: discord.Interaction, member: discord.Member):
    await interaction.guild.ban(member)
    await interaction.response.send_message(f"Banned {member}")

```