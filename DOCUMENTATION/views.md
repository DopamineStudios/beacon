from beacon.core import beacon_commands

## `views.py` Documentation

The `views.py` utility provides subclasses or wrappers of `discord.ui.View` and `discord.ui.LayoutView` that restrict interaction to a specific user and doesn't let anyone use the interaction (buttons, dropdowns, etc.) other than the person who triggered the command or interaction, and provides Confirmation Views that trigger a given callback upon confirmation.

---

### PrivateLayoutView

Use `PrivateLayoutView` when working with classes that inherit from `discord.ui.LayoutView` (Components V2).

**Usage:**

```python
import discord.ui
from beacon import PrivateLayoutView, beacon_commands


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
@beacon_commands.command(name="private-button")
async def private_button(interaction: discord.Interaction):
    view = MyLayout(user=interaction.user)
    await interaction.response.send_message("Only you can use this:", view=view)
```

---

### PrivateView

Use `PrivateView` for classes that inherit from `discord.ui.View` (Traditional embeds-with-buttons).

**Usage:**

```python
from beacon import PrivateView, beacon_commands
import discord

class MyPersistentView(PrivateView):
    def __init__(self, user):
        super().__init__(user=user, timeout=None)
    @discord.ui.button(label="Click Me", style=discord.ButtonStyle.primary)
    async def my_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You clicked the button!")

# To use in a command:
@beacon_commands.command(name="private-button")
async def private_button(interaction: discord.Interaction):
    view = MyPersistentView(user=interaction.user)
    await interaction.response.send_message("Only you can use this:", view=view)
```

---

### Private View Parameters

|       Parameter       |       Type       |                                                                                                       Description                                                                                                       |
|:---------------------:|:----------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|        `user`         |  `discord.User`  |  The user who triggered the internation. IMPORTANT: This is a required perimeter for the Private Views to function. Your bot will crash if you don't pass internaction.user into the function as shown in the example.  |
| `*args` / `**kwargs`  |        -         |                                                                                 Standard `discord.ui.View` arguments (e.g., `timeout`).                                                                                 |

---

### ConfirmationView

A ready-made, layout-based confirmation dialog that builds a structured interface complete with a custom title, body text, and automatically handled success/failure states. It executes a custom callback function when the user selects "Confirm".

**Usage:**

```python
from beacon import ConfirmationView, beacon_commands
import discord

async def process_purchase(item_id: int, user_id: int):
    # Your confirmation logic here
    print(f"Processing item {item_id} for user {user_id}")

@beacon_commands.command(name="buy-item")
async def buy_item(interaction: discord.Interaction, item_id: int):
    view = ConfirmationView(
        user=interaction.user,
        timeout=30.0,
        title_text="Confirm Purchase",
        body_text=f"Are you sure you want to buy item #{item_id}?",
        on_confirmation_callback=process_purchase,
        item_id=item_id,       # Forwarded to process_purchase
        user_id=interaction.user.id  # Forwarded to process_purchase
    )
    
    await interaction.response.send_message("Please confirm your action:", view=view)
    view.message = await interaction.original_response()

```

---

### DestructiveConfirmationView

Operates identically to `ConfirmationView`, but styles the "Confirm" button with `discord.ButtonStyle.danger` (red) instead of green. Use this to warn users before performing irreversible or sensitive actions like deletions, bans, or data resets, or when the UI leading up to your confirmation view makes the user press a big red button for UI colour consistency.

**Usage:**

```python
from beacon import DestructiveConfirmationView
import discord

async def purge_data():
    pass

@beacon_commands.command(name="wipe-profile")
async def wipe_profile(interaction: discord.Interaction):
    view = DestructiveConfirmationView(
        user=interaction.user,
        title_text="Wipe Profile Data",
        body_text="This action is permanent. All your data will be cleared.",
        on_confirmation_callback=purge_data
    )
    await interaction.response.send_message("⚠️ CRITICAL WARNING:", view=view)
    view.message = await interaction.original_response()

```

---

### Confirmation View Parameters

Both `ConfirmationView` and `DestructiveConfirmationView` accept the following additional parameters:

|          Parameter          |    Type     |                  Default                  |                                               Description                                               |
|:---------------------------:|:-----------:|:-----------------------------------------:|:-------------------------------------------------------------------------------------------------------:|
|          `timeout`          |   `float`   |                  `30.0`                   |              Time in seconds before the confirmation interaction automatically times out.               |
|        `title_text`         |    `str`    |         `"Pending Confirmation"`          |                        Header title text displayed at the top of the interface.                         |
|         `body_text`         |    `str`    | `"Click Confirm to confirm the action."`  |                               Main body description detailing the choice.                               |
| `on_confirmation_callback`  | `Callable`  |                  `None`                   |                                                 `None`                                                  | A synchronous or asynchronous function to execute when "Confirm" is successfully pressed. |
|    `*args` / `**kwargs`     |      -      |                     -                     | Extra positional and keyword arguments forwarded directly into your custom `on_confirmation_callback`.  |

