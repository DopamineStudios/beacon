from beacon.core import beacon_commands

## `timeparser.py` Documentation

The `timeparser.py` utility provides functions for converting human-readable duration strings into integer seconds and calculating future Unix timestamps. This is primarily used for features requiring time offsets, such as temporary bans, reminders, or mute durations.

---

### Functions

#### 1. `duration_to_seconds(duration_str: str) -> int`

Parses a string containing time units and returns the total duration in seconds.

* **Supported Units:**
* `mon`: Months (calculated as 30 days / 2,592,000 seconds for simplicity's sake)
* `w`: Weeks
* `d`: Days
* `h`: Hours
* `m`: Minutes
* `s`: Seconds
**Example Usage:**

```python
from beacon import duration_to_seconds

# Single unit
seconds = duration_to_seconds("1h") 
# returns 3600

# Combined units with whitespace
seconds = duration_to_seconds("1d 2h 30m") 
# returns 95400

# Case-insensitivity
seconds = duration_to_seconds("1Mon 15S")
# returns 2592015
```
---

#### 2. `now_plus_seconds_unix(seconds: int) -> int`

Calculates a future timestamp by adding the provided number of seconds to the current UTC time.

* **Returns:** A Unix timestamp (integer).
* **Timezone:** Uses `timezone.utc` for calculation to ensure consistency across different host environments.

**Example Usage:**

```python
from beacon import duration_to_seconds, now_plus_seconds_unix

# Calculate a timestamp for 7 days from now
duration = duration_to_seconds("7d")
timestamp = now_plus_seconds_unix(duration)

print(timestamp) 
# returns 1715856000 (example value)
```

---

### Implementation Example (Timeout Command)

This utility is typically used within Discord commands to handle user input for durations.

```python
@beacon_commands.command(name="mute", description="Mute a user for a specific duration")
async def mute(interaction: discord.Interaction, user: discord.Member, duration: str):
    # Convert input like "1d 6h" to seconds
    seconds = duration_to_seconds(duration)
    
    if seconds <= 0:
        return await interaction.response.send_message("Invalid duration format.")

    # Get the Unix timestamp for the expiration
    expiry_timestamp = now_plus_seconds_unix(seconds)
    
    # Example: Applying the mute (logic depends on your implementation)
    await user.timeout(timedelta(seconds=seconds))
    
    await interaction.response.send_message(
        f"{user.mention} has been muted. Expires: <t:{expiry_timestamp}:R>"
    )
```