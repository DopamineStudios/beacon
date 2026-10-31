"""Shared pytest fixtures and configuration for Beacon framework tests.

This module provides reusable test fixtures for mocking Discord.py components,
bot instances, and common test scenarios.
"""

import asyncio
import pytest
import discord
from discord.ext import commands
from unittest.mock import Mock, AsyncMock, MagicMock
import tempfile
import os
from pathlib import Path


@pytest.fixture
def mock_user():
    """Create a mock Discord user.
    
    Returns:
        Mock: Discord user with standard attributes.
    """
    user = Mock(spec=discord.User)
    user.id = 123456789012345678
    user.name = "TestUser"
    user.display_name = "TestUser"
    user.discriminator = "0001"
    user.bot = False
    user.mention = "<@123456789012345678>"
    return user


@pytest.fixture
def mock_member(mock_user):
    """Create a mock Discord member (guild-specific user).
    
    Args:
        mock_user: Base user fixture.
        
    Returns:
        Mock: Discord member with guild-specific attributes.
    """
    member = Mock(spec=discord.Member)
    member.id = mock_user.id
    member.name = mock_user.name
    member.display_name = mock_user.display_name
    member.discriminator = mock_user.discriminator
    member.bot = mock_user.bot
    member.mention = mock_user.mention
    member.guild_permissions = discord.Permissions.all()
    return member


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild.
    
    Returns:
        Mock: Discord guild with standard attributes.
    """
    guild = Mock(spec=discord.Guild)
    guild.id = 987654321098765432
    guild.name = "Test Guild"
    guild.owner_id = 123456789012345678
    return guild


@pytest.fixture
def mock_channel():
    """Create a mock Discord text channel.
    
    Returns:
        Mock: Discord text channel.
    """
    channel = Mock(spec=discord.TextChannel)
    channel.id = 111222333444555666
    channel.name = "test-channel"
    return channel


@pytest.fixture
def mock_message(mock_user, mock_channel):
    """Create a mock Discord message.
    
    Args:
        mock_user: Author of the message.
        mock_channel: Channel containing the message.
        
    Returns:
        Mock: Discord message.
    """
    message = Mock(spec=discord.Message)
    message.id = 999888777666555444
    message.author = mock_user
    message.channel = mock_channel
    message.content = "Test message"
    message.attachments = []
    return message


@pytest.fixture
def mock_interaction(mock_user, mock_guild, mock_channel):
    """Create a mock Discord interaction.
    
    Args:
        mock_user: User triggering the interaction.
        mock_guild: Guild where interaction occurs.
        mock_channel: Channel where interaction occurs.
        
    Returns:
        Mock: Discord interaction with response methods.
    """
    interaction = Mock(spec=discord.Interaction)
    interaction.user = mock_user
    interaction.guild = mock_guild
    interaction.guild_id = mock_guild.id
    interaction.channel = mock_channel
    interaction.channel_id = mock_channel.id
    interaction.permissions = discord.Permissions.all()
    
    # Mock response
    interaction.response = Mock()
    interaction.response.is_done = Mock(return_value=False)
    interaction.response.send_message = AsyncMock()
    interaction.response.edit_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_modal = AsyncMock()
    
    # Mock followup
    interaction.followup = Mock()
    interaction.followup.send = AsyncMock()
    
    # Mock edit_original_response
    interaction.edit_original_response = AsyncMock()
    
    # Mock message
    interaction.message = None
    
    return interaction


@pytest.fixture
def mock_app_command():
    """Create a mock Discord app command.
    
    Returns:
        Mock: Discord app command.
    """
    command = Mock(spec=discord.app_commands.Command)
    command.id = 123456789012345678
    command.name = "test_command"
    command.description = "Test command description"
    command.options = []
    return command


@pytest.fixture
def mock_bot():
    """Create a mock BeaconBot instance.
    
    Returns:
        Mock: Bot instance with standard Beacon attributes.
    """
    bot = Mock(spec=commands.Bot)
    bot.user = Mock(spec=discord.ClientUser)
    bot.user.id = 111111111111111111
    bot.user.name = "TestBot"
    bot.user.display_name = "TestBot"
    
    bot.instance_id = "test5"
    bot.owner_id = 123456789012345678
    bot.owner_ids = {123456789012345678}
    bot.logger = Mock()
    bot.logger.info = Mock()
    bot.logger.warning = Mock()
    bot.logger.error = Mock()
    bot.logger.critical = Mock()
    
    # Bot attributes
    bot.extensions = {}
    bot.cogs = {}
    bot.guilds = []
    bot.latency = 0.05
    bot.is_ready = Mock(return_value=True)
    bot.wait_until_ready = AsyncMock()
    
    # Tree
    bot.tree = Mock(spec=discord.app_commands.CommandTree)
    bot.tree.sync = AsyncMock()
    bot.tree.fetch_commands = AsyncMock(return_value=[])
    bot.tree.get_commands = Mock(return_value=[])
    
    # Extension management
    bot.load_extension = AsyncMock()
    bot.unload_extension = AsyncMock()
    bot.reload_extension = AsyncMock()
    
    # Application info
    bot.application = Mock()
    bot.application.id = 111111111111111111
    bot.application.team = None
    bot.application.owner = Mock()
    bot.application.owner.id = 123456789012345678
    bot.application_info = AsyncMock(return_value=bot.application)
    
    # HTTP
    bot.http = Mock()
    bot.http.request = AsyncMock()
    
    # Get/fetch users
    bot.get_user = Mock(return_value=None)
    bot.fetch_user = AsyncMock()
    
    # Get guild
    bot.get_guild = Mock(return_value=None)
    
    # Beacon-specific attributes
    bot.global_cooldown_mapping = commands.CooldownMapping.from_cooldown(
        10, 60.0, commands.BucketType.user
    )
    bot.accent_colour = (44, 129, 124)
    bot.secure_mode = False
    bot.FRAMEWORK_WATERMARK = "\n-# Powered by [Beacon Framework](<https://beacon.dopaminestudios.in/>)."
    
    # Command cache for link resolution
    bot._beacon_command_cache = {"global": {}}
    bot._beacon_command_fetch_lock = asyncio.Lock()
    
    return bot


@pytest.fixture
def temp_cogs_dir(tmp_path):
    """Create a temporary cogs directory for testing.
    
    Args:
        tmp_path: pytest's temporary directory fixture.
        
    Returns:
        Path: Path to temporary cogs directory.
    """
    cogs_dir = tmp_path / "cogs"
    cogs_dir.mkdir()
    return cogs_dir


@pytest.fixture
def temp_version_file(tmp_path):
    """Create a temporary version file for testing.
    
    Args:
        tmp_path: pytest's temporary directory fixture.
        
    Returns:
        Path: Path to temporary version file.
    """
    version_file = tmp_path / "version.txt"
    version_file.write_text("bot_version = 'v1.2.3'")
    return version_file


@pytest.fixture
def clean_sync_state():
    """Clean up sync state file before and after tests.
    
    Yields:
        None
    """
    # Setup: Remove sync state if it exists
    from beacon.core.commands_registry import CommandRegistry
    state_file = Path(__file__).parent.parent / "src" / "beacon" / "core" / "sync_state.json"
    
    if state_file.exists():
        state_file.unlink()
    
    yield
    
    # Teardown: Clean up again
    if state_file.exists():
        state_file.unlink()


@pytest.fixture
def event_loop():
    """Create an event loop for async tests.
    
    Yields:
        asyncio.AbstractEventLoop: Event loop for test execution.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_permissions_none():
    """Create permissions object with no permissions.
    
    Returns:
        discord.Permissions: Permissions with no flags set.
    """
    return discord.Permissions.none()


@pytest.fixture
def mock_permissions_all():
    """Create permissions object with all permissions.
    
    Returns:
        discord.Permissions: Permissions with all flags set.
    """
    return discord.Permissions.all()


@pytest.fixture
def mock_permissions_moderator():
    """Create permissions for moderator preset.
    
    Returns:
        discord.Permissions: Moderator permissions.
    """
    return discord.Permissions(
        manage_messages=True,
        kick_members=True,
        ban_members=True,
        moderate_members=True
    )
