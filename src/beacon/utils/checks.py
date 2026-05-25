import discord
from discord.ext import commands
from discord import app_commands

# MOD CHECKS (legacy and Next):
def prefix_mod_check():
    """Create a prefix-command check requiring basic moderation permissions.

    Returns:
        Any: Result produced by this function.
    """
    async def predicate(ctx):
        """Allow execution only for members with moderation-level permissions.

        Args:
            ctx: Command invocation context.

        Returns:
            bool: True when the check passes.
        """
        perms = ctx.author.guild_permissions
        if perms.moderate_members or perms.ban_members:
            return True
        raise commands.MissingPermissions(["moderate_members", "ban_members"])
    return commands.check(predicate)


async def mod_check(interaction: discord.Interaction):
    """Validate moderation permissions for slash-command interactions.

    Args:
        interaction: Interaction context received from Discord.

    Returns:
        bool: True when the check passes.
    """
    if not interaction.guild:
        raise app_commands.MissingPermissions(["moderate_members", "ban_members"])

    perms = interaction.user.guild_permissions
    if perms.moderate_members or perms.ban_members:
        return True
    raise app_commands.MissingPermissions(["moderate_members", "ban_members"])