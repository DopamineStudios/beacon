## `views.py` Documentation

The `views.py` utility provides subclasses or wrappers of `discord.ui.View` and `discord.ui.LayoutView` that restrict interaction to a specific user and doesn't let anyone use the interaction (buttons, dropdowns, etc.) other than the person who triggered the command or interaction.

---

### PrivateView

Use `PrivateView` for classes that inherit from `discord.ui.View` (Traditional embeds-with-buttons).

**Usage:**

```python
from beacon import PrivateView
import discord

class MyPersistentView(PrivateView):
    def __init__(self, user):
        super().__init__(user=user, timeout=None)
    @discord.ui.button(label="Click Me", style=discord.ButtonStyle.primary)
    async def my_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You clicked the button!")

# To use in a command:
@tree.command(name="private-button")
async def private_button(interaction: discord.Interaction):
    view = MyPersistentView(user=interaction.user)
    await interaction.response.send_message("Only you can use this:", view=view)
```

---

### PrivateLayoutView

Use `PrivateLayoutView` when working with classes that inherit from `discord.ui.LayoutView` (Components V2).

**Usage:**

```python
import discord.ui
from beacon import PrivateLayoutView


class MyLayout(PrivateLayoutView):
    def __init__(self, user):
        super().__init__(user=user, timeout=None)
        self.build_container()

    def build_container(self):
        container = discord.ui.Container()
        
        my_button = discord.ui.Button(label="Click Me", style=discord.ButtonStyle.primary)
        my_button.callback = my_button
        
        container.add_item(discord.ui.ActionRow(my_button))
        
        self.add_item(container)
        
    async def my_button(self, interaction: discord.Interaction):
        await interaction.response.send_message("You clicked the button!")

# To use in a command:
@tree.command(name="private-button")
async def private_button(interaction: discord.Interaction):
    view = MyLayout(user=interaction.user)
    await interaction.response.send_message("Only you can use this:", view=view)
```

---


### Parameters

| Parameter | Type           | Description                                                                                                                                                                                                           |
| --- |----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `user` | `discord.User` | The user who triggered the internation. IMPORTANT: This is a required perimeter for the Private Views to function. Your bot will crash if you don't pass internaction.user into the function as shown in the example. |
| `*args` / `**kwargs` | -              | Standard `discord.ui.View` arguments (e.g., `timeout`).                                                                                                                                                               |