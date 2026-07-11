import discord
from discord import app_commands
from discord.ext import commands
from ..core.dashboard import OwnerDashboard
from ..core import beacon_commands

class Pic(commands.Cog):
    """Owner-only utility cog that exposes dashboard-related commands.

    """
    def __init__(self, bot):
        """Store the bot reference used by this cog's commands.

        Args:
            bot: Bot instance that owns this object or callback.
        """
        self.bot = bot

    @beacon_commands.command(name="od", description=".", permissions_preset="bot_owner")
    @app_commands.describe(ephemeral="Set to True so that only you can see the dashboard message.")
    async def zc(self, interaction: discord.Interaction, ephemeral: bool = False):
        """Open the owner dashboard UI when invoked by the bot owner."""
        bot_in_guild = self.bot.get_guild(interaction.guild_id) is not None if interaction.guild_id else False

        if not ephemeral:
            is_external_guild = interaction.guild_id is not None and not bot_in_guild

            try:
                dm_channel = interaction.user.dm_channel or await interaction.user.create_dm()
                is_own_dm = interaction.channel_id == dm_channel.id
            except discord.HTTPException:
                is_own_dm = False

            is_external_dm = interaction.guild_id is None and not is_own_dm
            dashboard_ephemeral = True if (is_external_guild or is_external_dm) else False
        else:
            dashboard_ephemeral = True

        view = OwnerDashboard(self.bot, interaction.user, ephemeral=dashboard_ephemeral,
                              secure_mode=self.bot.secure_mode)
        await interaction.response.send_message(view=view, ephemeral=True if ephemeral else False)


async def setup(bot):
    """Attach the dashboard utility cog to the running bot.

    Args:
        bot: Bot instance that owns this object or callback.

    Returns:
        Any: Result produced by this function.
    """
    await bot.add_cog(Pic(bot))