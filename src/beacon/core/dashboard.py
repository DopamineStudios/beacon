import os
import sys
import discord
import signal
import asyncio
from typing import TYPE_CHECKING

from discord import Message

from ..core.commands_registry import CommandRegistry
import logging
import io
from pathlib import Path

if TYPE_CHECKING:
    from discord.ext import commands
from ..utils import PrivateLayoutView


class OwnerDashboard(PrivateLayoutView):
    """Interactive owner dashboard for extension control and sync operations.

    """
    UPLOAD_MODE_MESSAGE = (
        "Upload mode is now on! Send a module file within the next 60 seconds.\n\n"
        "### How to Upload a Module File\n"
        "* **Step 1:** Attach the file you want to upload into your Discord message through the Discord UI.\n"
        "* **Step 2:** Enter the name of the file to be used in your chosen modules folder. For example, if you want to replace a module called `moderation.py`, type \"moderation.py\" into the text part of your message. If you want to add a brand new file, do the same but with whatever name you want to use.\n"
        "* **Step 3:** Click Enter!"
    )

    def __init__(self, bot: 'commands.Bot', user: discord.User | discord.Member, page: int = 1, ephemeral: bool = False,
                 secure_mode: bool = False):
        """Initialize owner dashboard state and build the first layout.

        Args:
            bot: Bot instance that owns this object or callback.
            user (discord.User | discord.Member): User that is allowed to interact with this flow.
            page: Initial dashboard page index (1-based).
            ephemeral: Whether the dashboard message is only visible to the owner.
        """
        super().__init__(user, timeout=None)
        self.bot = bot
        self.page = page
        self.ephemeral = ephemeral
        self.secure_mode = secure_mode
        self._upload_in_progress = False
        self.items_per_page = 5
        self.registry = CommandRegistry(bot)
        self.build_layout()

    def build_layout(self):
        """Rebuild all dashboard controls based on the current page and cog state.

        Returns:
            Any: Result produced by this function.
        """
        self.clear_items()
        container = discord.ui.Container()

        # pyrefly: ignore [missing-attribute]
        container.add_item(
            # pyrefly: ignore [missing-attribute]
            (discord.ui.TextDisplay(f"## Beacon Owner Dashboard (Beacon Instance ID: `{self.bot.instance_id}`)")))
        container.add_item(discord.ui.Separator())

        cogs_dir = os.path.join(os.getcwd(), "cogs")
        cog_files = []
        if os.path.exists(cogs_dir):
            cog_files = [f for f in os.listdir(cogs_dir) if f.endswith(".py") and not f.startswith("__")]

        cog_files.sort()
        total_items = len(cog_files)
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page if total_items > 0 else 1

        start_idx = (self.page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        current_page_cogs = cog_files[start_idx:end_idx]

        if not current_page_cogs:
            container.add_item(discord.ui.TextDisplay("*No extensions found in cogs folder.*"))
        if self.secure_mode:
            container.add_item(discord.ui.TextDisplay("*Secure mode is enabled, cog unloading is not allowed.*"))
        else:
            for idx, filename in enumerate(current_page_cogs, start_idx + 1):
                ext_name = f"cogs.{filename[:-3]}"
                is_loaded = ext_name in self.bot.extensions

                cog_btn = discord.ui.Button(
                    label="Unload" if is_loaded else "Load",
                    style=discord.ButtonStyle.secondary if is_loaded else discord.ButtonStyle.primary
                )

                cog_btn.callback = self.create_toggle_callback(ext_name, is_loaded)
                container.add_item(
                    discord.ui.Section(discord.ui.TextDisplay(f"{idx}. `{filename}`"), accessory=cog_btn))


        if total_pages > 1:
            nav_row = discord.ui.ActionRow()

            left_btn = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.primary, disabled=(self.page <= 1))
            left_btn.callback = self.prev_page
            nav_row.add_item(left_btn)

            go_btn = discord.ui.Button(label=f"Page {self.page} of {total_pages}", style=discord.ButtonStyle.secondary)
            go_btn.callback = self.go_to_page_callback
            nav_row.add_item(go_btn)

            right_btn = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.primary,
                                          disabled=(self.page >= total_pages))
            right_btn.callback = self.next_page
            nav_row.add_item(right_btn)
            container.add_item(discord.ui.Separator())
            container.add_item(nav_row)

        container.add_item(discord.ui.Separator())

        sync_btn = discord.ui.Button(label="Sync Slash Global", style=discord.ButtonStyle.primary)
        sync_local_btn = discord.ui.Button(label="Sync Slash Guild", style=discord.ButtonStyle.primary)
        force_sync_btn = discord.ui.Button(label="Force Sync", style=discord.ButtonStyle.secondary)
        reload_btn = discord.ui.Button(label="Reload All Cogs", style=discord.ButtonStyle.primary)
        upload_btn = discord.ui.Button(label="Upload Cog", style=discord.ButtonStyle.success,
                                       disabled=True if self.ephemeral else False)
        shutdown_btn = discord.ui.Button(label="Shutdown", style=discord.ButtonStyle.danger)
        restart_btn = discord.ui.Button(label="Restart", style=discord.ButtonStyle.danger)
        log_btn = discord.ui.Button(label="Show Log", style=discord.ButtonStyle.secondary)

        sync_btn.callback = self.sync_callback
        sync_local_btn.callback = self.sync_local_callback
        force_sync_btn.callback = self.force_sync_callback
        reload_btn.callback = self.reload_all_callback
        upload_btn.callback = self.upload_cog_callback
        shutdown_btn.callback = self.shutdown_callback
        restart_btn.callback = self.restart_callback
        log_btn.callback = self.show_log_callback

        action_row = discord.ui.ActionRow()
        action_row.add_item(sync_btn)
        action_row.add_item(sync_local_btn)
        action_row.add_item(force_sync_btn)
        if not self.secure_mode:
            action_row.add_item(log_btn)
        container.add_item(action_row)

        action_row = discord.ui.ActionRow()
        if not self.secure_mode:
            action_row.add_item(upload_btn)
        action_row.add_item(reload_btn)
        if not self.secure_mode:
            action_row.add_item(shutdown_btn)
            action_row.add_item(restart_btn)

        container.add_item(action_row)
        if not self.secure_mode and self.ephemeral:
            container.add_item(discord.ui.TextDisplay(
                "-# For Beacon's Upload Cog feature to function, please run the `/od` command in a server where your bot is present or in the bot's own DMs and not any other DM, with the ephemeral mode set to False."))
        self.add_item(container)

    def create_toggle_callback(self, ext_name, is_loaded):
        """Create a button callback that loads or unloads one extension.

        Args:
            ext_name: Extension module path to toggle.
            is_loaded: Whether the extension is currently loaded.

        Returns:
            Any: Result produced by this function.
        """

        async def callback(interaction: discord.Interaction):
            """Toggle extension state and refresh the dashboard message.

            Args:
                interaction: Interaction context received from Discord.

            Returns:
                Any: Result produced by this function.
            """
            await interaction.response.defer()
            try:
                if is_loaded:
                    await self.bot.unload_extension(ext_name)
                else:
                    await self.bot.load_extension(ext_name)
                self.build_layout()

                if interaction.message:
                    await interaction.message.edit(view=self)

            except Exception as e:
                await interaction.followup.send(f"Error: {e}", ephemeral=True)

        return callback

    async def prev_page(self, interaction: discord.Interaction):
        """Move to the previous dashboard page and redraw controls.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        self.page -= 1
        self.build_layout()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        """Move to the next dashboard page and redraw controls.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        self.page += 1
        self.build_layout()
        await interaction.response.edit_message(view=self)

    async def go_to_page_callback(self, interaction: discord.Interaction):
        """Open a modal that lets the owner jump to a specific page.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        cogs_dir = os.path.join(os.getcwd(), "cogs")
        cog_files = [f for f in os.listdir(cogs_dir) if f.endswith(".py") and not f.startswith("__")] if os.path.exists(
            cogs_dir) else []
        total_pages = (len(cog_files) + self.items_per_page - 1) // self.items_per_page
        await interaction.response.send_modal(OwnerGoToPageModal(self.bot, self, total_pages))

    async def upload_cog_callback(self, interaction: discord.Interaction):
        """Enable a timed upload window so the owner can send a cog file via Discord.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        if self._upload_in_progress:
            await interaction.response.send_message(
                # pyrefly: ignore [missing-attribute]
                f"[`{self.bot.instance_id}`] Beacon: An upload is already in progress.",
                ephemeral=True,
            )
            return

        self._upload_in_progress = True
        dashboard_message: Message | None = interaction.message

        try:
            await interaction.response.defer(ephemeral=self.ephemeral)
            upload_message = await interaction.followup.send(
                self.UPLOAD_MODE_MESSAGE,
                ephemeral=self.ephemeral,
                wait=True,
            )

            def upload_check(message: discord.Message) -> bool:
                return (
                        message.author.id == self.user.id
                        and message.channel.id == interaction.channel_id
                        and len(message.attachments) > 0
                )

            try:
                owner_message = await self.bot.wait_for(
                    "message", check=upload_check, timeout=60.0
                )
            except asyncio.TimeoutError:
                # pyrefly: ignore [missing-attribute]
                await upload_message.edit(
                    # pyrefly: ignore [missing-attribute]
                    content=f"[`{self.bot.instance_id}`] Beacon: Upload timed out. No file received within 60 seconds.")
                if not self.ephemeral:
                    await asyncio.sleep(5.0)
                    try:
                        await upload_message.delete()
                    except discord.Forbidden or discord.NotFound:
                        pass
                return

            filename = owner_message.content.strip()
            if not filename:
                # pyrefly: ignore [missing-attribute]
                await upload_message.edit(
                    # pyrefly: ignore [missing-attribute]
                    content=f"[`{self.bot.instance_id}`] Beacon: ERROR: Enter a filename (e.g. `moderation.py`) in your message.")
                return

            if os.path.basename(filename) != filename or ".." in filename:
                # pyrefly: ignore [missing-attribute]
                await upload_message.edit(content=f"[`{self.bot.instance_id}`] Beacon: ERROR: Invalid filename.")
                return

            if not filename.endswith(".py") or filename.startswith("__"):
                # pyrefly: ignore [missing-attribute]
                await upload_message.edit(
                    # pyrefly: ignore [missing-attribute]
                    content=f"[`{self.bot.instance_id}`] Beacon: ERROR: Filename must end with `.py` and cannot start with `__`.")
                return

            cogs_path = getattr(self.bot, "cogs_path", "cogs")
            cogs_dir = cogs_path if os.path.isabs(cogs_path) else os.path.join(os.getcwd(), cogs_path)
            os.makedirs(cogs_dir, exist_ok=True)

            file_path = os.path.join(cogs_dir, filename)
            await owner_message.attachments[0].save(Path(file_path))

            await upload_message.edit(content="File successfully uploaded!")
            await owner_message.delete()
            self.build_layout()
            if not dashboard_message is None:
                await dashboard_message.edit(view=self)

            if not self.ephemeral:
                await asyncio.sleep(5)
                await upload_message.delete()
        except Exception as e:
            if interaction.response.is_done():
                # pyrefly: ignore [missing-attribute]
                await interaction.followup.send(f"[`{self.bot.instance_id}`] Beacon: ERROR: {e}", ephemeral=True)
            else:
                # pyrefly: ignore [missing-attribute]
                await interaction.response.send_message(f"[`{self.bot.instance_id}`] Beacon: ERROR: {e}",
                                                        ephemeral=True)
        finally:
            self._upload_in_progress = False

    async def reload_all_callback(self, interaction: discord.Interaction):
        """Reload all non-internal extensions and report successes and failures.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.defer(ephemeral=True)
        extensions = list(self.bot.extensions.keys())
        reloaded, failed = [], []
        internal_extensions = ("beacon.ext.diagnostics", "beacon.ext.pic")
        for ext in extensions:
            if ext not in internal_extensions:
                try:
                    await self.bot.reload_extension(ext)
                    reloaded.append(ext)
                except Exception as e:
                    failed.append(f"{ext} ({e})")
        # pyrefly: ignore [missing-attribute]
        status = f"[`{self.bot.instance_id}`] Beacon: Reloaded {len(reloaded)} cogs."
        if failed: status += f"\n**Failed:** {', '.join(failed)}"
        await interaction.followup.send(status, ephemeral=True)

    async def sync_callback(self, interaction: discord.Interaction):
        """Run global smart sync for the app-command tree.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        # pyrefly: ignore [missing-attribute]
        await interaction.response.send_message(
            # pyrefly: ignore [missing-attribute]
            f"[`{self.bot.instance_id}`] Beacon: Syncing Slash commands, Please wait. This may take a while if you already synced recently due to Discord rate-limiting the bot.",
            ephemeral=True)
        response = await self.registry.smart_sync(guild=None)
        try:
            await interaction.edit_original_response(content=response)
        except discord.Forbidden or discord.NotFound:
            pass

    async def sync_local_callback(self, interaction: discord.Interaction):
        """Run guild-scoped smart sync for the current server.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        # pyrefly: ignore [missing-attribute]
        await interaction.response.send_message(
            # pyrefly: ignore [missing-attribute]
            f"[`{self.bot.instance_id}`] Beacon: Syncing Slash commands, Please wait. This may take a while if you already synced recently due to Discord rate-limiting the bot.",
            ephemeral=True)
        response = await self.registry.smart_sync(guild=None)
        try:
            await interaction.edit_original_response(content=response)
        except discord.Forbidden or discord.NotFound:
            pass

    async def force_sync_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            # pyrefly: ignore [missing-attribute]
            f"[`{self.bot.instance_id}`] Beacon: Syncing Slash commands using Beacon Framework's `force_sync` method which forces a sync regardless of whether there is a change detected or not, Please wait. This may take a while if you already synced recently due to Discord rate-limiting the bot.",
            ephemeral=True)
        response = await self.registry.force_sync(guild=interaction.guild)
        try:
            await interaction.edit_original_response(content=response)
        except discord.Forbidden or discord.NotFound:
            pass

    async def shutdown_callback(self, interaction: discord.Interaction):
        """Acknowledge and trigger a graceful bot shutdown.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.send_message("Beacon: Shutting down...", ephemeral=True)
        # pyrefly: ignore [missing-attribute]
        await self.bot.signal_handler()

    async def restart_callback(self, interaction: discord.Interaction):
        """Acknowledge and trigger a full bot process restart.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.send_message("Beacon: Restarting process...", ephemeral=True)
        # pyrefly: ignore [missing-attribute]
        await self.bot.restart_bot()

    async def show_log_callback(self, interaction: discord.Interaction):
        """Send the most recent log output to the owner safely.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        log_path = os.path.join(os.getcwd(), "discord.log")

        for handler in logging.getLogger().handlers:
            handler.flush()

        if not os.path.exists(log_path):
            return await interaction.response.send_message(
                # pyrefly: ignore [missing-attribute]
                f"[`{self.bot.instance_id}`] Beacon: ERROR: Log file not found.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
                trailing_lines = all_lines[-70:] if len(all_lines) > 70 else all_lines
                text_content = "".join(trailing_lines)

                if not text_content.strip():
                    return await interaction.followup.send("Log file is empty.", ephemeral=True)

                if len(text_content) > 1900:
                    log_file = discord.File(
                        io.BytesIO(text_content.encode("utf-8")),
                        filename="tail_discord.log"
                    )
                    await interaction.followup.send(
                        # pyrefly: ignore [missing-attribute]
                        f"[`{self.bot.instance_id}`] Beacon: Last 70 lines exceed 1900 chars, sending snippet file:",
                        file=log_file,
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(f"### Last 70 Log Lines\n```\n{text_content}\n```", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                # pyrefly: ignore [missing-attribute]
                f"[`{self.bot.instance_id}`] Beacon: ERROR: Failed to read log: {e}",
                ephemeral=True
            )


class OwnerGoToPageModal(discord.ui.Modal):
    """Modal that asks the owner which dashboard page to open.

    """

    def __init__(self, bot, parent_view: OwnerDashboard, total_pages: int):
        """Initialize page-jump modal bounds and input field.

        Args:
            parent_view: Dashboard view that will be updated after submission.
            total_pages: Maximum number of available pages.
        """
        super().__init__(title="Jump to Page")
        self.bot = bot
        self.parent_view = parent_view
        self.total_pages = max(total_pages, 1)
        self.page_input = discord.ui.TextInput(
            label=f"Page Number (1-{self.total_pages})",
            placeholder="Enter a page number...",
            default=str(self.parent_view.page),
            min_length=1, max_length=5, required=True
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Validate modal input and update the dashboard to the requested page.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        try:
            page_num = int(self.page_input.value)
            if 1 <= page_num <= self.total_pages:
                self.parent_view.page = page_num
                self.parent_view.build_layout()
                await interaction.response.edit_message(view=self.parent_view)
            else:
                await interaction.response.send_message(
                    f"[`{self.bot.instance_id}`] Beacon: Enter a number between 1-{self.total_pages}.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(f"[`{self.bot.instance_id}`] Beacon: Invalid input.",
                                                    ephemeral=True)
