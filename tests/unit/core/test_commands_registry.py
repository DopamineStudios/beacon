"""Unit tests for beacon.core.commands_registry module.

This test module validates the CommandRegistry class functionality including
hash generation, state persistence, smart sync logic, and rate-limit handling.
"""

import pytest
import json
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
from discord import app_commands, HTTPException, AppCommandType
from beacon.core.commands_registry import CommandRegistry


class TestCommandRegistryInitialization:
    """Test suite for CommandRegistry initialization."""

    def test_initialization_basic(self, mock_bot):
        """Test basic CommandRegistry initialization."""
        registry = CommandRegistry(mock_bot)
        
        assert registry.bot is mock_bot
        assert registry.state_path.endswith("sync_state.json")
        assert hasattr(registry, 'sync_lock')

    def test_initialization_creates_sync_lock(self):
        """Test that initialization creates _global_cmd_sync_lock on bot."""
        mock_bot = MagicMock(spec=['instance_id', 'tree', 'user', 'logger'])
        mock_bot.instance_id = "test-instance"
        mock_bot.tree = MagicMock()
        mock_bot.user = MagicMock()
        mock_bot.logger = MagicMock()
        
        # Bot doesn't have lock yet (spec prevents auto-creation)
        assert not hasattr(mock_bot, '_global_cmd_sync_lock')
        
        registry = CommandRegistry(mock_bot)
        
        # Lock should be created
        assert hasattr(mock_bot, '_global_cmd_sync_lock')
        assert isinstance(mock_bot._global_cmd_sync_lock, asyncio.Lock)

    def test_initialization_reuses_existing_lock(self):
        """Test that initialization reuses existing _global_cmd_sync_lock."""
        mock_bot = MagicMock()
        mock_bot.instance_id = "test-instance"
        existing_lock = asyncio.Lock()
        mock_bot._global_cmd_sync_lock = existing_lock
        
        registry = CommandRegistry(mock_bot)
        
        # Should reuse the same lock
        assert registry.sync_lock is existing_lock

    def test_state_path_location(self, mock_bot):
        """Test that state_path is in the correct directory."""
        registry = CommandRegistry(mock_bot)
        
        # State path should be in the core directory
        assert "beacon" in registry.state_path
        assert "core" in registry.state_path
        assert registry.state_path.endswith("sync_state.json")


class TestGetLocalSignature:
    """Test suite for _get_local_signature method."""

    def test_signature_basic_command(self, mock_bot):
        """Test signature generation for a basic command."""
        registry = CommandRegistry(mock_bot)
        
        # Create a mock command
        mock_cmd = MagicMock(spec=app_commands.Command)
        mock_cmd.name = "testcmd"
        mock_cmd.description = "Test command"
        mock_cmd._params = {}
        
        signature = registry._get_local_signature(mock_cmd)
        
        assert signature["name"] == "testcmd"
        assert signature["description"] == "Test command"
        assert signature["type"] == AppCommandType.chat_input.value
        assert signature["options"] == []

    def test_signature_group_with_subcommands(self, mock_bot):
        """Test signature generation for a group with subcommands."""
        registry = CommandRegistry(mock_bot)
        
        # Create mock subcommand
        mock_subcmd = MagicMock(spec=app_commands.Command)
        mock_subcmd.name = "subcmd"
        mock_subcmd.description = "Subcommand"
        mock_subcmd._params = {}
        
        # Create mock group
        mock_group = MagicMock(spec=app_commands.Group)
        mock_group.name = "group"
        mock_group.description = "Group description"
        mock_group.commands = [mock_subcmd]
        
        signature = registry._get_local_signature(mock_group)
        
        assert signature["name"] == "group"
        assert signature["description"] == "Group description"
        assert len(signature["options"]) == 1
        assert signature["options"][0]["name"] == "subcmd"

    def test_signature_with_parameters(self, mock_bot):
        """Test signature generation for command with parameters."""
        registry = CommandRegistry(mock_bot)
        
        # Create mock parameter
        mock_param = MagicMock()
        mock_param.name = "user"
        mock_param.description = "Target user"
        mock_param.type = MagicMock(value=6)  # User type
        mock_param.required = True
        mock_param.choices = None
        
        # Create command with parameter
        mock_cmd = MagicMock(spec=app_commands.Command)
        mock_cmd.name = "testcmd"
        mock_cmd.description = "Test command"
        mock_cmd._params = {"user": mock_param}
        
        signature = registry._get_local_signature(mock_cmd)
        
        assert len(signature["options"]) == 1
        opt = signature["options"][0]
        assert opt["name"] == "user"
        assert opt["description"] == "Target user"
        assert opt["type"] == 6
        assert opt["required"] is True

    def test_signature_with_choices(self, mock_bot):
        """Test signature generation for parameter with choices."""
        registry = CommandRegistry(mock_bot)
        
        # Create mock choices
        choice1 = MagicMock()
        choice1.value = "option1"
        choice2 = MagicMock()
        choice2.value = "option2"
        
        # Create mock parameter with choices
        mock_param = MagicMock()
        mock_param.name = "choice"
        mock_param.description = "Select option"
        mock_param.type = MagicMock(value=3)  # String type
        mock_param.required = True
        mock_param.choices = [choice1, choice2]
        
        mock_cmd = MagicMock(spec=app_commands.Command)
        mock_cmd.name = "testcmd"
        mock_cmd.description = "Test"
        mock_cmd._params = {"choice": mock_param}
        
        signature = registry._get_local_signature(mock_cmd)
        
        opt = signature["options"][0]
        assert "choices" in opt
        assert sorted(opt["choices"]) == ["option1", "option2"]

    def test_signature_options_sorted_by_name(self, mock_bot):
        """Test that options are sorted alphabetically by name."""
        registry = CommandRegistry(mock_bot)
        
        # Create multiple parameters
        param_z = MagicMock()
        param_z.name = "zebra"
        param_z.description = "Last"
        param_z.type = MagicMock(value=3)
        param_z.required = True
        param_z.choices = None
        
        param_a = MagicMock()
        param_a.name = "alpha"
        param_a.description = "First"
        param_a.type = MagicMock(value=3)
        param_a.required = True
        param_a.choices = None
        
        mock_cmd = MagicMock(spec=app_commands.Command)
        mock_cmd.name = "testcmd"
        mock_cmd.description = "Test"
        mock_cmd._params = {"zebra": param_z, "alpha": param_a}
        
        signature = registry._get_local_signature(mock_cmd)
        
        # Options should be sorted alphabetically
        assert signature["options"][0]["name"] == "alpha"
        assert signature["options"][1]["name"] == "zebra"


class TestGenerateTreeHash:
    """Test suite for _generate_tree_hash method."""

    def test_hash_generation_empty_tree(self, mock_bot):
        """Test hash generation with no commands."""
        registry = CommandRegistry(mock_bot)
        mock_bot.tree.get_commands.return_value = []
        
        hash1 = registry._generate_tree_hash()
        hash2 = registry._generate_tree_hash()
        
        # Hash should be consistent
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex chars

    def test_hash_generation_with_commands(self, mock_bot):
        """Test hash generation with commands."""
        registry = CommandRegistry(mock_bot)
        
        mock_cmd = MagicMock(spec=app_commands.Command)
        mock_cmd.name = "testcmd"
        mock_cmd.description = "Test"
        mock_cmd._params = {}
        
        mock_bot.tree.get_commands.return_value = [mock_cmd]
        
        hash_result = registry._generate_tree_hash()
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

    def test_hash_changes_when_command_changes(self, mock_bot):
        """Test that hash changes when command details change."""
        registry = CommandRegistry(mock_bot)
        
        mock_cmd1 = MagicMock(spec=app_commands.Command)
        mock_cmd1.name = "testcmd"
        mock_cmd1.description = "Test"
        mock_cmd1._params = {}
        
        mock_bot.tree.get_commands.return_value = [mock_cmd1]
        hash1 = registry._generate_tree_hash()
        
        # Change command description
        mock_cmd1.description = "Different description"
        hash2 = registry._generate_tree_hash()
        
        assert hash1 != hash2

    def test_hash_guild_vs_global(self, mock_bot, mock_guild):
        """Test that guild and global scopes produce different hashes."""
        registry = CommandRegistry(mock_bot)
        
        mock_cmd = MagicMock(spec=app_commands.Command)
        mock_cmd.name = "testcmd"
        mock_cmd.description = "Test"
        mock_cmd._params = {}
        
        # Different commands for different scopes
        def get_commands_side_effect(guild=None):
            if guild:
                return [mock_cmd]
            return []
        
        mock_bot.tree.get_commands.side_effect = get_commands_side_effect
        
        global_hash = registry._generate_tree_hash()
        guild_hash = registry._generate_tree_hash(mock_guild)
        
        # Hashes should differ due to different command sets
        assert global_hash != guild_hash


class TestStateManagement:
    """Test suite for state persistence (_get_stored_state, _save_state)."""

    def test_get_stored_state_no_file(self, mock_bot, tmp_path):
        """Test getting stored state when file doesn't exist."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "nonexistent.json")
        
        result = registry._get_stored_state("global")
        
        assert result is None

    def test_get_stored_state_valid(self, mock_bot, tmp_path):
        """Test getting stored state from valid file."""
        registry = CommandRegistry(mock_bot)
        state_file = tmp_path / "sync_state.json"
        registry.state_path = str(state_file)
        
        # Create state file
        state_data = {
            "global": {
                "hash": "abc123",
                "bot_id": 123456
            }
        }
        state_file.write_text(json.dumps(state_data))
        
        result = registry._get_stored_state("global")
        
        assert result is not None
        assert result["hash"] == "abc123"
        assert result["bot_id"] == 123456

    def test_get_stored_state_invalid_json(self, mock_bot, tmp_path):
        """Test getting stored state from corrupted file."""
        registry = CommandRegistry(mock_bot)
        state_file = tmp_path / "sync_state.json"
        registry.state_path = str(state_file)
        
        # Create invalid JSON file
        state_file.write_text("{ invalid json")
        
        result = registry._get_stored_state("global")
        
        # Should return None on error
        assert result is None

    def test_save_state_new_file(self, mock_bot, tmp_path):
        """Test saving state creates new file."""
        registry = CommandRegistry(mock_bot)
        state_file = tmp_path / "sync_state.json"
        registry.state_path = str(state_file)
        
        mock_bot.user = MagicMock()
        mock_bot.user.id = 987654
        
        registry._save_state("global", "newhash123")
        
        # File should exist
        assert state_file.exists()
        
        # Verify content
        data = json.loads(state_file.read_text())
        assert "global" in data
        assert data["global"]["hash"] == "newhash123"
        assert data["global"]["bot_id"] == 987654

    def test_save_state_updates_existing(self, mock_bot, tmp_path):
        """Test saving state updates existing file."""
        registry = CommandRegistry(mock_bot)
        state_file = tmp_path / "sync_state.json"
        registry.state_path = str(state_file)
        
        # Create initial state
        initial_data = {
            "guild_123": {
                "hash": "oldhash",
                "bot_id": 111
            }
        }
        state_file.write_text(json.dumps(initial_data))
        
        mock_bot.user = MagicMock()
        mock_bot.user.id = 222
        
        registry._save_state("global", "newhash")
        
        # Verify both entries exist
        data = json.loads(state_file.read_text())
        assert "guild_123" in data
        assert "global" in data
        assert data["global"]["hash"] == "newhash"
        assert data["global"]["bot_id"] == 222


class TestSmartSync:
    """Test suite for smart_sync method."""

    @pytest.mark.asyncio
    async def test_smart_sync_already_in_progress(self, mock_bot):
        """Test smart_sync returns early if sync is already in progress."""
        registry = CommandRegistry(mock_bot)
        
        # Acquire the lock to simulate sync in progress
        await registry.sync_lock.acquire()
        
        try:
            result = await registry.smart_sync()
            
            assert "already in progress" in result.lower()
        finally:
            registry.sync_lock.release()

    @pytest.mark.asyncio
    async def test_smart_sync_no_changes(self, mock_bot, tmp_path):
        """Test smart_sync skips sync when no changes detected."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        # Calculate current hash
        current_hash = registry._generate_tree_hash()
        
        # Save matching state
        registry._save_state("global", current_hash)
        
        result = await registry.smart_sync()
        
        # Should skip sync
        assert "up to date" in result.lower()
        assert "skipping" in result.lower()
        mock_bot.tree.sync.assert_not_called()

    @pytest.mark.asyncio
    async def test_smart_sync_detects_changes(self, mock_bot, tmp_path):
        """Test smart_sync performs sync when changes detected."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.tree.sync = AsyncMock()
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        # Save different hash
        registry._save_state("global", "oldhash")
        
        result = await registry.smart_sync()
        
        # Should perform sync
        assert "completed" in result.lower()
        mock_bot.tree.sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_smart_sync_detects_bot_change(self, mock_bot, tmp_path):
        """Test smart_sync performs sync when bot ID changes."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.tree.sync = AsyncMock()
        mock_bot.user = MagicMock()
        mock_bot.user.id = 999999  # Different bot ID
        
        # Save state with same hash but different bot
        current_hash = registry._generate_tree_hash()
        state_data = {
            "global": {
                "hash": current_hash,
                "bot_id": 123456  # Old bot ID
            }
        }
        (tmp_path / "sync_state.json").write_text(json.dumps(state_data))
        
        result = await registry.smart_sync()
        
        # Should perform sync due to bot ID mismatch
        assert "completed" in result.lower()
        mock_bot.tree.sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_smart_sync_guild_scope(self, mock_bot, mock_guild, tmp_path):
        """Test smart_sync with guild scope."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.tree.sync = AsyncMock()
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        result = await registry.smart_sync(mock_guild)
        
        # Should sync with guild parameter
        mock_bot.tree.sync.assert_called_once_with(guild=mock_guild)
        
        # Should save guild-scoped state
        data = json.loads((tmp_path / "sync_state.json").read_text())
        assert f"guild_{mock_guild.id}" in data

    @pytest.mark.asyncio
    async def test_smart_sync_http_429_retry(self, mock_bot, tmp_path):
        """Test smart_sync retries on HTTP 429 rate limit."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        # First call raises 429, second succeeds
        http_error = HTTPException(MagicMock(), MagicMock())
        http_error.status = 429
        mock_bot.tree.sync = AsyncMock(side_effect=[http_error, None])
        
        # Save different hash to trigger sync
        registry._save_state("global", "oldhash")
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await registry.smart_sync()
        
        # Should retry and eventually succeed
        assert mock_bot.tree.sync.call_count == 2
        mock_sleep.assert_called_once()
        assert "completed" in result.lower()

    @pytest.mark.asyncio
    async def test_smart_sync_unretriable_http_error(self, mock_bot, tmp_path):
        """Test smart_sync handles unretriable HTTP errors."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        # Raise 403 Forbidden (unretriable)
        http_error = HTTPException(MagicMock(), MagicMock())
        http_error.status = 403
        mock_bot.tree.sync = AsyncMock(side_effect=http_error)
        
        registry._save_state("global", "oldhash")
        
        result = await registry.smart_sync()
        
        # Should not retry
        assert mock_bot.tree.sync.call_count == 1
        assert "error" in result.lower()
        assert "403" in result

    @pytest.mark.asyncio
    async def test_smart_sync_clears_command_cache(self, mock_bot, tmp_path):
        """Test smart_sync clears command cache after successful sync."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.tree.sync = AsyncMock()
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        # Add command cache attributes
        mock_bot._beacon_command_cache = {"global": "cached_data"}
        mock_bot._beacon_command_fetch_lock = asyncio.Lock()
        
        registry._save_state("global", "oldhash")
        
        await registry.smart_sync()
        
        # Cache should be cleared
        assert "global" not in mock_bot._beacon_command_cache


class TestForceSync:
    """Test suite for force_sync method."""

    @pytest.mark.asyncio
    async def test_force_sync_already_in_progress(self, mock_bot):
        """Test force_sync returns early if sync is already in progress."""
        registry = CommandRegistry(mock_bot)
        
        await registry.sync_lock.acquire()
        
        try:
            result = await registry.force_sync()
            
            assert "already in progress" in result.lower()
        finally:
            registry.sync_lock.release()

    @pytest.mark.asyncio
    async def test_force_sync_success_global(self, mock_bot, tmp_path):
        """Test force_sync performs sync for global scope."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.tree.sync = AsyncMock()
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        result = await registry.force_sync()
        
        assert "synced" in result.lower()
        assert "global" in result.lower()
        mock_bot.tree.sync.assert_called_once_with(guild=None)

    @pytest.mark.asyncio
    async def test_force_sync_success_guild(self, mock_bot, mock_guild, tmp_path):
        """Test force_sync performs sync for guild scope."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.tree.sync = AsyncMock()
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        result = await registry.force_sync(mock_guild)
        
        assert "synced" in result.lower()
        assert mock_guild.name in result or str(mock_guild.id) in result
        mock_bot.tree.sync.assert_called_once_with(guild=mock_guild)

    @pytest.mark.asyncio
    async def test_force_sync_saves_state(self, mock_bot, tmp_path):
        """Test force_sync saves state after successful sync."""
        registry = CommandRegistry(mock_bot)
        state_file = tmp_path / "sync_state.json"
        registry.state_path = str(state_file)
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.tree.sync = AsyncMock()
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        await registry.force_sync()
        
        # State should be saved
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert "global" in data

    @pytest.mark.asyncio
    async def test_force_sync_http_exception(self, mock_bot, tmp_path):
        """Test force_sync handles HTTP exceptions."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        http_error = HTTPException(MagicMock(), MagicMock())
        http_error.status = 429
        mock_bot.tree.sync = AsyncMock(side_effect=http_error)
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        result = await registry.force_sync()
        
        assert "error" in result.lower() or "rate limit" in result.lower()

    @pytest.mark.asyncio
    async def test_force_sync_clears_command_cache(self, mock_bot, tmp_path):
        """Test force_sync clears command cache after successful sync."""
        registry = CommandRegistry(mock_bot)
        registry.state_path = str(tmp_path / "sync_state.json")
        
        mock_bot.tree.get_commands.return_value = []
        mock_bot.tree.sync = AsyncMock()
        mock_bot.user = MagicMock()
        mock_bot.user.id = 123456
        
        # Add command cache
        mock_bot._beacon_command_cache = {"global": "cached_data"}
        mock_bot._beacon_command_fetch_lock = asyncio.Lock()
        
        await registry.force_sync()
        
        # Cache should be cleared
        assert "global" not in mock_bot._beacon_command_cache
