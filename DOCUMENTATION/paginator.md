
## `paginator.py` Documentation

The `paginator.py` module contains two primary classes for handling list-based data within Discord interactions.

### 1. ViewPaginator

A standard interface for paginating data using a `discord.ui.View`.

**Parameters**

* `data` (List[Any]): The collection of items to paginate.
* `per_page` (int): Number of items displayed per page. Defaults to `10`.
* `timeout` (int): View expiration in seconds. Defaults to `120`.

**Methods**

* `get_current_page_data()`: Slices `self.data` based on `self.page` and `self.per_page`.
* `update_view(interaction)`: Edits the message to update the current view state.

**Usage**

```python
from beacon import ViewPaginator

# Example: Displaying a list of strings
data = [f"Item {i}" for i in range(1, 101)]
view = ViewPaginator(data=data, per_page=10)
current_data = view.get_current_page_data()
await interaction.response.send_message("\n".join(current_data), view=view)
```

---

### 2. LayoutViewPaginator

An implementation using `discord.ui.LayoutView`. This class enforces a user check and provides a method for building structured UI containers.

**Parameters**

* `user` (discord.User): The user authorized to interact with the pagination components.
* `data` (List[Any]): The collection of items to paginate.
* `per_page` (int): Number of items displayed per page. Defaults to `5`.

**Interface Methods**

* `add_pagination_controls(container)`: Appends a text indicator and a `discord.ui.ActionRow` containing navigation buttons to the provided `Container`.
* `update_view(interaction)`: Executes `self.build_layout()` and edits the message.

**Implementation Requirement**
Developers using `LayoutViewPaginator` must define `build_layout()` in a subclass to specify how items and pagination controls are arranged.

**Usage**

```python
from beacon import LayoutViewPaginator
from discord.ui import Container

class MyPaginator(LayoutViewPaginator):
    def build_layout(self):
        self.clear_items()
        container = Container()
        self.add_pagination_controls(container)
        self.add_item(container)

view = MyPaginator(user=interaction.user, data=my_list)
view.build_layout()
await interaction.response.send_message(view=view)
```

---

### 3. GoToPageModal

Both paginator classes utilize `GoToPageModal` via their "Go to Page" buttons.

* **Input**: A `TextInput` field limited to the character length of the maximum page number.
* **Logic**: Validates that the input is an integer within the range of  and `total_pages`.
* **Action**: On valid submission, updates `parent.page` and calls `parent.update_view()`.
u like me to generate a standalone script demonstrating a full integration of `LayoutViewPaginator` with an Embed?