"""Unit tests for Diagnostics extension and MonitorView component."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import discord
import pytest

from beacon.ext.diagnostics import Diagnostics, MonitorView


class TestMonitorView:
    """Tests for MonitorView component behavior and lifecycle."""

    @pytest.mark.asyncio
    async def test_initialization_without_message_does_not_start_loop(self, mock_bot, mock_user):
        """Test that initializing MonitorView without a message leaves update_monitor dormant.

        Args:
            mock_bot: Mocked Beacon bot instance.
            mock_user: Mocked Discord user instance.
        """
        cog = MagicMock(spec=Diagnostics)
        view = MonitorView(cog, mock_bot, mock_user)

        try:
            assert view.message is None
            assert view.is_active is True
            assert not view.update_monitor.is_running()
        finally:
            await view.stop_monitoring()

    @pytest.mark.asyncio
    async def test_initialization_with_message_starts_loop(self, mock_bot, mock_user, mock_message):
        """Test that initializing MonitorView with a message starts update_monitor.

        Args:
            mock_bot: Mocked Beacon bot instance.
            mock_user: Mocked Discord user instance.
            mock_message: Mocked Discord message instance.
        """
        cog = MagicMock(spec=Diagnostics)
        view = MonitorView(cog, mock_bot, mock_user, message=mock_message)

        try:
            assert view.message is mock_message
            assert view.is_active is True
            assert view.update_monitor.is_running()
        finally:
            await view.stop_monitoring()

    @pytest.mark.asyncio
    async def test_start_and_stop_monitoring(self, mock_bot, mock_user, mock_message):
        """Test starting and stopping the monitor background loop.

        Args:
            mock_bot: Mocked Beacon bot instance.
            mock_user: Mocked Discord user instance.
            mock_message: Mocked Discord message instance.
        """
        cog = MagicMock(spec=Diagnostics)
        view = MonitorView(cog, mock_bot, mock_user)
        view.message = mock_message

        assert not view.update_monitor.is_running()
        view.start_monitoring()
        assert view.update_monitor.is_running()

        await view.stop_monitoring()
        assert not view.update_monitor.is_running()
        assert view.is_active is False

    @pytest.mark.asyncio
    async def test_stop_callback_handles_rgb_tuple_accent_colour(self, mock_bot, mock_user, mock_interaction, mock_message):
        """Test that stop_callback converts RGB tuple accent_colour properly and generates valid components.

        Args:
            mock_bot: Mocked Beacon bot instance.
            mock_user: Mocked Discord user instance.
            mock_interaction: Mocked Discord interaction instance.
            mock_message: Mocked Discord message instance.
        """
        mock_bot.accent_colour = (44, 129, 124)
        mock_interaction.message = mock_message
        cog = MagicMock(spec=Diagnostics)
        cog.api_latency_cache = []
        cog.heartbeat_latency_cache = []
        cog.current_cpu = 0.0
        cog.process = MagicMock()
        cog.process.memory_info.return_value.rss = 100 * 1024 * 1024
        view = MonitorView(cog, mock_bot, mock_user)
        view.build_layout()

        # Verify view can serialize to components without AttributeError
        components = view.to_components()
        assert len(components) == 1
        assert components[0]["type"] == 17  # Container component type
        assert components[0]["accent_color"] == discord.Colour.from_rgb(44, 129, 124).value

        try:
            await view.stop_callback(mock_interaction)

            mock_interaction.response.defer.assert_awaited_once()
            mock_message.delete.assert_awaited_once()
        finally:
            await view.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stop_callback_handles_discord_colour_accent_colour(self, mock_bot, mock_user, mock_interaction, mock_message):
        """Test that stop_callback works when accent_colour is already a discord.Colour.

        Args:
            mock_bot: Mocked Beacon bot instance.
            mock_user: Mocked Discord user instance.
            mock_interaction: Mocked Discord interaction instance.
            mock_message: Mocked Discord message instance.
        """
        mock_bot.accent_colour = discord.Colour(0x2C817C)
        mock_interaction.message = mock_message
        cog = MagicMock(spec=Diagnostics)
        cog.api_latency_cache = []
        cog.heartbeat_latency_cache = []
        cog.current_cpu = 0.0
        cog.process = MagicMock()
        cog.process.memory_info.return_value.rss = 100 * 1024 * 1024
        view = MonitorView(cog, mock_bot, mock_user)
        view.build_layout()

        components = view.to_components()
        assert len(components) == 1
        assert components[0]["type"] == 17
        assert components[0]["accent_color"] == 0x2C817C

        try:
            await view.stop_callback(mock_interaction)

            mock_interaction.response.defer.assert_awaited_once()
            mock_message.delete.assert_awaited_once()
        finally:
            await view.stop_monitoring()

    @pytest.mark.asyncio
    async def test_monitor_view_battery_bypass_charging(self, mock_bot, mock_user, mock_message):
        """Test MonitorView battery status layout with bypass charging and various states.

        Args:
            mock_bot: Mocked Beacon bot instance.
            mock_user: Mocked Discord user instance.
            mock_message: Mocked Discord message instance.
        """
        cog = MagicMock(spec=Diagnostics)
        cog.api_latency_cache = []
        cog.heartbeat_latency_cache = []
        cog.current_cpu = 0.0
        cog.process = MagicMock()
        cog.process.memory_info.return_value.rss = 100 * 1024 * 1024

        view = MonitorView(cog, mock_bot, mock_user, message=mock_message)

        try:
            # Test battery idling / bypass charging
            cog.is_battery_idling = True
            mock_battery = MagicMock()
            mock_battery.percent = 80
            mock_battery.power_plugged = True

            with patch("psutil.sensors_battery", return_value=mock_battery):
                view.build_layout()
                # Verify container built successfully with battery info
                components = view.to_components()
                assert len(components) == 1

            # Test battery normal charging
            cog.is_battery_idling = False
            with patch("psutil.sensors_battery", return_value=mock_battery):
                view.build_layout()

            # Test battery discharging
            mock_battery.power_plugged = False
            with patch("psutil.sensors_battery", return_value=mock_battery):
                view.build_layout()

            # Test no battery
            with patch("psutil.sensors_battery", return_value=None):
                view.build_layout()

            # Test battery exception
            with patch("psutil.sensors_battery", side_effect=Exception("Error")):
                view.build_layout()

        finally:
            await view.stop_monitoring()

    @pytest.mark.asyncio
    async def test_update_monitor_iteration_edits_message(self, mock_bot, mock_user, mock_message):
        """Test that an update_monitor iteration builds layout and edits the message.

        Args:
            mock_bot: Mocked Beacon bot instance.
            mock_user: Mocked Discord user instance.
            mock_message: Mocked Discord message instance.
        """
        cog = MagicMock(spec=Diagnostics)
        cog.api_latency_cache = [40, 50]
        cog.heartbeat_latency_cache = [25, 30]
        cog.current_cpu = 5.0
        cog.process = MagicMock()
        cog.process.memory_info.return_value.rss = 100 * 1024 * 1024

        mock_message.edit = AsyncMock()
        view = MonitorView(cog, mock_bot, mock_user)
        view.message = mock_message

        try:
            await view.update_monitor()
            mock_message.edit.assert_awaited_once_with(view=view)
        finally:
            await view.stop_monitoring()

    @pytest.mark.asyncio
    async def test_update_monitor_cancels_when_inactive(self, mock_bot, mock_user, mock_message):
        """Test that update_monitor loop cancels itself if view is inactive.

        Args:
            mock_bot: Mocked Beacon bot instance.
            mock_user: Mocked Discord user instance.
            mock_message: Mocked Discord message instance.
        """
        cog = MagicMock(spec=Diagnostics)
        view = MonitorView(cog, mock_bot, mock_user)
        view.message = mock_message
        view.is_active = False

        view.update_monitor.cancel = MagicMock()
        await view.update_monitor()
        view.update_monitor.cancel.assert_called_once()


class TestDiagnosticsMonitorCommand:
    """Tests for the /beacon monitor command execution."""

    @pytest.mark.asyncio
    async def test_monitor_command_flow(self, mock_bot, mock_interaction, mock_message):
        """Test that monitor command responds ephemerally, posts view to channel, and starts loop.

        Args:
            mock_bot: Mocked Beacon bot instance.
            mock_interaction: Mocked Discord interaction instance.
            mock_message: Mocked Discord message instance.
        """
        mock_interaction.channel.send = AsyncMock(return_value=mock_message)
        with patch.object(Diagnostics, "__init__", lambda self, bot: None):
            cog = Diagnostics(mock_bot)
            cog.bot = mock_bot
            cog.api_latency_cache = []
            cog.heartbeat_latency_cache = []
            cog.current_cpu = 0.0
            cog.process = MagicMock()
            cog.process.memory_info.return_value.rss = 50 * 1024 * 1024

            await cog.monitor.callback(cog, mock_interaction)

            mock_interaction.response.send_message.assert_awaited_once()
            mock_interaction.channel.send.assert_awaited_once()

            # Retrieve view passed to channel.send
            sent_view = mock_interaction.channel.send.call_args.kwargs["view"]
            assert sent_view.message is mock_message
            assert sent_view.update_monitor.is_running()

            await sent_view.stop_monitoring()
