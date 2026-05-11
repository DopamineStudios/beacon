import discord
from discord import app_commands
from discord.ext import commands
from ..core.dashboard import OwnerDashboard
from ...dopamineframework import dopamine_commands

class Pic(commands.Cog):
    """Owner-only utility cog that exposes dashboard-related commands.

    """
    def __init__(self, bot):
        """Store the bot reference used by this cog's commands.

        Args:
            bot: Bot instance that owns this object or callback.
        """
        self.bot = bot

    @dopamine_commands.command(name="od", description=".", permissions_preset="bot_owner")
    @app_commands.describe(ephemeral="Set to True so that only you can see the dashboard message.")
    async def zc(self, interaction: discord.Interaction, ephemeral: bool = False):
        """Open the owner dashboard UI when invoked by the bot owner.

        Args:
            interaction: Interaction context received from Discord.
            ephemeral: Whether the response should only be visible to the command user.

        Returns:
            Any: Result produced by this function.
        """
        view = OwnerDashboard(self.bot, interaction.user)
        await interaction.response.send_message(view=view, ephemeral=True if ephemeral else False)


async def setup(bot):
    """Attach the dashboard utility cog to the running bot.

    Args:
        bot: Bot instance that owns this object or callback.

    Returns:
        Any: Result produced by this function.
    """
    await bot.add_cog(Pic(bot))