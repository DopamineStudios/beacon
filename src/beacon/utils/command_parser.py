"""Dynamic command link parser and mention resolver for Discord application commands.

Provides utilities to dynamically resolve command names and hierarchical paths to their active Discord snowflake IDs, ensuring application command mention links (</command>) never break after command syncs.
"""

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
        except Exception as e:
            if hasattr(bot, "logger") and bot.logger:
                bot.logger.warning(f"[{getattr(bot, 'instance_id', 'Beacon')}] Failed to fetch application commands for link resolution: {e}")

        bot._beacon_command_cache[scope_id] = command_map
        return command_map


async def resolve_command_mention(bot: commands.Bot, command_path: str, guild: discord.Guild | None = None) -> str:
    """Resolve a command path (e.g. 'ping' or 'beacon diagnostics') to a clickable Discord mention string.

    Args:
        bot: Bot instance owning the command tree.
        command_path: Name or space-separated hierarchical path of the command.
        guild: Optional guild for guild-scoped command resolution.

    Returns:
        str: Formatted Discord command mention (e.g. '</ping:123456789012345678>') or fallback '<!-- command_path -->'.
    """
    cleaned_path = command_path.strip().lower()
    cache = await _get_or_fetch_command_cache(bot, guild=guild)

    cmd_id = cache.get(cleaned_path)
    if not cmd_id:
        # Refresh cache once if command is missing (in case of recent syncs)
        cache = await _get_or_fetch_command_cache(bot, guild=guild, force_refresh=True)
        cmd_id = cache.get(cleaned_path)

    if cmd_id:
        return f"</{cleaned_path}:{cmd_id}>"
    
    return f"</{cleaned_path}>"


async def parse_command_links(bot: commands.Bot, text: str, guild: discord.Guild | None = None) -> str:
    """Scan text for dynamic command tags (e.g. '</ping>' or '</beacon diagnostics>') and replace with valid mentions.

    Args:
        bot: Bot instance owning the command tree.
        text: Input string containing dynamic command tags.
        guild: Optional guild for guild-scoped resolution.

    Returns:
        str: Text with all command tags resolved to valid Discord app command mentions.
    """
    pattern = r"</([a-zA-Z0-9_\s]+)>"
    matches = sorted(set(re.findall(pattern, text)), key=len, reverse=True)

    resolved_text = text
    for match in matches:
        full_tag = f"</{match}>"
        mention = await resolve_command_mention(bot, match, guild=guild)
        resolved_text = resolved_text.replace(full_tag, mention)

    return resolved_text
