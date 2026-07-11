## `paginator.py` Documentation

The `paginator.py` module contains two primary classes for handling list-based data within Discord interactions.

### 1. ViewPaginator

A standard interface for paginating data using a `discord.ui.View` that outputs content inside a standard `discord.Embed` layout.

**Parameters**

* `user` (`discord.User | discord.Member`): The user authorised to interact with the view.


* `title` (`str`): The title displayed at the top of the embed.


* `data` (`List[str]`): The collection of string items to paginate.


* `per_page` (`int`): Number of items displayed per page. Defaults to `10`.


* `colour` (`discord.Colour`): The colour theme of the embed layout. Defaults to `discord.Colour.blue()`.


* `timeout` (`int`): View expiration in seconds. Defaults to `120`.



**Methods**

* `format_embed()`: Builds and returns the `discord.Embed` matching the current page's slice of data.


* `update_view(interaction)`: Modifies the original message with the recalculated embed and button states.



**Usage**

```python
from beacon import ViewPaginator

data = [f"Item {i}" for i in range(1, 101)]
view = ViewPaginator(user=interaction.user, title="My List", data=data, per_page=10)
await interaction.response.send_message(embed=view.format_embed(), view=view)

```

---

### 2. LayoutViewPaginator

An all-in-one implementation using `discord.ui.LayoutView`. This class constructs its data rows, separators, title, and buttons natively into UI layout containers without requiring external embeds or custom subclasses.

**Parameters**

* `user` (`discord.User | discord.Member`): The user authorised to interact with the pagination components.


* `title` (`str`): The header text rendered at the top of the UI layout container.


* `data` (`List[Any]`): The collection of items to paginate.


* `per_page` (`int`): Number of items displayed per page. Defaults to `5`.


* `timeout` (`int`): View expiration in seconds. Defaults to `120`.



**Methods**

* `build_layout()`: Automatically clears existing items and handles the structural generation of `Container`, `Section`, `TextDisplay`, and `ActionRow` objects to display both text data and navigation buttons simultaneously. Called automatically on initialisation.


* `get_current_page_data()`: Obtains the specific data subset intended for the current page layout.


* `update_view(interaction)`: Rebuilds the core layout elements and edits the active interaction message.



**Usage**

```python
from beacon import LayoutViewPaginator

my_list = [f"Data Entry {i}" for i in range(1, 26)]

# Instantiating automatically renders the initial layout and controls
view = LayoutViewPaginator(user=interaction.user, title="System Metrics", data=my_list, per_page=5)
await interaction.response.send_message(view=view)

```

---

### 3. GoToPageModal

Both paginator classes utilise `GoToPageModal` via their "Go to Page" buttons to jump directly to specific entries.

* **Input**: A `TextInput` field dynamically sized to match the maximum page number string length.


* **Logic**: Validates that the input is a valid integer string falling securely between `1` and `total_pages`.


* **Action**: Updates the primary page position tracker on the parent paginator object and triggers `parent.update_view()`.