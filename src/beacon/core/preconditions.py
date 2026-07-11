import discord
from discord import app_commands
from discord.ext import commands
from .errors import MissingBeaconPermissions, RateLimited, PreconditionFailed, NotBotOwner

def global_cooldown():
    """Create a global slash-command cooldown check bound to the bot mapping."""
    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client

        if not hasattr(bot, 'global_cooldown_mapping'):
            return True

        class MockMessage:
            def __init__(self, user):
                self.author = user

        bucket = bot.global_cooldown_mapping.get_bucket(MockMessage(interaction.user))
        retry_after = bucket.update_rate_limit()

        if retry_after:
            raise RateLimited(retry_after)

        return True

    return app_commands.check(predicate)


def permissions_preset(preset_name: str):
    """Create a check that enforces one of the framework permission presets."""
    PRESETS = {
        "moderator": {"manage_messages": True, "kick_members": True, "ban_members": True},
        "admin": {"administrator": True},
        "giveaways": {"manage_guild": True, "manage_messages": True},
        "automation": {"manage_guild": True, "manage_messages": True, "manage_channels": True},
        "manager": {"manage_guild": True, "manage_roles": True, "manage_channels": True},
        "support": {"manage_messages": True, "read_message_history": True},
        "security": {"view_audit_log": True, "moderate_members": True},
        "community": {"manage_expressions": True, "manage_threads": True, "create_public_threads": True},
        "technical": {"manage_webhooks": True, "manage_guild": True}
    }

    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client

        if preset_name.lower() == "bot_owner":
            is_owner = (
                interaction.user.id in bot.owner_ids
                if bot.owner_ids else
                interaction.user.id == bot.owner_id
            )
            if not is_owner:
                raise NotBotOwner()
            return True

        perms_to_check = PRESETS.get(preset_name.lower())
        if perms_to_check is None:
            raise ValueError(f"[{bot.instance_id}] Beacon: Permission preset '{preset_name}' not found.")

        if not interaction.guild:
            raise PreconditionFailed("This command can only be used in a server.")

        permissions = interaction.permissions

        missing = [
            perm for perm, required in perms_to_check.items()
            if required and not getattr(permissions, perm)
        ]

        if missing:
            raise MissingBeaconPermissions(missing)

        return True

    def decorator(obj):
        if preset_name.lower() != "bot_owner":
            obj = app_commands.guild_only()(obj)

            perms_to_check = PRESETS.get(preset_name.lower())
            if perms_to_check:
                obj = app_commands.default_permissions(**perms_to_check)(obj)

        return app_commands.check(predicate)(obj)

    return decorator


def has_permissions(min_required: int = None, **perms):
    """Create a check requiring a minimum number of the provided permission values to match.

    Args:
        min_required: The number of permissions out of all permissions that the user must have for the check to pass. Defaults to None which means all the permissions must be present."""
    if min_required is not None and min_required > len(perms):
        raise ValueError(
            f"Beacon: min_required ({min_required}) cannot be greater than the number of permissions provided ({len(perms)})."
        )
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            raise PreconditionFailed("This command can only be used in a server.")

        permissions = interaction.permissions

        matching_count = sum(1 for perm, value in perms.items() if getattr(permissions, perm) == value)

        required_count = min_required if min_required is not None else len(perms)

        if matching_count < required_count:
            missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]
            raise MissingBeaconPermissions(missing)

        return True

    def decorator(obj):
        obj = app_commands.guild_only()(obj)
        if min_required is None:
            obj = app_commands.default_permissions(**perms)(obj)
        return app_commands.check(predicate)(obj)

    return decorator

def is_bot_owner():
    """Create a check that enforces the user must be a bot owner."""
    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client

        is_owner = (
            interaction.user.id in bot.owner_ids
            if bot.owner_ids else
            interaction.user.id == bot.owner_id
        )

        if not is_owner:
            raise NotBotOwner()

        return True

    return app_commands.check(predicate)

def cooldown(rate: int = 10, per: float = 60):
    """Create a per-command user cooldown check."""
    mapping = commands.CooldownMapping.from_cooldown(rate, per, commands.BucketType.user)

    async def predicate(interaction: discord.Interaction) -> bool:
        class MockMessage:
            def __init__(self, user):
                self.author = user

        bucket = mapping.get_bucket(MockMessage(interaction.user))
        retry_after = bucket.update_rate_limit()

        if retry_after:
            raise RateLimited(retry_after)

        return True

    return app_commands.check(predicate)