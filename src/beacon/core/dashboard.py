import os
import sys
import discord
import signal
import asyncio
from typing import TYPE_CHECKING
from ..bot import Bot
from ..core.commands_registry import CommandRegistry
import logging
import io

if TYPE_CHECKING:
    from discord.ext import commands

class PrivateLayoutView(discord.ui.LayoutView):
    """Base layout view that restricts interactions to one authorized user.

    """
    def __init__(self, user: discord.User, *args, **kwargs):
        """Initialize a restricted layout view for the provided user.

        Args:
            user: User that is allowed to interact with this flow.
            *args: Additional positional arguments forwarded to the parent implementation.
            **kwargs: Additional keyword arguments forwarded to the underlying API.
        """
        super().__init__(*args, **kwargs)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Reject interactions from users other than the dashboard owner.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            bool: True when the check passes.
        """
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This isn't for you!",
                ephemeral=True
            )
            return False
        return True

class OwnerDashboard(PrivateLayoutView):
    """Interactive owner dashboard for extension control and sync operations.

    """
    def __init__(self, bot: 'commands.Bot', user: discord.User, page: int = 1):
        """Initialize owner dashboard state and build the first layout.

        Args:
            bot: Bot instance that owns this object or callback.
            user: User that is allowed to interact with this flow.
            page: Initial dashboard page index (1-based).
        """
        super().__init__(user, timeout=None)
        self.bot = bot
        self.page = page
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
        container.add_item((discord.ui.TextDisplay("## Beacon Owner Dashboard")))
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
            container.add_item(discord.ui.TextDisplay("*No extensions found in /cogs.*"))
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

            container.add_item(discord.ui.TextDisplay(f"-# Page {self.page} of {total_pages}"))

        if total_pages > 1:
            nav_row = discord.ui.ActionRow()

            left_btn = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.primary, disabled=(self.page <= 1))
            left_btn.callback = self.prev_page
            nav_row.add_item(left_btn)

            go_btn = discord.ui.Button(label="Go To Page", style=discord.ButtonStyle.secondary)
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
        reload_btn = discord.ui.Button(label="Reload All Cogs", style=discord.ButtonStyle.primary)
        shutdown_btn = discord.ui.Button(label="Shutdown", style=discord.ButtonStyle.danger)
        restart_btn = discord.ui.Button(label="Restart", style=discord.ButtonStyle.danger)
        log_btn = discord.ui.Button(label="Show Log", style=discord.ButtonStyle.secondary)

        sync_btn.callback = self.sync_callback
        sync_local_btn.callback = self.sync_local_callback
        reload_btn.callback = self.reload_all_callback
        shutdown_btn.callback = self.shutdown_callback
        restart_btn.callback = self.restart_callback
        log_btn.callback = self.show_log_callback

        action_row = discord.ui.ActionRow()
        action_row.add_item(sync_btn)
        action_row.add_item(sync_local_btn)
        action_row.add_item(log_btn)
        container.add_item(action_row)

        action_row = discord.ui.ActionRow()
        action_row.add_item(reload_btn)
        action_row.add_item(shutdown_btn)
        action_row.add_item(restart_btn)

        container.add_item(action_row)
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
            try:
                if is_loaded:
                    await self.bot.unload_extension(ext_name)
                else:
                    await self.bot.load_extension(ext_name)
                self.build_layout()
                await interaction.response.edit_message(view=self)
            except Exception as e:
                await interaction.response.send_message(f"Error: {e}", ephemeral=True)
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
        cog_files = [f for f in os.listdir(cogs_dir) if f.endswith(".py") and not f.startswith("__")] if os.path.exists(cogs_dir) else []
        total_pages = (len(cog_files) + self.items_per_page - 1) // self.items_per_page
        await interaction.response.send_modal(OwnerGoToPageModal(self, total_pages))

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
        status = f"Beacon: Reloaded {len(reloaded)} cogs."
        if failed: status += f"\n**Failed:** {', '.join(failed)}"
        await interaction.followup.send(status, ephemeral=True)

    async def sync_callback(self, interaction: discord.Interaction):
        """Run global smart sync for the app-command tree.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.defer()
        response = await self.registry.smart_sync(guild=None)
        await interaction.followup.send(response, ephemeral=True)

    async def sync_local_callback(self, interaction: discord.Interaction):
        """Run guild-scoped smart sync for the current server.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.defer()
        response = await self.registry.smart_sync(guild=interaction.guild)
        await interaction.followup.send(response, ephemeral=True)


    async def shutdown_callback(self, interaction: discord.Interaction):
        """Acknowledge and trigger a graceful bot shutdown.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.send_message("Beacon: Shutting down...", ephemeral=True)
        await self.bot.signal_handler()

    async def restart_callback(self, interaction: discord.Interaction):
        """Acknowledge and trigger a full bot process restart.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.send_message("Beacon: Restarting process...", ephemeral=True)
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
                "Beacon: ERROR: Log file not found.",
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
                        "Beacon: Last 70 lines exceed 1900 chars, sending snippet file:",
                        file=log_file,
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(f"### Last 70 Log Lines\n```\n{text_content}\n```", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                f"Beacon: ERROR: Failed to read log: {e}",
                ephemeral=True
            )

class OwnerGoToPageModal(discord.ui.Modal):
    """Modal that asks the owner which dashboard page to open.

    """
    def __init__(self, parent_view: OwnerDashboard, total_pages: int):
        """Initialize page-jump modal bounds and input field.

        Args:
            parent_view: Dashboard view that will be updated after submission.
            total_pages: Maximum number of available pages.
        """
        super().__init__(title="Jump to Page")
        self.parent_view = parent_view
        self.total_pages = max(total_pages, 1)
        self.page_input = discord.ui.TextInput(
            label=f"Page Number (1-{self.total_pages})",
            placeholder="Enter a page number...",
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
                await interaction.response.send_message(f"Enter a number between 1-{self.total_pages}.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Invalid input.", ephemeral=True)