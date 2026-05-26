import os
import time
import signal
import asyncio
import logging
import discord
import datetime
from discord import app_commands, Status, Activity
from discord.ext import commands
from .utils.log import LoggingManager
from .core.commands_registry import CommandRegistry
from .ext.path import framework_version
import os
import sys

logger = logging.getLogger("discord")


class Bot(commands.Bot):
    """Framework bot subclass that loads extensions, syncs commands, and manages lifecycle.

    """
    def __init__(self, cogs_path: str = "cogs", log_path: str = None, default_diagnostics: bool = True, status: discord.Status = None, activity: discord.Activity = None, global_cooldown_rate: int = 10,
        global_cooldown_per: float = 60.0, minimal_cacheing: bool = False, accent_colour: discord.Colour = discord.Colour(0x2C817C), bot_logger: logging.Logger = logging.getLogger("discord"), *args, **kwargs):
        """Initialize the bot with framework defaults, cooldowns, and extension settings.

        Args:
            cogs_path: Directory that contains extension modules to load.
            log_path: Path to the logging database file. If none is defined, logging backend is disabled.
            default_diagnostics: Whether to load the built-in diagnostics extension at startup.
            status: Discord presence status to apply when the bot is ready.
            activity: Discord activity to apply when the bot is ready.
            global_cooldown_rate: Default global cooldown rate limit for slash commands.
            global_cooldown_per: Default global cooldown window in seconds.
            minimal_cacheing: Whether to minimize member caching for lower memory usage.
            accent_colour: The colour to be used for accents (and more) in the `/ping` embed, and the `/latency info` graph.
            bot_logger: The logger for the bot process.
            *args: Additional positional arguments forwarded to the parent implementation.
            **kwargs: Additional keyword arguments forwarded to the underlying API.
        """
        self.init_start_time = time.time()
        command_prefix = kwargs.pop("command_prefix", "!")

        cache_flags = (
            discord.MemberCacheFlags(voice=False, joined=False)
            if minimal_cacheing else discord.MemberCacheFlags.all()
        )
        chunk_at_startup = False if minimal_cacheing else True

        super().__init__(
            command_prefix=command_prefix,
            help_command=None,
            member_cache_flags=cache_flags,
            chunk_guilds_at_startup=chunk_at_startup,
            guild_ready_timeout=0,
            *args, **kwargs
        )
        self.cogs_path = cogs_path
        self.log_path = log_path
        self.process_start_time = time.time()
        self.default_diagnostics = default_diagnostics
        self._status=status
        self._activity=activity
        self.global_cooldown_rate = global_cooldown_rate
        self.global_cooldown_per = global_cooldown_per
        self.global_cooldown_mapping = commands.CooldownMapping.from_cooldown(
            self.global_cooldown_rate,
            self.global_cooldown_per,
            commands.BucketType.user
        )
        self.minimal_cacheing = minimal_cacheing
        self.accent_colour = accent_colour.to_rgb()
        self.registry = CommandRegistry(self)
        self.logger = bot_logger
        self.start_time = None
        self.count = None
        self.total_setup_time = None

    async def setup_hook(self):
        """Load configured extensions, wire command error handling, and run smart sync.

        Returns:
            Any: Result produced by this function.
        """
        if self.log_path:
            try:
                self.logger = LoggingManager(self.log_path)
            except Exception as e:
                logger.error(f"Beacon: Failed to initialize logging manager: {e}")

        count = 0

        if os.path.exists(self.cogs_path):
            base_module = self.cogs_path.replace(os.path.sep, ".").strip(".")
            print()
            for filename in os.listdir(self.cogs_path):
                if filename.endswith(".py") and not filename.startswith("__"):
                    extension = f"{base_module}.{filename[:-3]}"
                    try:
                        await self.load_extension(extension)
                        print(f"> Beacon: Loaded {extension} Successfully")
                        count += 1
                    except Exception as e:
                        print(f"Beacon: ERROR: Failed to load {extension}: {e}")
            self.count = count
        else:
            print(f"Beacon: WARNING: '{self.cogs_path}' directory not found.")
        if self.default_diagnostics:
            await self.load_extension("beacon.ext.diagnostics")
        await self.load_extension("beacon.ext.pic")
        status = await self.registry.smart_sync()
        print(status)

        for s in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(
                s, lambda: asyncio.create_task(self.signal_handler())
            )

        async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):

            """Handle slash-command errors and convert framework exceptions to user responses.

            Args:
                interaction: Interaction context received from Discord.
                error: Value for error.

            Returns:
                Any: Result produced by this function.
            """
            if isinstance(error, app_commands.CommandInvokeError):
                error = error.original

            from .core.errors import PreconditionFailed
            if isinstance(error, PreconditionFailed):
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"{error.message}", ephemeral=True)
                else:
                    await interaction.followup.send(f"{error.message}", ephemeral=True)
                return

            if isinstance(error, app_commands.CheckFailure):
                if not interaction.response.is_done():
                    await interaction.response.send_message("You do not meet the requirements to run this command.",
                                                            ephemeral=True)
                return

            self.logger.error(f"Ignoring exception in command {interaction.command.name}: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message("⚠An unexpected error occurred.", ephemeral=True)

        self.tree.on_error = on_tree_error

        self.total_setup_time = time.time() - self.init_start_time

    async def signal_handler(self):
        """Gracefully unload extensions and close the bot process.

        Returns:
            Any: Result produced by this function.
        """
        print("\nBeacon: Bot shutdown requested...")
        extensions = list(self.extensions.keys())
        if self.default_diagnostics:
            await self.unload_extension("beacon.ext.diagnostics")
        await self.unload_extension("beacon.ext.pic")
        internal_extensions = ("beacon.ext.diagnostics", "beacon.ext.pic")
        print()
        for extension in extensions:
            if extension not in internal_extensions:
                try:
                    await self.unload_extension(extension)
                    print(f"> Beacon: Unloaded {extension} successfully")
                except Exception as e:
                    print(f"Beacon: Error unloading {extension}: {e}")

        print("👋 Goodbye!")
        await self.close()

    async def restart_bot(self):
        """Restart the running bot process after a graceful shutdown.

        Returns:
            Any: Result produced by this function.
        """
        print()
        print("Beacon: Restarting bot...")
        await self.signal_handler()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    async def on_ready(self):
        """Finalize startup presence and emit readiness diagnostics once connected.

        Returns:
            Any: Result produced by this function.
        """
        start = time.time()
        if self.owner_id is None:
            app_info = await self.application_info()
            if app_info.team:
                self.owner_id = app_info.team.owner_id
            else:
                self.owner_id = app_info.owner.id

        owner_user = self.get_user(self.owner_id) or await self.fetch_user(self.owner_id)
        owner_user_name = owner_user.name


        if self._activity and self._status:
            try:
                await self.change_presence(activity=self._activity, status=self._status)
            except Exception as e:
                logger.critical(f"Beacon: ERROR: Failed to set activity or status: {e}")
        elif self._activity:
            try:
                await self.change_presence(activity=self._activity)
            except Exception as e:
                logger.critical(f"Beacon: ERROR: Failed to set activity: {e}")
        elif self._status:
            try:
                await self.change_presence(status=self._status)
            except Exception as e:
                logger.critical(f"Beacon: ERROR: Failed to set status: {e}")

        total_ready = time.time() - start


        banner = ("\n"
                  f"---------------------------------------------------\n"
                  f"Powered by Beacon v{framework_version}\n"
                  "\n"
                  f"Internal Initialization Time (setup hook + init of Bot class): {self.total_setup_time:.2f}s\n"
                  f"Time taken by on_ready: {total_ready:.2f}s\n"
                  f"Total Cogs Loaded: {self.count}\n"
                  "\n"
                  f"Bot ready: {self.user} (ID: {self.user.id})\n"
                  f"Bot Owner identified: {owner_user_name}\n"
                  f"---------------------------------------------------"
                  "\n")

        print(banner)

        logger.info(banner)

        self.start_time = time.time()