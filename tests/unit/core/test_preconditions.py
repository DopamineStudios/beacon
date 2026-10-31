"""Unit tests for beacon.core.preconditions module.

Tests permission checks, cooldowns, and other precondition decorators.
"""

import pytest
import discord
from discord import app_commands
from discord.ext import commands
from unittest.mock import Mock, AsyncMock, patch
from beacon.core.preconditions import (
    global_cooldown,
    permissions_preset,
    has_permissions,
    is_bot_owner,
    cooldown
)
from beacon.core.errors import (
    MissingBeaconPermissions,
    RateLimited,
    PreconditionFailed,
    NotBotOwner
)


class TestGlobalCooldown:
    """Test suite for global_cooldown precondition."""
    
    @pytest.mark.asyncio
    async def test_no_cooldown_mapping(self, mock_interaction, mock_bot):
        """Test that check passes when bot has no cooldown mapping."""
        mock_interaction.client = mock_bot
        delattr(mock_bot, 'global_cooldown_mapping')
        
        # Create a mock command to apply the decorator to
        @global_cooldown()
        async def mock_command(interaction):
            pass
        
        # The check is the predicate function itself
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_first_use_no_cooldown(self, mock_interaction, mock_bot):
        """Test that first command use passes without cooldown."""
        mock_interaction.client = mock_bot
        
        @global_cooldown()
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cooldown_triggered(self, mock_interaction, mock_bot):
        """Test that cooldown is enforced on rapid reuse."""
        mock_interaction.client = mock_bot
        # Set cooldown mapping to 1 per 60s to trigger immediately on 2nd use
        mock_bot.global_cooldown_mapping = commands.CooldownMapping.from_cooldown(
            1, 60.0, commands.BucketType.user
        )
        
        @global_cooldown()
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        # First call should pass
        await predicate(mock_interaction)
        
        # Immediate second call should trigger rate limit
        with pytest.raises(RateLimited) as exc_info:
            await predicate(mock_interaction)
        
        assert exc_info.value.retry_after > 0


class TestPermissionsPreset:
    """Test suite for permissions_preset precondition."""
    
    @pytest.mark.asyncio
    async def test_bot_owner_preset_authorized(self, mock_interaction, mock_bot):
        """Test bot_owner preset passes for actual bot owner."""
        mock_bot.owner_id = mock_interaction.user.id
        mock_interaction.client = mock_bot
        
        @permissions_preset("bot_owner")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_bot_owner_preset_unauthorized(self, mock_interaction, mock_bot):
        """Test bot_owner preset raises NotBotOwner for non-owners."""
        mock_bot.owner_id = 999999999999999999  # Different ID
        mock_bot.owner_ids = set()
        mock_interaction.client = mock_bot
        
        @permissions_preset("bot_owner")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        with pytest.raises(NotBotOwner):
            await predicate(mock_interaction)
    
    @pytest.mark.asyncio
    async def test_bot_owner_preset_multiple_owners(self, mock_interaction, mock_bot):
        """Test bot_owner preset with multiple owners (owner_ids)."""
        mock_bot.owner_ids = {123456789012345678, 111111111111111111}
        mock_interaction.user.id = 111111111111111111
        mock_interaction.client = mock_bot
        
        @permissions_preset("bot_owner")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_moderator_preset_all_permissions(self, mock_interaction, mock_bot):
        """Test moderator preset passes with all required permissions."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(
            manage_messages=True,
            kick_members=True,
            ban_members=True,
            moderate_members=True
        )
        
        @permissions_preset("moderator")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_moderator_preset_missing_permissions(self, mock_interaction, mock_bot):
        """Test moderator preset fails with missing permissions."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(
            manage_messages=True,
            kick_members=False,  # Missing
            ban_members=True,
            moderate_members=True
        )
        
        @permissions_preset("moderator")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        with pytest.raises(MissingBeaconPermissions) as exc_info:
            await predicate(mock_interaction)
        
        assert "kick_members" in exc_info.value.missing_permissions
    
    @pytest.mark.asyncio
    async def test_admin_preset(self, mock_interaction, mock_bot):
        """Test admin preset requires administrator permission."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(administrator=True)
        
        @permissions_preset("admin")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_giveaways_preset(self, mock_interaction, mock_bot):
        """Test giveaways preset permissions."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(
            manage_guild=True,
            manage_messages=True
        )
        
        @permissions_preset("giveaways")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_automation_preset(self, mock_interaction, mock_bot):
        """Test automation preset permissions."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(
            manage_guild=True,
            manage_messages=True,
            manage_channels=True
        )
        
        @permissions_preset("automation")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_manager_preset(self, mock_interaction, mock_bot):
        """Test manager preset permissions."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(
            manage_guild=True,
            manage_roles=True,
            manage_channels=True
        )
        
        @permissions_preset("manager")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_support_preset(self, mock_interaction, mock_bot):
        """Test support preset permissions."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(
            manage_messages=True,
            read_message_history=True
        )
        
        @permissions_preset("support")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_security_preset(self, mock_interaction, mock_bot):
        """Test security preset permissions."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(
            view_audit_log=True,
            moderate_members=True
        )
        
        @permissions_preset("security")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_community_preset(self, mock_interaction, mock_bot):
        """Test community preset permissions."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(
            manage_expressions=True,
            manage_threads=True,
            create_public_threads=True
        )
        
        @permissions_preset("community")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_technical_preset(self, mock_interaction, mock_bot):
        """Test technical preset permissions."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.permissions = discord.Permissions(
            manage_webhooks=True,
            manage_guild=True
        )
        
        @permissions_preset("technical")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_invalid_preset_name(self, mock_interaction, mock_bot):
        """Test that invalid preset name raises ValueError."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        
        @permissions_preset("invalid_preset")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        with pytest.raises(ValueError) as exc_info:
            await predicate(mock_interaction)
        
        assert "invalid_preset" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_preset_requires_guild(self, mock_interaction, mock_bot):
        """Test that non-bot_owner presets require guild context."""
        mock_bot.instance_id = "test5"
        mock_interaction.client = mock_bot
        mock_interaction.guild = None  # DM context
        
        @permissions_preset("moderator")
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        with pytest.raises(PreconditionFailed) as exc_info:
            await predicate(mock_interaction)
        
        assert "server" in str(exc_info.value).lower()


class TestHasPermissions:
    """Test suite for has_permissions precondition."""
    
    @pytest.mark.asyncio
    async def test_all_permissions_required_success(self, mock_interaction):
        """Test that all specified permissions are required by default."""
        mock_interaction.permissions = discord.Permissions(
            manage_messages=True,
            kick_members=True
        )
        
        @has_permissions(manage_messages=True, kick_members=True)
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_all_permissions_required_failure(self, mock_interaction):
        """Test that missing any permission fails the check."""
        mock_interaction.permissions = discord.Permissions(
            manage_messages=True,
            kick_members=False
        )
        
        @has_permissions(manage_messages=True, kick_members=True)
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        with pytest.raises(MissingBeaconPermissions) as exc_info:
            await predicate(mock_interaction)
        
        assert "kick_members" in exc_info.value.missing_permissions
    
    @pytest.mark.asyncio
    async def test_min_required_subset_success(self, mock_interaction):
        """Test that min_required allows subset of permissions."""
        mock_interaction.permissions = discord.Permissions(
            manage_messages=True,
            kick_members=False,
            ban_members=True
        )
        
        # Require 2 out of 3 permissions
        @has_permissions(
            min_required=2,
            manage_messages=True,
            kick_members=True,
            ban_members=True
        )
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_min_required_subset_failure(self, mock_interaction):
        """Test that min_required fails with insufficient permissions."""
        mock_interaction.permissions = discord.Permissions(
            manage_messages=True,
            kick_members=False,
            ban_members=False
        )
        
        # Require 2 out of 3, but only have 1
        @has_permissions(
            min_required=2,
            manage_messages=True,
            kick_members=True,
            ban_members=True
        )
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        with pytest.raises(MissingBeaconPermissions):
            await predicate(mock_interaction)
    
    def test_min_required_exceeds_total(self):
        """Test that min_required > total permissions raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            has_permissions(min_required=3, manage_messages=True, kick_members=True)
        
        assert "cannot be greater than" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_requires_guild_context(self, mock_interaction):
        """Test that has_permissions requires guild context."""
        mock_interaction.guild = None
        
        @has_permissions(manage_messages=True)
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        with pytest.raises(PreconditionFailed) as exc_info:
            await predicate(mock_interaction)
        
        assert "server" in str(exc_info.value).lower()


class TestIsBotOwner:
    """Test suite for is_bot_owner precondition."""
    
    @pytest.mark.asyncio
    async def test_single_owner_authorized(self, mock_interaction, mock_bot):
        """Test authorized access with single owner_id."""
        mock_bot.owner_id = mock_interaction.user.id
        mock_interaction.client = mock_bot
        
        @is_bot_owner()
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_single_owner_unauthorized(self, mock_interaction, mock_bot):
        """Test unauthorized access with single owner_id."""
        mock_bot.owner_id = 999999999999999999
        mock_bot.owner_ids = set()
        mock_interaction.client = mock_bot
        
        @is_bot_owner()
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        with pytest.raises(NotBotOwner):
            await predicate(mock_interaction)
    
    @pytest.mark.asyncio
    async def test_multiple_owners_authorized(self, mock_interaction, mock_bot):
        """Test authorized access with owner_ids list."""
        mock_bot.owner_ids = {123456789012345678, 111111111111111111}
        mock_interaction.user.id = 111111111111111111
        mock_interaction.client = mock_bot
        
        @is_bot_owner()
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_multiple_owners_unauthorized(self, mock_interaction, mock_bot):
        """Test unauthorized access with owner_ids list."""
        mock_bot.owner_ids = {999999999999999999, 888888888888888888}
        mock_interaction.client = mock_bot
        
        @is_bot_owner()
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        with pytest.raises(NotBotOwner):
            await predicate(mock_interaction)


class TestCooldown:
    """Test suite for cooldown precondition."""
    
    @pytest.mark.asyncio
    async def test_first_use_no_cooldown(self, mock_interaction):
        """Test that first command use passes without cooldown."""
        @cooldown(rate=1, per=60)
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        result = await predicate(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cooldown_triggered(self, mock_interaction):
        """Test that cooldown is enforced on rapid reuse."""
        @cooldown(rate=1, per=60)
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        # First call should pass
        await predicate(mock_interaction)
        
        # Immediate second call should trigger rate limit
        with pytest.raises(RateLimited) as exc_info:
            await predicate(mock_interaction)
        
        assert exc_info.value.retry_after > 0
    
    @pytest.mark.asyncio
    async def test_custom_rate_and_per(self, mock_interaction):
        """Test cooldown with custom rate and per values."""
        @cooldown(rate=5, per=30)
        async def mock_command(interaction):
            pass
        
        predicate = mock_command.__discord_app_commands_checks__[0]
        
        # Should allow 5 uses
        for _ in range(5):
            result = await predicate(mock_interaction)
            assert result is True
        
        # 6th use should trigger cooldown
        with pytest.raises(RateLimited):
            await predicate(mock_interaction)
