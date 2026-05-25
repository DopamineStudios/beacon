# Make classes inherent PrivateView or PrivateLayoutView to prevent accidental use of the view by other users.
import discord

class PrivateView(discord.ui.View):
    """Base view that only accepts interactions from one authorized user.

    """
    def __init__(self, user, *args, **kwargs):
        """Initialize a private interaction view bound to a specific user.

        Args:
            user: User that is allowed to interact with this flow.
            *args: Additional positional arguments forwarded to the parent implementation.
            **kwargs: Additional keyword arguments forwarded to the underlying API.
        """
        super().__init__(*args, **kwargs)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction):
        """Reject interactions from users other than the authorized one.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            bool: True when the check passes.
        """
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This isn't for you!",
                ephemeral=True
            )
            return False
        return True



class PrivateLayoutView(discord.ui.LayoutView):
    """Layout-view variant that enforces single-user interaction ownership.

    """
    def __init__(self, user, *args, **kwargs):
        """Initialize a private layout view bound to a specific user.

        Args:
            user: User that is allowed to interact with this flow.
            *args: Additional positional arguments forwarded to the parent implementation.
            **kwargs: Additional keyword arguments forwarded to the underlying API.
        """
        super().__init__(*args, **kwargs)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction):
        """Reject interactions from users other than the authorized one.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            bool: True when the check passes.
        """
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This isn't for you!",
                ephemeral=True
            )
            return False
        return True