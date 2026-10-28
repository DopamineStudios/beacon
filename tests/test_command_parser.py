"""Unit tests for the dynamic command link parser and mention resolver.

Tests parsing of command tags and resolution of command mentions with mock bot trees.
"""

import pytest
import discord
from discord.ext import commands
import asyncio
from beacon.utils.command_parser import resolve_command_mention, parse_command_links


def test_resolve_command_mention_success() -> None:
    """Test resolving a command mention successfully when present in cache.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {
            "global": {
                "ping": 123456789012345678,
                "beacon diagnostics": 987654321098765432
            }
        }

        mention = await resolve_command_mention(bot, "ping")
        assert mention == "</ping:123456789012345678>"

        sub_mention = await resolve_command_mention(bot, "beacon diagnostics")
        assert sub_mention == "</beacon diagnostics:987654321098765432>"

    asyncio.run(_run())


def test_parse_command_links() -> None:
    """Test parsing multiple command links in text.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {
            "global": {
                "ping": 111111111111111111,
                "beacon diagnostics": 222222222222222222
            }
        }

        text = "Use </ping> or check </beacon diagnostics> for details."
        result = await parse_command_links(bot, text)
        assert result == "Use </ping:111111111111111111> or check </beacon diagnostics:222222222222222222> for details."

    asyncio.run(_run())
