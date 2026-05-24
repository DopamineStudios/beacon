import discord
from discord.app_commands import AppCommandError

class PreconditionFailed(AppCommandError):
    """Base app-command error raised when a precondition check fails.

    """
    pass

class MissingDopaminePermissions(PreconditionFailed):
    """Raised when a user is missing one or more required permissions.

    """
    def __init__(self, missing_permissions: list[str]):
        """Build a permission error with a user-friendly missing list.

        Args:
            missing_permissions: Permission names that are required but currently missing.
        """
        self.missing_permissions = missing_permissions
        formatted = [perm.replace('_', ' ').title() for perm in missing_permissions]
        self.message = f"You can't use this command because you don't have the following permissions: **{', '.join(formatted)}**"
        super().__init__(self.message)

class RateLimited(PreconditionFailed):
    """Raised when a command invocation exceeds the configured cooldown.

    """
    def __init__(self, retry_after: float):
        """Build a cooldown error message with retry timing.

        Args:
            retry_after: Seconds until the command can be used again.
        """
        self.retry_after = retry_after
        self.message = f"You are using commands too quickly! Please try again in **{retry_after:.0f}s**."
        super().__init__(self.message)

class NotBotOwner(PreconditionFailed):
    """Raised when a command restricted to the bot owner is used by someone else."""
    def __init__(self):
        self.message = "This command is restricted to the bot owner."
        super().__init__(self.message)