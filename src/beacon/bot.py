import os
import time
import signal
import asyncio
import logging
import discord
import re
import sys
from discord import app_commands
from discord.ext import commands
from .core.commands_registry import CommandRegistry
from .ext.path import framework_version
import secrets
import inspect
from collections.abc import Callable, Coroutine
from typing import Any
from pathlib import Path

logger = logging.getLogger("discord")


class BeaconFrameworkBotMixin:
    """A mixin providing Beacon Framework features, ensuring compatibility with both
    commands.Bot and commands.AutoShardedBot base implementations.
    """

    def __init__(self, cogs_path: str = "cogs", default_diagnostics: bool = True, default_help_command: commands.HelpCommand | None = None,
                 status: discord.Status | None = None, activity: discord.Activity | None = None, global_cooldown_rate: int = 10,
                 global_cooldown_per: float = 60.0, minimal_caching: bool = False,
                 accent_colour: discord.Colour = discord.Colour(0x2C817C),
                 bot_logger: logging.Logger = logging.getLogger("discord"),
                 version_file: str | None = None,
                 secure_mode: bool = False,
                 on_shard_ready_callback: Callable[[int], Any | Coroutine[Any, Any, Any]] | None = None,
                 *args, **kwargs):
        """Initialise the bot with framework defaults, cooldowns, and extension settings.

        Args:
            cogs_path: Directory that contains extension modules to load.
            default_diagnostics: Whether to load the built-in diagnostics extension at startup.
            default_help_command: Configuration for the default built-in prefix help command. Expects an instance of a class that inherits from commands.HelpCommand to customise the output of the command, or None to disable the default help command. Defaults to None.
            status: Discord presence status to apply when the bot is ready.
            activity: Discord activity to apply when the bot is ready.
            global_cooldown_rate: Default global cooldown rate limit for slash commands.
            global_cooldown_per: Default global cooldown window in seconds.
            minimal_caching: Whether to minimize member caching for lower memory usage.
            accent_colour: The colour to be used for accents (and more) in the `/ping` embed, and the `/latency info` graph.
            bot_logger: The logger for the bot process.
            version_file: Optional path to a file containing the bot's deployment version.
            secure_mode: Optional parameter to enable Beacon's secure mode. Strips down the /ping command to not show host location and not load in geocoder, and Owner Dashboard to only cog reloading and slash command syncing to prevent damage such as if bot owner account is hacked. Cog unloading & uploading, bot shutdown and restart, and the ability to view logs is disabled.
            on_shard_ready_callback: Custom callback that will be executed automatically for each shard when using AutoShardedBot. Useful for purposes such as setting a custom Bot status for each shard like "Running on shard 67 of 69", etc.
            *args: Additional positional arguments forwarded to the parent implementation.
            **kwargs: Additional keyword arguments forwarded to the underlying API.
        """
        self.process_start_time = time.time()
        command_prefix = kwargs.pop("command_prefix", "!")

        cache_flags = (
            discord.MemberCacheFlags(voice=False, joined=False)
            if minimal_caching else discord.MemberCacheFlags.all()
        )
        chunk_at_startup = False if minimal_caching else True
        # pyrefly: ignore [unexpected-keyword]
        super().__init__(
            # pyrefly: ignore [unexpected-keyword]
            command_prefix=command_prefix,
            # pyrefly: ignore [unexpected-keyword]
            help_command=default_help_command,
            # pyrefly: ignore [unexpected-keyword]
            member_cache_flags=cache_flags,
            # pyrefly: ignore [unexpected-keyword]
            chunk_guilds_at_startup=chunk_at_startup,
            # pyrefly: ignore [unexpected-keyword]
            guild_ready_timeout=0 if minimal_caching else 2.0,
            *args, **kwargs
        )
        self.cogs_path = cogs_path
        self.default_diagnostics = default_diagnostics
        self._status = status
        self._activity = activity
        self.global_cooldown_rate = global_cooldown_rate
        self.global_cooldown_per = global_cooldown_per
        self.global_cooldown_mapping = commands.CooldownMapping.from_cooldown(
            self.global_cooldown_rate,
            self.global_cooldown_per,
            # pyrefly: ignore [bad-argument-type]
            commands.BucketType.user
        )
        self.minimal_caching = minimal_caching
        self.accent_colour = accent_colour.to_rgb()
        self.registry = CommandRegistry(self)
        self.logger = bot_logger
        if version_file is not None:
            self.version = self._parse_version_file(version_file)
        self.secure_mode = secure_mode
        self.start_time = None
        self.count = None
        self.cog_load_time = None
        self.booted = False
        self.instance_id = self.generate_instance_id()
        self.on_shard_ready_callback = on_shard_ready_callback

    def generate_instance_id(self):
        alphabet = "23456789abcdefghjklmnpqrstuvwxyz"
        return "".join(secrets.choice(alphabet) for _ in range(5))

    def _parse_version_file(self, path: str) -> str | None:
        """Helper method to dynamically parse the version file and normalise its format."""
        if not path or not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                logger.warning(f"""[{self.instance_id}] Beacon: Your given version file is empty. Bot version will not be shown in /ping command's embed. For the safest method, define it as: bot_version="Your.Bot.Version".""")
                return None

            assignment_match = re.search(r'(?:bot_version|version)\s*[:=]\s*["\']?([^"\']+)["\']?', content,
                                         re.IGNORECASE)
            if assignment_match:
                version_str = assignment_match.group(1).strip()
            else:
                standalone_match = re.search(r'v?\d+(?:\.\d+)+[^\s"\']*', content, re.IGNORECASE)
                if standalone_match:
                    version_str = standalone_match.group(0).strip()
                else:
                    version_str = content.splitlines()[0].strip()

            version_str = version_str.strip("'\" ")

            if version_str and not version_str.lower().startswith('v'):
                version_str = f"v{version_str}"

            return version_str or None

        except Exception as e:
            logger.error(f"""[{self.instance_id}] Beacon: Bot version is not defined in your provided file, or isn't defined properly. Bot version will not be shown in /ping command's embed. For the safest method, define it as: bot_version="Your.Bot.Version".""")
            return None

    async def setup_hook(self):
        """Load configured extensions, wire command error handling, and run smart sync."""
        self.logger.info(f"This is the beginning of the Discord bot instance powered by Beacon Framework, with the Beacon Instance ID: {self.instance_id}.")
        print(f"This is the beginning of the Discord bot instance powered by Beacon Framework, with the Beacon Instance ID: {self.instance_id}.")

        count = 0

        if os.path.exists(self.cogs_path):
            base_module = self.cogs_path.replace(os.path.sep, ".").strip(".")
            start = time.time()
            for filename in os.listdir(self.cogs_path):
                if filename.endswith(".py") and not filename.startswith("__"):
                    extension = f"{base_module}.{filename[:-3]}"
                    try:
                        # pyrefly: ignore [missing-attribute]
                        await self.load_extension(extension)
                        logger.info(f"[{self.instance_id}] Beacon: Loaded {extension} Successfully")
                        count += 1
                    except Exception as e:
                        logger.error(f"[{self.instance_id}] Beacon: Failed to load {extension}: {e}")
            self.cog_load_time = time.time() - start
            self.count = count
        else:
            logger.warning(f"[{self.instance_id}] Beacon: '{self.cogs_path}' directory not found.")
        if self.default_diagnostics:
            # pyrefly: ignore [missing-attribute]
            await self.load_extension("beacon.ext.diagnostics")
        # pyrefly: ignore [missing-attribute]
        await self.load_extension("beacon.ext.pic")
        status = await self.registry.smart_sync()

        for s in (signal.SIGINT, signal.SIGTERM):
            # pyrefly: ignore [missing-attribute]
            self.loop.add_signal_handler(
                s, lambda: asyncio.create_task(self.signal_handler())
            )

        async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            """Handle slash-command errors and convert framework (or any other) exceptions to user responses."""
            if isinstance(error, app_commands.CommandInvokeError):
                # pyrefly: ignore [bad-assignment]
                error = error.original

            from .core.errors import PreconditionFailed
            if isinstance(error, PreconditionFailed):
                if not interaction.response.is_done():
                    # pyrefly: ignore [missing-attribute]
                    await interaction.response.send_message(f"{error.message}", ephemeral=True)
                else:
                    # pyrefly: ignore [missing-attribute]
                    await interaction.followup.send(f"{error.message}", ephemeral=True)
                return

            if isinstance(error, app_commands.CheckFailure):
                if not interaction.response.is_done():
                    await interaction.response.send_message("Beacon: You do not meet the requirements to run this command.",
                                                            ephemeral=True)
                return
            if interaction.command is not None:
                self.logger.error(f"[{self.instance_id}] Beacon: Ignoring exception in command {interaction.command.name}: {error}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(content=f"""An unexpected error occurred :(\nPlease contact the developers or the support team of this Discord bot.\nThis unhandled error was caught by [Beacon Framework](https://beacon.dopaminestudios.in/). If you are a developer, please check the logs where it says: "[{self.instance_id}] Beacon: Ignoring exception in command {interaction.command.name}".""", suppress_embeds=True, ephemeral=True)

        # pyrefly: ignore [missing-attribute]
        self.tree.on_error = on_tree_error

    async def signal_handler(self):
        """Gracefully unload extensions and close the bot process."""
        logger.info("Beacon: Bot shutdown requested...")
        # pyrefly: ignore [missing-attribute]
        extensions = list(self.extensions.keys())
        if self.default_diagnostics:
            # pyrefly: ignore [missing-attribute]
            await self.unload_extension("beacon.ext.diagnostics")
        # pyrefly: ignore [missing-attribute]
        await self.unload_extension("beacon.ext.pic")
        internal_extensions = ("beacon.ext.diagnostics", "beacon.ext.pic")
        for extension in extensions:
            if extension not in internal_extensions:
                try:
                    # pyrefly: ignore [missing-attribute]
                    await self.unload_extension(extension)
                    logger.info(f"[{self.instance_id}] Beacon: Unloaded {extension} successfully")
                except Exception as e:
                    logger.error(f"[{self.instance_id}] Beacon: Error unloading {extension}: {e}")

        print(f"This is the end of the Discord bot instance powered by Beacon Framework, with the Beacon Instance ID: {self.instance_id}. 👋 Goodbye!")
        logger.info(f"This is the end of the Discord bot instance powered by Beacon Framework, with the Beacon Instance ID: {self.instance_id}. 👋 Goodbye!\n")
        # pyrefly: ignore [missing-attribute]
        await self.close()

    async def restart_bot(self):
        """Restart the running bot process after a graceful shutdown."""
        logger.info("Beacon: Restarting bot...")
        await self.signal_handler()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    async def on_shard_ready(self, shard_id: int):
        self.logger.info(f"[{self.instance_id}] Beacon: Shard {shard_id} is ready.")

        if self.on_shard_ready_callback:
            if inspect.iscoroutinefunction(self.on_shard_ready_callback):
                await self.on_shard_ready_callback(shard_id)
            else:
                self.on_shard_ready_callback(shard_id)

    async def on_ready(self):
        """Finalize startup presence and emit readiness diagnostics once connected."""
        if self.owner_id is None:
            # pyrefly: ignore [missing-attribute]
            app_info = await self.application_info()
            if app_info.team:
                self.owner_id = app_info.team.owner_id
            else:
                self.owner_id = app_info.owner.id

        # pyrefly: ignore [missing-attribute]


        if self._activity and self._status:
            try:
                # pyrefly: ignore [missing-attribute]
                await self.change_presence(activity=self._activity, status=self._status)
            except Exception as e:
                logger.error(f"[{self.instance_id}] Beacon: ERROR: Failed to set activity or status: {e}")
        elif self._activity:
            try:
                # pyrefly: ignore [missing-attribute]
                await self.change_presence(activity=self._activity)
            except Exception as e:
                logger.error(f"[{self.instance_id}] Beacon: ERROR: Failed to set activity: {e}")
        elif self._status:
            try:
                # pyrefly: ignore [missing-attribute]
                await self.change_presence(status=self._status)
            except Exception as e:
                logger.error(f"[{self.instance_id}] Beacon: ERROR: Failed to set status: {e}")
        owner_user_name = None
        # pyrefly: ignore [missing-attribute]
        if not self.owner_ids and self.application and self.application.team:
            # pyrefly: ignore [missing-attribute]
            self.owner_ids = {m.id for m in self.application.team.members}
        if self.owner_ids:
            owner_names = []
            for o_id in self.owner_ids:
                # pyrefly: ignore [missing-attribute]
                user = self.get_user(o_id) or await self.fetch_user(o_id)
                owner_names.append(user.display_name)
            owner_user_name = ", ".join(owner_names)
        elif self.owner_id:
            # pyrefly: ignore [missing-attribute]
            user = self.get_user(self.owner_id) or await self.fetch_user(self.owner_id)
            owner_user_name = user.display_name
        else:
            owner_user_name = "Unknown"

        if not self.booted:
            total_startup_time = time.time() - self.process_start_time
            bot_version_line = f"Bot Version: {self.version}\n" if self.version else ""
            banner = ("\n"
                      f"---------------------------------------------------\n"
                      f"Beacon Instance ID: {self.instance_id}\n"
                      f"{bot_version_line}"
                      f"Powered by Beacon v{framework_version}\n"
                      "\n"
                      f"Total Startup Time: {total_startup_time:.2f}s\n"
                      f"Total Cogs Loading Time: {self.cog_load_time:.2f}s\n"
                      f"Total Cogs Loaded: {self.count}\n"
                      "\n"
                      # pyrefly: ignore [missing-attribute]
                      f"Bot ready: {self.user} (ID: {self.user.id})\n"
                      f"Bot Owner(s) identified: {owner_user_name}\n"
                      f"---------------------------------------------------"
                      "\n")

            print(banner)
            logger.info(banner)
        self.booted = True
        self.start_time = time.time()

class BeaconBot(BeaconFrameworkBotMixin, commands.Bot):
    """Standard framework bot subclass that loads extensions, syncs commands, and manages lifecycle."""
    pass

class BeaconAutoShardedBot(BeaconFrameworkBotMixin, commands.AutoShardedBot):
    """Auto-sharded variant of the framework bot subclass that fetches shard configurations from Discord."""
    pass