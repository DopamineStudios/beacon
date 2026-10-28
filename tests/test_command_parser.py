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


def test_resolve_command_mention_not_found() -> None:
    """Test fallback behavior when command doesn't exist in cache.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {"global": {}}
        bot._beacon_command_fetch_lock = asyncio.Lock()  # Prevent actual fetch attempts

        mention = await resolve_command_mention(bot, "nonexistent")
        assert mention == "`/nonexistent`"

        # Test with hierarchical path
        sub_mention = await resolve_command_mention(bot, "fake command group")
        assert sub_mention == "`/fake command group`"

    asyncio.run(_run())


def test_resolve_command_mention_case_insensitive() -> None:
    """Test that command resolution is case-insensitive.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {
            "global": {
                "ping": 123456789012345678
            }
        }

        # Test various cases
        mention1 = await resolve_command_mention(bot, "PING")
        assert mention1 == "</ping:123456789012345678>"

        mention2 = await resolve_command_mention(bot, "PiNg")
        assert mention2 == "</ping:123456789012345678>"

        mention3 = await resolve_command_mention(bot, "  ping  ")  # With whitespace
        assert mention3 == "</ping:123456789012345678>"

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


def test_parse_command_links_mixed_found_not_found() -> None:
    """Test parsing text with both existing and non-existing commands.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {
            "global": {
                "ping": 123456789012345678
            }
        }
        bot._beacon_command_fetch_lock = asyncio.Lock()  # Prevent actual fetch attempts

        text = "Try </ping> or </nonexistent> commands."
        result = await parse_command_links(bot, text)
        assert result == "Try </ping:123456789012345678> or `/nonexistent` commands."

    asyncio.run(_run())


def test_parse_command_links_no_matches() -> None:
    """Test parsing text with no command tags.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {"global": {}}

        text = "This is just plain text without any command tags."
        result = await parse_command_links(bot, text)
        assert result == text  # Should remain unchanged

    asyncio.run(_run())


def test_parse_command_links_empty_string() -> None:
    """Test parsing empty string.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {"global": {}}

        result = await parse_command_links(bot, "")
        assert result == ""

    asyncio.run(_run())


def test_parse_command_links_multiple_spaces_normalized() -> None:
    """Test that command tags with multiple consecutive spaces are normalized during lookup.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {
            "global": {
                "beacon diagnostics": 123456789012345678
            }
        }
        bot._beacon_command_fetch_lock = asyncio.Lock()  # Prevent actual fetch attempts

        # Tags with multiple spaces are matched but normalized during lookup (strips extra spaces)
        # Since "beacon  diagnostics" (2 spaces) doesn't match "beacon diagnostics" (1 space) in cache,
        # it falls back to monospace format
        text = "Try </beacon  diagnostics> command."
        result = await parse_command_links(bot, text)
        assert result == "Try `/beacon  diagnostics` command."

    asyncio.run(_run())


def test_parse_command_links_special_characters_ignored() -> None:
    """Test that command tags with special characters are not matched.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {"global": {}}

        # These should NOT match due to special characters
        text = "Try </ping!> or </command-name> or </test@cmd>."
        result = await parse_command_links(bot, text)
        assert result == text  # Should remain unchanged

    asyncio.run(_run())


def test_parse_command_links_nested_subcommands() -> None:
    """Test parsing deeply nested subcommand paths.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {
            "global": {
                "config": 111111111111111111,
                "config set": 222222222222222222,
                "config set value": 333333333333333333
            }
        }

        text = "Use </config>, </config set>, or </config set value>."
        result = await parse_command_links(bot, text)
        assert result == "Use </config:111111111111111111>, </config set:222222222222222222>, or </config set value:333333333333333333>."

    asyncio.run(_run())


def test_parse_command_links_duplicate_tags() -> None:
    """Test parsing text with duplicate command tags.

    Args:
        None

    Returns:
        None
    """
    async def _run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        bot._beacon_command_cache = {
            "global": {
                "ping": 123456789012345678
            }
        }

        text = "Use </ping> here and </ping> there and </ping> everywhere."
        result = await parse_command_links(bot, text)
        assert result == "Use </ping:123456789012345678> here and </ping:123456789012345678> there and </ping:123456789012345678> everywhere."

    asyncio.run(_run())
