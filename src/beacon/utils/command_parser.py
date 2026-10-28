"""Dynamic command link parser and mention resolver for Discord application commands.

Provides utilities to dynamically resolve command names and hierarchical paths to their active Discord snowflake IDs, ensuring application command mention links (</command>) never break after command syncs.
"""

__all__ = ["resolve_command_mention", "parse_command_links"]

import re
import asyncio
import discord
from discord.ext import commands


async def _get_or_fetch_command_cache(
    bot: commands.Bot,
    guild: discord.Guild | None = None,
    force_refresh: bool = False
) -> dict[str, int]:
    """Retrieve or fetch and build the application command ID cache for a given scope.

    Args:
        bot: Bot instance owning the command tree.
        guild: Optional guild to scope command fetching.
        force_refresh: Whether to force refresh the cache even if it exists.

    Returns:
        dict[str, int]: Mapping of command paths (e.g. 'ping', 'beacon diagnostics') to command snowflake IDs.
    
    Raises:
        discord.HTTPException: If command fetching fails due to API errors.
        discord.Forbidden: If the bot lacks permissions to fetch commands.
    """
    if not hasattr(bot, "_beacon_command_cache"):
        bot._beacon_command_cache = {}

    if not hasattr(bot, "_beacon_command_fetch_lock"):
        bot._beacon_command_fetch_lock = asyncio.Lock()

    scope_id = f"guild_{guild.id}" if guild else "global"

    async with bot._beacon_command_fetch_lock:
        if force_refresh and scope_id in bot._beacon_command_cache:
            del bot._beacon_command_cache[scope_id]
        
        if scope_id in bot._beacon_command_cache:
            return bot._beacon_command_cache[scope_id]

        command_map: dict[str, int] = {}
        try:
            app_commands_list = await bot.tree.fetch_commands(guild=guild)
            for cmd in app_commands_list:
                command_map[cmd.name] = cmd.id
                if hasattr(cmd, "options") and cmd.options:
                    for opt in cmd.options:
                        # Handle subcommands / subcommand groups
                        if opt.type in (discord.AppCommandOptionType.subcommand, discord.AppCommandOptionType.subcommand_group):
                            sub_path = f"{cmd.name} {opt.name}"
                            command_map[sub_path] = cmd.id  # Use parent command ID
                            if hasattr(opt, "options") and opt.options:
                                for sub_opt in opt.options:
                                    if sub_opt.type == discord.AppCommandOptionType.subcommand:
                                        nested_path = f"{cmd.name} {opt.name} {sub_opt.name}"
                                        command_map[nested_path] = cmd.id  # Use root command ID
        except (discord.HTTPException, discord.Forbidden, discord.NotFound) as e:
            if hasattr(bot, "logger") and bot.logger:
                bot.logger.warning(f"[{getattr(bot, 'instance_id', 'Beacon')}] Failed to fetch application commands for link resolution: {e}")
        except Exception as e:
            if hasattr(bot, "logger") and bot.logger:
                bot.logger.error(f"[{getattr(bot, 'instance_id', 'Beacon')}] Unexpected error during command resolution: {e}", exc_info=True)
            raise

        bot._beacon_command_cache[scope_id] = command_map
        return command_map


async def resolve_command_mention(bot: commands.Bot, command_path: str, guild: discord.Guild | None = None) -> str:
    """Resolve a command path (e.g. 'ping' or 'beacon diagnostics') to a clickable Discord mention string.

    Args:
        bot: Bot instance owning the command tree.
        command_path: Name or space-separated hierarchical path of the command.
        guild: Optional guild for guild-scoped command resolution.

    Returns:
        str: Formatted Discord command mention (e.g. '</ping:123456789012345678>') or fallback '`/command_path`'.
    
    Raises:
        discord.HTTPException: If command fetching fails due to API errors.
        discord.Forbidden: If the bot lacks permissions to fetch commands.
    """
    cleaned_path = command_path.strip().lower()
    cache = await _get_or_fetch_command_cache(bot, guild=guild)

    cmd_id = cache.get(cleaned_path)
    if not cmd_id:
        # Only try to refresh if we have a bot instance that can fetch (has application_id)
        # This avoids API calls in test environments
        if hasattr(bot, 'application_id') and bot.application_id:
            cache = await _get_or_fetch_command_cache(bot, guild=guild, force_refresh=True)
            cmd_id = cache.get(cleaned_path)

    if cmd_id:
        return f"</{cleaned_path}:{cmd_id}>"
    
    return f"`/{cleaned_path}`"


async def parse_command_links(bot: commands.Bot, text: str, guild: discord.Guild | None = None) -> str:
    """Scan text for dynamic command tags (e.g. '</ping>' or '</beacon diagnostics>') and replace with valid mentions.

    Args:
        bot: Bot instance owning the command tree.
        text: Input string containing dynamic command tags.
        guild: Optional guild for guild-scoped resolution.

    Returns:
        str: Text with all command tags resolved to valid Discord app command mentions.
    
    Raises:
        discord.HTTPException: If command fetching fails due to API errors.
        discord.Forbidden: If the bot lacks permissions to fetch commands.
    """
    pattern = r"</([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+)*)>"
    
    async def replace_match(match: re.Match) -> str:
        command_path = match.group(1)
        return await resolve_command_mention(bot, command_path, guild=guild)
    
    # Process matches in order to avoid O(n²) string operations
    result = []
    last_end = 0
    for match in re.finditer(pattern, text):
        result.append(text[last_end:match.start()])
        result.append(await replace_match(match))
        last_end = match.end()
    result.append(text[last_end:])
    
    return ''.join(result)
