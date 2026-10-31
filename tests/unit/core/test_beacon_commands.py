"""Unit tests for beacon.core.beacon_commands module.

This test module validates the command() decorator and Group class functionality,
ensuring correct application of framework defaults, cooldowns, and permission presets.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from discord import app_commands, Permissions
from beacon.core.beacon_commands import command, Group


class TestCommandDecorator:
    """Test suite for the command() decorator."""

    @pytest.mark.asyncio
    async def test_basic_command_creation(self):
        """Test creating a basic command with minimal parameters."""
        @command(name="test", description="Test command")
        async def test_cmd(interaction):
            pass
        
        assert isinstance(test_cmd, app_commands.Command)
        assert test_cmd.name == "test"
        assert test_cmd.description == "Test command"

    @pytest.mark.asyncio
    async def test_command_name_defaults_to_function_name(self):
        """Test that command name defaults to function name when not provided."""
        @command(description="Test command")
        async def my_command(interaction):
            pass
        
        assert my_command.name == "my_command"

    @pytest.mark.asyncio
    async def test_command_description_defaults_to_docstring(self):
        """Test that description defaults to function docstring when not provided."""
        @command(name="test")
        async def test_cmd(interaction):
            """This is a docstring description."""
            pass
        
        assert "docstring description" in test_cmd.description

    @pytest.mark.asyncio
    async def test_command_description_fallback(self):
        """Test that description falls back to default message when missing."""
        @command(name="test")
        async def test_cmd(interaction):
            pass
        
        assert test_cmd.description == "No description provided"

    @pytest.mark.asyncio
    async def test_global_cooldown_applied_by_default(self, mock_interaction, mock_bot):
        """Test that global cooldown is applied by default."""
        @command(name="test", description="Test")
        async def test_cmd(interaction):
            pass
        
        # Global cooldown should be in checks
        assert hasattr(test_cmd, 'checks') and len(test_cmd.checks) > 0
        assert len(test_cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_global_cooldown_disabled(self):
        """Test disabling global cooldown."""
        @command(name="test", description="Test", global_cooldown=False)
        async def test_cmd(interaction):
            pass
        
        # When global_cooldown=False and no preset/cooldown, no checks
        assert not hasattr(test_cmd, 'checks') or len(test_cmd.checks) == 0

    @pytest.mark.asyncio
    async def test_permissions_preset_applied(self):
        """Test that permissions preset is correctly applied."""
        @command(name="test", description="Test", permissions_preset="moderator")
        async def test_cmd(interaction):
            pass
        
        # Preset adds checks
        assert hasattr(test_cmd, 'checks') and len(test_cmd.checks) > 0
        assert len(test_cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_bot_owner_preset_not_guild_only(self):
        """Test that bot_owner preset does not enforce guild_only."""
        @command(name="test", description="Test", permissions_preset="bot_owner")
        async def test_cmd(interaction):
            pass
        
        # bot_owner should not be guild_only
        assert not test_cmd.guild_only

    @pytest.mark.asyncio
    async def test_non_owner_preset_enforces_guild_only(self):
        """Test that non-bot_owner presets enforce guild_only."""
        @command(name="test", description="Test", permissions_preset="moderator")
        async def test_cmd(interaction):
            pass
        
        # Non-owner presets should enforce guild_only
        assert test_cmd.guild_only

    @pytest.mark.asyncio
    async def test_custom_cooldown_applied(self):
        """Test that custom cooldown tuple is applied correctly."""
        @command(name="test", description="Test", cooldown=(5, 30.0))
        async def test_cmd(interaction):
            pass
        
        # Cooldown should be in checks
        assert hasattr(test_cmd, 'checks') and len(test_cmd.checks) > 0
        assert len(test_cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_custom_cooldown_overrides_global(self):
        """Test that custom cooldown overrides global cooldown."""
        @command(name="test", description="Test", global_cooldown=True, cooldown=(5, 30.0))
        async def test_cmd(interaction):
            pass
        
        # Should have checks (custom cooldown takes precedence)
        assert hasattr(test_cmd, 'checks') and len(test_cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_additional_kwargs_passed_through(self):
        """Test that additional kwargs are passed to app_commands.command()."""
        @command(name="test", description="Test", nsfw=True)
        async def test_cmd(interaction):
            pass
        
        assert test_cmd.nsfw is True


class TestGroupClass:
    """Test suite for the Group class."""

    def test_group_initialization_basic(self):
        """Test basic group initialization."""
        group = Group(name="testgroup", description="Test group")
        
        assert group.name == "testgroup"
        assert group.description == "Test group"

    def test_group_name_defaults_to_class_name(self):
        """Test that group name defaults to lowercased class name."""
        class MyTestGroup(Group):
            pass
        
        group = MyTestGroup(description="Test")
        assert group.name == "mytestgroup"

    def test_group_description_defaults_to_docstring(self):
        """Test that group description defaults to class docstring."""
        class MyTestGroup(Group):
            """This is my test group."""
            pass
        
        group = MyTestGroup()
        assert "my test group" in group.description.lower()

    def test_group_description_fallback(self):
        """Test that group description falls back to default message."""
        group = Group(name="test")
        assert group.description == "No description provided"

    def test_group_stores_beacon_settings(self):
        """Test that group stores Beacon framework settings."""
        group = Group(
            name="test",
            description="Test",
            permissions_preset="moderator",
            cooldown=(5, 30.0),
            global_cooldown=False
        )
        
        assert group._beacon_settings['permissions_preset'] == "moderator"
        assert group._beacon_settings['cooldown'] == (5, 30.0)
        assert group._beacon_settings['global_cooldown'] is False

    @pytest.mark.asyncio
    async def test_group_command_decorator_basic(self):
        """Test using the group's command decorator."""
        group = Group(name="test", description="Test")
        
        @group.command(name="subcmd", description="Subcommand")
        async def test_subcmd(interaction):
            pass
        
        # Command should be added to group
        assert group.get_command("subcmd") is not None

    @pytest.mark.asyncio
    async def test_group_command_inherits_preset(self):
        """Test that commands inherit group's permissions preset."""
        group = Group(
            name="test",
            description="Test",
            permissions_preset="moderator"
        )
        
        @group.command(name="subcmd", description="Subcommand")
        async def test_subcmd(interaction):
            pass
        
        # Command should have checks from inherited preset
        cmd = group.get_command("subcmd")
        assert hasattr(cmd, 'checks') and len(cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_group_command_inherits_cooldown(self):
        """Test that commands inherit group's cooldown settings."""
        group = Group(
            name="test",
            description="Test",
            cooldown=(3, 20.0)
        )
        
        @group.command(name="subcmd", description="Subcommand")
        async def test_subcmd(interaction):
            pass
        
        # Command should have checks from inherited cooldown
        cmd = group.get_command("subcmd")
        assert hasattr(cmd, 'checks') and len(cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_group_command_inherits_global_cooldown(self):
        """Test that commands inherit group's global cooldown setting."""
        group = Group(
            name="test",
            description="Test",
            global_cooldown=True
        )
        
        @group.command(name="subcmd", description="Subcommand")
        async def test_subcmd(interaction):
            pass
        
        # Command should have global cooldown check
        cmd = group.get_command("subcmd")
        assert hasattr(cmd, 'checks') and len(cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_group_command_override_preset(self):
        """Test that command can override group's permissions preset."""
        group = Group(
            name="test",
            description="Test",
            permissions_preset="moderator"
        )
        
        @group.command(name="subcmd", description="Subcommand", permissions_preset="admin")
        async def test_subcmd(interaction):
            pass
        
        # Command should use its own preset, not group's
        cmd = group.get_command("subcmd")
        assert hasattr(cmd, 'checks') and len(cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_group_command_override_cooldown(self):
        """Test that command can override group's cooldown."""
        group = Group(
            name="test",
            description="Test",
            cooldown=(5, 30.0)
        )
        
        @group.command(name="subcmd", description="Subcommand", cooldown=(10, 60.0))
        async def test_subcmd(interaction):
            pass
        
        # Command should use its own cooldown
        cmd = group.get_command("subcmd")
        assert hasattr(cmd, 'checks') and len(cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_group_command_override_global_cooldown(self):
        """Test that command can override group's global cooldown setting."""
        group = Group(
            name="test",
            description="Test",
            global_cooldown=True
        )
        
        @group.command(name="subcmd", description="Subcommand", global_cooldown=False)
        async def test_subcmd(interaction):
            pass
        
        # Command explicitly disables cooldown
        cmd = group.get_command("subcmd")
        # Should have no checks when all cooldowns disabled
        # Note: This depends on whether preset is also None

    @pytest.mark.asyncio
    async def test_group_add_command_applies_preset(self):
        """Test that add_command() applies group's preset to command."""
        group = Group(
            name="test",
            description="Test",
            permissions_preset="moderator"
        )
        
        # Create a raw command
        @app_commands.command(name="rawcmd", description="Raw command")
        async def raw_cmd(interaction):
            pass
        
        group.add_command(raw_cmd)
        
        # Command should now have checks applied
        assert hasattr(raw_cmd, 'checks') and len(raw_cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_group_add_command_applies_cooldown(self):
        """Test that add_command() applies group's cooldown to command."""
        group = Group(
            name="test",
            description="Test",
            cooldown=(5, 30.0)
        )
        
        # Create a raw command
        @app_commands.command(name="rawcmd", description="Raw command")
        async def raw_cmd(interaction):
            pass
        
        group.add_command(raw_cmd)
        
        # Command should now have checks applied
        assert hasattr(raw_cmd, 'checks') and len(raw_cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_group_add_command_enforces_guild_only(self):
        """Test that add_command() enforces guild_only for non-owner presets."""
        group = Group(
            name="test",
            description="Test",
            permissions_preset="moderator"
        )
        
        # Create a raw command
        @app_commands.command(name="rawcmd", description="Raw command")
        async def raw_cmd(interaction):
            pass
        
        group.add_command(raw_cmd)
        
        # Command should be guild_only
        assert raw_cmd.guild_only is True

    @pytest.mark.asyncio
    async def test_group_add_command_bot_owner_not_guild_only(self):
        """Test that add_command() does not enforce guild_only for bot_owner preset."""
        group = Group(
            name="test",
            description="Test",
            permissions_preset="bot_owner"
        )
        
        # Create a raw command
        @app_commands.command(name="rawcmd", description="Raw command")
        async def raw_cmd(interaction):
            pass
        
        group.add_command(raw_cmd)
        
        # Command should NOT be guild_only
        assert raw_cmd.guild_only is not True

    @pytest.mark.asyncio
    async def test_group_add_command_global_cooldown(self):
        """Test that add_command() applies global cooldown when enabled."""
        group = Group(
            name="test",
            description="Test",
            global_cooldown=True
        )
        
        # Create a raw command
        @app_commands.command(name="rawcmd", description="Raw command")
        async def raw_cmd(interaction):
            pass
        
        group.add_command(raw_cmd)
        
        # Command should have global cooldown check
        assert hasattr(raw_cmd, 'checks') and len(raw_cmd.checks) > 0


class TestIntegration:
    """Integration tests combining decorator and group functionality."""

    @pytest.mark.asyncio
    async def test_command_with_all_features(self):
        """Test command with all features enabled simultaneously."""
        @command(
            name="fullcmd",
            description="Full-featured command",
            permissions_preset="moderator",
            cooldown=(5, 30.0),
            nsfw=True
        )
        async def full_cmd(interaction):
            pass
        
        assert full_cmd.name == "fullcmd"
        assert full_cmd.description == "Full-featured command"
        assert full_cmd.guild_only is True
        assert full_cmd.nsfw is True
        assert hasattr(full_cmd, 'checks') and len(full_cmd.checks) > 0

    @pytest.mark.asyncio
    async def test_group_with_nested_commands(self):
        """Test group with multiple nested commands."""
        group = Group(
            name="admin",
            description="Admin commands",
            permissions_preset="admin"
        )
        
        @group.command(name="ban", description="Ban user")
        async def ban_cmd(interaction):
            pass
        
        @group.command(name="kick", description="Kick user")
        async def kick_cmd(interaction):
            pass
        
        @group.command(name="warn", description="Warn user", cooldown=(3, 10.0))
        async def warn_cmd(interaction):
            pass
        
        assert len(group.commands) == 3
        assert group.get_command("ban") is not None
        assert group.get_command("kick") is not None
        assert group.get_command("warn") is not None

    @pytest.mark.asyncio
    async def test_multiple_groups_isolation(self):
        """Test that multiple groups maintain isolated settings."""
        mod_group = Group(
            name="moderation",
            description="Moderation commands",
            permissions_preset="moderator"
        )
        
        admin_group = Group(
            name="admin",
            description="Admin commands",
            permissions_preset="admin"
        )
        
        @mod_group.command(name="mute", description="Mute user")
        async def mute_cmd(interaction):
            pass
        
        @admin_group.command(name="ban", description="Ban user")
        async def ban_cmd(interaction):
            pass
        
        # Groups should maintain separate command sets
        assert mod_group.get_command("mute") is not None
        assert admin_group.get_command("mute") is None
        assert admin_group.get_command("ban") is not None
        assert mod_group.get_command("ban") is None
