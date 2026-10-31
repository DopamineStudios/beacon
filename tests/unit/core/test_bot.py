"""Unit tests for beacon.bot module.

Tests cover:
- BeaconFrameworkBotMixin initialization and configuration
- Instance ID generation
- Version file parsing with multiple formats
- Extension loading in setup_hook
- Signal handler for graceful shutdown
- Ready event handling and presence management
- Callback execution (on_shard_ready_callback, on_beacon_ready_callback)
"""

import pytest
import asyncio
import os
import time
import signal
import logging
from unittest.mock import MagicMock, AsyncMock, patch, mock_open, call, PropertyMock
from discord.ext import commands
import discord

from beacon.bot import BeaconFrameworkBotMixin, BeaconBot, BeaconAutoShardedBot


class MutableProperty:
    """Descriptor that allows mocking/modifying properties on bot instances."""

    def __init__(self, name, default=None):
        self.name = name
        self.default = default

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(
            self.name,
            self.default() if callable(self.default) else self.default,
        )

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value


@pytest.fixture
def beacon_bot():
    """Create a real BeaconBot instance for testing.
    
    Returns:
        BeaconBot: Real bot instance with mocked discord.py dependencies.
    """
    orig_props = {}
    props = ["user", "tree", "extensions", "cogs", "application", "latency"]
    for p in props:
        orig_props[p] = getattr(BeaconBot, p, None)
        setattr(BeaconBot, p, MutableProperty(f"_{p}", dict if p in ("extensions", "cogs") else None))
    
    intents = discord.Intents.default()
    intents.members = True
    bot = BeaconBot(command_prefix="!", intents=intents)
    
    # Create a mock user
    mock_user = MagicMock(spec=discord.ClientUser)
    mock_user.id = 111111111111111111
    mock_user.name = "TestBot"
    mock_user.display_name = "TestBot"
    bot.user = mock_user
    
    bot.owner_id = None
    bot.owner_ids = set()
    bot.extensions = {}
    bot.cogs = {}
    bot.cog_load_time = 0.05
    
    # Mock tree
    bot.tree = MagicMock(spec=discord.app_commands.CommandTree)
    bot.tree.sync = AsyncMock(return_value=[])
    bot.tree.fetch_commands = AsyncMock(return_value=[])
    bot.tree.get_commands = MagicMock(return_value=[])
    bot.tree.on_error = None
    
    # Mock extension management
    bot.load_extension = AsyncMock()
    bot.unload_extension = AsyncMock()
    bot.reload_extension = AsyncMock()
    
    # Mock application
    bot.application = MagicMock()
    bot.application.id = 111111111111111111
    bot.application.team = None
    bot.application.owner = MagicMock()
    bot.application.owner.id = 123456789012345678
    bot.application_info = AsyncMock(return_value=bot.application)
    
    # Mock presence
    bot.change_presence = AsyncMock()
    
    # Mock user fetch
    bot.get_user = MagicMock(return_value=None)
    bot.fetch_user = AsyncMock()
    
    # Mock close
    bot.close = AsyncMock()
    
    yield bot
    
    for p, orig_val in orig_props.items():
        if orig_val is not None:
            setattr(BeaconBot, p, orig_val)


class TestBeaconFrameworkBotMixin:
    """Test suite for BeaconFrameworkBotMixin class."""

    @pytest.mark.asyncio
    async def test_initialization_defaults(self, beacon_bot):
        """Test that bot initializes with expected default values."""
        bot = beacon_bot
        
        assert bot.cogs_path == "cogs"
        assert bot.default_diagnostics is True
        assert bot.global_cooldown_rate == 10
        assert bot.global_cooldown_per == 60.0
        assert bot.minimal_caching is False
        assert bot.accent_colour == (44, 129, 124)
        assert bot.secure_mode is False
        assert bot.version is None
        assert bot.booted is False
        assert hasattr(bot, 'instance_id')
        assert len(bot.instance_id) == 5

    @pytest.mark.asyncio
    async def test_initialization_custom_values(self):
        """Test that bot accepts and stores custom configuration values."""
        custom_logger = logging.getLogger("test_logger")
        custom_colour = discord.Colour(0xFF0000)
        
        with patch.object(commands.Bot, '__init__', return_value=None):
            bot = BeaconBot(
                intents=discord.Intents.default(),
                cogs_path="custom_cogs",
                default_diagnostics=False,
                global_cooldown_rate=5,
                global_cooldown_per=30.0,
                minimal_caching=True,
                accent_colour=custom_colour,
                bot_logger=custom_logger,
                secure_mode=True
            )
            
            assert bot.cogs_path == "custom_cogs"
            assert bot.default_diagnostics is False
            assert bot.global_cooldown_rate == 5
            assert bot.global_cooldown_per == 30.0
            assert bot.minimal_caching is True
            assert bot.accent_colour == (255, 0, 0)
            assert bot.logger == custom_logger
            assert bot.secure_mode is True

    @pytest.mark.asyncio
    async def test_initialization_creates_cooldown_mapping(self, mock_bot):
        """Test that global cooldown mapping is created with correct configuration."""
        bot = mock_bot
        
        assert hasattr(bot, 'global_cooldown_mapping')
        assert bot.global_cooldown_mapping is not None

    @pytest.mark.asyncio
    async def test_initialization_creates_command_registry(self, beacon_bot):
        """Test that CommandRegistry is instantiated during initialization."""
        bot = beacon_bot
        
        assert hasattr(bot, 'registry')
        assert bot.registry is not None

    def test_generate_instance_id_length(self, beacon_bot):
        """Test that instance ID is exactly 5 characters long."""
        bot = beacon_bot
        instance_id = bot.generate_instance_id()
        
        assert len(instance_id) == 5

    def test_generate_instance_id_uniqueness(self, beacon_bot):
        """Test that multiple calls generate different instance IDs."""
        bot = beacon_bot
        ids = set(bot.generate_instance_id() for _ in range(100))
        
        # With 5 characters from 32-char alphabet, collisions are rare
        assert len(ids) > 90

    def test_generate_instance_id_valid_characters(self, beacon_bot):
        """Test that instance ID only contains valid characters."""
        bot = beacon_bot
        alphabet = "23456789abcdefghjklmnpqrstuvwxyz"
        
        for _ in range(50):
            instance_id = bot.generate_instance_id()
            assert all(c in alphabet for c in instance_id)


class TestVersionFileParsing:
    """Test suite for version file parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_version_file_assignment_format(self, beacon_bot, tmp_path):
        """Test parsing version from assignment format: bot_version="1.0.0"."""
        version_file = tmp_path / "version.txt"
        version_file.write_text('bot_version="1.2.3"')
        
        result = beacon_bot._parse_version_file(str(version_file))
        
        assert result == "v1.2.3"

    @pytest.mark.asyncio
    async def test_parse_version_file_colon_format(self, beacon_bot, tmp_path):
        """Test parsing version from colon format: version: 1.0.0."""
        version_file = tmp_path / "version.txt"
        version_file.write_text("version: 2.5.1")
        
        result = beacon_bot._parse_version_file(str(version_file))
        
        assert result == "v2.5.1"

    @pytest.mark.asyncio
    async def test_parse_version_file_standalone_format(self, beacon_bot, tmp_path):
        """Test parsing standalone version number."""
        version_file = tmp_path / "version.txt"
        version_file.write_text("3.0.0")
        
        result = beacon_bot._parse_version_file(str(version_file))
        
        assert result == "v3.0.0"

    @pytest.mark.asyncio
    async def test_parse_version_file_with_v_prefix(self, beacon_bot, tmp_path):
        """Test that v prefix is preserved when already present."""
        version_file = tmp_path / "version.txt"
        version_file.write_text("v4.2.0")
        
        result = beacon_bot._parse_version_file(str(version_file))
        
        assert result == "v4.2.0"

    @pytest.mark.asyncio
    async def test_parse_version_file_with_quotes(self, beacon_bot, tmp_path):
        """Test parsing version with various quote styles."""
        version_file = tmp_path / "version.txt"
        version_file.write_text('"5.1.2"')
        
        result = beacon_bot._parse_version_file(str(version_file))
        
        assert result == "v5.1.2"

    @pytest.mark.asyncio
    async def test_parse_version_file_empty(self, beacon_bot, tmp_path):
        """Test that empty version file returns None."""
        version_file = tmp_path / "version.txt"
        version_file.write_text("")
        
        result = beacon_bot._parse_version_file(str(version_file))
        
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_version_file_nonexistent(self, beacon_bot):
        """Test that nonexistent version file returns None."""
        result = beacon_bot._parse_version_file("/nonexistent/path/version.txt")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_version_file_with_metadata(self, beacon_bot, tmp_path):
        """Test parsing version with build metadata."""
        version_file = tmp_path / "version.txt"
        version_file.write_text("1.0.0-beta.1")
        
        result = beacon_bot._parse_version_file(str(version_file))
        
        assert result == "v1.0.0-beta.1"

    @pytest.mark.asyncio
    async def test_parse_version_file_multiline(self, beacon_bot, tmp_path):
        """Test that multiline file returns first line as version."""
        version_file = tmp_path / "version.txt"
        version_file.write_text("1.5.0\nExtra content\nMore lines")
        
        result = beacon_bot._parse_version_file(str(version_file))
        
        assert result == "v1.5.0"

    @pytest.mark.asyncio
    async def test_reload_version_file(self, beacon_bot, tmp_path):
        """Test that reload_version_file updates the version attribute."""
        version_file = tmp_path / "version.txt"
        version_file.write_text("1.0.0")
        
        beacon_bot._version_file_path = str(version_file)
        beacon_bot.version = None
        
        result = beacon_bot.reload_version_file()
        
        assert result == "v1.0.0"
        assert beacon_bot.version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_reload_version_file_no_path(self, beacon_bot):
        """Test reload when no version file path is configured."""
        beacon_bot._version_file_path = None
        beacon_bot.version = None
        
        result = beacon_bot.reload_version_file()
        
        assert result is None


class TestSetupHook:
    """Test suite for setup_hook extension loading."""

    @pytest.mark.asyncio
    async def test_setup_hook_loads_cogs_from_directory(self, beacon_bot, temp_cogs_dir):
        """Test that setup_hook loads all Python files from cogs directory."""
        (temp_cogs_dir / "test_cog1.py").write_text("")
        (temp_cogs_dir / "test_cog2.py").write_text("")
        
        beacon_bot.cogs_path = str(temp_cogs_dir)
        beacon_bot.load_extension = AsyncMock()
        beacon_bot.loop = asyncio.get_event_loop()
        
        await beacon_bot.setup_hook()
        
        # Should load test_cog1.py and test_cog2.py
        assert beacon_bot.load_extension.call_count >= 2
        loaded_extensions = [call[0][0] for call in beacon_bot.load_extension.call_args_list]
        assert any("test_cog1" in ext for ext in loaded_extensions)
        assert any("test_cog2" in ext for ext in loaded_extensions)

    @pytest.mark.asyncio
    async def test_setup_hook_skips_dunder_files(self, beacon_bot, tmp_path):
        """Test that setup_hook ignores __init__.py and __pycache__."""
        cogs_dir = tmp_path / "cogs"
        cogs_dir.mkdir()
        (cogs_dir / "__init__.py").write_text("")
        (cogs_dir / "valid_cog.py").write_text("")
        
        beacon_bot.cogs_path = str(cogs_dir)
        beacon_bot.load_extension = AsyncMock()
        beacon_bot.loop = asyncio.get_event_loop()
        
        await beacon_bot.setup_hook()
        
        # Should only load valid_cog, not __init__
        loaded_extensions = [call[0][0] for call in beacon_bot.load_extension.call_args_list]
        assert any("valid_cog" in ext for ext in loaded_extensions)
        assert not any("__init__" in ext for ext in loaded_extensions)

    @pytest.mark.asyncio
    async def test_setup_hook_handles_missing_cogs_directory(self, beacon_bot):
        """Test that setup_hook handles nonexistent cogs directory gracefully."""
        beacon_bot.cogs_path = "/nonexistent/cogs"
        beacon_bot.load_extension = AsyncMock()
        beacon_bot.loop = asyncio.get_event_loop()
        
        # Should not raise exception
        await beacon_bot.setup_hook()
        
        # Should not attempt to load any cogs
        assert beacon_bot.load_extension.call_count == 2  # Only diagnostics and pic

    @pytest.mark.asyncio
    async def test_setup_hook_loads_diagnostics_extension(self, beacon_bot, tmp_path):
        """Test that default diagnostics extension is loaded."""
        beacon_bot.cogs_path = str(tmp_path / "empty_cogs")
        os.makedirs(beacon_bot.cogs_path, exist_ok=True)
        beacon_bot.default_diagnostics = True
        beacon_bot.load_extension = AsyncMock()
        beacon_bot.loop = asyncio.get_event_loop()
        
        await beacon_bot.setup_hook()
        
        loaded_extensions = [call[0][0] for call in beacon_bot.load_extension.call_args_list]
        assert "beacon.ext.diagnostics" in loaded_extensions

    @pytest.mark.asyncio
    async def test_setup_hook_skips_diagnostics_when_disabled(self, beacon_bot, tmp_path):
        """Test that diagnostics extension is not loaded when disabled."""
        beacon_bot.cogs_path = str(tmp_path / "empty_cogs")
        os.makedirs(beacon_bot.cogs_path, exist_ok=True)
        beacon_bot.default_diagnostics = False
        beacon_bot.load_extension = AsyncMock()
        beacon_bot.loop = asyncio.get_event_loop()
        
        await beacon_bot.setup_hook()
        
        loaded_extensions = [call[0][0] for call in beacon_bot.load_extension.call_args_list]
        assert "beacon.ext.diagnostics" not in loaded_extensions

    @pytest.mark.asyncio
    async def test_setup_hook_loads_pic_extension(self, beacon_bot, tmp_path):
        """Test that pic extension is always loaded."""
        beacon_bot.cogs_path = str(tmp_path / "empty_cogs")
        os.makedirs(beacon_bot.cogs_path, exist_ok=True)
        beacon_bot.load_extension = AsyncMock()
        beacon_bot.loop = asyncio.get_event_loop()
        
        await beacon_bot.setup_hook()
        
        loaded_extensions = [call[0][0] for call in beacon_bot.load_extension.call_args_list]
        assert "beacon.ext.pic" in loaded_extensions

    @pytest.mark.asyncio
    async def test_setup_hook_handles_extension_load_failure(self, beacon_bot, temp_cogs_dir):
        """Test that setup_hook continues loading other cogs when one fails."""
        (temp_cogs_dir / "fail_cog.py").write_text("")
        (temp_cogs_dir / "success_cog.py").write_text("")
        
        beacon_bot.cogs_path = str(temp_cogs_dir)
        beacon_bot.load_extension = AsyncMock(side_effect=[
            Exception("Load failed"),  # First cog fails
            None,  # Second cog succeeds
            None,  # diagnostics
            None   # pic
        ])
        beacon_bot.loop = asyncio.get_event_loop()
        
        # Should not raise exception
        await beacon_bot.setup_hook()
        
        # Should attempt to load all cogs despite failure
        assert beacon_bot.load_extension.call_count >= 3

    @pytest.mark.asyncio
    async def test_setup_hook_sets_cog_load_time(self, beacon_bot, temp_cogs_dir):
        """Test that setup_hook tracks extension loading time."""
        beacon_bot.cogs_path = str(temp_cogs_dir)
        beacon_bot.load_extension = AsyncMock()
        beacon_bot.loop = asyncio.get_event_loop()
        
        await beacon_bot.setup_hook()
        
        assert hasattr(beacon_bot, 'cog_load_time')
        assert isinstance(beacon_bot.cog_load_time, float)
        assert beacon_bot.cog_load_time >= 0

    @pytest.mark.asyncio
    async def test_setup_hook_registers_signal_handlers(self, beacon_bot):
        """Test that setup_hook registers SIGINT and SIGTERM handlers."""
        beacon_bot.cogs_path = "/nonexistent"
        beacon_bot.load_extension = AsyncMock()
        beacon_bot.loop = MagicMock()
        beacon_bot.loop.add_signal_handler = MagicMock()
        
        await beacon_bot.setup_hook()
        
        # Should register handlers for SIGINT and SIGTERM
        assert beacon_bot.loop.add_signal_handler.call_count == 2
        calls = beacon_bot.loop.add_signal_handler.call_args_list
        signals = [call[0][0] for call in calls]
        assert signal.SIGINT in signals
        assert signal.SIGTERM in signals

    @pytest.mark.asyncio
    async def test_setup_hook_sets_tree_error_handler(self, beacon_bot):
        """Test that setup_hook sets custom error handler on command tree."""
        beacon_bot.cogs_path = "/nonexistent"
        beacon_bot.load_extension = AsyncMock()
        beacon_bot.loop = asyncio.get_event_loop()
        
        await beacon_bot.setup_hook()
        
        assert beacon_bot.tree.on_error is not None


class TestSignalHandler:
    """Test suite for graceful shutdown signal handler."""

    @pytest.mark.asyncio
    async def test_signal_handler_unloads_extensions(self, beacon_bot):
        """Test that signal handler unloads all loaded extensions."""
        beacon_bot.extensions = {
            "custom.cog1": MagicMock(),
            "custom.cog2": MagicMock(),
            "beacon.ext.diagnostics": MagicMock(),
            "beacon.ext.pic": MagicMock()
        }
        beacon_bot.default_diagnostics = True
        beacon_bot.unload_extension = AsyncMock()
        beacon_bot.close = AsyncMock()
        
        await beacon_bot.signal_handler()
        
        # Should unload all extensions
        assert beacon_bot.unload_extension.call_count == 4

    @pytest.mark.asyncio
    async def test_signal_handler_unloads_diagnostics_first(self, beacon_bot):
        """Test that signal handler unloads diagnostics extension first."""
        beacon_bot.extensions = {
            "custom.cog1": MagicMock(),
            "beacon.ext.diagnostics": MagicMock(),
            "beacon.ext.pic": MagicMock()
        }
        beacon_bot.default_diagnostics = True
        beacon_bot.unload_extension = AsyncMock()
        beacon_bot.close = AsyncMock()
        
        await beacon_bot.signal_handler()
        
        # First call should be diagnostics
        first_call = beacon_bot.unload_extension.call_args_list[0][0][0]
        assert first_call == "beacon.ext.diagnostics"

    @pytest.mark.asyncio
    async def test_signal_handler_skips_diagnostics_when_disabled(self, beacon_bot):
        """Test that signal handler doesn't try to unload diagnostics when disabled."""
        beacon_bot.extensions = {
            "custom.cog1": MagicMock(),
            "beacon.ext.pic": MagicMock()
        }
        beacon_bot.default_diagnostics = False
        beacon_bot.unload_extension = AsyncMock()
        beacon_bot.close = AsyncMock()
        
        await beacon_bot.signal_handler()
        
        loaded_extensions = [call[0][0] for call in beacon_bot.unload_extension.call_args_list]
        assert "beacon.ext.diagnostics" not in loaded_extensions

    @pytest.mark.asyncio
    async def test_signal_handler_handles_unload_failure(self, beacon_bot):
        """Test that signal handler continues when unloading an extension fails."""
        beacon_bot.extensions = {
            "custom.cog1": MagicMock(),
            "custom.cog2": MagicMock(),
            "beacon.ext.diagnostics": MagicMock(),
            "beacon.ext.pic": MagicMock()
        }
        beacon_bot.default_diagnostics = True
        beacon_bot.unload_extension = AsyncMock(side_effect=[
            None,  # diagnostics succeeds
            None,  # pic succeeds
            Exception("Unload failed"),  # cog1 fails
            None   # cog2 succeeds
        ])
        beacon_bot.close = AsyncMock()
        
        # Should not raise exception
        await beacon_bot.signal_handler()
        
        # Should still close the bot
        beacon_bot.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_handler_closes_bot(self, beacon_bot):
        """Test that signal handler calls bot.close()."""
        beacon_bot.extensions = {}
        beacon_bot.unload_extension = AsyncMock()
        beacon_bot.close = AsyncMock()
        
        await beacon_bot.signal_handler()
        
        beacon_bot.close.assert_called_once()


class TestRestartBot:
    """Test suite for bot restart functionality."""

    @pytest.mark.asyncio
    async def test_restart_bot_calls_signal_handler(self, beacon_bot):
        """Test that restart_bot calls signal_handler first."""
        beacon_bot.signal_handler = AsyncMock()
        
        with patch('os.execv'):
            await beacon_bot.restart_bot()
        
        beacon_bot.signal_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_bot_executes_restart(self, beacon_bot):
        """Test that restart_bot calls os.execv to restart process."""
        beacon_bot.signal_handler = AsyncMock()
        
        with patch('os.execv') as mock_execv:
            await beacon_bot.restart_bot()
            
            mock_execv.assert_called_once()


class TestOnShardReady:
    """Test suite for on_shard_ready callback handling."""

    @pytest.mark.asyncio
    async def test_on_shard_ready_no_callback(self, beacon_bot):
        """Test on_shard_ready with no callback configured."""
        beacon_bot.on_shard_ready_callback = None
        
        # Should not raise exception
        await beacon_bot.on_shard_ready(1)

    @pytest.mark.asyncio
    async def test_on_shard_ready_sync_callback(self, beacon_bot):
        """Test on_shard_ready with synchronous callback."""
        callback = MagicMock()
        beacon_bot.on_shard_ready_callback = callback
        
        await beacon_bot.on_shard_ready(5)
        
        callback.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_on_shard_ready_async_callback(self, beacon_bot):
        """Test on_shard_ready with asynchronous callback."""
        callback = AsyncMock()
        beacon_bot.on_shard_ready_callback = callback
        
        await beacon_bot.on_shard_ready(3)
        
        callback.assert_awaited_once_with(3)


class TestOnBeaconReady:
    """Test suite for on_beacon_ready callback handling."""

    @pytest.mark.asyncio
    async def test_on_beacon_ready_no_callback(self, beacon_bot):
        """Test on_beacon_ready with no callback configured."""
        beacon_bot.on_beacon_ready_callback = None
        
        # Should not raise exception
        await beacon_bot.on_beacon_ready()

    @pytest.mark.asyncio
    async def test_on_beacon_ready_sync_callback(self, beacon_bot):
        """Test on_beacon_ready with synchronous callback."""
        callback = MagicMock()
        beacon_bot.on_beacon_ready_callback = callback
        
        await beacon_bot.on_beacon_ready()
        
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_beacon_ready_async_callback(self, beacon_bot):
        """Test on_beacon_ready with asynchronous callback."""
        callback = AsyncMock()
        beacon_bot.on_beacon_ready_callback = callback
        
        await beacon_bot.on_beacon_ready()
        
        callback.assert_awaited_once()


class TestOnReady:
    """Test suite for on_ready event handling."""

    @pytest.mark.asyncio
    async def test_on_ready_calls_smart_sync(self, beacon_bot):
        """Test that on_ready triggers command registry smart sync."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = 123456789012345678
        beacon_bot.application_info = AsyncMock()
        beacon_bot.change_presence = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        
        await beacon_bot.on_ready()
        
        beacon_bot.registry.smart_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_ready_fetches_owner_info_when_none(self, beacon_bot):
        """Test that on_ready fetches owner info when not set."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = None
        
        mock_app_info = MagicMock()
        mock_app_info.team = None
        mock_app_info.owner.id = 999888777666
        beacon_bot.application_info = AsyncMock(return_value=mock_app_info)
        beacon_bot.change_presence = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        
        await beacon_bot.on_ready()
        
        assert beacon_bot.owner_id == 999888777666

    @pytest.mark.asyncio
    async def test_on_ready_sets_activity_and_status(self, beacon_bot):
        """Test that on_ready sets activity and status when configured."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = 123456789012345678
        beacon_bot._activity = discord.Game(name="Test Game")
        beacon_bot._status = discord.Status.dnd
        beacon_bot.change_presence = AsyncMock()
        beacon_bot.application_info = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        
        await beacon_bot.on_ready()
        
        beacon_bot.change_presence.assert_called_once()
        call_kwargs = beacon_bot.change_presence.call_args[1]
        assert call_kwargs['activity'] == beacon_bot._activity
        assert call_kwargs['status'] == beacon_bot._status

    @pytest.mark.asyncio
    async def test_on_ready_sets_only_activity(self, beacon_bot):
        """Test that on_ready sets activity when status is not configured."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = 123456789012345678
        beacon_bot._activity = discord.Game(name="Test Game")
        beacon_bot._status = None
        beacon_bot.change_presence = AsyncMock()
        beacon_bot.application_info = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        
        await beacon_bot.on_ready()
        
        beacon_bot.change_presence.assert_called_once()
        call_kwargs = beacon_bot.change_presence.call_args[1]
        assert call_kwargs['activity'] == beacon_bot._activity
        assert 'status' not in call_kwargs

    @pytest.mark.asyncio
    async def test_on_ready_sets_only_status(self, beacon_bot):
        """Test that on_ready sets status when activity is not configured."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = 123456789012345678
        beacon_bot._activity = None
        beacon_bot._status = discord.Status.idle
        beacon_bot.change_presence = AsyncMock()
        beacon_bot.application_info = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        
        await beacon_bot.on_ready()
        
        beacon_bot.change_presence.assert_called_once()
        call_kwargs = beacon_bot.change_presence.call_args[1]
        assert call_kwargs['status'] == beacon_bot._status
        assert 'activity' not in call_kwargs

    @pytest.mark.asyncio
    async def test_on_ready_handles_presence_error(self, beacon_bot):
        """Test that on_ready handles presence change errors gracefully."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = 123456789012345678
        beacon_bot._activity = discord.Game(name="Test Game")
        beacon_bot._status = discord.Status.online
        beacon_bot.change_presence = AsyncMock(side_effect=Exception("Presence error"))
        beacon_bot.application_info = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        
        # Should not raise exception
        await beacon_bot.on_ready()

    @pytest.mark.asyncio
    async def test_on_ready_calls_on_beacon_ready(self, beacon_bot):
        """Test that on_ready calls on_beacon_ready callback."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = 123456789012345678
        beacon_bot.application_info = AsyncMock()
        beacon_bot.change_presence = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        
        await beacon_bot.on_ready()
        
        beacon_bot.on_beacon_ready.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_ready_sets_booted_flag(self, beacon_bot):
        """Test that on_ready sets booted flag after first run."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = 123456789012345678
        beacon_bot.application_info = AsyncMock()
        beacon_bot.change_presence = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        beacon_bot.booted = False
        
        await beacon_bot.on_ready()
        
        assert beacon_bot.booted is True

    @pytest.mark.asyncio
    async def test_on_ready_sets_start_time(self, beacon_bot):
        """Test that on_ready updates start_time on each call."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = 123456789012345678
        beacon_bot.application_info = AsyncMock()
        beacon_bot.change_presence = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        
        await beacon_bot.on_ready()
        
        assert beacon_bot.start_time is not None
        assert isinstance(beacon_bot.start_time, float)

    @pytest.mark.asyncio
    async def test_on_ready_handles_team_application(self, beacon_bot):
        """Test that on_ready handles team-based application owner correctly."""
        beacon_bot.registry.smart_sync = AsyncMock(return_value="Synced")
        beacon_bot.owner_id = None
        
        mock_member1 = MagicMock(id=111111111111)
        mock_member2 = MagicMock(id=222222222222)
        mock_team = MagicMock()
        mock_team.owner_id = 333333333333
        mock_team.members = [mock_member1, mock_member2]
        
        mock_app_info = MagicMock()
        mock_app_info.team = mock_team
        
        beacon_bot.application_info = AsyncMock(return_value=mock_app_info)
        beacon_bot.application = mock_app_info
        beacon_bot.change_presence = AsyncMock()
        beacon_bot.get_user = MagicMock(return_value=None)
        beacon_bot.fetch_user = AsyncMock(return_value=MagicMock(display_name="Owner"))
        beacon_bot.on_beacon_ready = AsyncMock()
        
        await beacon_bot.on_ready()
        
        # Should set owner_id to team owner
        assert beacon_bot.owner_id == 333333333333


class TestBeaconBotClasses:
    """Test suite for BeaconBot and BeaconAutoShardedBot subclasses."""

    def test_beacon_bot_inherits_from_mixin_and_bot(self):
        """Test that BeaconBot inherits from both mixin and commands.Bot."""
        assert issubclass(BeaconBot, BeaconFrameworkBotMixin)
        assert issubclass(BeaconBot, commands.Bot)

    def test_beacon_autosharded_bot_inherits_from_mixin_and_autoshardedbot(self):
        """Test that BeaconAutoShardedBot inherits from both mixin and commands.AutoShardedBot."""
        assert issubclass(BeaconAutoShardedBot, BeaconFrameworkBotMixin)
        assert issubclass(BeaconAutoShardedBot, commands.AutoShardedBot)


class TestFrameworkWatermark:
    """Test suite for framework watermark constant."""

    def test_framework_watermark_exists(self, beacon_bot):
        """Test that FRAMEWORK_WATERMARK constant is defined."""
        assert hasattr(beacon_bot, 'FRAMEWORK_WATERMARK')

    def test_framework_watermark_format(self, beacon_bot):
        """Test that watermark contains expected content."""
        watermark = beacon_bot.FRAMEWORK_WATERMARK
        
        assert "Beacon Framework" in watermark
        assert "https://beacon.dopaminestudios.in/" in watermark
