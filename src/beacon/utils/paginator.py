import discord
from discord.ui import View, LayoutView, Container, ActionRow, Button, TextDisplay, Section, Separator, Modal, TextInput
from typing import List, Any, Callable


class GoToPageModal(Modal):
    """Modal that prompts the user for a page number to navigate to.

    """
    def __init__(self, parent_paginator: Any, max_pages: int):
        """Initialize modal state for page-jump validation and defaults.

        Args:
            parent_paginator: Paginator view that owns this modal.
            max_pages: Maximum allowed page number.
        """
        super().__init__(title="Go to Page")
        self.parent = parent_paginator
        self.max_pages = max_pages
        self.page_input = TextInput(
            label=f"Enter Page Number (between 1 and {max_pages})",
            default=str(self.parent.page),
            min_length=1,
            max_length=len(str(max_pages))
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Validate page input and update the parent paginator when valid.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        try:
            page_num = int(self.page_input.value)
            if 1 <= page_num <= self.max_pages:
                self.parent.page = page_num
                await self.parent.update_view(interaction)
            else:
                await interaction.response.send_message(f"Please enter a number between 1 and {self.max_pages}.",
                                                        ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Invalid number entered.", ephemeral=True)


class ViewPaginator(discord.ui.View):
    """Button-driven embed paginator for simple list-style page navigation.

    """
    def __init__(
            self,
            title: str,
            data: List[str],
            per_page: int = 10,
            color: discord.Color = discord.Color.blue(),
            timeout: int = 120
    ):
        """Initialize paginator state, paging limits, and button states.

        Args:
            title: Embed title shown on each page.
            data: Collection of items that will be paginated.
            per_page: Number of entries shown per page.
            color: Embed color used for the paginator output.
            timeout: View timeout in seconds.
        """
        super().__init__(timeout=timeout)
        self.title = title
        self.data = data
        self.per_page = per_page
        self.color = color

        self.page = 1
        self.total_pages = (len(self.data) - 1) // per_page + 1 if data else 1

        self.update_button_states()

    def update_button_states(self):
        """Enable or disable navigation buttons for the current page.

        Returns:
            Any: Result produced by this function.
        """
        self.prev_page.disabled = (self.page == 1)
        self.next_page.disabled = (self.page == self.total_pages)
        self.go_to_page.disabled = (self.total_pages <= 1)

    def format_embed(self) -> discord.Embed:
        """Build the embed for the current data slice and page footer.

        Returns:
            Any: Formatted embed value.
        """
        start = (self.page - 1) * self.per_page
        end = start + self.per_page
        current_chunk = self.data[start:end]

        description = "\n".join(current_chunk) if current_chunk else "No data available."

        embed = discord.Embed(
            title=self.title,
            description=description,
            color=self.color
        )
        embed.set_footer(text=f"Page {self.page} of {self.total_pages}")
        return embed

    async def update_view(self, interaction: discord.Interaction):
        """Refresh the paginator message after a page change.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        self.update_button_states()
        await interaction.response.edit_message(embed=self.format_embed(), view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Move one page backward when previous data exists.

        Args:
            interaction: Interaction context received from Discord.
            button: Button that triggered the callback.

        Returns:
            Any: Result produced by this function.
        """
        if self.page > 1:
            self.page -= 1
            await self.update_view(interaction)

    @discord.ui.button(label="Go To Page", style=discord.ButtonStyle.gray)
    async def go_to_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open the page-jump modal for direct navigation.

        Args:
            interaction: Interaction context received from Discord.
            button: Button that triggered the callback.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.send_modal(GoToPageModal(self, self.total_pages))

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Move one page forward when additional data exists.

        Args:
            interaction: Interaction context received from Discord.
            button: Button that triggered the callback.

        Returns:
            Any: Result produced by this function.
        """
        if self.page < self.total_pages:
            self.page += 1
            await self.update_view(interaction)


class LayoutViewPaginator(LayoutView):
    """Layout-based paginator scaffold for richer, custom paged interfaces.

    """
    def __init__(self, user: discord.User, data: List[Any], per_page: int = 5):
        """Initialize pagination state and user ownership for interactions.

        Args:
            user: User that is allowed to interact with this flow.
            data: Collection of items that will be paginated.
            per_page: Number of entries shown per page.
        """
        super().__init__(timeout=None)
        self.user = user
        self.data = data
        self.page = 1
        self.per_page = per_page
        self.total_pages = (len(data) - 1) // per_page + 1 if data else 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Reject interactions from users other than the view owner.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            bool: True when the check passes.
        """
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This isn't for you!", ephemeral=True)
            return False
        return True

    def get_current_page_data(self):
        """Return the data subset that should be shown on the current page.

        Returns:
            Any: Current page data.
        """
        start = (self.page - 1) * self.per_page
        return self.data[start: start + self.per_page]

    async def update_view(self, interaction: discord.Interaction):
        """Rebuild the layout and edit the message with updated controls.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        self.build_layout()
        await interaction.response.edit_message(view=self)

    def add_pagination_controls(self, container: Container):
        """Attach page indicators and navigation controls to a container.

        Args:
            container: Layout container that receives pagination controls.

        Returns:
            Any: Result produced by this function.
        """
        container.add_item(TextDisplay(f"-# Page {self.page} of {self.total_pages}"))
        container.add_item(Separator())

        row = ActionRow()

        left_btn = Button(emoji="◀️", style=discord.ButtonStyle.primary, disabled=self.page == 1)
        left_btn.callback = self.prev_callback

        go_btn = Button(label="Go to Page", style=discord.ButtonStyle.secondary, disabled=self.total_pages <= 1)
        go_btn.callback = self.goto_callback

        right_btn = Button(emoji="▶️", style=discord.ButtonStyle.primary, disabled=self.page == self.total_pages)
        right_btn.callback = self.next_callback

        row.add_item(left_btn)
        row.add_item(go_btn)
        row.add_item(right_btn)
        container.add_item(row)

    async def prev_callback(self, interaction: discord.Interaction):
        """Go to the previous page and refresh the layout.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        self.page -= 1
        await self.update_view(interaction)

    async def next_callback(self, interaction: discord.Interaction):
        """Go to the next page and refresh the layout.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        self.page += 1
        await self.update_view(interaction)

    async def goto_callback(self, interaction: discord.Interaction):
        """Open the page-jump modal for layout paginator navigation.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.send_modal(GoToPageModal(self, self.total_pages))